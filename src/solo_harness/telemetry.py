"""Best-effort browser telemetry. Dense rrweb data stays outside PostgreSQL."""
from __future__ import annotations

import hashlib
import json
import math
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from solo_harness.db.models import AssessmentInstance, Attempt, ParticipantUIEvent

TELEMETRY_SCHEMA_VERSION = "1.0"
RRWEB_VERSION = "2.1.7"
KEYBOARD_SCHEMA_VERSION = "keyboard-1.0"
MAX_BATCH_EVENTS = 500
MAX_EVENT_BYTES = 256_000
MAX_UI_EVENTS = 100
MAX_UI_PAYLOAD_BYTES = 4096
UI_EVENT_TYPES = {
    "SESSION_PAGE_RENDERED", "SECTION_RENDERED", "TEACHING_ACTIVITY_RENDERED",
    "BEGIN_CLICKED", "PROCESSING_SHOWN", "PROCESSING_HIDDEN", "TUTOR_MESSAGE_RENDERED",
    "TUTOR_RESPONSE_SUBMIT_CLICKED", "ASSESSMENT_RENDERED", "ASSESSMENT_RESPONSE_SUBMIT_CLICKED",
    "ASSESSMENT_COMPLETED_MARKER_RENDERED", "GENERATION_ERROR_RENDERED", "RETRY_CLICKED",
    "SECTION_COMPLETE_RENDERED", "COMPLETED_SECTION_REVIEW_OPENED", "NEXT_CLICKED",
    "FINISH_CLICKED", "STUDY_COMPLETE_RENDERED",
}
SURFACES = {"session", "section", "teaching", "processing", "assessment", "error", "section_complete", "study_complete", "review"}
KEYBOARD_EVENT_TYPES = {"KEYDOWN", "KEYUP"}
KEYBOARD_SURFACES = {"TUTOR_RESPONSE", "ASSESSMENT_RESPONSE"}
KEY_CLASSES = {"CHAR", "DIGIT", "SPACE", "ENTER", "BACKSPACE", "DELETE", "TAB", "ARROW", "MODIFIER", "PUNCTUATION", "OTHER"}
KEYBOARD_EVENT_FIELDS = {
    "telemetry_schema_version", "browser_run_id", "client_sequence", "event_type", "press_id",
    "client_event_at_utc_ms", "client_performance_ms", "performance_time_origin_ms", "section_number",
    "teaching_activity_number", "surface", "key_class", "flags",
}
_write_lock = threading.Lock()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid(value: object, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(f"invalid {field}") from exc


def _finite(value: object, field: str, *, nonnegative: bool = True) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"invalid {field}")
    result = float(value)
    if nonnegative and result < 0:
        raise ValueError(f"invalid {field}")
    return result


