"""Participant-facing HTTP adapter for a trusted, single-participant installation."""
from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from solo_harness.config import Settings
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
)
from solo_harness.runtime.ai import AIExecutionRuntime, OpenAICompatibleClient
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.research_time import in_research_timezone
from solo_harness.telemetry import append_keyboard_batch, append_rrweb_batch, ensure_browser_manifest, record_ui_events

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


class ParticipantApplication:
    """One browser-facing participant bound to one trusted app process at a time."""

    def __init__(self, catalog, settings: Settings, execution: AIExecutionRuntime | None = None):
        self.settings = settings
        self.factory = make_session_factory(settings.database_url)
        self.execution = execution or AIExecutionRuntime(SessionRuntime(catalog), OpenAICompatibleClient(settings), settings)
        self.active_session_id: uuid.UUID | None = None

    def _active_capture_run_id(self, db) -> uuid.UUID | None:
        """Return the one fresh recorder marker, never guessing from stale files."""
        marker = self.settings.research_data_dir / "active_capture.json"
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
            capture_run_id = uuid.UUID(str(payload["capture_run_id"]))
            started = datetime.fromisoformat(str(payload["started_at_utc"]).replace("Z", "+00:00"))
            relative = Path(str(payload["capture_directory"]))
            if payload.get("schema_version") != "1.0" or payload.get("status") != "RECORDING": return None
            if relative.is_absolute() or ".." in relative.parts: return None
            if datetime.now(timezone.utc) - started.astimezone(timezone.utc) > timedelta(seconds=self.settings.active_capture_max_age_seconds): return None
            directory = self.settings.research_data_dir / relative
            if directory != self.settings.research_data_dir / "capture-runs" / str(capture_run_id): return None
            manifest = json.loads((directory / "capture_manifest.json").read_text(encoding="utf-8"))
            if not directory.is_dir() or manifest.get("capture_run_id") != str(capture_run_id) or manifest.get("status") != "RECORDING": return None
            if db.scalar(select(Session.id).where(Session.capture_run_id == capture_run_id)): return None
            return capture_run_id
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    def activate(self, institutional_id: str) -> uuid.UUID | None:
        normalized = institutional_id.strip()
        if not normalized:
            return None
        with self.factory() as db:
            if db.scalar(select(Session.id).where(Session.institutional_id == normalized)):
                return None
            requires_capture = getattr(self.settings, "require_active_capture", False)
            capture_run_id = self._active_capture_run_id(db) if requires_capture else None
            if requires_capture and capture_run_id is None: return None
            active = db.scalar(select(ActiveStudyVersion).order_by(ActiveStudyVersion.activated_at.desc()))
            if active is None: return None
            try:
                session = self.execution.runtime.create_session(db, active.study_version_id, build_id=self.settings.app_build_id, institutional_id=normalized, capture_run_id=capture_run_id, commit=False)
                self.execution.runtime._event(db, session, "PARTICIPANT_ENTERED", {"entry_method": "INSTITUTIONAL_ID", "study_information_acknowledged": True}, session.current_attempt_id)
                db.commit()
            except IntegrityError:
                db.rollback()
                return None
            self.active_session_id = session.id
            return session.id

    def deactivate(self):
        if self.active_session_id is not None:
            with self.factory() as db:
                session = db.get(Session, self.active_session_id)
                if session:
                    self.execution.runtime._event(db, session, "PARTICIPANT_EXITED", {}, session.current_attempt_id)
                    db.commit()
        self.active_session_id = None

    def require(self) -> uuid.UUID | None:
        if self.active_session_id is None:
            return None
        with self.factory() as db:
            return self.active_session_id if db.get(Session, self.active_session_id) else None

    def _transition_ids(self, db, session: Session) -> list[str]:
        return list(self.execution.runtime._compiled(db, session).protocol["transition_ids"])

    def view(self, session_id, selected_section: int | None = None):
        """Build a participant-safe projection with no research-only fields."""
        with self.factory() as db:
            session = db.get(Session, session_id)
            if not session:
                return None
            transition_ids = self._transition_ids(db, session)
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
            messages = db.scalars(
                select(Message).where(Message.attempt_id.in_(attempt_ids)).order_by(Message.created_at, Message.sequence_no)
            ).all() if attempt_ids else []
            messages_by_attempt: dict[uuid.UUID, list[Message]] = defaultdict(list)
            for message in messages:
                messages_by_attempt[message.attempt_id].append(message)
            events = db.scalars(
                select(ProtocolEvent).where(ProtocolEvent.session_id == session.id).order_by(ProtocolEvent.sequence_no)
            ).all()
            completed_transition_ids = {
                event.payload.get("transition_id") for event in events if event.event_type == "SECTION_COMPLETED"
            }

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
                    state = "completed"
                elif index == current_index and session.phase != "TERMINAL":
                    state = "current"
                elif index < current_index:
                    state = "completed"
                else:
                    state = "locked"
                sections.append({"number": index + 1, "state": state, "enabled": index <= current_index})

            timeline = []
            for attempt in attempts_by_transition[selected_transition_id]:
                timeline.append({
                    "kind": "activity",
                    "label": f"Teaching activity {attempt.sequence_in_transition}",
                    "activity_number": attempt.sequence_in_transition,
                    "timestamp": in_research_timezone(attempt.assigned_at),
                })
                for message in messages_by_attempt[attempt.id]:
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
                timeline.append({"kind": "section", "label": "Section completed", "timestamp": in_research_timezone(completed_event.occurred_at)})

            current_attempt = db.get(Attempt, session.current_attempt_id) if session.current_attempt_id else None
            current_assessment = assessments_by_attempt.get(current_attempt.id) if current_attempt else None
            latest = db.scalar(
                select(LLMCall).where(LLMCall.session_id == session.id).order_by(LLMCall.started_at.desc())
            )
            stale = bool(
                latest and latest.status == "STARTED"
                and datetime.now(timezone.utc) - latest.started_at
                >= timedelta(seconds=self.settings.llm_request_timeout_seconds + self.settings.llm_stale_grace_seconds)
            )
            pending = bool(latest and latest.status in ("STARTED", "RECEIVED") and not stale)
            retryable = bool(latest and (latest.status in ("FAILED", "INVALID_OUTPUT") or stale))
            now = session.ended_at or datetime.now(timezone.utc)
            elapsed_seconds = max(0, int((now - session.started_at).total_seconds())) if session.started_at else 0

            return {
                "id": session.id,
                "phase": session.phase,
                "status": session.status,
                "section_number": requested_index + 1,
                "section_count": len(transition_ids),
                "sections": sections,
                "is_current": is_current,
                "is_read_only": not is_current or session.phase == "TERMINAL",
                "is_final_section": current_index == len(transition_ids) - 1,
                "timeline": timeline,
                "attempt_status": current_attempt.status if current_attempt and is_current else None,
                "activity_number": current_attempt.sequence_in_transition if current_attempt and is_current else None,
                "assessment_prompt": (
                    current_assessment.prompt_snapshot
                    if current_assessment and current_assessment.status == "ACTIVE" and is_current else None
                ),
                "pending": pending,
                "pending_status": latest.status if pending else None,
                "retryable": retryable,
                "failed_purpose": latest.purpose if retryable else None,
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
                if call and call.status in ("STARTED", "RECEIVED"):
                    call.status = "FAILED"
                    call.error_class = "APPLICATION_ERROR"
                    call.error_message = str(exc)[:4000]
                    call.completed_at = datetime.now(timezone.utc)
                    db.commit()

    async def recover_persisted_operations(self):
        with self.factory() as db:
            started = db.scalars(select(LLMCall).where(LLMCall.status == "STARTED")).all()
            for call in started:
                call.status = "FAILED"
                call.error_class = "PROCESS_INTERRUPTED"
                call.error_message = "The application restarted before this operation completed."
                call.completed_at = datetime.now(timezone.utc)
            received_ids = list(db.scalars(select(LLMCall.id).where(LLMCall.status == "RECEIVED")).all())
            db.commit()
        for call_id in received_ids:
            await self.run_operation(call_id)

    @staticmethod
    def _request_hash(action_type: str, payload: dict) -> str:
        canonical = json.dumps({"action_type": action_type, "payload": payload}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def reserve_idempotent(self, db, session_id, action_type, idempotency_key, payload, reserve):
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
            result_object_type="LLMCall",
            response_snapshot={"state": "RESERVING"},
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.settings.idempotency_retention_seconds),
        )
        db.add(record); db.flush()
        try:
            call_id = reserve()
        except Exception:
            record.response_snapshot = {"state": "REJECTED"}
            db.commit()
            raise
        record.result_object_id = call_id
        record.response_snapshot = {"state": "RESERVED", "llm_call_id": str(call_id)}
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
        if application.activate(institutional_id) is None:
            message = "The study is not ready yet. Please contact the researcher." if getattr(application.settings, "require_active_capture", False) else "This participant cannot start a new study session. Please contact the researcher."
            return templates.TemplateResponse(request, "join.html", {"error": message, "settings": application.settings}, status_code=403)
        return RedirectResponse("/session", status_code=303)

    @router.post("/leave")
    async def leave():
        application.deactivate()
        return RedirectResponse("/join", status_code=303)

    def render_session(request: Request, session_id, selected_section=None):
        view = application.view(session_id, selected_section)
        return templates.TemplateResponse(request, "session.html", {"view": view, "new_key": str(uuid.uuid4()), "settings": application.settings})

    @router.get("/session", response_class=HTMLResponse)
    async def session_page(request: Request):
        session_id = application.require()
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        return render_session(request, session_id)

    @router.get("/session/sections/{section_number}", response_class=HTMLResponse)
    async def section_page(request: Request, section_number: int):
        session_id = application.require()
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        current = application.view(session_id)
        return render_session(request, session_id, None if current and current["pending"] else section_number)

    @router.get("/session/operation", response_class=HTMLResponse)
    async def operation(request: Request):
        session_id = application.require()
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        # A pending operation has no participant-visible change. Returning 204
        # preserves the existing chat DOM and its user-selected scroll position.
        if (view := application.view(session_id)) and view["pending"]:
            return Response(status_code=204)
        return application.render_main(request, session_id)

    @router.post("/session/telemetry/rrweb")
    async def rrweb_telemetry(request: Request):
        session_id = application.require()
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
        session_id = application.require()
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
        session_id = application.require()
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
        session_id = application.require()
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
        session_id = application.require()
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
    async def assessment_response(request: Request, background_tasks: BackgroundTasks, response_text: str = Form(..., max_length=12000), idempotency_key: str = Form(...)):
        session_id = application.require()
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        try:
            text = response_text.strip()
            action_id = uuid.uuid5(uuid.NAMESPACE_URL, f"solo-harness:{session_id}:{idempotency_key}")
            call_id, created = reserve_action(session_id, "ASSESSMENT_RESPONSE", idempotency_key, {"response_text": text}, lambda db: application.execution.reserve_judge(db, session_id, text, action_id, commit=False))
        except ValueError:
            return rejected(request, session_id)
        if created:
            background_tasks.add_task(application.run_operation, call_id)
        return application.render_main(request, session_id)

    @router.post("/session/actions/retry", response_class=HTMLResponse)
    async def retry(request: Request, background_tasks: BackgroundTasks, idempotency_key: str = Form(...)):
        session_id = application.require()
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        try:
            call_id, created = reserve_action(session_id, "RETRY", idempotency_key, {}, lambda db: application.execution.reserve_manual_retry(db, session_id, commit=False))
        except ValueError:
            return rejected(request, session_id)
        if created:
            background_tasks.add_task(application.run_operation, call_id)
        return application.render_main(request, session_id)

    @router.post("/session/actions/next", response_class=HTMLResponse)
    async def next_section(request: Request):
        session_id = application.require()
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
        session_id = application.require()
        if not session_id:
            return RedirectResponse("/join", status_code=303)
        try:
            with application.factory() as db:
                application.execution.runtime.finish_session(db, session_id)
        except ValueError:
            return rejected(request, session_id)
        return application.render_main(request, session_id)

    return router
