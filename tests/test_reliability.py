import json
import os
import uuid
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from solo_harness.db.base import Base
from solo_harness.db.models import IdempotencyRecord, LLMCall, ParticipantUIEvent, Session
from solo_harness.research_export import build_session_export, inspect_session
from solo_harness.telemetry import record_ui_events
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.studies.activation import activate
from solo_harness.studies.catalog import StudyCatalog
from solo_harness.studies.compiler import compile_study
from solo_harness.studies.loader import load
from solo_harness.studies.validation import validate
from solo_harness.web import ParticipantApplication

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="requires TEST_DATABASE_URL PostgreSQL")
STUDY = Path(__file__).parents[1] / "studies/python_fibonacci_memoization/v0.1"


class Settings:
    database_url = URL
    idempotency_retention_seconds = 3600
    llm_request_timeout_seconds = 1
    llm_stale_grace_seconds = 1
    app_build_id = "test"
    require_active_capture = False
    active_capture_max_age_seconds = 300
    research_data_dir = Path("research-data")


@pytest.fixture
def database():
    engine = create_engine(URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        study = load(STUDY); validate(study); version = activate(db, compile_study(study))
        session = SessionRuntime(StudyCatalog()).create_session(db, version.id)
        session.institutional_id = "TEST-CODE"; db.commit()
    return factory, session.id


def test_idempotency_replays_same_result_and_rejects_changed_payload(database):
    factory, session_id = database
    app = ParticipantApplication.__new__(ParticipantApplication)
    app.settings = Settings()
    calls = []
    with factory() as db:
        def reserve():
            calls.append(True)
            call = LLMCall(session_id=session_id, purpose="TUTOR", status="STARTED", retry_group_id=uuid.uuid4(), retry_number=0, provider="TEST", model="TEST", generation_parameters={}, request_payload={}, request_body_text="")
            db.add(call); db.flush(); return call.id
        first, created = app.reserve_idempotent(db, session_id, "BEGIN", "same-key", {}, reserve)
    with factory() as db:
        replay, replay_created = app.reserve_idempotent(db, session_id, "BEGIN", "same-key", {}, lambda: None)
        assert replay == first and not replay_created and len(calls) == 1
        with pytest.raises(ValueError):
            app.reserve_idempotent(db, session_id, "BEGIN", "same-key", {"changed": True}, lambda: None)


def test_university_id_creates_once_and_never_resumes(database):
    factory, _ = database
    app = ParticipantApplication.__new__(ParticipantApplication)
    app.factory = factory; app.settings = Settings(); app.execution = SimpleNamespace(runtime=SessionRuntime(StudyCatalog())); app.active_session_id = None
    first = app.activate("u20240132")
    assert first is not None
    assert app.activate("u20240132") is None
    with factory() as db:
        rows = db.scalars(select(Session).where(Session.institutional_id == "u20240132")).all()
        assert len(rows) == 1 and rows[0].id == first


def test_required_capture_binds_valid_marker_once(database, tmp_path):
    factory, _ = database
    capture_run_id = uuid.uuid4(); directory = tmp_path / "capture-runs" / str(capture_run_id); directory.mkdir(parents=True)
    (directory / "capture_manifest.json").write_text(json.dumps({"schema_version": "1.0", "capture_run_id": str(capture_run_id), "status": "RECORDING"}))
    (tmp_path / "active_capture.json").write_text(json.dumps({"schema_version": "1.0", "capture_run_id": str(capture_run_id), "status": "RECORDING", "started_at_utc": datetime.now(timezone.utc).isoformat(), "capture_directory": f"capture-runs/{capture_run_id}"}))
    settings = Settings(); settings.require_active_capture = True; settings.research_data_dir = tmp_path
    app = ParticipantApplication.__new__(ParticipantApplication)
    app.factory = factory; app.settings = settings; app.execution = SimpleNamespace(runtime=SessionRuntime(StudyCatalog())); app.active_session_id = None
    created = app.activate("u20240133")
    assert created is not None
    with factory() as db:
        assert db.get(Session, created).capture_run_id == capture_run_id
    exported = build_session_export(URL, created, tmp_path)
    assert exported["data"]["session"]["capture_run_id"] == str(capture_run_id)
    assert exported["data"]["research_artifacts"]["manifests"][0]["relative_path"] == f"research-data/capture-runs/{capture_run_id}/capture_manifest.json"
    assert app.activate("u20240134") is None


def test_two_different_keys_cannot_reserve_two_concurrent_actions(database):
    factory, session_id = database
    app = ParticipantApplication.__new__(ParticipantApplication); app.settings = Settings()
    barrier = Barrier(2)

    def submit(key):
        barrier.wait()
        with factory() as db:
            def reserve():
                if db.scalar(select(LLMCall.id).where(LLMCall.session_id == session_id, LLMCall.status == "STARTED")):
                    raise ValueError("operation already pending")
                call = LLMCall(session_id=session_id, purpose="TUTOR", status="STARTED", retry_group_id=uuid.uuid4(), retry_number=0, provider="TEST", model="TEST", generation_parameters={}, request_payload={}, request_body_text="")
                db.add(call); db.flush(); return call.id
            try:
                return app.reserve_idempotent(db, session_id, "BEGIN", key, {}, reserve)[0]
            except ValueError:
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, ("tab-one", "tab-two")))
    assert sum(result is not None for result in results) == 1
    with factory() as db:
        assert len(db.scalars(select(LLMCall).where(LLMCall.session_id == session_id)).all()) == 1


