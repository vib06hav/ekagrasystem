"""Read-only researcher inspection and versioned Session export."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from solo_harness.db.engine import make_engine, make_session_factory
from solo_harness.db.models import (
    AssessmentInstance,
    AssessmentResponse,
    Attempt,
    IdempotencyRecord,
    Judgment,
    LearnerHistorySnapshot,
    LLMCall,
    Message,
    ParticipantUIEvent,
    ProtocolEvent,
    RubricEvaluation,
    Session,
    StudyVersion,
)
from solo_harness.research_time import RESEARCH_TIMEZONE_NAME, in_research_timezone

EXPORT_SCHEMA_VERSION = "1.2"


def _derived_transition_outcomes(events) -> dict[str, str]:
    """Derived only from persisted section-completion event payloads; unknown stays unknown."""
    result = {}
    for event in events:
        if event.event_type == "SECTION_COMPLETED" and event.payload.get("transition_id"):
            outcome = event.payload.get("scientific_outcome")
            if outcome in {"PASSED", "UNRESOLVED"}:
                result[event.payload["transition_id"]] = outcome
    return result


def _json_value(value: Any, field_name: str | None = None) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        if isinstance(value, datetime) and not (field_name or "").endswith("_utc"):
            value = in_research_timezone(value)
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item, str(key)) for key, item in value.items()}
    return value


def _row(instance, *, omit: set[str] | None = None) -> dict[str, Any]:
    omitted = omit or set()
    return {
        column.name: _json_value(getattr(instance, column.name), column.name)
        for column in instance.__table__.columns
        if column.name not in omitted
    }


def _ordered(db: DbSession, model, criterion, *order_columns):
    statement = select(model).where(criterion)
    if order_columns:
        statement = statement.order_by(*order_columns)
    return list(db.scalars(statement).all())


def inspect_session(database_url: str, session_id: uuid.UUID) -> dict[str, Any]:
    factory = make_session_factory(database_url)
    with factory() as db:
        session = db.get(Session, session_id)
        if session is None:
            raise ValueError(f"Session {session_id} was not found")
        attempts = _ordered(db, Attempt, Attempt.session_id == session_id, Attempt.assigned_at, Attempt.id)
        calls = _ordered(db, LLMCall, LLMCall.session_id == session_id, LLMCall.started_at, LLMCall.id)
        return {
            "session_id": str(session.id),
            "study_version_id": str(session.study_version_id),
            "status": session.status,
            "phase": session.phase,
            "formal_state_id": session.formal_state_id,
            "current_transition_id": session.current_transition_id,
            "current_attempt_number": session.current_attempt_number,
            "terminal_reason": session.terminal_reason,
            "attempt_count": len(attempts),
            "llm_call_counts": {
                status: sum(call.status == status for call in calls)
                for status in sorted({call.status for call in calls})
            },
            "last_event_sequence": session.last_event_sequence,
            "created_at": _json_value(session.created_at, "created_at"),
            "updated_at": _json_value(session.updated_at, "updated_at"),
        }


def _artifact_index(root: Path | None, session_id: uuid.UUID, capture_run_id: uuid.UUID | None = None) -> dict[str, Any]:
    if root is None:
        return {"status": "ABSENT", "manifests": []}
    root = root.resolve()
    base = root / str(session_id)
    manifests = []
    for relative, kind in (("browser/manifest.json", "browser_telemetry"), ("capture/capture_manifest.json", "windows_capture")):
        path = base / relative
        if not path.is_file():
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            manifests.append({"relative_path": str(Path("research-data") / str(session_id) / relative).replace("\\", "/"), "manifest_type": kind, "schema_version": document.get("schema_version"), "status": document.get("status", "PRESENT"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        except (OSError, json.JSONDecodeError):
            manifests.append({"relative_path": str(Path("research-data") / str(session_id) / relative).replace("\\", "/"), "manifest_type": kind, "status": "UNREADABLE"})
    if capture_run_id:
        path = root / "capture-runs" / str(capture_run_id) / "capture_manifest.json"
        relative = Path("research-data") / "capture-runs" / str(capture_run_id) / "capture_manifest.json"
        if path.is_file():
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                manifests.append({"relative_path": str(relative).replace("\\", "/"), "manifest_type": "windows_capture", "schema_version": document.get("schema_version"), "status": document.get("status", "PRESENT"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            except (OSError, json.JSONDecodeError):
                manifests.append({"relative_path": str(relative).replace("\\", "/"), "manifest_type": "windows_capture", "status": "UNREADABLE"})
    return {"status": "PRESENT" if manifests else "ABSENT", "manifests": manifests}


def build_session_export(database_url: str, session_id: uuid.UUID, research_data_root: Path | None = None) -> dict[str, Any]:
    """Build a transactionally consistent export without mutating experiment state."""
    engine = make_engine(database_url)
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with connection.begin():
            with DbSession(bind=connection, expire_on_commit=False) as db:
                session = db.get(Session, session_id)
                if session is None:
                    raise ValueError(f"Session {session_id} was not found")
                version = db.get(StudyVersion, session.study_version_id)
                attempts = _ordered(db, Attempt, Attempt.session_id == session_id, Attempt.assigned_at, Attempt.id)
                attempt_ids = [attempt.id for attempt in attempts]
                assessments = _ordered(db, AssessmentInstance, AssessmentInstance.session_id == session_id, AssessmentInstance.selected_at, AssessmentInstance.id)
                assessment_ids = [assessment.id for assessment in assessments]
                responses = _ordered(db, AssessmentResponse, AssessmentResponse.assessment_instance_id.in_(assessment_ids), AssessmentResponse.submitted_at, AssessmentResponse.id) if assessment_ids else []
                response_ids = [response.id for response in responses]
                judgments = _ordered(db, Judgment, Judgment.assessment_response_id.in_(response_ids), Judgment.created_at, Judgment.id) if response_ids else []
                judgment_ids = [judgment.id for judgment in judgments]
                protocol_events = _ordered(db, ProtocolEvent, ProtocolEvent.session_id == session_id, ProtocolEvent.sequence_no)
                data = {
                    "session": {
                        **_row(session, omit={"institutional_id"}),
                        "institutional_id_sha256": hashlib.sha256((session.institutional_id or "").encode("utf-8")).hexdigest() if session.institutional_id else None,
                    },
                    "study_version": _row(version),
                    "attempts": [_row(item) for item in attempts],
                    "learner_history_snapshots": [_row(item) for item in _ordered(db, LearnerHistorySnapshot, LearnerHistorySnapshot.session_id == session_id, LearnerHistorySnapshot.created_at, LearnerHistorySnapshot.id)],
                    "messages": [_row(item) for item in _ordered(db, Message, Message.attempt_id.in_(attempt_ids), Message.created_at, Message.attempt_id, Message.sequence_no)] if attempt_ids else [],
                    "assessment_instances": [_row(item) for item in assessments],
                    "assessment_responses": [_row(item) for item in responses],
                    "llm_calls": [_row(item) for item in _ordered(db, LLMCall, LLMCall.session_id == session_id, LLMCall.started_at, LLMCall.id)],
                    "judgments": [_row(item) for item in judgments],
                    "rubric_evaluations": [_row(item) for item in _ordered(db, RubricEvaluation, RubricEvaluation.judgment_id.in_(judgment_ids), RubricEvaluation.created_at, RubricEvaluation.id)] if judgment_ids else [],
                    "participant_ui_events": [_row(item) for item in _ordered(db, ParticipantUIEvent, ParticipantUIEvent.session_id == session_id, ParticipantUIEvent.server_received_at, ParticipantUIEvent.id)],
                    "protocol_events": [_row(item) for item in protocol_events],
                    "derived_transition_scientific_outcomes": _derived_transition_outcomes(protocol_events),
                    "idempotency_records": [_row(item, omit={"request_hash"}) for item in _ordered(db, IdempotencyRecord, IdempotencyRecord.session_id == session_id, IdempotencyRecord.created_at, IdempotencyRecord.id)],
                    "research_artifacts": _artifact_index(research_data_root, session_id, session.capture_run_id),
                }
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "time_representation": {
            "research_timezone": RESEARCH_TIMEZONE_NAME,
            "database_timestamp_storage": "timezone-aware UTC",
            "raw_telemetry_fields": "Fields explicitly suffixed _utc remain UTC compatibility values.",
        },
        "exported_at": in_research_timezone(datetime.now(timezone.utc)).isoformat(),
        "session_id": str(session_id),
        "data_sha256": hashlib.sha256(canonical).hexdigest(),
        "data": data,
    }


def write_session_export(database_url: str, session_id: uuid.UUID, output: Path, *, overwrite: bool = False, research_data_root: Path | None = None) -> dict[str, Any]:
    output = output.expanduser().resolve()
    if output.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing export: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    document = build_session_export(database_url, session_id, research_data_root)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(output)
    return document
