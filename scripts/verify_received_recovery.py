"""Controlled production-runtime check: recover a saved Tutor response without transport."""
from __future__ import annotations
import asyncio, json
from sqlalchemy import select
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import LLMCall, Message, Session
from solo_harness.runtime.ai import AIExecutionRuntime
from solo_harness.runtime.engine import SessionRuntime

class NoTransport:
    calls=0
    def prepare(self, request): raise AssertionError("transport preparation must not occur")
    async def send(self, prepared): self.calls+=1; raise AssertionError("provider resend must not occur")

def main():
    settings=get_settings(); db=make_session_factory(settings.database_url)()
    source=db.scalar(select(LLMCall).where(LLMCall.purpose=="TUTOR", LLMCall.status=="SUCCEEDED").order_by(LLMCall.started_at.desc()))
    session=db.get(Session,source.session_id)
    if not source or not session or session.phase!="INTERVENTION_ACTIVE": raise RuntimeError("need an active development Tutor session")
    clone=LLMCall(session_id=source.session_id,attempt_id=source.attempt_id,assessment_instance_id=None,purpose="TUTOR",status="RECEIVED",retry_group_id=source.retry_group_id, retry_number=99,provider=source.provider,model=source.model,generation_parameters=source.generation_parameters,compiled_prompt_text=source.compiled_prompt_text,request_payload=source.request_payload,request_body_text=source.request_body_text,raw_response_text=source.raw_response_text,response_payload=source.response_payload)
    db.add(clone); db.commit(); transport=NoTransport(); ai=AIExecutionRuntime(SessionRuntime(bootstrap(settings)),transport,settings)
    asyncio.run(ai.execute(db,clone.id)); first=db.scalar(select(Message).where(Message.llm_call_id==clone.id)); asyncio.run(ai.execute(db,clone.id)); count=len(db.scalars(select(Message).where(Message.llm_call_id==clone.id)).all()); call=db.get(LLMCall,clone.id)
    result={"call_id":str(clone.id),"provider_send_calls":transport.calls,"final_status":call.status,"messages_created":count,"recovered_text":first.content_text if first else None}
    (settings.research_data_dir/"recovery_received_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    assert result["provider_send_calls"]==0 and result["final_status"]=="SUCCEEDED" and count==1
    print(json.dumps(result))
if __name__=="__main__": main()
