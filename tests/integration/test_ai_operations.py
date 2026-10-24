import json
import os
import random
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from solo_harness.db.base import Base
import solo_harness.db.models  # noqa: F401
from solo_harness.db.models import AssessmentInstance, AssessmentResponse, LLMCall, Message
from solo_harness.runtime.ai import AIExecutionRuntime, PreparedLLMRequest, RawLLMResponse
from solo_harness.runtime.engine import RandomSelector, SessionRuntime
from solo_harness.studies.activation import activate
from solo_harness.studies.catalog import StudyCatalog
from solo_harness.studies.compiler import compile_study
from solo_harness.studies.loader import load
from solo_harness.studies.validation import validate

URL=os.getenv("TEST_DATABASE_URL")
pytestmark=pytest.mark.skipif(not URL,reason="requires TEST_DATABASE_URL PostgreSQL")
STUDY=Path(__file__).parents[2]/"studies/python_fibonacci_memoization/v0.1"


class ScriptedClient:
    def __init__(self, outputs): self.outputs=list(outputs); self.sent=[]
    def prepare(self, request):
        body={"model":request.model,"messages":[m.model_dump() for m in request.messages],**request.generation_parameters}
        return PreparedLLMRequest(request,body,json.dumps(body),{"Authorization":"Bearer [REDACTED]"})
    async def send(self, prepared):
        self.sent.append(prepared.request.logical_role); text=self.outputs.pop(0)
        payload={"choices":[{"message":{"content":text},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":10,"total_tokens":20}}
        return RawLLMResponse("test",200,json.dumps(payload),payload,text,"stop",False,payload["usage"],5)


class TestSettings:
    llm_provider="TEST_DOUBLE"; tutor_model="openai/gpt-5-nano"; judge_model="openai/gpt-5-nano"
    tutor_temperature=0.2; judge_temperature=0; tutor_max_output_tokens=1000; judge_max_output_tokens=1000
    llm_request_timeout_seconds=120; llm_stale_grace_seconds=30; llm_reasoning_effort="low"


@pytest.fixture
def harness():
    engine=create_engine(URL); Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    factory=sessionmaker(engine,expire_on_commit=False); catalog=StudyCatalog()
    with factory() as db:
        study=load(STUDY); validate(study); version=activate(db,compile_study(study))
    runtime=SessionRuntime(catalog,RandomSelector(random.Random(7),"seeded_random","7"))
    return factory,runtime,version.id


def tutor(move, disposition="CONTINUE", next_move=None):
    return json.dumps({"schema_version":"1.0","learner_message":"A freshly generated teaching message.","disposition":disposition,"current_move_id":move,"next_move_id":next_move,"progress_summary":"Compact persisted progress."})


@pytest.mark.asyncio
async def test_tutor_failure_is_manual_and_retry_does_not_duplicate_learner(harness):
    factory,runtime,version_id=harness; client=ScriptedClient([]); execution=AIExecutionRuntime(runtime,client,TestSettings())
    with factory() as db:
        session=runtime.create_session(db,version_id); study=runtime._compiled(db,session); attempt=db.get(solo_harness.db.models.Attempt,session.current_attempt_id); move=study.cells[f"C1:{attempt.pedagogy_id}"]["move_ids"][0]
        client.outputs += [tutor(move), "not-json", tutor(move)]
        await execution.execute(db,execution.reserve_tutor(db,session.id))
        await execution.execute(db,execution.reserve_tutor(db,session.id,"my one answer"))
        assert db.scalars(select(Message).where(Message.attempt_id==attempt.id,Message.role=="LEARNER")).all().__len__()==1
        failed=db.scalar(select(LLMCall).where(LLMCall.status=="INVALID_OUTPUT")); assert failed and len(client.sent)==2
        await execution.execute(db,execution.reserve_manual_retry(db,session.id))
        assert len(db.scalars(select(Message).where(Message.attempt_id==attempt.id,Message.role=="LEARNER")).all())==1
        assert len(db.scalars(select(Message).where(Message.attempt_id==attempt.id,Message.role=="TUTOR")).all())==2


@pytest.mark.asyncio
async def test_assessment_is_generated_and_frozen_once(harness):
    factory,runtime,version_id=harness; client=ScriptedClient([]); execution=AIExecutionRuntime(runtime,client,TestSettings())
    with factory() as db:
        session=runtime.create_session(db,version_id); study=runtime._compiled(db,session); attempt=db.get(solo_harness.db.models.Attempt,session.current_attempt_id); move=study.cells[f"C1:{attempt.pedagogy_id}"]["move_ids"][0]
        client.outputs += [tutor(move), tutor(move,"COMPLETE"), json.dumps({"schema_version":"1.0","learner_prompt":"Explain the relationship between two smaller recursive calls and the terminating cases in this fresh scenario.","hidden_scoring_context":"Require two-predecessor dependence and correct terminating base cases."})]
        await execution.execute(db,execution.reserve_tutor(db,session.id)); await execution.execute(db,execution.reserve_tutor(db,session.id,"They combine two prior values."))
        assessment=db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id==attempt.id)); frozen=assessment.prompt_snapshot
        assert assessment.status=="ACTIVE" and assessment.generation_llm_call_id and assessment.blueprint_snapshot and frozen
        assert client.sent==["TUTOR","TUTOR","ASSESSMENT"]
        with pytest.raises(ValueError): execution.reserve_assessment(db,session.id,assessment.id)
        assert assessment.prompt_snapshot==frozen


@pytest.mark.asyncio
async def test_judge_gets_exactly_one_automatic_retry(harness):
    factory,runtime,version_id=harness; client=ScriptedClient([]); execution=AIExecutionRuntime(runtime,client,TestSettings())
    with factory() as db:
        session=runtime.create_session(db,version_id); study=runtime._compiled(db,session); attempt=db.get(solo_harness.db.models.Attempt,session.current_attempt_id); move=study.cells[f"C1:{attempt.pedagogy_id}"]["move_ids"][0]
        client.outputs += [tutor(move),tutor(move,"COMPLETE"),json.dumps({"schema_version":"1.0","learner_prompt":"Explain how a recursive Fibonacci case combines two smaller calls and reaches terminating cases.","hidden_scoring_context":"Require the two predecessors and base cases."}),"bad","still bad"]
        await execution.execute(db,execution.reserve_tutor(db,session.id)); await execution.execute(db,execution.reserve_tutor(db,session.id,"Two calls are combined."))
        await execution.execute(db,execution.reserve_judge(db,session.id,"It uses both prior calls and stops at zero or one."))
        calls=db.scalars(select(LLMCall).where(LLMCall.purpose=="JUDGE").order_by(LLMCall.retry_number)).all()
        assert [c.retry_number for c in calls]==[0,1] and all(c.status=="INVALID_OUTPUT" for c in calls)
        assert db.scalar(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id==calls[0].assessment_instance_id)) is not None