def test_export_is_stable_complete_and_read_only(database):
    factory, session_id = database
    before = inspect_session(URL, session_id)
    first = build_session_export(URL, session_id)
    second = build_session_export(URL, session_id)
    after = inspect_session(URL, session_id)
    assert first["data_sha256"] == second["data_sha256"]
    assert before == after
    assert first["data"]["session"]["institutional_id_sha256"]
    assert "institutional_id" not in first["data"]["session"]
    assert first["data"]["study_version"]["compiled_snapshot"]
    assert first["data"]["protocol_events"]
    assert first["time_representation"]["research_timezone"] == "Asia/Kolkata"


def test_research_export_uses_ist_for_research_timestamps():
    from solo_harness.research_export import _json_value
    value = datetime.fromisoformat("2026-10-18T19:33:47.585669+00:00")
    assert _json_value(value, "started_at") == "2026-10-19T01:03:47.585669+05:30"


@pytest.mark.asyncio
async def test_startup_recovery_fails_started_and_finishes_received(database):
    factory, session_id = database
    class Execution:
        async def execute(self, db, call_id):
            call = db.get(LLMCall, call_id); call.status = "SUCCEEDED"; call.completed_at = datetime.now(timezone.utc); db.commit()
    app = ParticipantApplication.__new__(ParticipantApplication)
    app.factory = factory; app.execution = Execution()
    with factory() as db:
        started = LLMCall(session_id=session_id, purpose="TUTOR", status="STARTED", retry_group_id=uuid.uuid4(), retry_number=0, provider="TEST", model="TEST", generation_parameters={}, request_payload={}, request_body_text="")
        received = LLMCall(session_id=session_id, purpose="ASSESSMENT", status="RECEIVED", retry_group_id=uuid.uuid4(), retry_number=0, provider="TEST", model="TEST", generation_parameters={}, request_payload={}, request_body_text="", raw_response_text="{}")
        db.add_all([started, received]); db.commit(); started_id, received_id = started.id, received.id
    await app.recover_persisted_operations()
    with factory() as db:
        assert db.get(LLMCall, started_id).error_class == "PROCESS_INTERRUPTED"
        assert db.get(LLMCall, received_id).status == "SUCCEEDED"


def test_semantic_events_are_timestamped_exported_and_do_not_change_protocol(database, tmp_path):
    factory, session_id = database
    run = uuid.uuid4()
    payload = {"events": [{"event_type": "SESSION_PAGE_RENDERED", "surface": "session", "payload": {}, "browser_run_id": str(run), "client_sequence": 1, "client_event_at_utc_ms": 1700000000000, "client_performance_ms": 1.5, "performance_time_origin_ms": 1699999999000.0, "section_number": 1, "teaching_activity_number": 1}]}
    with factory() as db:
        session = db.get(Session, session_id); before = session.phase
        assert record_ui_events(db, session, payload["events"]) == 1
        row = db.scalar(select(ParticipantUIEvent)); assert row.server_received_at.tzinfo is not None and row.attempt_id == session.current_attempt_id
        with pytest.raises(ValueError):
            record_ui_events(db, session, [{**payload["events"][0], "event_type": "KEYDOWN", "client_sequence": 2}])
        assert db.get(Session, session_id).phase == before
    absent = build_session_export(URL, session_id, tmp_path)
    assert absent["data"]["research_artifacts"]["status"] == "ABSENT"
    browser = tmp_path / str(session_id) / "browser"; browser.mkdir(parents=True)
    manifest = browser / "manifest.json"; manifest.write_text(json.dumps({"schema_version": "1.0", "status": "PRESENT"}), encoding="utf-8")
    exported = build_session_export(URL, session_id, tmp_path)
    assert exported["data"]["participant_ui_events"] and exported["data"]["research_artifacts"]["manifests"]