def _client_time(value: object) -> datetime:
    milliseconds = _finite(value, "client_event_at_utc_ms", nonnegative=True)
    try:
        return datetime.fromtimestamp(milliseconds / 1000, timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError("invalid client_event_at_utc_ms") from exc


def _safe_payload(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("invalid payload")
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > MAX_UI_PAYLOAD_BYTES:
        raise ValueError("payload too large")
    return value


def _session_dir(root: Path, session_id: uuid.UUID) -> Path:
    return root.resolve() / str(session_id)


def ensure_browser_manifest(root: Path, session_id: uuid.UUID, run: uuid.UUID, metadata: dict) -> Path:
    browser = _session_dir(root, session_id) / "browser"
    browser.mkdir(parents=True, exist_ok=True)
    manifest = browser / "manifest.json"
    with _write_lock:
        data = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {
            "schema_version": TELEMETRY_SCHEMA_VERSION,
            "artifact_type": "browser_telemetry",
            "runs": [],
        }
        if not any(item.get("browser_run_id") == str(run) for item in data["runs"]):
            data["runs"].append(metadata)
            manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def update_keyboard_manifest(root: Path, session_id: uuid.UUID, run: uuid.UUID, event_count: int) -> None:
    manifest = _session_dir(root, session_id) / "browser" / "manifest.json"
    with _write_lock:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        item = next(entry for entry in data["runs"] if entry.get("browser_run_id") == str(run))
        keyboard = item.setdefault("keyboard", {
            "telemetry_schema_version": KEYBOARD_SCHEMA_VERSION,
            "artifact_relative_path": f"keyboard/{run}.ndjson",
            "event_count": 0,
            "batch_count": 0,
        })
        keyboard["event_count"] += event_count
        keyboard["batch_count"] += 1
        keyboard["last_server_received_at_utc"] = utc_now().isoformat()
        manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_rrweb_batch(root: Path, session_id: uuid.UUID, data: dict) -> dict:
    run = _uuid(data.get("browser_run_id"), "browser_run_id")
    batch_id = _uuid(data.get("batch_id"), "batch_id")
    events = data.get("events")
    if not isinstance(events, list) or not events or len(events) > MAX_BATCH_EVENTS:
        raise ValueError("invalid rrweb event batch")
    lines = []
    received = utc_now().isoformat()
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("rrweb_event"), dict):
            raise ValueError("invalid rrweb event")
        if event.get("telemetry_schema_version") != TELEMETRY_SCHEMA_VERSION or str(event.get("browser_run_id")) != str(run):
            raise ValueError("invalid rrweb wrapper")
        _finite(event.get("client_emit_utc_ms"), "client_emit_utc_ms")
        _finite(event.get("client_performance_ms"), "client_performance_ms")
        if not isinstance(event.get("sequence"), int) or event["sequence"] < 1:
            raise ValueError("invalid rrweb sequence")
        wrapped = {**event, "batch_id": str(batch_id), "server_received_at_utc": received}
        encoded = json.dumps(wrapped, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_EVENT_BYTES:
            raise ValueError("rrweb event too large")
        lines.append(encoded)
    rrweb_dir = _session_dir(root, session_id) / "browser" / "rrweb"
    rrweb_dir.mkdir(parents=True, exist_ok=True)
    path = rrweb_dir / f"{run}.ndjson"
    marker_dir = rrweb_dir / ".batches" / str(run)
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / f"{batch_id}.json"
    with _write_lock:
        if marker.exists():
            return {"accepted": False, "duplicate": True, "server_received_at_utc": received}
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
            handle.flush()
        marker.write_text(json.dumps({"event_count": len(lines), "server_received_at_utc": received}), encoding="utf-8")
    return {"accepted": True, "duplicate": False, "server_received_at_utc": received}


def append_keyboard_batch(root: Path, session_id: uuid.UUID, data: dict) -> dict:
    """Append validated, coarse keyboard dynamics only; raw key identity is refused."""
    run = _uuid(data.get("browser_run_id"), "browser_run_id")
    batch_id = _uuid(data.get("batch_id"), "batch_id")
    events = data.get("events")
    if not isinstance(events, list) or not events or len(events) > MAX_BATCH_EVENTS:
        raise ValueError("invalid keyboard event batch")
    lines = []
    received = utc_now().isoformat()
    for event in events:
        if not isinstance(event, dict) or set(event) != KEYBOARD_EVENT_FIELDS:
            raise ValueError("invalid keyboard event")
        if event.get("telemetry_schema_version") != KEYBOARD_SCHEMA_VERSION:
            raise ValueError("invalid keyboard schema")
        if event.get("event_type") not in KEYBOARD_EVENT_TYPES or event.get("surface") not in KEYBOARD_SURFACES:
            raise ValueError("invalid keyboard event")
        if str(event.get("browser_run_id")) != str(run) or not isinstance(event.get("client_sequence"), int) or event["client_sequence"] < 1:
            raise ValueError("invalid keyboard identity")
        if not isinstance(event.get("press_id"), int) or event["press_id"] < 1 or event.get("key_class") not in KEY_CLASSES:
            raise ValueError("invalid keyboard press")
        _client_time(event.get("client_event_at_utc_ms"))
        _finite(event.get("client_performance_ms"), "client_performance_ms")
        _finite(event.get("performance_time_origin_ms"), "performance_time_origin_ms")
        section, activity = event.get("section_number"), event.get("teaching_activity_number")
        if section is not None and (not isinstance(section, int) or section < 1):
            raise ValueError("invalid section_number")
        if activity is not None and (not isinstance(activity, int) or activity < 1):
            raise ValueError("invalid teaching_activity_number")
        flags = event.get("flags")
        if not isinstance(flags, dict) or set(flags) != {"repeat", "is_composing", "ctrl", "alt", "shift", "meta"} or not all(isinstance(value, bool) for value in flags.values()):
            raise ValueError("invalid keyboard flags")
        wrapped = {**event, "batch_id": str(batch_id), "server_received_at_utc": received}
        encoded = json.dumps(wrapped, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > 4096:
            raise ValueError("keyboard event too large")
        lines.append(encoded)
    keyboard_dir = _session_dir(root, session_id) / "browser" / "keyboard"
    keyboard_dir.mkdir(parents=True, exist_ok=True)
    path = keyboard_dir / f"{run}.ndjson"
    marker_dir = keyboard_dir / ".batches" / str(run)
    marker_dir.mkdir(parents=True, exist_ok=True)
    marker = marker_dir / f"{batch_id}.json"
    with _write_lock:
        if marker.exists():
            return {"accepted": False, "duplicate": True, "server_received_at_utc": received}
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")
            handle.flush()
        marker.write_text(json.dumps({"event_count": len(lines), "server_received_at_utc": received}), encoding="utf-8")
    update_keyboard_manifest(root, session_id, run, len(lines))
    return {"accepted": True, "duplicate": False, "server_received_at_utc": received}


def record_ui_events(db, session, events: object) -> int:
    if not isinstance(events, list) or not events or len(events) > MAX_UI_EVENTS:
        raise ValueError("invalid ui event batch")
    # Resolve participant-safe section numbers against frozen protocol server-side.
    from solo_harness.studies.catalog import StudyCatalog
    study = StudyCatalog().load(db, session.study_version_id)
    transitions = list(study.protocol["transition_ids"])
    inserted = 0
    for item in events:
        if not isinstance(item, dict) or item.get("event_type") not in UI_EVENT_TYPES or item.get("surface") not in SURFACES:
            raise ValueError("invalid ui event")
        run = _uuid(item.get("browser_run_id"), "browser_run_id")
        sequence = item.get("client_sequence")
        if not isinstance(sequence, int) or sequence < 1:
            raise ValueError("invalid client_sequence")
        section = item.get("section_number")
        if section is not None and (not isinstance(section, int) or section < 1 or section > len(transitions)):
            raise ValueError("invalid section_number")
        activity = item.get("teaching_activity_number")
        if activity is not None and (not isinstance(activity, int) or activity < 1 or activity > 3):
            raise ValueError("invalid teaching_activity_number")
        attempt_id = None
        assessment_id = None
        if section is not None:
            transition = transitions[section - 1]
            attempt = db.scalar(select(Attempt).where(Attempt.session_id == session.id, Attempt.transition_id == transition).order_by(Attempt.sequence_in_transition.desc()))
            if attempt:
                attempt_id = attempt.id
                assessment = db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id == attempt.id))
                assessment_id = assessment.id if assessment else None
        if db.scalar(select(ParticipantUIEvent.id).where(
            ParticipantUIEvent.session_id == session.id,
            ParticipantUIEvent.browser_run_id == run,
            ParticipantUIEvent.client_sequence == sequence,
        )):
            continue
        row = ParticipantUIEvent(
            session_id=session.id, attempt_id=attempt_id, assessment_instance_id=assessment_id,
            event_type=item["event_type"], client_event_at=_client_time(item.get("client_event_at_utc_ms")),
            client_performance_ms=_finite(item.get("client_performance_ms"), "client_performance_ms"),
            performance_time_origin_ms=_finite(item.get("performance_time_origin_ms"), "performance_time_origin_ms"),
            browser_run_id=run, client_sequence=sequence, section_number=section,
            teaching_activity_number=activity, surface=item["surface"], payload=_safe_payload(item.get("payload", {})),
            server_received_at=utc_now(),
        )
        db.add(row)
        inserted += 1
    db.commit()
    return inserted
