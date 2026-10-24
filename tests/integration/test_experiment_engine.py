"""Runs only against an explicitly supplied PostgreSQL database."""
import os
from pathlib import Path
import random
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from solo_harness.db.base import Base
import solo_harness.db.models  # noqa: F401
from solo_harness.runtime.engine import JudgeObservation, RandomSelector, SessionRuntime
from solo_harness.db.models import Attempt, LLMCall
from solo_harness.studies.activation import activate
from solo_harness.studies.catalog import StudyCatalog
from solo_harness.studies.compiler import compile_study
from solo_harness.studies.loader import load
from solo_harness.studies.validation import validate

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="requires TEST_DATABASE_URL PostgreSQL")
STUDY = Path(__file__).parents[2] / "studies/python_fibonacci_memoization/v0.1"

@pytest.fixture
def runtime():
    engine=create_engine(URL); Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    factory=sessionmaker(engine, expire_on_commit=False); catalog=StudyCatalog()
    with factory() as db:
        study=load(STUDY); validate(study); version=activate(db,compile_study(study))
    return factory, SessionRuntime(catalog, RandomSelector(random.Random(7),"seeded_random","7")), version.id

def _pass(runtime, db, session_id):
    from solo_harness.db.models import Session, Attempt
    session=db.get(Session,session_id); attempt=db.get(Attempt,session.current_attempt_id)
    _activate_assessment(runtime,db,session_id); runtime.submit_assessment(db,session_id,"answer")
    compiled=runtime._compiled(db,session); rubric=compiled.rubrics[attempt.transition_id]; transition=compiled.knowledge_slices[attempt.transition_id]["transition"]
    evidence=tuple(rubric["evidence_ids"])
    call=_judge_call(db,session,attempt)
    runtime.apply_judgment(db,session_id,JudgeObservation(True,"CORRECT",transition["target_state_id"],evidence),call.id)

def _judge_call(db, session, attempt):
    from solo_harness.db.models import AssessmentInstance
    assessment=db.scalar(__import__('sqlalchemy').select(AssessmentInstance).where(AssessmentInstance.attempt_id==attempt.id))
    call=LLMCall(session_id=session.id,attempt_id=attempt.id,assessment_instance_id=assessment.id,purpose="JUDGE",status="SUCCEEDED",retry_group_id=uuid.uuid4(),retry_number=0,provider="TEST_DOUBLE",model="TEST_DOUBLE",generation_parameters={},request_payload={},request_body_text="",completed_at=datetime.now(timezone.utc)); db.add(call); db.flush(); return call

def _activate_assessment(runtime, db, session_id):
    from solo_harness.db.models import Session, AssessmentInstance
    session=db.get(Session,session_id); assessment=runtime.complete_intervention(db,session_id)
    assessment.prompt_snapshot="Generated test prompt"; assessment.hidden_scoring_context_snapshot="Generated scoring context"; assessment.status="ACTIVE"
    db.get(Attempt,session.current_attempt_id).status="ASSESSMENT_ACTIVE"; session.phase="ASSESSMENT_ACTIVE"; db.commit(); return assessment

def test_straight_success_to_ea(runtime):
    factory, service, version_id=runtime
    with factory() as db:
        session=service.create_session(db,version_id)
        for section in range(4):
            _pass(service,db,session.id)
            assert session.phase == "SECTION_COMPLETE"
            service.finish_session(db, session.id) if section == 3 else service.advance_section(db, session.id)
        db.refresh(session)
        assert session.status=="COMPLETED" and session.terminal_reason=="COMPLETED_EA"

def test_failure_then_success_gets_new_pedagogy_and_history(runtime):
    factory, service, version_id=runtime
    with factory() as db:
        session=service.create_session(db,version_id); first=session.current_attempt_id
        _activate_assessment(service,db,session.id); service.submit_assessment(db,session.id,"bad")
        service.apply_judgment(db,session.id,JudgeObservation(False,"NOT_GRADABLE",None,()),_judge_call(db,session,db.get(Attempt,session.current_attempt_id)).id)
        db.refresh(session); second=session.current_attempt_id
        from solo_harness.db.models import LearnerHistorySnapshot
        assert first!=second and db.get(Attempt,first).pedagogy_id!=db.get(Attempt,second).pedagogy_id
        assert db.scalar(__import__('sqlalchemy').select(LearnerHistorySnapshot).where(LearnerHistorySnapshot.target_attempt_id==second))

def test_three_failures_allow_administrative_continuation_without_false_pass(runtime):
    factory, service, version_id=runtime
    with factory() as db:
        session=service.create_session(db,version_id)
        for _ in range(3):
            _activate_assessment(service,db,session.id); service.submit_assessment(db,session.id,"bad")
            service.apply_judgment(db,session.id,JudgeObservation(False,"NOT_GRADABLE",None,()),_judge_call(db,session,db.get(Attempt,session.current_attempt_id)).id)
        db.refresh(session)
        attempts=db.scalars(__import__('sqlalchemy').select(Attempt).where(Attempt.session_id==session.id).order_by(Attempt.sequence_in_transition)).all()
        assert session.status=="ACTIVE" and session.phase=="SECTION_COMPLETE"
        assert session.formal_state_id == "P"
        assert attempts[-1].outcome_details["administrative_outcome"] == "PEDAGOGIES_EXHAUSTED_CONTINUE"
        assert len(attempts)==3 and len({a.pedagogy_id for a in attempts})==3
        service.advance_section(db, session.id)
        db.refresh(session)
        assert session.current_transition_id == "C2" and session.formal_state_id == "P"
