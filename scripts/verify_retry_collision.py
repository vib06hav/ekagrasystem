"""Verify a second retry reservation is rejected while the first is active."""
from __future__ import annotations
import json, uuid
from sqlalchemy import select
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import LLMCall, Session
from solo_harness.runtime.ai import AIExecutionRuntime, OpenAICompatibleClient
from solo_harness.runtime.engine import SessionRuntime

def main():
 c=get_settings(); d=make_session_factory(c.database_url)(); runtime=SessionRuntime(bootstrap(c)); source=d.scalar(select(Session).order_by(Session.created_at.desc())); s=runtime.create_session(d,source.study_version_id,build_id="fault-retry-collision",institutional_id="fault-collision-"+uuid.uuid4().hex[:10],commit=False); ai=AIExecutionRuntime(runtime,OpenAICompatibleClient(c),c); prior=LLMCall(session_id=s.id,attempt_id=s.current_attempt_id,assessment_instance_id=None,purpose="TUTOR",status="FAILED",retry_group_id=uuid.uuid4(),retry_number=0,provider="fault",model="fault",generation_parameters={},request_payload={},request_body_text="{}",error_class="TIMEOUT",error_message="injected"); d.add(prior); d.commit(); first=ai.reserve_manual_retry(d,s.id,commit=True); rejected=False
 try: ai.reserve_manual_retry(d,s.id,commit=True)
 except ValueError as exc: rejected="already active" in str(exc)
 result={"first_retry":str(first),"second_rejected":rejected,"active_calls":len(d.scalars(select(LLMCall).where(LLMCall.session_id==s.id,LLMCall.status=="STARTED")).all())}; assert rejected and result["active_calls"]==1; (c.research_data_dir/"retry_collision_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result))
if __name__=="__main__": main()
