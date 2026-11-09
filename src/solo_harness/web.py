"""Participant-facing HTTP adapter for a trusted, single-participant installation."""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from solo_harness.config import Settings
from solo_harness.capture_gate import inspect_active_capture
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import (
    AssessmentInstance,
    ActiveStudyVersion,
    Attempt,
    IdempotencyRecord,
    LLMCall,
    Message,
    ProtocolEvent,
    Session,
    StudyVersion,
    SubsectionProgress,
)
from solo_harness.runtime.ai import AIExecutionRuntime, OpenAICompatibleClient
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.transition_summaries import post_pass_transition_summary
from solo_harness.teaching_render import render_tutor_markdown
from solo_harness.runtime.paas import instrument_snapshot
from solo_harness.runtime.v04_persistence import is_deliverable_f1, is_f1_frozen, is_f1_study, public_projection, submit_f1_response
from solo_harness.research_time import in_research_timezone
from solo_harness.telemetry import append_keyboard_batch, append_rrweb_batch, ensure_browser_manifest, record_ui_events

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.filters["tutor_markdown"] = render_tutor_markdown


def _v051_subsection_projection(compiled, attempt, progress_rows):
    """Participant-safe subsection labels from the persisted attempt ledger."""
    if not attempt or not SessionRuntime._v051(compiled):
        return []
    curriculum = compiled.authored["v051"]["scientific"]["curriculum.yaml"]
    titles = {item["id"]: item["title"] for item in curriculum["subsections"]}
    return [{"id": row.subsection_id, "title": titles[row.subsection_id],
             "order": row.order_in_attempt, "state": row.status}
            for row in sorted(progress_rows, key=lambda row: row.order_in_attempt)]


def _operation_refresh_required(pending, client_subsection_id, active_subsection_id):
    return not pending or client_subsection_id != active_subsection_id


def _internal_v051_access_enabled(settings, presented_token):
    configured = getattr(settings, "v051_internal_testing_token", None)
    return bool(getattr(settings, "enable_v051_internal_testing", False) and configured and presented_token
                and secrets.compare_digest(configured.get_secret_value(), presented_token))


