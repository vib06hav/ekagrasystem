"""Database-backed three-failure progression and terminal-status demonstration."""
from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from sqlalchemy import select
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance, AssessmentResponse, Attempt, LLMCall, ProtocolEvent, Session
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.runtime.v04_execution import finalize_v04_evaluation
from solo_harness.runtime.v04_native import SubjectiveJudgment

def make_failed_assessment(db, session, attempt, source, source_response):
 item=AssessmentInstance(session_id=session.id,attempt_id=attempt.id,transition_id=attempt.transition_id,assessment_family_id=source.assessment_family_id,assessment_form_id=source.assessment_form_id+"-"+str(attempt.sequence_in_transition),status="AWAITING_EVALUATION",candidate_form_ids=source.candidate_form_ids,selection_method="FAULT",selection_audit={"fixture":"three-failures"},blueprint_snapshot=source.blueprint_snapshot,resolved_component_ids=source.resolved_component_ids,frozen_public_snapshot=source.frozen_public_snapshot,frozen_private_snapshot=source.frozen_private_snapshot,frozen_package_fingerprint=source.frozen_package_fingerprint,frozen_schema_version=source.frozen_schema_version,frozen_metadata_snapshot=source.frozen_metadata_snapshot,delivery_status="DEVELOPMENT_ONLY",frozen_at=datetime.now(timezone.utc)); db.add(item); db.flush()
 answers={q['id']:next(o['id'] for o in q['options'] if o['id']!=next(k['correct_option_id'] for k in item.frozen_private_snapshot['mcqs'] if k['id']==q['id'])) for q in item.frozen_public_snapshot['mcqs']}
 db.add(AssessmentResponse(assessment_instance_id=item.id,response_text=source_response.response_text,response_format="plain",client_action_id=uuid.uuid4(),structured_response={"mcq_answers":answers},response_schema_version="v04.native.2")); attempt.status="AWAITING_EVALUATION"; session.phase="ASSESSMENT_AWAITING_EVALUATION"; call=LLMCall(session_id=session.id,attempt_id=attempt.id,assessment_instance_id=item.id,purpose="JUDGE",status="SUCCEEDED",retry_group_id=uuid.uuid4(),retry_number=0,provider="fault",model="fault",generation_parameters={},request_payload={},request_body_text="{}"); db.add(call); db.flush(); return call
def main():
 cfg=get_settings(); db=make_session_factory(cfg.database_url)(); runtime=SessionRuntime(bootstrap(cfg)); source=db.scalar(select(AssessmentInstance).where(AssessmentInstance.status=="CLOSED").order_by(AssessmentInstance.closed_at.desc())); source_response=db.scalar(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id==source.id)); session=runtime.create_session(db,db.get(Session,source.session_id).study_version_id,build_id="unresolved-demo",institutional_id="unresolved-demo-"+uuid.uuid4().hex[:10],commit=False); initial_state=session.formal_state_id
 for _ in range(3):
  attempt=db.get(Attempt,session.current_attempt_id); call=make_failed_assessment(db,session,attempt,source,source_response); db.commit(); judgment=SubjectiveJudgment(gradable_status="GRADABLE",subjective_points=1,observed_solo_structure="multistructural",material_correctness="partial",criterion_evidence=[],misconception_evidence=[],verbatim_quotes=[source_response.response_text[:30]],alternative_reasoning_used=False,unverified_claims=[],review_reason=None,score_justification="controlled failing assessment"); finalize_v04_evaluation(db,runtime,session.id,judgment,call.id)
 session=db.get(Session,session.id); attempts=db.scalars(select(Attempt).where(Attempt.session_id==session.id).order_by(Attempt.sequence_in_transition)).all(); events=db.scalars(select(ProtocolEvent).where(ProtocolEvent.session_id==session.id,ProtocolEvent.event_type=="SECTION_COMPLETED")).all(); result={"attempt_sequences":[a.sequence_in_transition for a in attempts],"phase_after_failures":session.phase,"formal_state_unchanged":session.formal_state_id==initial_state,"completion_events":[e.payload for e in events]}
 # Move administratively through the remaining sections, recording canonical completion events.
 compiled=runtime._compiled(db,session)
 while session.current_transition_id != compiled.protocol['transition_ids'][-1]:
  runtime.advance_section(db,session.id); attempt=db.get(Attempt,session.current_attempt_id); session.phase="SECTION_COMPLETE"; runtime.complete_section(db,session,attempt,"PASSED",False); db.commit()
 runtime.finish_session(db,session.id); result["terminal_status"]=db.get(Session,session.id).status; result["terminal_reason"]=db.get(Session,session.id).terminal_reason
 assert result['attempt_sequences']==[1,2,3] and result['phase_after_failures']=="SECTION_COMPLETE" and result['formal_state_unchanged'] and result['completion_events'][0]['scientific_outcome']=="UNRESOLVED" and result['terminal_status']=="UNRESOLVED"
 (cfg.research_data_dir/"unresolved_termination_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result))
if __name__=="__main__": main()
