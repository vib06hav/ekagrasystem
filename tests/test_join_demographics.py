"""Demographic enrollment contracts without touching real study participants or PostgreSQL."""

import importlib.util
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect
from starlette.middleware.sessions import SessionMiddleware

from solo_harness.db.models import Session
from solo_harness.research_export import EXPORT_SCHEMA_VERSION, _row
from solo_harness.web import ParticipantApplication, _validate_join_details, participant_router


class DummyApplication:
    settings = SimpleNamespace(participant_study_title="Test Study", require_active_capture=False)

    def __init__(self):
        self.calls = []
        self.id = uuid.uuid4()

    def activate(self, institutional_id, **kwargs):
        self.calls.append((institutional_id, kwargs))
        return self.id


@pytest.fixture
def web_client():
    backend = DummyApplication()
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-only")
    app.include_router(participant_router(backend))
    return TestClient(app), backend


def _form(**overrides):
    data = {
        "institutional_id": " P-200 ", "age": "19", "gender": "other",
        "educational_qualification": "higher_secondary_school", "acknowledged": "yes",
    }
    data.update(overrides)
    return data


def test_enrollment_post_saves_parsed_demographics_and_session_cookie(web_client):
    client, backend = web_client
    response = client.post("/join", data=_form(), follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/session"
    assert backend.calls == [("P-200", {
        "age": 19, "gender": "other", "educational_qualification": "higher_secondary_school",
    })]
    assert "session" in response.cookies


@pytest.mark.parametrize("changes", [
    {"age": "20.5"}, {"age": "-1"}, {"age": "121"}, {"age": "0"},
    {"age": "not-an-age"}, {"gender": "invalid"},
    {"educational_qualification": "other_degree"}, {"institutional_id": "   "},
    {"acknowledged": "no"},
])
def test_tampered_join_rejected_before_session_creation(web_client, changes):
    client, backend = web_client
    response = client.post("/join", data=_form(**changes), follow_redirects=False)
    assert response.status_code == 422
    assert backend.calls == []
    assert "session" not in response.cookies
    assert 'id="id-entry"' in response.text


def test_missing_required_fields_are_rejected(web_client):
    client, backend = web_client
    for field in ("age", "gender", "educational_qualification", "acknowledged"):
        data = _form()
        data.pop(field)
        response = client.post("/join", data=data, follow_redirects=False)
        assert response.status_code == 422
    assert backend.calls == []


def test_consent_discloses_new_fields_but_keeps_draft_warning(web_client):
    client, _ = web_client
    response = client.get("/join")
    assert response.status_code == 200
    assert "Your age, gender and educational qualification" in response.text
    assert "PENDING RESEARCH-TEAM APPROVAL" in response.text


def test_valid_options_match_enrollment_form():
    assert _validate_join_details(" Test-1 ", "20", "female", "undergraduate", "yes") == (
        "Test-1", 20, "female", "undergraduate",
    )


def test_activate_attaches_demographics_atomically_to_session():
    application = ParticipantApplication.__new__(ParticipantApplication)
    application.settings = SimpleNamespace(
        require_active_capture=False, enable_f1_v04_development=True,
        enable_v051_unified_study=False, app_build_id="test",
    )
    application.factory = MagicMock()
    db = application.factory.return_value.__enter__.return_value
    db.scalar.side_effect = [None, SimpleNamespace(study_version_id=uuid.uuid4())]
    application.execution = MagicMock()
    application.execution.runtime.catalog.load.return_value = SimpleNamespace(authored={"v04": True})
    session = SimpleNamespace(id=uuid.uuid4(), current_attempt_id=uuid.uuid4())
    application.execution.runtime.create_session.return_value = session
    assert application.activate("Sample", age=18, gender="male", educational_qualification="undergraduate") == session.id
    assert (session.age, session.gender, session.educational_qualification) == (18, "male", "undergraduate")
    db.commit.assert_called_once()
    # Demographics are not included in prompt-visible config or protocol event payloads.
    kwargs = application.execution.runtime.create_session.call_args.kwargs
    assert not any(key in kwargs["runtime_config"] for key in ("age", "gender", "educational_qualification"))
    event_kwargs = application.execution.runtime._event.call_args.args[3]
    assert not any(key in event_kwargs for key in ("age", "gender", "educational_qualification"))


def test_legacy_sessions_are_nullable_and_research_export_includes_demographics():
    prior = Session(institutional_id="test")
    assert _row(prior)["age"] is None
    newer = Session(institutional_id="test", age=20, gender="female", educational_qualification="postgraduate")
    projected = _row(newer, omit={"institutional_id"})
    assert (projected["age"], projected["gender"], projected["educational_qualification"]) == (
        20, "female", "postgraduate",
    )
    assert "institutional_id" not in projected
    assert EXPORT_SCHEMA_VERSION == "1.5"


def test_migration_adds_nullable_columns_to_existing_sessions_and_is_idempotent():
    path = Path(__file__).resolve().parents[1] / "migrations/versions/0011_session_demographics.py"
    spec = importlib.util.spec_from_file_location("demographics_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        metadata = MetaData()
        Table("sessions", metadata, Column("institutional_id", String))
        metadata.create_all(connection)
        context = MigrationContext.configure(connection)
        operations = Operations(context)
        original_op = module.op
        try:
            module.op = operations
            module.upgrade()
            module.upgrade()
            columns = {c["name"]: c for c in inspect(connection).get_columns("sessions")}
            assert {"age", "gender", "educational_qualification"} <= columns.keys()
            assert not columns["age"]["nullable"] is False
            module.downgrade()
            assert "age" not in {c["name"] for c in inspect(connection).get_columns("sessions")}
        finally:
            module.op = original_op
