"""# CHANGED: SQLite-adapted database smoke of real study ORM/AI flow.

SQLite is ONLY a local orchestration-test substitute; PostgreSQL/Alembic
acceptance remains required before launch. No live LLM calls are made.
"""
import asyncio
import json
import os
import uuid
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import CheckConstraint, JSON, create_engine, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Session as SQLSession

from solo_harness.db.base import Base
from solo_harness.db.models import Attempt, LLMCall, Session, SubsectionProgress, PaasResponse, AssessmentInstance, V04Evaluation
from solo_harness.runtime.ai import AIExecutionRuntime, PreparedLLMRequest, RawLLMResponse
from solo_harness.runtime.controlled_executor import contract, state
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.runtime.paas import record_paas_response
from solo_harness.runtime.assessment_persistence import submit_f1_response
from solo_harness.studies.activation import activate
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051

ROOT = Path(__file__).resolve().parents[1]
SCIENTIFIC = ROOT / "studies/networks_error_detection_parity_f1/v0.5"


def _db():
    # Only mutate in-memory SQLAlchemy metadata for this test process, never the app schema.
    changed_columns, removed_constraints = [], []
    for table in Base.metadata.tables.values():
        for col in table.c:
            if isinstance(col.type, ARRAY):
                changed_columns.append((col, col.type))
                col.type = JSON()
        for constraint in list(table.constraints):
            if isinstance(constraint, CheckConstraint) and "~" in str(constraint.sqltext):
                removed_constraints.append((table, constraint))
                table.constraints.discard(constraint)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = SQLSession(engine)
    db.info['sqlite_type_restoration'] = (changed_columns, removed_constraints)
    return db


def _close_db(db):
    # CHANGED: do not contaminate subsequent normal PostgreSQL-model tests.
    columns, constraints = db.info['sqlite_type_restoration']
    db.close()
    for col, original_type in columns:
        col.type = original_type
    for table, constraint in constraints:
        table.append_constraint(constraint)


class _ScriptedLLM:
    def __init__(self):
        self.tutor_count = Counter()
        self.judge_count = Counter()

    def prepare(self, request):
        return PreparedLLMRequest(request, {}, "{}", {})

    async def send(self, prepared):
        request = prepared.request
        if request.logical_role == "TUTOR":
            system = request.messages[0].content
            # Determine current move from the real prompt, not a test-side counter.
            match = next((key for section in ("C1", "C2", "C3", "C4")
                for subsection in contract(section)["subsections"]
                for p in ("P1", "P2", "P3")
                for key in (f"{subsection}-{p}-M01",) if key in system), None)
            # Other move IDs are also in the prompt. Search all if needed.
            if match is None:
                import re
                res = re.search(r"C[1-4]\.\d-P[123]-M\d\d", system)
                if res: match = res.group()
            assert match, system[:300]
            self.tutor_count[match] += 1
            from solo_harness.runtime.controlled_executor import contract as co
            sub, ped, _ = match.split('-')
            authored = next(m for m in co(sub.split('.')[0])["subsections"][sub]["moves_by_pedagogy"][ped] if m['id']==match)
            guided = authored['learner_response_policy']=='guided'
            ready = (not guided or self.tutor_count[match] > 1)
            payload={"learner_message":"Scripted complete scientific teaching for "+match, "ready_for_judge":ready}
        elif request.logical_role == "CONVERSATION_JUDGE":
            payload={"decision":"ADVANCE","guidance":"Author-approved move completed."}
            self.judge_count["ADVANCE"] += 1
        elif request.logical_role == "ASSESSMENT_WRITER":
            if request.response_schema_name == "MCQProse":
                payload = {"stem": "Which conclusion follows from the displayed verified parity case?",
                    "correct_option": "The oracle-backed conclusion.",
                    "distractors": ["Unsupported A.", "Unsupported B.", "Unsupported C."]}
            else:
                payload = {"question": "Explain the displayed parity result using its stated facts."}
        elif request.logical_role == "SEMANTIC_REVIEW":
            if request.response_schema_name == "SemanticReview":
                payload = {"verdict": "ACCEPT", "stem_matches_contract": True,
                    "assumptions_visible": True, "exactly_one_defensible_option": True,
                    "option_assessments": [{"truth_status": "TRUE", "matches_intended_meaning": True,
                        "scientific_reason": "Verified."}, *[{"truth_status": "FALSE",
                        "matches_intended_meaning": True, "scientific_reason": "Unsupported."} for _ in range(3)]],
                    "rationale": "Verified contract."}
            else:
                payload = {"verdict": "ACCEPT", "elicits_slot_evidence": True,
                    "assumes_only_visible_facts": True, "scientifically_consistent": True,
                    "does_not_reveal_answer": True, "rationale": "Verified contract."}
        elif request.logical_role == "JUDGE":
            payload = {"subjective_points": 1, "reason": "Scripted evidence matches minimum rubric anchor."}
        else: raise AssertionError(request.logical_role)
        return RawLLMResponse(None,200,json.dumps(payload),{"choices":[{"message":{"parsed":payload}}]},payload,"stop",False,{},1)


