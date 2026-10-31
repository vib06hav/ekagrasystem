"""Controlled PostgreSQL interruption matrix for Tutor→assessment durability."""
from __future__ import annotations
import asyncio,json,uuid
from datetime import datetime,timezone
from sqlalchemy import select
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance,Attempt,LLMCall,Session
from solo_harness.runtime.ai import AIExecutionRuntime
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.web import ParticipantApplication

class NoTransport:
 def __init__(self): self.calls=0
 async def send(self, prepared):
  self.calls += 1
  raise AssertionError('recovery must not send')

def build_call(db,s,a):
 payload={'choices':[{'message':{'content':json.dumps({'learner_message':'Completed synthetic instruction.','fidelity_note':'fault fixture','teaching_complete':True})}}]}
 c=LLMCall(session_id=s.id,attempt_id=a.id,assessment_instance_id=None,purpose='TUTOR',status='RECEIVED',retry_group_id=uuid.uuid4(),retry_number=0,provider='fault',model='fault',generation_parameters={},request_payload={'schema_name':'TutorProse'},request_body_text='{}',raw_response_text=json.dumps(payload),response_payload=payload);db.add(c);db.commit();return c
def count_builds(db,assessment): return len(db.scalars(select(LLMCall).where(LLMCall.assessment_instance_id==assessment.id,LLMCall.purpose=='ASSESSMENT_BUILD')).all())
def main():
 cfg=get_settings(); catalog=bootstrap(cfg); runtime=SessionRuntime(catalog); db=make_session_factory(cfg.database_url)(); source=db.scalar(select(Session).order_by(Session.created_at.desc())); trace={}
 # interruption immediately after Tutor response finalization: reservation must be durable before callback.
 s=runtime.create_session(db,source.study_version_id,build_id='tutor-atomic',institutional_id='fault-tutor-'+uuid.uuid4().hex[:8],commit=False);a=db.get(Attempt,s.current_attempt_id);c=build_call(db,s,a);transport=NoTransport();ai=AIExecutionRuntime(runtime,transport,cfg)
 async def stop_after_reservation(db_,call_id): trace['reserved_callback']=str(call_id)
 ai.execute=stop_after_reservation
 asyncio.run(ai._finalize_received(db,c.id)); item=db.scalar(select(AssessmentInstance).where(AssessmentInstance.session_id==s.id)); trace['tutor_completion']={'phase':db.get(Session,s.id).phase,'builds':count_builds(db,item),'callback':bool(trace.get('reserved_callback')),'provider_sends':transport.calls}
 # legacy split-commit/orphan: startup reconciliation reserves exactly one build and is idempotent.
 orphan=runtime.create_session(db,source.study_version_id,build_id='orphan',institutional_id='fault-orphan-'+uuid.uuid4().hex[:8],commit=False);orphan_item=runtime.complete_intervention(db,orphan.id,'FAULT_ORPHAN',commit=True);recovery_transport=NoTransport();app=ParticipantApplication(catalog,cfg,execution=AIExecutionRuntime(runtime,recovery_transport,cfg));runs=[]
 async def no_run(call_id): runs.append(str(call_id))
 app.run_operation=no_run
 asyncio.run(app.recover_persisted_operations()); first=count_builds(db,orphan_item); asyncio.run(app.recover_persisted_operations()); second=count_builds(db,orphan_item); trace['orphan_reconcile']={'phase':db.get(Session,orphan.id).phase,'builds_first':first,'builds_second':second,'runs':len(runs),'provider_sends':recovery_transport.calls}
 # checkpointed generating assessment stays resumable and is not duplicated.
 meta=dict(orphan_item.frozen_metadata_snapshot or {});meta['generation_checkpoints']={'MCQ1':{'instance_id':'fixture','writer_call_id':'w','reviewer_call_id':'r'}};orphan_item.frozen_metadata_snapshot=meta;db.commit();asyncio.run(app.recover_persisted_operations()); trace['checkpoint_recovery']={'builds':count_builds(db,orphan_item),'checkpoints':len((db.get(AssessmentInstance,orphan_item.id).frozen_metadata_snapshot or {}).get('generation_checkpoints',{}))}
 # once frozen, reconciliation creates no operation and leaves the immutable package intact.
 orphan_item.status='ACTIVE';orphan_item.frozen_public_snapshot={'mcqs':[],'subjective':{'id':'SUB1','prompt':'fixture'}};orphan_item.frozen_private_snapshot={'mcqs':[],'subjective_resolved':{}};orphan_item.frozen_schema_version='v04.native.2';orphan_item.frozen_at=datetime.now(timezone.utc);db.get(Session,orphan.id).phase='ASSESSMENT_ACTIVE';db.commit();asyncio.run(app.recover_persisted_operations());trace['post_freeze']={'builds':count_builds(db,orphan_item),'status':db.get(AssessmentInstance,orphan_item.id).status,'frozen':bool(db.get(AssessmentInstance,orphan_item.id).frozen_public_snapshot)}
 assert trace['tutor_completion']['builds']==1 and trace['tutor_completion']['provider_sends']==0 and first==second==1 and trace['orphan_reconcile']['provider_sends']==0 and trace['checkpoint_recovery']['checkpoints']==1 and trace['post_freeze']['builds']==1 and trace['post_freeze']['frozen']
 (cfg.research_data_dir/'tutor_assessment_recovery_trace.json').write_text(json.dumps(trace,indent=2),encoding='utf-8');print(json.dumps(trace))
if __name__=='__main__':main()
