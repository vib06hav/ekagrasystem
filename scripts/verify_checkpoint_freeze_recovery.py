"""Resume a failed build from four real durable checkpoints without provider I/O."""
from __future__ import annotations
import asyncio,json,uuid
from datetime import datetime,timezone
from sqlalchemy import select
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance,Attempt,LLMCall,Session
from solo_harness.runtime.ai import AIExecutionRuntime,PreparedLLMRequest
from solo_harness.runtime.engine import SessionRuntime
class NoSend:
 def __init__(self):self.calls=0
 def prepare(self,r):return PreparedLLMRequest(r,{},"{}",{})
 async def send(self,p):self.calls+=1;raise AssertionError("complete checkpoints require no provider send")
def main():
 cfg=get_settings();db=make_session_factory(cfg.database_url)();runtime=SessionRuntime(bootstrap(cfg));src=db.scalar(select(AssessmentInstance).where(AssessmentInstance.status=="CLOSED",AssessmentInstance.frozen_metadata_snapshot.is_not(None)).order_by(AssessmentInstance.closed_at.desc())); assert src
 session=runtime.create_session(db,db.get(Session,src.session_id).study_version_id,build_id="checkpoint-recovery",institutional_id="checkpoint-"+uuid.uuid4().hex[:10],commit=False);attempt=db.get(Attempt,session.current_attempt_id)
 item=AssessmentInstance(session_id=session.id,attempt_id=attempt.id,transition_id=attempt.transition_id,assessment_family_id=src.assessment_family_id,assessment_form_id=src.assessment_form_id,status="GENERATING",candidate_form_ids=src.candidate_form_ids,selection_method="CHECKPOINT_RECOVERY",selection_audit={"fixture":"rejected item then build failure"},blueprint_snapshot=src.blueprint_snapshot,resolved_component_ids=src.resolved_component_ids,frozen_metadata_snapshot=src.frozen_metadata_snapshot)
 db.add(item);db.flush();session.phase="ASSESSMENT_GENERATING";attempt.status="ASSESSMENT_GENERATING"
 failed=LLMCall(session_id=session.id,attempt_id=attempt.id,assessment_instance_id=item.id,purpose="ASSESSMENT_BUILD",status="FAILED",retry_group_id=uuid.uuid4(),retry_number=0,provider="fault",model="fault",generation_parameters={},request_payload={"rejected_item":"MCQ1"},request_body_text="{}",error_class="SEMANTIC_REVIEW_REJECTED")
 db.add(failed);db.commit();client=NoSend();ai=AIExecutionRuntime(runtime,client,cfg);retry=ai.reserve_manual_retry(db,session.id,commit=True);asyncio.run(ai.execute(db,retry));db.expire_all();item=db.get(AssessmentInstance,item.id); calls=list(db.scalars(select(LLMCall).where(LLMCall.assessment_instance_id==item.id,LLMCall.purpose=="ASSESSMENT_BUILD")).all());result={"retry_of":db.get(LLMCall,retry).request_payload.get("retry_of"),"checkpoint_count":len((item.frozen_metadata_snapshot or {}).get("generation_checkpoints",{})),"status":item.status,"public_mcqs":len((item.frozen_public_snapshot or {}).get("mcqs",[])),"subjective":bool((item.frozen_public_snapshot or {}).get("subjective")),"frozen_packages":len([x for x in db.scalars(select(AssessmentInstance).where(AssessmentInstance.session_id==session.id)).all() if x.status=="ACTIVE"]),"build_calls":len(calls),"provider_sends":client.calls};assert result["status"]=="ACTIVE" and result["checkpoint_count"]==4 and result["public_mcqs"]==3 and result["subjective"] and result["frozen_packages"]==1 and result["build_calls"]==2 and result["provider_sends"]==0;(cfg.research_data_dir/"checkpoint_freeze_recovery_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps(result))
if __name__=="__main__":main()
