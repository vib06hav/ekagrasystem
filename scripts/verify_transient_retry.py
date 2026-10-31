"""Controlled production-runtime transient provider recovery check."""
from __future__ import annotations
import asyncio, json
from sqlalchemy import select
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import LLMCall, Message, Session
from solo_harness.runtime.ai import AIExecutionRuntime, ProviderError, RawLLMResponse
from solo_harness.runtime.engine import SessionRuntime

class FailOnce:
    def __init__(self, source): self.source,self.calls=source,0
    async def send(self, prepared):
        self.calls+=1
        if self.calls==1: raise ProviderError("TIMEOUT","injected timeout",True)
        return RawLLMResponse(None,200,self.source.raw_response_text,self.source.response_payload,None,None,False,{},1)

def main():
    s=get_settings(); db=make_session_factory(s.database_url)(); source=db.scalar(select(LLMCall).where(LLMCall.purpose=="TUTOR",LLMCall.status=="SUCCEEDED").order_by(LLMCall.started_at.desc())); session=db.get(Session,source.session_id)
    if session.phase!="INTERVENTION_ACTIVE": raise RuntimeError("need active Tutor session")
    c=LLMCall(session_id=source.session_id,attempt_id=source.attempt_id,assessment_instance_id=None,purpose="TUTOR",status="STARTED",retry_group_id=source.retry_group_id,retry_number=98,provider=source.provider,model=source.model,generation_parameters=source.generation_parameters,compiled_prompt_text=source.compiled_prompt_text,request_payload=source.request_payload,request_body_text=source.request_body_text); db.add(c); db.commit()
    client=FailOnce(source); asyncio.run(AIExecutionRuntime(SessionRuntime(bootstrap(s)),client,s).execute(db,c.id)); c=db.get(LLMCall,c.id); result={"call_id":str(c.id),"send_attempts":client.calls,"status":c.status,"automatic_transport_retries":c.request_payload.get("automatic_transport_retries")}; assert client.calls==2 and c.status=="SUCCEEDED" and len(result["automatic_transport_retries"])==1
    (s.research_data_dir/"transient_retry_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result))
if __name__=="__main__": main()