class ParticipantApplication:
    """One browser-facing participant bound to one trusted app process at a time."""

    def __init__(self, catalog, settings: Settings, execution: AIExecutionRuntime | None = None):
        self.settings = settings
        self.factory = make_session_factory(settings.database_url)
        self.execution = execution or AIExecutionRuntime(SessionRuntime(catalog), OpenAICompatibleClient(settings), settings)

    def _active_capture_run_id(self, db) -> uuid.UUID | None:
        """Validate host recorder independently of candidate-study development mode."""
        capture_run_id, reason = inspect_active_capture(
            self.settings.research_data_dir,
            required_streams=self.settings.required_capture_streams,
            heartbeat_max_age_seconds=self.settings.active_capture_max_age_seconds,
        )
        if capture_run_id is None:
            logger.warning("Capture-required enrollment blocked: %s", reason)
            return None
        if db.scalar(select(Session.id).where(Session.capture_run_id == capture_run_id)):
            logger.warning("Capture-required enrollment blocked: capture run already assigned")
            return None
        return capture_run_id

    def activate(self, institutional_id: str) -> uuid.UUID | None:
        normalized = institutional_id.strip()
        if not normalized:
            return None
        with self.factory() as db:
            if db.scalar(select(Session.id).where(Session.institutional_id == normalized)):
                return None
            # Capture policy and candidate-study development mode are orthogonal.
            # Recorded development requires the same recorder marker as research.
            requires_capture = self.settings.require_active_capture
            capture_run_id = self._active_capture_run_id(db) if requires_capture else None
            if requires_capture and capture_run_id is None: return None
            active = db.scalar(select(ActiveStudyVersion).order_by(ActiveStudyVersion.activated_at.desc()))
            if active is None: return None
            compiled = self.execution.runtime.catalog.load(db, active.study_version_id)
            if compiled.authored.get("v051", {}).get("candidate_only"):
                return None
            # Candidate F1 v0.4 is development-only.  The source status is not
            # transformed by this switch; production startup fails closed.
            if (compiled.authored.get("v04") and not self.settings.enable_f1_v04_development):
                return None
            try:
                session = self.execution.runtime.create_session(
                    db, active.study_version_id,
                    build_id=self.settings.app_build_id,
                    institutional_id=normalized,
                    capture_run_id=capture_run_id,
                    runtime_config={
                        "f1_v04_development_enabled": self.settings.enable_f1_v04_development,
                        "capture_required_at_join": requires_capture,
                        "capture_required_streams": self.settings.required_capture_streams if requires_capture else "none",
                        "capture_heartbeat_max_age_seconds": self.settings.active_capture_max_age_seconds if requires_capture else None,
                    },
                    commit=False,
                )
                self.execution.runtime._event(db, session, "PARTICIPANT_ENTERED", {"entry_method": "INSTITUTIONAL_ID", "study_information_acknowledged": True}, session.current_attempt_id)
                db.commit()
            except IntegrityError:
                db.rollback()
                return None
            return session.id

    def deactivate(self, browser_session):
        active_session_id = self.require(browser_session)
        if active_session_id is not None:
            with self.factory() as db:
                session = db.get(Session, active_session_id)
                if session:
                    self.execution.runtime._event(db, session, "PARTICIPANT_EXITED", {}, session.current_attempt_id)
                    db.commit()
        browser_session.pop("participant_session_id", None)

    def require(self, browser_session) -> uuid.UUID | None:
        raw_id = browser_session.get("participant_session_id")
        if not raw_id:
            return None
        try: session_id=uuid.UUID(str(raw_id))
        except (ValueError, TypeError): return None
        with self.factory() as db:
            return session_id if db.get(Session, session_id) else None

    def _transition_ids(self, db, session: Session) -> list[str]:
        return list(self.execution.runtime._compiled(db, session).protocol["transition_ids"])

    def view(self, session_id, selected_section: int | None = None):
        """Build a participant-safe projection with no research-only fields."""
        with self.factory() as db:
            session = db.get(Session, session_id)
            if not session:
                return None
            compiled = self.execution.runtime._compiled(db, session)
            transition_ids = list(compiled.protocol["transition_ids"])
            f1_study = is_f1_study(compiled)
            v051_candidate = self.execution.runtime._v051(compiled)
            attempts = db.scalars(
                select(Attempt).where(Attempt.session_id == session.id).order_by(Attempt.assigned_at, Attempt.sequence_in_transition)
            ).all()
            attempts_by_transition: dict[str, list[Attempt]] = defaultdict(list)
            for attempt in attempts:
                attempts_by_transition[attempt.transition_id].append(attempt)
            assessments = db.scalars(
                select(AssessmentInstance).where(AssessmentInstance.session_id == session.id)
            ).all()
            assessments_by_attempt = {item.attempt_id: item for item in assessments}
            attempt_ids = [attempt.id for attempt in attempts]
            progress_by_attempt: dict[uuid.UUID, list[SubsectionProgress]] = defaultdict(list)
            if attempt_ids and v051_candidate:
                for progress in db.scalars(select(SubsectionProgress).where(SubsectionProgress.attempt_id.in_(attempt_ids))).all():
                    progress_by_attempt[progress.attempt_id].append(progress)
            messages = db.scalars(
                select(Message).where(Message.attempt_id.in_(attempt_ids)).order_by(Message.created_at, Message.sequence_no)
            ).all() if attempt_ids else []
            messages_by_attempt: dict[uuid.UUID, list[Message]] = defaultdict(list)
            for message in messages:
                messages_by_attempt[message.attempt_id].append(message)
            events = db.scalars(
                select(ProtocolEvent).where(ProtocolEvent.session_id == session.id).order_by(ProtocolEvent.sequence_no)
            ).all()
            completed_outcomes = {
                event.payload.get("transition_id"): event.payload.get("scientific_outcome")
                for event in events if event.event_type == "SECTION_COMPLETED" and event.payload.get("transition_id")
            }
            completed_transition_ids = set(completed_outcomes)
            # The recap is post-assessment material, authorized only by an
            # already-persisted SECTION_COMPLETED PASSED outcome. Never show it
            # on a failed attempt, administrative UNRESOLVED continuation, or
            # other study types. It is identical for all three pedagogies.

            if session.current_transition_id in transition_ids:
                current_index = transition_ids.index(session.current_transition_id)
            elif completed_transition_ids:
                current_index = max(transition_ids.index(item) for item in completed_transition_ids if item in transition_ids)
            else:
                current_index = 0
            requested_index = current_index if selected_section is None else selected_section - 1
            if requested_index < 0 or requested_index >= len(transition_ids) or requested_index > current_index:
                requested_index = current_index
            selected_transition_id = transition_ids[requested_index]
            is_current = requested_index == current_index

            sections = []
            for index, transition_id in enumerate(transition_ids):
                if transition_id in completed_transition_ids:
                    state = "unresolved" if completed_outcomes.get(transition_id) == "UNRESOLVED" else "completed"
                elif index == current_index and session.phase != "TERMINAL":
                    state = "current"
                elif index < current_index:
                    state = "completed"
                else:
                    state = "locked"
                sections.append({"number": index + 1, "state": state, "enabled": index <= current_index})

            current_attempt = db.get(Attempt, session.current_attempt_id) if session.current_attempt_id else None
            section_titles = {item["id"]: item["title"] for item in compiled.authored.get("v051", {}).get("scientific", {}).get("curriculum.yaml", {}).get("sections", [])}
            subsection_titles = {item["id"]: item["title"] for item in compiled.authored.get("v051", {}).get("scientific", {}).get("curriculum.yaml", {}).get("subsections", [])}
            timeline = []
            for attempt in attempts_by_transition[selected_transition_id]:
                timeline.append({
                    "kind": "activity",
                    "label": f"Teaching activity {attempt.sequence_in_transition}",
                    "activity_number": attempt.sequence_in_transition,
                    "timestamp": in_research_timezone(attempt.assigned_at),
                })
                marked_subsection = None
                for message in messages_by_attempt[attempt.id]:
                    subsection_id = (message.instructional_trace or {}).get("subsection_id") if v051_candidate else None
                    if subsection_id and subsection_id != marked_subsection:
                        timeline.append({"kind": "subsection", "label": f"{subsection_id} — {subsection_titles[subsection_id]}",
                                         "subsection_id": subsection_id})
                        marked_subsection = subsection_id
                    timeline.append({
                        "kind": "message",
                        "role": message.role,
                        "content": message.content_text,
                        "sequence_no": message.sequence_no,
                        "timestamp": in_research_timezone(message.created_at),
                    })
                assessment = assessments_by_attempt.get(attempt.id)
                if assessment and assessment.status == "CLOSED":
                    timeline.append({"kind": "assessment", "label": "Assessment completed", "timestamp": in_research_timezone(assessment.closed_at)})
            if selected_transition_id in completed_transition_ids:
                completed_event = next(
                    event for event in reversed(events)
                    if event.event_type == "SECTION_COMPLETED" and event.payload.get("transition_id") == selected_transition_id
                )
                outcome = completed_event.payload.get("scientific_outcome")
                timeline.append({"kind": "section", "label": "Section ended — transition unresolved" if outcome == "UNRESOLVED" else "Section completed", "timestamp": in_research_timezone(completed_event.occurred_at)})

            current_assessment = assessments_by_attempt.get(current_attempt.id) if current_attempt else None
            v051_subsections = _v051_subsection_projection(
                compiled, current_attempt, progress_by_attempt.get(current_attempt.id, []) if current_attempt and is_current else []
            )
            active_subsection = next((item for item in v051_subsections if item["state"] == "ACTIVE"), None)
            delivery_exception = any(item["state"] == "DELIVERY_EXCEPTION" for item in v051_subsections)
            latest = db.scalar(
                select(LLMCall).where(LLMCall.session_id == session.id).order_by(LLMCall.started_at.desc())
            )
            # Assessment construction is an orchestrated operation.  Its child
            # Writer/Reviewer rows are audit records, not the participant's
            # retry target; a successful child must not hide a failed parent.
            build = db.scalar(select(LLMCall).where(
                LLMCall.assessment_instance_id == current_assessment.id,
                LLMCall.purpose == "ASSESSMENT_BUILD",
            ).order_by(LLMCall.started_at.desc())) if current_assessment and current_assessment.status == "GENERATING" else None
            # Paas is a human-response gate, not an LLM operation. An older
            # failed Tutor call must never cover its form with a Retry panel.
            operation = None if session.phase in ("PAAS_PENDING", "SECTION_COMPLETE", "TERMINAL") else (build or latest)
            stale = bool(
                operation and operation.status in ("STARTED", "SENDING")
                and datetime.now(timezone.utc) - operation.started_at
                >= timedelta(seconds=self.settings.llm_request_timeout_seconds + self.settings.llm_stale_grace_seconds)
            )
            pending = bool(operation and operation.status in ("STARTED", "SENDING", "RECEIVED") and operation.error_class != "APPLICATION_FAILURE" and not stale)
            retryable = bool(operation and (operation.status in ("FAILED", "INVALID_OUTPUT") or operation.error_class in ("REVIEW_HOLD", "APPLICATION_FAILURE") or stale))
            technical_hold = bool(operation and operation.status == "TECHNICAL_HOLD")
            now = session.ended_at or datetime.now(timezone.utc)
            elapsed_seconds = max(0, int((now - session.started_at).total_seconds())) if session.started_at else 0

            return {
                "id": session.id,
                "phase": session.phase,
                "status": session.status,
                "section_number": requested_index + 1,
                "section_count": len(transition_ids),
                "section_title": section_titles.get(selected_transition_id),
                "sections": sections,
                "is_current": is_current,
                "is_read_only": not is_current or session.phase == "TERMINAL",
                "is_final_section": current_index == len(transition_ids) - 1,
                "section_scientific_outcome": completed_outcomes.get(selected_transition_id),
                "transition_summary": post_pass_transition_summary(
                    f1_v04=bool(f1_study and compiled.authored.get("v04")),
                    is_current=is_current,
                    phase=session.phase,
                    outcome=completed_outcomes.get(selected_transition_id),
                    transition_id=selected_transition_id,
                ),
                "timeline": timeline,
                "attempt_status": current_attempt.status if current_attempt and is_current else None,
                "paas_instrument": instrument_snapshot() if is_current and session.phase == "PAAS_PENDING" else None,
                "activity_number": current_attempt.sequence_in_transition if current_attempt and is_current else None,
                "v051_subsections": v051_subsections,
                "active_subsection": active_subsection,
                "delivery_exception": delivery_exception,
                "assessment_prompt": (
                    current_assessment.prompt_snapshot
                    if current_assessment and current_assessment.status == "ACTIVE" and is_current else None
                ),
                "f1_public_assessment": (
                    public_projection(current_assessment)
                    if f1_study and current_assessment and current_assessment.status == "ACTIVE" and is_current and is_deliverable_f1(current_assessment, self.settings, v051_candidate) else None
                ),
                "f1_assessment_submitted": bool(
                    f1_study and current_assessment and current_assessment.status == "AWAITING_EVALUATION" and is_f1_frozen(current_assessment) and is_current
                ),
                "f1_assessment_unavailable": bool(
                    f1_study and current_assessment and current_assessment.status == "ACTIVE" and is_current
                    and not is_deliverable_f1(current_assessment, self.settings, v051_candidate)
                ),
                "pending": pending,
                "pending_status": operation.status if pending else None,
                "retryable": retryable,
                "technical_hold": technical_hold,
                "failed_purpose": operation.purpose if retryable else None,
                "started_at": in_research_timezone(session.started_at),
                "ended_at": in_research_timezone(session.ended_at),
                "elapsed_seconds": elapsed_seconds,
            }

    async def run_operation(self, call_id):
        try:
            with self.factory() as db:
                await self.execution.execute(db, call_id)
        except Exception as exc:
            with self.factory() as db:
                call = db.get(LLMCall, call_id)
                if call and call.status == "RECEIVED":
                    # Provider output is durable.  Keep it in the recovery queue
                    # so retry applies the same response without another send.
                    call.error_class = "APPLICATION_FAILURE"
                    call.error_message = str(exc)[:4000]
                    db.commit()
                elif call and call.status in ("STARTED", "SENDING"):
                    call.status = "FAILED"
                    call.error_class = "APPLICATION_ERROR"
                    call.error_message = str(exc)[:4000]
                    call.completed_at = datetime.now(timezone.utc)
                    db.commit()

    async def recover_persisted_operations(self):
        with self.factory() as db:
            # The assessment build is a persisted orchestrator, not an external
            # request.  Resume it after applying any saved role responses.
            build_ids = list(db.scalars(select(LLMCall.id).where(LLMCall.status == "STARTED", LLMCall.purpose == "ASSESSMENT_BUILD")).all())
            started = db.scalars(select(LLMCall).where(LLMCall.status.in_(("STARTED", "SENDING")), LLMCall.purpose != "ASSESSMENT_BUILD")).all()
            for call in started:
                call.status = "FAILED"
                call.error_class = "PROCESS_INTERRUPTED"
                call.error_message = "The application restarted before this operation completed."
                call.completed_at = datetime.now(timezone.utc)
            received_ids = list(db.scalars(select(LLMCall.id).where(LLMCall.status == "RECEIVED")).all())
            db.commit()
        for call_id in received_ids:
            await self.run_operation(call_id)
        for call_id in build_ids:
            await self.run_operation(call_id)
        # Reconcile installations upgraded from the former split commit path.
        # Locking the session makes repeated startup recovery idempotent.
        with self.factory() as db:
            generating = db.scalars(select(AssessmentInstance).where(AssessmentInstance.status == "GENERATING")).all()
            orphaned=[]
            for assessment in generating:
                session=db.scalar(select(Session).where(Session.id==assessment.session_id).with_for_update())
                existing=db.scalar(select(LLMCall.id).where(LLMCall.assessment_instance_id==assessment.id,LLMCall.purpose=="ASSESSMENT_BUILD").order_by(LLMCall.started_at.desc()))
                if existing is None and session and session.phase=="ASSESSMENT_GENERATING":
                    orphaned.append(self.execution.reserve_assessment(db,session.id,assessment.id,commit=False))
            db.commit()
        for call_id in orphaned:
            await self.run_operation(call_id)

    @staticmethod
    def _request_hash(action_type: str, payload: dict) -> str:
        canonical = json.dumps({"action_type": action_type, "payload": payload}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def reserve_idempotent(self, db, session_id, action_type, idempotency_key, payload, reserve, result_type="LLMCall"):
        key = idempotency_key.strip()
        if not key or len(key) > 200:
            raise ValueError("invalid idempotency key")
        request_hash = self._request_hash(action_type, payload)
        session = db.scalar(select(Session).where(Session.id == session_id).with_for_update())
        if session is None:
            raise ValueError("session does not exist")
        existing = db.scalar(select(IdempotencyRecord).where(
            IdempotencyRecord.session_id == session_id,
            IdempotencyRecord.action_type == action_type,
            IdempotencyRecord.idempotency_key == key,
        ))
        if existing:
            if existing.request_hash != request_hash:
                raise ValueError("idempotency key was already used for a different request")
            return existing.result_object_id, False
        record = IdempotencyRecord(
            session_id=session_id,
            action_type=action_type,
            idempotency_key=key,
            request_hash=request_hash,
            result_object_type=result_type,
            response_snapshot={"state": "RESERVING"},
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.settings.idempotency_retention_seconds),
        )
        db.add(record); db.flush()
        try:
            # Callback mutations (notably the learner message inserted while a
            # Tutor turn is reserved) must disappear when reservation rejects.
            # The outer idempotency row survives as an audited rejection.
            with db.begin_nested():
                call_id = reserve()
        except Exception:
            record.response_snapshot = {"state": "REJECTED"}
            db.commit()
            raise
        record.result_object_id = call_id
        record.response_snapshot = {"state": "RESERVED", "object_id": str(call_id), "object_type": result_type}
        db.commit()
        return call_id, True

    def render_main(self, request: Request, session_id, status_code=200, selected_section=None):
        view = self.view(session_id, selected_section)
        if view is None:
            return RedirectResponse("/join", status_code=303)
        return templates.TemplateResponse(
            request, "partials/session_main.html", {"view": view, "new_key": str(uuid.uuid4()), "settings": self.settings}, status_code=status_code
        )

    def render_tutor_composer(self, request: Request, session_id):
        view = self.view(session_id)
        if view is None:
            return RedirectResponse("/join", status_code=303)
        return templates.TemplateResponse(
            request, "partials/tutor_composer.html", {"view": view, "new_key": str(uuid.uuid4()), "settings": self.settings}
        )


