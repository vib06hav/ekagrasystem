"""Verify all persisted response roles finalize without a provider resend."""
from __future__ import annotations
import asyncio, json, uuid
from sqlalchemy import select
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import LLMCall
from solo_harness.runtime.ai import AIExecutionRuntime
from solo_harness.runtime.engine import SessionRuntime

class NoTransport:
    def __init__(self): self.calls=0
    async def send(self, prepared): self.calls+=1; raise AssertionError("saved response must not resend")

def main():
    cfg=get_settings(); db=make_session_factory(cfg.database_url)(); client=NoTransport(); ai=AIExecutionRuntime(SessionRuntime(bootstrap(cfg)),client,cfg); results={}
    for role in ("TUTOR","ASSESSMENT_WRITER","SEMANTIC_REVIEW","JUDGE"):
        source=db.scalar(select(LLMCall).where(LLMCall.purpose==role,LLMCall.status=="SUCCEEDED",LLMCall.response_payload.is_not(None)).order_by(LLMCall.started_at.desc()))
        if not source: raise RuntimeError(f"no real {role} source call")
        clone=LLMCall(session_id=source.session_id,attempt_id=source.attempt_id,assessment_instance_id=source.assessment_instance_id,purpose=role,status="RECEIVED",retry_group_id=uuid.uuid4(),retry_number=0,provider=source.provider,model=source.model,generation_parameters=source.generation_parameters,compiled_prompt_text=source.compiled_prompt_text,request_payload=source.request_payload,request_body_text=source.request_body_text,raw_response_text=source.raw_response_text,response_payload=source.response_payload)
        db.add(clone); db.commit(); asyncio.run(ai.execute(db,clone.id)); clone=db.get(LLMCall,clone.id); results[role]={"status":clone.status,"parsed_schema":clone.request_payload.get("schema_name")}
    assert client.calls==0 and all(x["status"]=="SUCCEEDED" for x in results.values())
    results["provider_send_calls"]=client.calls; (cfg.research_data_dir/"received_role_dispatch_trace.json").write_text(json.dumps(results,indent=2),encoding="utf-8"); print(json.dumps(results))
if __name__=="__main__": main()