def _settings():
    return SimpleNamespace(llm_provider='test', tutor_model='tutor', judge_model='judge',
        tutor_temperature=0, judge_temperature=0, tutor_max_output_tokens=1000,
        judge_max_output_tokens=1000, llm_request_timeout_seconds=10)


def _run_complete_study(db, pedagogy):
    compiled=compile_v051(load_scientific_v051(SCIENTIFIC))
    version=activate(db,compiled,make_active=True,allow_unified_candidate=True)
    runtime=SessionRuntime(SimpleNamespace(load=lambda *_:compiled))
    created=runtime.create_v051_internal_test_session(db,version.id,
        unified_controlled_study=True,initial_pedagogy_id=pedagogy)
    llm=_ScriptedLLM()
    ai=AIExecutionRuntime(runtime,llm,_settings())
    expected=0
    boundaries=[]
    for section in ('C1','C2','C3','C4'):
        count=0
        subsections=list(contract(section)['subsections'])
        for subsection_id in subsections:
            moves=contract(section)['subsections'][subsection_id]['moves_by_pedagogy'][pedagogy]
            for i,move in enumerate(moves):
                sid=created.id
                call=ai.reserve_tutor(db,sid)
                asyncio.run(ai.execute(db,call))
                active=db.scalar(select(SubsectionProgress).where(
                    SubsectionProgress.session_id==sid,
                    SubsectionProgress.subsection_id==subsection_id,
                    SubsectionProgress.status=='ACTIVE'))
                assert active is not None, (subsection_id,i)
                status=state(active).get('status')
                if move['learner_response_policy']=='guided':
                    assert status=='AWAITING_LEARNER', (move['id'],status)
                    call=ai.reserve_tutor(db,sid,learner_text='I do not know')
                    asyncio.run(ai.execute(db,call))
                    db.refresh(active)
                    status=state(active)['status']
                assert status=='APPROVED_AWAITING_NEXT', (move['id'],status)
                assert state(active)['move_index']==i
                if i == 0 and subsection_id == subsections[0]:
                    # CHANGED: post-approval doubt must not consume Next or
                    # re-credit the already approved move in any C1-C4.
                    previous = state(active)['approval_version']
                    call=ai.reserve_tutor(db,sid,learner_text='Why is this rule valid?')
                    asyncio.run(ai.execute(db,call))
                    db.refresh(active)
                    assert state(active)['status']=='APPROVED_AWAITING_NEXT'
                    assert state(active)['approval_version']==previous
                    assert state(active)['pending_doubt'] is None
                    assert state(active)['move_index']==i
                next_move=runtime.continue_controlled_c11_move(db,sid,state(active)['approval_version'])
                if i<len(moves)-1:
                    assert next_move['id']==moves[i+1]['id']
                count+=1
            db.refresh(active)
            assert active.status=='COMPLETED'
        assert db.get(Session,created.id).phase=='PAAS_PENDING'
        boundaries.append(section)
        expected+=count
        build = ai.reserve_paas_assessment(db, created.id, 5, commit=True)
        assert db.scalar(select(PaasResponse).where(PaasResponse.attempt_id == db.get(Session,created.id).current_attempt_id))
        assert build is not None
        asyncio.run(ai.execute(db, build))
        assessment = db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id == db.get(Session,created.id).current_attempt_id))
        assert assessment.status == 'ACTIVE', (section, assessment.status)
        assert len(assessment.frozen_public_snapshot['mcqs']) == 3
        assert assessment.frozen_metadata_snapshot['generation_method'] == 'verified_authored_fixed_no_writer_reviewer'
        answers = {item['id']: next(private['correct_option_id'] for private in assessment.frozen_private_snapshot['mcqs'] if private['id']==item['id']) for item in assessment.frozen_public_snapshot['mcqs']}
        response = submit_f1_response(db, runtime, created.id, answers,
            'The complete receiver rule was applied correctly.', uuid.uuid4())
        db.commit()
        judge = ai.reserve_f1_judge(db, created.id, response, commit=True)
        asyncio.run(ai.execute(db, judge))
        assert db.scalar(select(V04Evaluation.assessment_response_id).where(V04Evaluation.assessment_response_id == response.id)) is not None
        assert db.get(Session,created.id).phase == 'SECTION_COMPLETE'
        assert db.get(Session,created.id).formal_state_id == {'C1':'U','C2':'M','C3':'R','C4':'EA'}[section]
        if section != 'C4':
            runtime.advance_section(db,created.id)
            next_active=db.scalar(select(SubsectionProgress).where(
                SubsectionProgress.session_id==created.id,
                SubsectionProgress.status=='ACTIVE'))
            assert next_active.subsection_id==list(contract('C'+str(int(section[1])+1))['subsections'])[0]
    # CHANGED: terminal step uses the real four-section completion gate.
    finished = runtime.finish_session(db, created.id)
    session = db.get(Session, created.id)
    assert session.phase == 'TERMINAL'
    assert session.status in ('COMPLETED', 'UNRESOLVED')  # independent rubric decides formal outcome
    assert expected=={'P1':61,'P2':65,'P3':61}[pedagogy]
    assert boundaries==['C1','C2','C3','C4']
    assert llm.judge_count['ADVANCE']==expected + 4  # one post-approval doubt per section
    assert not db.scalars(select(LLMCall.id).where(LLMCall.session_id == created.id,
        LLMCall.purpose.in_(('ASSESSMENT_WRITER','SEMANTIC_REVIEW')))).all()



