"""Inject a persisted Judge review hold, then use the normal real-provider retry."""
from __future__ import annotations
import asyncio, json, uuid
from datetime import datetime, timezone
from sqlalchemy import select
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance, AssessmentResponse, Attempt, LLMCall, Session, V04Evaluation
from solo_harness.runtime.ai import AIExecutionRuntime, OpenAICompatibleClient
from solo_harness.runtime.engine import SessionRuntime

def main():
    cfg=get_settings(); db=make_session_factory(cfg.database_url)(); runtime=SessionRuntime(bootstrap(cfg)); source=db.scalar(select(AssessmentInstance).where(AssessmentInstance.status=="CLOSED").order_by(AssessmentInstance.closed_at.desc())); source_response=db.scalar(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id==source.id))
    session=runtime.create_session(db,source.session_id and db.get(Session,source.session_id).study_version_id,build_id="fault-judge-hold",institutional_id="fault-judge-hold-"+uuid.uuid4().hex[:10],commit=False); attempt=db.get(Attempt,session.current_attempt_id)
    item=AssessmentInstance(session_id=session.id,attempt_id=attempt.id,transition_id=attempt.transition_id,assessment_family_id=source.assessment_family_id,assessment_form_id=source.assessment_form_id,status="AWAITING_EVALUATION",candidate_form_ids=source.candidate_form_ids,selection_method="FAULT_INJECTION",selection_audit={"fixture":"judge-review-hold"},blueprint_snapshot=source.blueprint_snapshot,resolved_component_ids=source.resolved_component_ids,frozen_public_snapshot=source.frozen_public_snapshot,frozen_private_snapshot=source.frozen_private_snapshot,frozen_package_fingerprint=source.frozen_package_fingerprint,frozen_schema_version=source.frozen_schema_version,frozen_metadata_snapshot=source.frozen_metadata_snapshot,delivery_status="DEVELOPMENT_ONLY",frozen_at=datetime.now(timezone.utc)); db.add(item); db.flush()
    response=AssessmentResponse(assessment_instance_id=item.id,response_text=source_response.response_text,response_format="plain",client_action_id=uuid.uuid4(),structured_response=source_response.structured_response,response_schema_version="v04.native.2"); db.add(response); attempt.status="AWAITING_EVALUATION"; session.phase="ASSESSMENT_AWAITING_EVALUATION"
    hold={"gradable_status":"REVIEW_REQUIRED","subjective_points":None,"observed_solo_structure":None,"material_correctness":"withheld","criterion_evidence":[],"misconception_evidence":[],"verbatim_quotes":[],"alternative_reasoning_used":False,"unverified_claims":[],"review_reason":"Injected review hold","score_justification":"Controlled fault injection"}; payload={"choices":[{"message":{"content":json.dumps(hold)}}]}
    call=LLMCall(session_id=session.id,attempt_id=attempt.id,assessment_instance_id=item.id,purpose="JUDGE",status="RECEIVED",retry_group_id=uuid.uuid4(),retry_number=0,provider="fault",model="fault",generation_parameters={},compiled_prompt_text="fault",request_payload={},request_body_text="{}",raw_response_text=json.dumps(payload),response_payload=payload); db.add(call); db.commit()
    ai=AIExecutionRuntime(runtime,OpenAICompatibleClient(cfg),cfg); asyncio.run(ai.execute(db,call.id)); held=db.get(LLMCall,call.id); retry=ai.reserve_manual_retry(db,session.id,commit=True); asyncio.run(ai.execute(db,retry)); evaluations=db.scalars(select(V04Evaluation).join(AssessmentResponse).where(AssessmentResponse.assessment_instance_id==item.id)).all(); result={"hold_status":held.status,"hold_class":held.error_class,"retry_call_id":str(retry),"response_count":len(db.scalars(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id==item.id)).all()),"evaluation_count":len(evaluations),"final_phase":db.get(Session,session.id).phase,"retry_link":db.get(LLMCall,retry).request_payload.get("retry_of")}; assert held.error_class=="REVIEW_HOLD" and len(evaluations)==1 and result["response_count"]==1 and result["retry_link"]==str(call.id)
    (cfg.research_data_dir/"judge_hold_retry_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result))
if __name__=="__main__": main()