def participant_router(application: ParticipantApplication) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    @router.get("/join", response_class=HTMLResponse)
    async def join_page(request: Request):
        return templates.TemplateResponse(request, "join.html", {"error": None, "settings": application.settings})

    @router.post("/join", response_class=HTMLResponse)
    async def join(request: Request, institutional_id: str = Form(..., max_length=200), acknowledged: str = Form(...)):
        session_id = application.activate(institutional_id)
        if session_id is None:
            message = "The study is not ready yet. Please contact the researcher." if getattr(application.settings, "require_active_capture", False) else "This participant cannot start a new study session. Please contact the researcher."
            return templates.TemplateResponse(request, "join.html", {"error": message, "settings": application.settings}, status_code=403)
        request.session["participant_session_id"] = str(session_id)
        return RedirectResponse("/session", status_code=303)

    @router.post("/internal/v051/session")
    async def internal_v051_session(request: Request, x_ekagra_internal_test_token: str | None = Header(None)):
        """Opt-in staff-only candidate entry point; ordinary enrollment never calls it."""
        if not _internal_v051_access_enabled(application.settings, x_ekagra_internal_test_token):
            raise HTTPException(status_code=404)
        with application.factory() as db:
            version = db.scalar(select(StudyVersion).where(StudyVersion.content_version == "v0.5.1").order_by(StudyVersion.created_at.desc()))
            if version is None:
                raise HTTPException(status_code=404)
            session = application.execution.runtime.create_v051_internal_test_session(db, version.id)
        request.session["participant_session_id"] = str(session.id)
        return RedirectResponse("/session", status_code=303)

    @router.post("/leave")
    async def leave(request: Request):
        application.deactivate(request.session)
        return RedirectResponse("/join", status_code=303)

    def render_session(request: Request, session_id, selected_section=None):
        view = application.view(session_id, selected_section)
        return templates.TemplateResponse(request, "session.html", {"view": view, "new_key": str(uuid.uuid4()), "settings": application.settings})

    @router.get("/session", response_class=HTMLResponse)
    async def session_page(request: Request):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        return render_session(request, session_id)

    @router.get("/session/sections/{section_number}", response_class=HTMLResponse)
    async def section_page(request: Request, section_number: int):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        current = application.view(session_id)
        return render_session(request, session_id, None if current and current["pending"] else section_number)

    @router.get("/session/operation", response_class=HTMLResponse)
    async def operation(request: Request, x_ekagra_subsection: str | None = Header(None)):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        # A pending operation has no participant-visible change. Returning 204
        # preserves the existing chat DOM and its user-selected scroll position.
        if (view := application.view(session_id)) and not _operation_refresh_required(
            view["pending"], x_ekagra_subsection,
            view["active_subsection"]["id"] if view["active_subsection"] else None,
        ):
            return Response(status_code=204)
        return application.render_main(request, session_id)

    @router.post("/session/telemetry/rrweb")
    async def rrweb_telemetry(request: Request):
        session_id = application.require(request.session)
        if not session_id:
            return {"accepted": False}
        try:
            data = await request.json()
            run = uuid.UUID(str(data.get("browser_run_id")))
            metadata = data.get("run_metadata")
            if not isinstance(metadata, dict) or metadata.get("browser_run_id") != str(run):
                raise ValueError("invalid run metadata")
            ensure_browser_manifest(application.settings.research_data_dir, session_id, run, metadata)
            result = append_rrweb_batch(application.settings.research_data_dir, session_id, data)
            return result
        except (ValueError, json.JSONDecodeError):
            return {"accepted": False}

    @router.post("/session/telemetry/keyboard")
    async def keyboard_telemetry(request: Request):
        session_id = application.require(request.session)
        if not session_id:
            return {"accepted": False}
        try:
            data = await request.json()
            run = uuid.UUID(str(data.get("browser_run_id")))
            metadata = data.get("run_metadata")
            safe_metadata = {
                "browser_run_id", "page_path", "recording_started_client_utc_ms", "performance_time_origin_ms",
                "initial_performance_ms", "telemetry_schema_version", "rrweb_version",
            }
            if not isinstance(metadata, dict) or set(metadata) - safe_metadata or metadata.get("browser_run_id") != str(run):
                raise ValueError("invalid run metadata")
            ensure_browser_manifest(application.settings.research_data_dir, session_id, run, metadata)
            return append_keyboard_batch(application.settings.research_data_dir, session_id, data)
        except (ValueError, json.JSONDecodeError):
            return {"accepted": False}

    @router.post("/session/telemetry/ui-events")
    async def ui_telemetry(request: Request):
        session_id = application.require(request.session)
        if not session_id:
            return {"accepted": False}
        try:
            data = await request.json()
            with application.factory() as db:
                session = db.get(Session, session_id)
                result = record_ui_events(db, session, data.get("events"))
            return {"accepted": True, "count": result}
        except (ValueError, json.JSONDecodeError, AttributeError):
            return {"accepted": False}

    def rejected(request, session_id):
        return application.render_main(request, session_id, status_code=409)

    def reserve_action(session_id, action_type, key, payload, callback):
        with application.factory() as db:
            return application.reserve_idempotent(db, session_id, action_type, key, payload, lambda: callback(db))

    @router.post("/session/actions/begin", response_class=HTMLResponse)
    async def begin(request: Request, background_tasks: BackgroundTasks, idempotency_key: str = Form(...)):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        try:
            call_id, created = reserve_action(session_id, "BEGIN", idempotency_key, {}, lambda db: application.execution.reserve_tutor(db, session_id, commit=False))
        except ValueError:
            return rejected(request, session_id)
        if created:
            background_tasks.add_task(application.run_operation, call_id)
        return application.render_main(request, session_id)

    @router.post("/session/actions/tutor-message", response_class=HTMLResponse)
    async def tutor_message(request: Request, background_tasks: BackgroundTasks, learner_text: str = Form(..., max_length=8000), idempotency_key: str = Form(...)):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        try:
            text = learner_text.strip()
            call_id, created = reserve_action(session_id, "TUTOR_MESSAGE", idempotency_key, {"learner_text": text}, lambda db: application.execution.reserve_tutor(db, session_id, text, commit=False))
        except ValueError:
            return rejected(request, session_id)
        if created:
            background_tasks.add_task(application.run_operation, call_id)
        view = application.view(session_id)
        if view and view["pending"]:
            return application.render_tutor_composer(request, session_id)
        # A retry whose operation completed while its response was in flight
        # must update the authoritative page, not insert it into the composer.
        response = application.render_main(request, session_id)
        response.headers["HX-Retarget"] = "#session-main"
        response.headers["HX-Reswap"] = "outerHTML"
        return response

    @router.post("/session/actions/assessment-response", response_class=HTMLResponse)
    async def assessment_response(request: Request, background_tasks: BackgroundTasks, response_text: str = Form(..., max_length=12000), idempotency_key: str = Form(...), mcq1_answer: str | None = Form(None), mcq2_answer: str | None = Form(None), mcq3_answer: str | None = Form(None)):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        try:
            text = response_text.strip()
            action_id = uuid.uuid5(uuid.NAMESPACE_URL, f"solo-harness:{session_id}:{idempotency_key}")
            with application.factory() as db:
                session = db.get(Session, session_id)
                attempt = db.get(Attempt, session.current_attempt_id) if session else None
                assessment = db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id == attempt.id)) if attempt else None
                compiled = application.execution.runtime._compiled(db, session)
                f1_request = is_f1_study(compiled)
                v051_candidate = application.execution.runtime._v051(compiled)
                if f1_request:
                    if not is_deliverable_f1(assessment, application.settings, v051_candidate):
                        raise ValueError("F1 assessment package is unavailable for learner delivery")
                    answers = {"MCQ1": mcq1_answer or "", "MCQ2": mcq2_answer or "", "MCQ3": mcq3_answer or ""}
                    payload = {"answers": answers, "subjective_response": text}
                    f1_judge = {}
                    def reserve_f1():
                        response = submit_f1_response(db, application.execution.runtime, session_id, answers, text, action_id)
                        f1_judge["id"] = application.execution.reserve_f1_judge(db, session_id, response, commit=False)
                        return response.id
                    call_id, created = application.reserve_idempotent(
                        db, session_id, "F1_ASSESSMENT_RESPONSE", idempotency_key, payload,
                        reserve_f1,
                        result_type="AssessmentResponse",
                    )
                else:
                    call_id, created = application.reserve_idempotent(
                        db, session_id, "ASSESSMENT_RESPONSE", idempotency_key, {"response_text": text},
                        lambda: application.execution.reserve_judge(db, session_id, text, action_id, commit=False),
                    )
        except ValueError:
            return rejected(request, session_id)
        if created and f1_request:
            background_tasks.add_task(application.run_operation, f1_judge["id"])
        elif created:
            background_tasks.add_task(application.run_operation, call_id)
        return application.render_main(request, session_id)

    @router.post("/session/actions/retry", response_class=HTMLResponse)
    async def retry(request: Request, background_tasks: BackgroundTasks, idempotency_key: str = Form(...)):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        try:
            call_id, created = reserve_action(session_id, "RETRY", idempotency_key, {}, lambda db: application.execution.reserve_manual_retry(db, session_id, commit=False))
        except ValueError:
            return rejected(request, session_id)
        if created:
            background_tasks.add_task(application.run_operation, call_id)
        return application.render_main(request, session_id)

    @router.post("/internal/technical-holds/{call_id}/requeue")
    async def requeue_technical_hold(call_id: uuid.UUID, background_tasks: BackgroundTasks, x_technical_hold_token: str | None = Header(None)):
        configured=application.settings.technical_hold_resolution_token
        if configured is None or x_technical_hold_token is None or not secrets.compare_digest(configured.get_secret_value(), x_technical_hold_token):
            raise HTTPException(status_code=403, detail="researcher authorization required")
        with application.factory() as db:
            held=db.get(LLMCall,call_id)
            if held is None or held.status!="TECHNICAL_HOLD": raise HTTPException(status_code=409, detail="operation is not an exhausted technical hold")
            new_id=application.execution.reserve_manual_retry(db,held.session_id,commit=True,authorized_requeue=True)
        background_tasks.add_task(application.run_operation,new_id)
        return {"requeued_call_id":str(new_id),"requeued_from":str(call_id)}

    @router.post("/session/actions/development-advance", response_class=HTMLResponse)
    async def development_advance(request: Request, idempotency_key: str = Form(...)):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        if not application.settings.enable_f1_v04_development:
            raise HTTPException(status_code=404, detail="not found")
        try:
            reserve_action(session_id, "DEVELOPMENT_ADVANCE", idempotency_key, {},
                           lambda db: application.execution.reserve_development_paas(db, session_id, commit=False))
        except ValueError:
            return rejected(request, session_id)
        return application.render_main(request, session_id)

    @router.post("/session/actions/paas", response_class=HTMLResponse)
    async def submit_paas(request: Request, background_tasks: BackgroundTasks,
                          rating: int = Form(...), idempotency_key: str = Form(...)):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        try:
            call_id, created = reserve_action(
                session_id, "PAAS_RESPONSE", idempotency_key, {"rating": rating},
                lambda db: application.execution.reserve_paas_assessment(db, session_id, rating, commit=False),
            )
        except ValueError:
            return rejected(request, session_id)
        if created:
            background_tasks.add_task(application.run_operation, call_id)
        return application.render_main(request, session_id)

    @router.post("/session/actions/next", response_class=HTMLResponse)
    async def next_section(request: Request):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        try:
            with application.factory() as db:
                application.execution.runtime.advance_section(db, session_id)
        except ValueError:
            return rejected(request, session_id)
        return application.render_main(request, session_id)

    @router.post("/session/actions/finish", response_class=HTMLResponse)
    async def finish(request: Request):
        session_id = application.require(request.session)
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        try:
            with application.factory() as db:
                application.execution.runtime.finish_session(db, session_id)
        except ValueError:
            return rejected(request, session_id)
        return application.render_main(request, session_id)

    return router
