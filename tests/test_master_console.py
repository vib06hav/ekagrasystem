"""Master Console: fixed-study isolation, true direct entry, and token/CSRF guards."""
import io
import json
import re
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SQLSession, sessionmaker
from starlette.middleware.sessions import SessionMiddleware

from solo_harness.db.base import Base
from solo_harness.db.models import (
    AssessmentInstance, Attempt, LLMCall, PaasResponse, ProtocolEvent, Session, SubsectionProgress,
)
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.runtime.master_console import create_master_session, is_master_session
from solo_harness.studies.activation import activate
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051
from solo_harness.web import ParticipantApplication, _master_console_enabled, participant_router

from test_unified_c1_c4_sqlite_runtime import _db, _close_db

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def setup_runtime():
    db = _db()
    compiled = compile_v051(load_scientific_v051(ROOT / 'studies/networks_error_detection_parity_f1/v0.5'))
    version = activate(db, compiled, make_active=True, allow_unified_candidate=True)
    runtime = SessionRuntime(SimpleNamespace(load=lambda *_: compiled))
    try:
        yield db, compiled, version, runtime
    finally:
        _close_db(db)


@pytest.mark.parametrize('section,pedagogy', [('C1','P1'), ('C2','P2'), ('C3','P3'), ('C4','random')])
def test_direct_teaching_starts_at_chosen_section_without_fabricated_history(setup_runtime, section, pedagogy):
    db, compiled, version, runtime = setup_runtime
    created = create_master_session(db, runtime, version.id, section=section,
                                    pedagogy=pedagogy, mode='teaching')
    attempt = db.get(Attempt, created.current_attempt_id)
    progress = db.scalars(select(SubsectionProgress).where(SubsectionProgress.session_id == created.id)).all()
    assert is_master_session(created)
    assert created.institutional_id.startswith('DEV-')
    assert (created.age, created.gender, created.educational_qualification) == (20, 'other', 'undergraduate')
    assert created.formal_state_id == compiled.knowledge_slices[section]['transition']['from_state_id']
    assert created.current_transition_id == section
    assert attempt.pedagogy_id == (pedagogy if pedagogy != 'random' else attempt.pedagogy_id)
    assert attempt.pedagogy_id in ('P1','P2','P3')
    assert attempt.sequence_in_transition == 1 and attempt.status == 'ASSIGNED'
    assert len(progress) == len(runtime._v051_specs(compiled, attempt))
    assert progress[0].status == 'ACTIVE'
    assert {item.subsection_id.split('.')[0] for item in progress} == {section}
    assert db.scalars(select(AssessmentInstance).where(AssessmentInstance.session_id == created.id)).all() == []
    assert db.scalars(select(PaasResponse).where(PaasResponse.session_id == created.id)).all() == []


@pytest.mark.parametrize('section,set_id', [('C1','A'), ('C2','B'), ('C3','C'), ('C4','A')])
def test_direct_assessment_is_frozen_without_teaching_paas_or_build_call(setup_runtime, section, set_id):
    db, compiled, version, runtime = setup_runtime
    created = create_master_session(db, runtime, version.id, section=section, pedagogy='P2',
                                    mode='assessment', assessment_set=set_id)
    attempt = db.get(Attempt, created.current_attempt_id)
    item = db.scalar(select(AssessmentInstance).where(AssessmentInstance.session_id == created.id))
    assert is_master_session(created)
    assert created.formal_state_id == compiled.knowledge_slices[section]['transition']['from_state_id']
    assert attempt.status == 'ASSESSMENT_ACTIVE' and created.phase == 'ASSESSMENT_ACTIVE'
    assert attempt.completion_reason is None and attempt.intervention_completed_at is None
    assert item.assessment_form_id == f'{section}-SET-{set_id}'
    assert item.frozen_schema_version == 'v051.fixed.1' and item.status == 'ACTIVE'
    assert len(item.frozen_public_snapshot['mcqs']) == len(item.frozen_private_snapshot['mcqs']) == 3
    assert item.frozen_public_snapshot['subjective']['id'] == 'SUB1'
    assert 'subjective_resolved' not in item.frozen_public_snapshot
    for public, private in zip(item.frozen_public_snapshot['mcqs'], item.frozen_private_snapshot['mcqs']):
        assert private['correct_option_id'] in {x['id'] for x in public['options']}
        assert 'oracle' not in public
    assert db.scalars(select(SubsectionProgress).where(SubsectionProgress.session_id == created.id)).all() == []
    assert db.scalars(select(PaasResponse).where(PaasResponse.session_id == created.id)).all() == []
    assert db.scalars(select(LLMCall).where(LLMCall.session_id == created.id)).all() == []
    events = [x.event_type for x in db.scalars(select(ProtocolEvent).where(ProtocolEvent.session_id == created.id))]
    assert 'MASTER_CONSOLE_ASSESSMENT_OPENED' in events
    assert 'PAAS_RECORDED' not in events


def test_bad_selections_are_rejected_without_creating_sessions(setup_runtime):
    db, _, version, runtime = setup_runtime
    for kwargs in [
        dict(section='C5', pedagogy='P1', mode='teaching'),
        dict(section='C1', pedagogy='P4', mode='teaching'),
        dict(section='C1', pedagogy='P1', mode='unknown'),
        dict(section='C1', pedagogy='P1', mode='assessment', assessment_set='D'),
        dict(section='C1', pedagogy='P1', mode='teaching', assessment_set='B'),
    ]:
        with pytest.raises(ValueError):
            create_master_session(db, runtime, version.id, **kwargs)
    assert db.scalar(select(Session.id)) is None


