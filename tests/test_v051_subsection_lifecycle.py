"""PostgreSQL integration coverage for the candidate-only Stage 3 lifecycle.

Set EKAGRA_STAGE3_DATABASE_URL to a disposable PostgreSQL database that has
already been migrated to head. The test intentionally uses real ORM rows and
separate database sessions to exercise restart persistence.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import ActiveStudyVersion, Attempt, Message, Session, StudyVersion, SubsectionProgress
from solo_harness.runtime.engine import RandomSelector, SessionRuntime
from solo_harness.studies.activation import activate
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051


DATABASE_URL = os.environ.get("EKAGRA_STAGE3_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="set EKAGRA_STAGE3_DATABASE_URL for PostgreSQL lifecycle integration")
ROOT = Path("studies/networks_error_detection_parity_f1/v0.5")


class _FirstSelector:
    def choice(self, values): return sorted(values)[0]


def _compiled_and_version(db):
    compiled = compile_v051(load_scientific_v051(ROOT))
    version = activate(db, compiled)  # Default must register candidates without activation.
    assert db.get(ActiveStudyVersion, compiled.study_id) is None
    return compiled, version


def _new_attempt(db, runtime, version, compiled, transition_id):
    session = Session(study_version_id=version.id, status="ACTIVE", phase="INTERVENTION_ACTIVE", formal_state_id="P",
                      current_attempt_number=0, application_build_id="stage3-test", runtime_config_snapshot={})
    db.add(session); db.flush()
    attempt = runtime._create_attempt(db, session, compiled, transition_id)
    db.commit()
    return session.id, attempt.id


def _record_complete_active(db, runtime, session_id):
    active = next(item for item in runtime.inspect_v051_subsections(db, session_id) if item.status == "ACTIVE")
    attempt = db.get(Attempt, active.attempt_id)
    message = Message(attempt_id=attempt.id, sequence_no=active.order_in_attempt, role="TUTOR", content_text="Recorded delivery evidence.", content_format="plain", instructional_trace={"subsection_id": active.subsection_id}, material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])
    db.add(message); db.flush()
    move_evidence = {item: [str(message.id)] for item in active.required_move_ids}
    content_evidence = {item: [str(message.id)] for item in active.required_content_ids}
    runtime.record_v051_subsection_evidence(db, session_id, active.subsection_id, move_evidence, content_evidence,
                                            instructional_state={"source": "controlled-test", "tutor_completion": "non_authoritative"},
                                            clarification_evidence_ids=[str(message.id)], commit=False)
    runtime.advance_v051_subsection(db, session_id, active.subsection_id, commit=False)
    return active


def test_v051_subsection_lifecycle_persists_order_evidence_recovery_and_retries():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        compiled, version = _compiled_and_version(db)
        runtime = SessionRuntime(SimpleNamespace(load=lambda _db, _id: compiled), selector=RandomSelector(_FirstSelector()))
        with pytest.raises(ValueError, match="not participant-executable"):
            SessionRuntime(SimpleNamespace(load=lambda _db, _id: compiled)).create_session(SimpleNamespace(), version.id)

        session_ids = {}
        for transition_id, count in {"C1": 4, "C2": 4, "C3": 2, "C4": 3}.items():
            session_id, _ = _new_attempt(db, runtime, version, compiled, transition_id)
            session_ids[transition_id] = session_id
            rows = runtime.inspect_v051_subsections(db, session_id)
            assert len(rows) == count and rows[0].status == "ACTIVE" and all(row.status == "PENDING" for row in rows[1:])
            with pytest.raises(ValueError, match="locked order"):
                runtime.record_v051_subsection_evidence(db, session_id, rows[-1].subsection_id, {}, {}, commit=False)
            with pytest.raises(ValueError, match="incomplete"):
                runtime.advance_v051_subsection(db, session_id, rows[0].subsection_id, commit=False)
            with pytest.raises(ValueError, match="persisted message ids"):
                runtime.record_v051_subsection_evidence(db, session_id, rows[0].subsection_id, {rows[0].required_move_ids[0]: []}, {}, commit=False)

        c1 = session_ids["C1"]
        c2 = session_ids["C2"]
        c1_active = next(row for row in runtime.inspect_v051_subsections(db, c1) if row.status == "ACTIVE")
        c1_attempt = db.get(Attempt, c1_active.attempt_id)
        learner = Message(attempt_id=c1_attempt.id, sequence_no=99, role="LEARNER", content_text="not Tutor evidence", content_format="plain", material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])
        wrong_subsection = Message(attempt_id=c1_attempt.id, sequence_no=100, role="TUTOR", content_text="wrong subsection", content_format="plain", instructional_trace={"subsection_id": "C1.2"}, material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])
        db.add_all([learner, wrong_subsection]); db.flush()
        with pytest.raises(ValueError, match="Tutor messages"):
            runtime.record_v051_subsection_evidence(db, c1, c1_active.subsection_id, {c1_active.required_move_ids[0]: [str(learner.id)]}, {}, commit=False)
        with pytest.raises(ValueError, match="active subsection"):
            runtime.record_v051_subsection_evidence(db, c1, c1_active.subsection_id, {c1_active.required_move_ids[0]: [str(wrong_subsection.id)]}, {}, commit=False)
        with pytest.raises(ValueError, match="does not belong"):
            runtime.inspect_v051_subsections(db, c1, db.get(Attempt, next(row for row in runtime.inspect_v051_subsections(db, c2) if row.status == "ACTIVE").attempt_id).id)
        first = _record_complete_active(db, runtime, c1)
        db.commit()

    # New ORM session proves the committed evidence and active pointer survive a restart.
    with factory() as db:
        compiled = compile_v051(load_scientific_v051(ROOT))
        runtime = SessionRuntime(SimpleNamespace(load=lambda _db, _id: compiled), selector=RandomSelector(_FirstSelector()))
        rows = runtime.inspect_v051_subsections(db, c1)
        assert rows[0].status == "COMPLETED" and rows[0].move_evidence and rows[0].content_evidence
        assert rows[1].status == "ACTIVE"
        current = rows[1]
        attempt = db.get(Attempt, current.attempt_id)
        clarification_a = Message(attempt_id=attempt.id, sequence_no=201, role="TUTOR", content_text="clarification A", content_format="plain", instructional_trace={"subsection_id": current.subsection_id}, material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])
        clarification_b = Message(attempt_id=attempt.id, sequence_no=202, role="TUTOR", content_text="clarification B", content_format="plain", instructional_trace={"subsection_id": current.subsection_id}, material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])
        db.add_all([clarification_a, clarification_b]); db.flush()
        previous_subsection_message = next(iter(rows[0].move_evidence.values()))[0]
        with pytest.raises(ValueError, match="active subsection"):
            runtime.record_v051_subsection_evidence(db, c1, current.subsection_id, {current.required_move_ids[0]: [previous_subsection_message]}, {}, commit=False)
        runtime.record_v051_subsection_evidence(db, c1, current.subsection_id, {}, {}, clarification_evidence_ids=[str(clarification_a.id)], commit=False)
        runtime.record_v051_subsection_evidence(db, c1, current.subsection_id, {}, {}, clarification_evidence_ids=[str(clarification_b.id)], commit=False)
        allowance = runtime.v051_clarification_allowance(db, c1, current.subsection_id)
        assert allowance["used"] == 2 and allowance["remaining"] is None
        assert runtime.v051_clarification_allowance(db, c1, current.subsection_id, approved_limit=3)["remaining"] == 1
        with pytest.raises(ValueError, match="locked order"):
            runtime.advance_v051_subsection(db, c1, first.subsection_id, commit=False)
        while any(row.status == "ACTIVE" for row in runtime.inspect_v051_subsections(db, c1)):
            _record_complete_active(db, runtime, c1)
        db.commit()
        runtime.complete_intervention(db, c1, reason="STAGE3_CONTROLLED_DELIVERY", commit=False)
        assert db.get(Session, c1).phase == "PAAS_PENDING"

        # A retry receives a fresh ordered ledger while the completed first attempt remains intact.
        session = db.get(Session, c1)
        retry = runtime._create_attempt(db, session, compiled, "C1")
        db.commit()
        assert retry.id != rows[0].attempt_id
        assert len(runtime.inspect_v051_subsections(db, c1, retry.id)) == 4
        assert all(row.attempt_id == rows[0].attempt_id for row in runtime.inspect_v051_subsections(db, c1, rows[0].attempt_id))

        c2 = session_ids["C2"]
        active = next(row for row in runtime.inspect_v051_subsections(db, c2) if row.status == "ACTIVE")
        runtime.record_v051_delivery_exception(db, c2, active.subsection_id, {"reason": "controlled missing verified case"}, commit=False)
        db.commit()
        assert db.scalar(select(SubsectionProgress.status).where(SubsectionProgress.id == active.id)) == "DELIVERY_EXCEPTION"
        with pytest.raises(ValueError, match="all v0.5 subsections"):
            runtime.complete_intervention(db, c2, commit=False)
