"""One complete development F1 v0.4 session using the configured provider."""
from __future__ import annotations
import asyncio, json, uuid
from sqlalchemy import select
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance, AssessmentResponse, Attempt, LLMCall, Message, Session, V04Evaluation
from solo_harness.runtime.ai import AIExecutionRuntime, OpenAICompatibleClient
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.runtime.v04_persistence import submit_f1_response

def main():
    cfg=get_settings(); db=make_session_factory(cfg.database_url)(); runtime=SessionRuntime(bootstrap(cfg))
    source=db.scalar(select(Session).order_by(Session.created_at.desc())); assert source is not None
    session=runtime.create_session(db,source.study_version_id,build_id="task7-real-provider",institutional_id="task7-real-"+uuid.uuid4().hex[:12],commit=True)
    ai=AIExecutionRuntime(runtime,OpenAICompatibleClient(cfg),cfg)
    tutor=ai.reserve_tutor(db,session.id,commit=True); asyncio.run(ai.execute(db,tutor))
    session=db.get(Session,session.id)
    advance=None
    if session.phase=="INTERVENTION_ACTIVE":
        advance=ai.reserve_development_assessment(db,session.id,commit=True)
        asyncio.run(ai.execute(db,advance))
    item=db.scalar(select(AssessmentInstance).where(AssessmentInstance.session_id==session.id)); session=db.get(Session,session.id)
    assert item and item.status=="ACTIVE" and session.phase=="ASSESSMENT_ACTIVE"
    public=item.frozen_public_snapshot; private=item.frozen_private_snapshot
    answers={row["id"]:row["correct_option_id"] for row in private["mcqs"]}
    response=submit_f1_response(db,runtime,session.id,answers,"The code must transmit exactly the structured fields that the receiver reads, preserve grouping and ordering, and validate the parity/check-bit relationship before accepting a record.",uuid.uuid4())
    judge=ai.reserve_f1_judge(db,session.id,response,commit=True); asyncio.run(ai.execute(db,judge))
    db.expire_all(); session=db.get(Session,session.id); item=db.get(AssessmentInstance,item.id); evaluation=db.scalar(select(V04Evaluation).join(AssessmentResponse).where(AssessmentResponse.assessment_instance_id==item.id))
    calls=list(db.scalars(select(LLMCall).where(LLMCall.session_id==session.id).order_by(LLMCall.started_at)).all())
    result={
      "session_id":str(session.id),"phase":session.phase,"formal_state":session.formal_state_id,
      "tutor_messages":len(list(db.scalars(select(Message).join(Attempt).where(Attempt.session_id==session.id,Message.role=="TUTOR")).all())),
      "completion_mode":"development_advance" if advance else "tutor_complete",
      "assessment":{"status":item.status,"mcqs":len(public["mcqs"]),"subjective":bool(public.get("subjective")),"private_keys":len(private["mcqs"]),"fingerprint":bool(item.frozen_package_fingerprint)},
      "roles":[{"purpose":call.purpose,"status":call.status} for call in calls],
      "response_count":len(list(db.scalars(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id==item.id)).all())),
      "evaluation":{"count":1 if evaluation else 0,"passed":evaluation.passed if evaluation else None,"mcq_score":evaluation.mcq_score if evaluation else None,"subjective_score":evaluation.subjective_score if evaluation else None},
    }
    assert result["tutor_messages"]>=1 and result["assessment"]["mcqs"]==3 and result["assessment"]["subjective"] and result["assessment"]["private_keys"]==3 and result["assessment"]["fingerprint"]
    assert {"ASSESSMENT_WRITER","SEMANTIC_REVIEW","JUDGE"}.issubset({row["purpose"] for row in result["roles"]}) and result["response_count"]==1 and result["evaluation"]["count"]==1
    (cfg.research_data_dir/"task7_real_provider_session_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result))
if __name__=="__main__": main()