@pytest.mark.parametrize('pedagogy', ['P1', 'P2', 'P3'])
def test_full_course_real_orm_lifecycle_through_every_move(pedagogy):
    db = _db()
    try:
        _run_complete_study(db, pedagogy)
    finally:
        _close_db(db)

@pytest.mark.skipif(not os.getenv('EKAGRA_STAGE3_DATABASE_URL'), reason='requires disposable migrated PostgreSQL')
@pytest.mark.parametrize('pedagogy', ['P1', 'P2', 'P3'])
def test_full_course_real_postgres_lifecycle_through_every_move(pedagogy):
    # CHANGED: same complete move-by-move test against actual PostgreSQL.
    from solo_harness.db.engine import make_session_factory
    with make_session_factory(os.environ['EKAGRA_STAGE3_DATABASE_URL'])() as db:
        _run_complete_study(db, pedagogy)


def test_legacy_c11_pilot_boundary_remains_unchanged():
    """# CHANGED: an ordinary C1.1 pilot cannot silently become the whole study."""
    db = _db()
    try:
        compiled = compile_v051(load_scientific_v051(SCIENTIFIC))
        version = activate(db, compiled, make_active=False)
        runtime = SessionRuntime(SimpleNamespace(load=lambda *_: compiled))
        session = runtime.create_v051_internal_test_session(db, version.id,
            controlled_c11_pilot=True, initial_pedagogy_id='P1')
        ai = AIExecutionRuntime(runtime, _ScriptedLLM(), _settings())
        for i in range(4):
            call = ai.reserve_tutor(db, session.id)
            asyncio.run(ai.execute(db,call))
            progress = db.scalar(select(SubsectionProgress).where(
                SubsectionProgress.session_id == session.id, SubsectionProgress.subsection_id == 'C1.1'))
            assert state(progress)['move_index'] == i
            assert state(progress)['status'] == 'APPROVED_AWAITING_NEXT'
            next_move = runtime.continue_controlled_c11_move(db, session.id, state(progress)['approval_version'])
            if i < 3: assert next_move['id'] == f'C1.1-P1-M{i+2:02d}'
            else: assert next_move is None
        db.refresh(progress)
        assert progress.status == 'ACTIVE'
        assert state(progress)['status'] == 'PILOT_BOUNDARY_HANDOFF'
        assert db.get(Session,session.id).phase == 'INTERVENTION_ACTIVE'
    finally:
        _close_db(db)
