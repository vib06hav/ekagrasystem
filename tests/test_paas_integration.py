"""Paas integration smoke checks without a live PostgreSQL or LLM server.

These do not replace the transaction/restart verification required in Docker.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import CheckConstraint, UniqueConstraint

from solo_harness.db.models import PaasResponse
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.runtime.paas import ANCHORS, instrument_snapshot, record_paas_response, validate_rating


class _SessionLockDb:
    def __init__(self):
        self.session = SimpleNamespace(id=uuid.uuid4(), status="ACTIVE", phase="INTERVENTION_ACTIVE", current_attempt_id=uuid.uuid4(), last_event_sequence=0)
        self.attempt = SimpleNamespace(id=self.session.current_attempt_id, session_id=self.session.id, transition_id="C1", pedagogy_id="P1", completion_reason=None, status="INTERVENTION_ACTIVE", intervention_completed_at=None)
        self.events = []
        self.rating = None
        self.assessment = None
        self.commits = 0

    def scalar(self, query):
        # All queries in these two routines are either the locked Session or
        # existing PaasResponse selection. No live DB behavior is simulated.
        name = query.column_descriptions[0].get("name")
        if name == "Session":
            return self.session
        return None if self.rating is None else self.rating.id

    def get(self, klass, key):
        if klass.__name__ == "Attempt" and key == self.attempt.id:
            return self.attempt
        return None

    def add(self, obj):
        if isinstance(obj, PaasResponse):
            self.rating = obj
            obj.id = uuid.uuid4()
        elif obj.__class__.__name__ == "AssessmentInstance":
            self.assessment = obj
            obj.id = uuid.uuid4()
        else:
            self.events.append(obj)

    def scalars(self, query):
        return SimpleNamespace(all=lambda: [])

    def flush(self):
        pass

    def commit(self):
        self.commits += 1


def test_instrument_has_all_nine_ordered_categories_and_fixed_referent():
    snapshot = instrument_snapshot()
    assert snapshot["referent"] == "JUST_COMPLETED_TUTOR_INTERVENTION"
    assert len(ANCHORS) == 9
    assert [x["value"] for x in snapshot["anchors"]] == list(range(1, 10))
    assert snapshot["instrument_version"] == "1.0"
    assert snapshot["question"].endswith("you just completed?")


@pytest.mark.parametrize("invalid", [0, -1, 10, 1.0, "5", True, None])
def test_invalid_ratings_rejected(invalid):
    with pytest.raises(ValueError):
        validate_rating(invalid)


@pytest.mark.parametrize("rating", [1, 5, 9])
def test_valid_ratings(rating):
    assert validate_rating(rating) == rating


def test_database_has_once_per_attempt_and_1_to_9_constraints():
    table = PaasResponse.__table__
    assert any(isinstance(item, CheckConstraint) and "BETWEEN 1 AND 9" in str(item.sqltext) for item in table.constraints)
    assert table.c.attempt_id.unique is True


def test_teaching_to_paas_to_single_rating_without_assessment():
    db = _SessionLockDb()
    runtime = SessionRuntime(None)
    attempt = runtime.complete_intervention(db, db.session.id, "TUTOR_COMPLETE", commit=False)
    assert attempt.id == db.attempt.id
    assert db.session.phase == "PAAS_PENDING"
    assert db.attempt.status == "PAAS_PENDING"
    assert db.attempt.completion_reason == "TUTOR_COMPLETE"
    assert [e.event_type for e in db.events] == ["INTERVENTION_COMPLETED", "PAAS_PRESENTED"]
    with pytest.raises(ValueError):
        runtime.complete_intervention(db, db.session.id)

    response = record_paas_response(db, db.session.id, 7, commit=False)
    assert response.rating == 7
    assert response.transition_id == "C1"
    assert response.pedagogy_id == "P1"
    assert response.completion_reason == "TUTOR_COMPLETE"
    assert response.question_snapshot == instrument_snapshot()["question"]
    with pytest.raises(ValueError):
        record_paas_response(db, db.session.id, 8)


def test_paas_template_renders_separate_nine_choice_form():
    env = Environment(loader=FileSystemLoader("src/solo_harness/templates"))
    view = dict(
        phase="PAAS_PENDING", status="ACTIVE", is_current=True, sections=[dict(enabled=True, state="current", number=1)],
        section_number=1, timeline=[], started_at=None, ended_at=None, pending=False, retryable=False,
        technical_hold=False, paas_instrument=instrument_snapshot(), attempt_status="PAAS_PENDING",
    )
    rendered = env.get_template("partials/session_main.html").render(view=view, settings=SimpleNamespace(enable_f1_v04_development=False), new_key="abc")
    assert 'hx-post="/session/actions/paas"' in rendered
    assert rendered.count('name="rating"') == 9
    assert 'hx-post="/session/actions/assessment-response"' not in rendered
    assert 'hx-post="/session/actions/development-advance"' not in rendered


def test_assessment_is_selected_only_after_paas_rating():
    db = _SessionLockDb()
    form = {
        "id": "C1-A2", "target_kc_ids": [], "target_relation_ids": [],
        "target_evidence_ids": [], "relevant_misconception_ids": [],
    }
    compiled = SimpleNamespace(assessment_families={"C1": {"id": "C1-fam", "forms": [form]}})
    runtime = SessionRuntime(SimpleNamespace(load=lambda db, version: compiled))
    runtime._compiled = lambda db, session: compiled
    runtime.complete_intervention(db, db.session.id, commit=False)
    with pytest.raises(ValueError, match="Paas response is required"):
        runtime.begin_assessment_after_paas(db, db.session.id, commit=False)
    record_paas_response(db, db.session.id, 4, commit=False)
    assessment = runtime.begin_assessment_after_paas(db, db.session.id, commit=False)
    assert assessment.id == db.assessment.id
    assert assessment.assessment_form_id == "C1-A2"
    assert db.session.phase == "ASSESSMENT_GENERATING"
    assert db.attempt.status == "ASSESSMENT_GENERATING"
    assert any(e.event_type == "ASSESSMENT_SELECTED" and e.payload["paas_response_id"] == str(db.rating.id) for e in db.events)
    with pytest.raises(ValueError):
        runtime.begin_assessment_after_paas(db, db.session.id, commit=False)