def test_console_requires_explicit_development_environment():
    assert not _master_console_enabled(SimpleNamespace(app_environment='production'))
    assert _master_console_enabled(SimpleNamespace(app_environment='development'))


def test_http_console_direct_dev_access_csrf_launch_and_restricted_trace(setup_runtime, monkeypatch, tmp_path):
    _, compiled, _, runtime = setup_runtime
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'master.sqlite'}")
    Base.metadata.create_all(engine)
    db = SQLSession(engine)
    version = activate(db, compiled, make_active=True, allow_unified_candidate=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = SimpleNamespace(
        app_environment='development', enable_v051_internal_testing=False,
        enable_v051_unified_study=True,
        web_session_secret=SecretStr('long-test-cookie-signing-secret-1234567890'),
        v051_internal_candidate_version='v0.5.5', app_build_id='master-test',
        research_data_dir=tmp_path, required_capture_streams='screen',
        active_capture_max_age_seconds=30, database_url='sqlite:///:memory:',
    )
    backend = ParticipantApplication.__new__(ParticipantApplication)
    backend.settings = settings
    backend.factory = factory
    backend.execution = SimpleNamespace(runtime=runtime)
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key=settings.web_session_secret.get_secret_value())
    app.include_router(participant_router(backend))
    client = TestClient(app)
    assert client.get('/internal/master').status_code == 200
    screen = client.get('/internal/master')
    assert 'Create a test session' in screen.text
    csrf = re.search(r'name="csrf" value="([^"]+)"', screen.text).group(1)
    form = dict(section='C3',pedagogy='P3',mode='assessment',assessment_set='B',csrf=csrf)
    assert client.post('/internal/master/launch', data={**form,'csrf':'invalid'}).status_code == 403
    response = client.post('/internal/master/launch',data=form,follow_redirects=False)
    assert response.status_code == 303 and response.headers['location'] == '/session'
    delivered = client.get('/session')
    assert delivered.status_code == 200
    assert 'Answer all four questions' in delivered.text
    assert 'C3' in delivered.text
    assert 'section-link skipped' in delivered.text
    current = db.scalars(select(Session).order_by(Session.created_at.desc())).first()
    assert current and is_master_session(current) and current.current_transition_id == 'C3'
    item = db.scalar(select(AssessmentInstance).where(AssessmentInstance.session_id==current.id))
    assert item.assessment_form_id == 'C3-SET-B'
    from solo_harness.research_export import build_session_export
    actual_export = build_session_export(
        f"sqlite+pysqlite:///{tmp_path / 'master.sqlite'}", current.id, research_data_root=tmp_path,
    )
    assert 'subsection_progress' in actual_export['data']
    assert 'conversation_judge_decisions' in actual_export['data']
    assert actual_export['data']['session']['runtime_config_snapshot']['master_console_test'] is True
    monkeypatch.setattr('solo_harness.research_export.build_session_export',
                        lambda *a,**k: {'data':{'session':{'id':str(current.id)}},'data_sha256':'test'})
    archive = client.get(f'/internal/master/trace/{current.id}')
    assert archive.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
        assert {'session_export.json','manifest.json'} <= set(z.namelist())
        assert json.loads(z.read('manifest.json'))['synthetic_dev_session'] is True
    assert client.get(f'/internal/master/trace/{uuid.uuid4()}').status_code == 404
    settings.app_environment = 'production'
    assert client.get('/internal/master').status_code == 404
    assert client.get(f'/internal/master/trace/{current.id}').status_code == 404


@pytest.mark.parametrize('pass_assessment', [True, False])
def test_direct_assessment_uses_real_submission_judge_and_retry_flow(setup_runtime, pass_assessment):
    import asyncio
    from solo_harness.runtime.assessment_persistence import submit_f1_response
    from solo_harness.runtime.ai import AIExecutionRuntime
    from test_unified_c1_c4_sqlite_runtime import _ScriptedLLM, _settings

    db, _, version, runtime = setup_runtime
    db.bind.dialect._json_serializer = lambda obj: json.dumps(obj, default=str)
    created = create_master_session(db, runtime, version.id, section='C4',
                                    pedagogy='P2', mode='assessment', assessment_set='B')
    item = db.scalar(select(AssessmentInstance).where(AssessmentInstance.session_id == created.id))
    answers = {private['id']: (private['correct_option_id'] if pass_assessment else
        next(x['id'] for x in public['options'] if x['id'] != private['correct_option_id']))
        for public, private in zip(item.frozen_public_snapshot['mcqs'], item.frozen_private_snapshot['mcqs'])}
    response = submit_f1_response(db, runtime, created.id, answers, 'A relevant parity explanation.', uuid.uuid4())
    db.commit()
    ai = AIExecutionRuntime(runtime, _ScriptedLLM(), _settings())
    call = ai.reserve_f1_judge(db, created.id, response)
    asyncio.run(ai.execute(db, call))
    db.refresh(created)
    if pass_assessment:
        assert created.phase == 'SECTION_COMPLETE'
        assert created.formal_state_id == 'EA'
        assert created.current_transition_id == 'C4'
    else:
        assert created.phase == 'INTERVENTION_ACTIVE'
        retry = db.get(Attempt, created.current_attempt_id)
        assert retry.sequence_in_transition == 2
        assert retry.pedagogy_id != 'P2'
        assert len(db.scalars(select(SubsectionProgress).where(
            SubsectionProgress.attempt_id == retry.id)).all()) == 3
