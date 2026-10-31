"""Focused Task 8 ledger checks using the production database/runtime."""
from __future__ import annotations
import asyncio,json,uuid
from sqlalchemy import select
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance,Attempt,LLMCall,Message,Session
from solo_harness.runtime.ai import AIExecutionRuntime,PreparedLLMRequest
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.web import ParticipantApplication

class Stub:
 def prepare(self,r): return PreparedLLMRequest(r,{},"{}",{})
 async def send(self,p): raise AssertionError("saved response recovery must not send")

def main():
 cfg=get_settings(); db=make_session_factory(cfg.database_url)(); runtime=SessionRuntime(bootstrap(cfg)); source=db.scalar(select(Session).order_by(Session.created_at.desc())); ai=AIExecutionRuntime(runtime,Stub(),cfg); app=ParticipantApplication(runtime.catalog,cfg,execution=ai)
 # Failed parent + successful child: view and retry must use parent build.
 s=runtime.create_session(db,source.study_version_id,build_id="task8-build",institutional_id="task8-build-"+uuid.uuid4().hex[:10],commit=False); item=runtime.complete_intervention(db,s.id,"TASK8",commit=False); a=db.get(Attempt,s.current_attempt_id)
 build=LLMCall(session_id=s.id,attempt_id=a.id,assessment_instance_id=item.id,purpose="ASSESSMENT_BUILD",status="FAILED",retry_group_id=uuid.uuid4(),retry_number=0,provider="fault",model="fault",generation_parameters={},request_payload={},request_body_text="{}",error_class="TECHNICAL_FAILURE")
 child=LLMCall(session_id=s.id,attempt_id=a.id,assessment_instance_id=item.id,purpose="SEMANTIC_REVIEW",status="SUCCEEDED",retry_group_id=uuid.uuid4(),retry_number=0,provider="fault",model="fault",generation_parameters={},request_payload={},request_body_text="{}",parsed_response={})
 item.frozen_metadata_snapshot={"generation_checkpoints":{"MCQ1":{"instance_id":"checkpoint-1"}}}; db.add_all([build,child]); db.commit()
 view=app.view(s.id); retry=ai.reserve_manual_retry(db,s.id,commit=True); retry_call=db.get(LLMCall,retry)
 # A valid saved Writer and Reviewer response each finalizes locally with no send.
 role_results={}
 for role in ("ASSESSMENT_WRITER","SEMANTIC_REVIEW"):
  origin=db.scalar(select(LLMCall).where(LLMCall.purpose==role,LLMCall.status=="SUCCEEDED",LLMCall.raw_response_text.is_not(None)).order_by(LLMCall.started_at.desc())); clone=LLMCall(session_id=s.id,attempt_id=a.id,assessment_instance_id=item.id,purpose=role,status="RECEIVED",retry_group_id=uuid.uuid4(),retry_number=0,provider=origin.provider,model=origin.model,generation_parameters=origin.generation_parameters,request_payload=origin.request_payload,request_body_text=origin.request_body_text,raw_response_text=origin.raw_response_text,response_payload=origin.response_payload); db.add(clone); db.commit(); asyncio.run(ai._finalize_received(db,clone.id)); role_results[role]=db.get(LLMCall,clone.id).status
 # Idempotency callback mutates then rejects: nested savepoint removes message.
 t=runtime.create_session(db,source.study_version_id,build_id="task8-idem",institutional_id="task8-idem-"+uuid.uuid4().hex[:10],commit=True); ta=db.get(Attempt,t.current_attempt_id)
 def bad_reservation():
  db.add(Message(attempt_id=ta.id,sequence_no=999,role="LEARNER",content_text="must roll back",content_format="plain",material_ids=[],exposed_kc_ids=[],exposed_relation_ids=[])); db.flush(); raise ValueError("injected reservation rejection")
 try: app.reserve_idempotent(db,t.id,"TUTOR_MESSAGE","task8-key",{"learner_text":"x"},bad_reservation)
 except ValueError: pass
 orphan=len(list(db.scalars(select(Message).where(Message.attempt_id==ta.id,Message.sequence_no==999)).all()))
 result={"build_view":{"retryable":view["retryable"],"failed_purpose":view["failed_purpose"]},"build_retry":{"new_purpose":retry_call.purpose,"retry_of":retry_call.request_payload.get("retry_of"),"checkpoint_count":len((db.get(AssessmentInstance,item.id).frozen_metadata_snapshot or {}).get("generation_checkpoints",{}))},"received_roles":role_results,"provider_sends":ai.client.sends if hasattr(ai.client,"sends") else 0,"idempotency":{"orphan_messages":orphan}}
 assert result["build_view"]=={"retryable":True,"failed_purpose":"ASSESSMENT_BUILD"} and result["build_retry"]["new_purpose"]=="ASSESSMENT_BUILD" and result["build_retry"]["retry_of"]==str(build.id) and result["build_retry"]["checkpoint_count"]==1 and all(x=="SUCCEEDED" for x in role_results.values()) and orphan==0
 (cfg.research_data_dir/"assessment_build_recovery_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result))
if __name__=="__main__":main()