def test_legacy_full_c1_pilot_still_stops_at_its_own_paas_boundary():
    """# CHANGED: full-C1 pilot remains isolated from newly enabled C2-C4."""
    db = _db()
    try:
        compiled = compile_v051(load_scientific_v051(SCIENTIFIC))
        version = activate(db, compiled, make_active=False)
        runtime = SessionRuntime(SimpleNamespace(load=lambda *_: compiled))
        session = runtime.create_v051_internal_test_session(db, version.id,
            controlled_c11_pilot=True, controlled_c1_full_pilot=True,
            initial_pedagogy_id='P1')
        ai = AIExecutionRuntime(runtime, _ScriptedLLM(), _settings())
        for subsection in contract('C1')['subsections']:
            for index in range(4):
                call = ai.reserve_tutor(db, session.id)
                asyncio.run(ai.execute(db,call))
                progress = db.scalar(select(SubsectionProgress).where(
                    SubsectionProgress.session_id == session.id,
                    SubsectionProgress.subsection_id == subsection))
                assert state(progress)['status'] == 'APPROVED_AWAITING_NEXT'
                runtime.continue_controlled_c11_move(db, session.id, state(progress)['approval_version'])
        assert db.get(Session, session.id).phase == 'PAAS_PENDING'
        all_progress=runtime.inspect_v051_subsections(db,session.id)
        assert all(p.status=='COMPLETED' for p in all_progress)
        assert len(all_progress)==4
    finally:
        _close_db(db)


# CHANGED: persisted-state recovery and concurrent-study isolation are separate
# CHANGED: acceptance checks from the uninterrupted 187-move path above.
def test_unified_sessions_remain_isolated_after_runtime_reconstruction():
    # CHANGED: use real ORM rows with distinct assigned pedagogy tracks.
    db = _db()
    try:
        compiled = compile_v051(load_scientific_v051(SCIENTIFIC))
        version = activate(db, compiled, make_active=True, allow_unified_candidate=True)
        catalog = SimpleNamespace(load=lambda *_: compiled)
        runtime = SessionRuntime(catalog)
        first = runtime.create_v051_internal_test_session(
            db, version.id, unified_controlled_study=True, initial_pedagogy_id='P1')
        second = runtime.create_v051_internal_test_session(
            db, version.id, unified_controlled_study=True, initial_pedagogy_id='P2')
        assert first.id != second.id
        ai = AIExecutionRuntime(runtime, _ScriptedLLM(), _settings())
        # CHANGED: finish a real Tutor/Judge call only for the first session.
        call = ai.reserve_tutor(db, first.id)
        asyncio.run(ai.execute(db, call))
        p1 = db.scalar(select(SubsectionProgress).where(
            SubsectionProgress.session_id == first.id, SubsectionProgress.status == 'ACTIVE'))
        p2 = db.scalar(select(SubsectionProgress).where(
            SubsectionProgress.session_id == second.id, SubsectionProgress.status == 'ACTIVE'))
        assert p1.subsection_id == p2.subsection_id == 'C1.1'
        assert state(p1)['status'] == 'APPROVED_AWAITING_NEXT'
        assert state(p2)['status'] == 'TEACHING'
        approval_version = state(p1)['approval_version']
        first_id, second_id = first.id, second.id
        # CHANGED: forget all ORM objects and reconstruct the runtime as after
        # CHANGED: a worker restart; do not reconstruct state from test counters.
        db.expunge_all()
        restarted = SessionRuntime(SimpleNamespace(load=lambda *_: compiled))
        next_move = restarted.continue_controlled_c11_move(db, first_id, approval_version)
        assert next_move['id'] == 'C1.1-P1-M02'
        p1 = db.scalar(select(SubsectionProgress).where(
            SubsectionProgress.session_id == first_id, SubsectionProgress.status == 'ACTIVE'))
        p2 = db.scalar(select(SubsectionProgress).where(
            SubsectionProgress.session_id == second_id, SubsectionProgress.status == 'ACTIVE'))
        assert state(p1)['move_index'] == 1
        assert state(p1)['status'] == 'TEACHING'
        assert state(p2)['move_index'] == 0
        assert state(p2)['status'] == 'TEACHING'
        with pytest.raises(ValueError, match='stale or not approved'):
            restarted.continue_controlled_c11_move(db, first_id, approval_version)
    finally:
        _close_db(db)
