"""Persist a valid received Tutor response for application-startup recovery."""
from __future__ import annotations
import json, uuid
from sqlalchemy import select
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import LLMCall, Session

def main():
    cfg=get_settings(); db=make_session_factory(cfg.database_url)()
    source=db.scalar(select(LLMCall).join(Session).where(LLMCall.purpose=="TUTOR",LLMCall.status=="SUCCEEDED",Session.phase=="INTERVENTION_ACTIVE").order_by(LLMCall.started_at.desc()))
    assert source is not None
    call=LLMCall(session_id=source.session_id,attempt_id=source.attempt_id,assessment_instance_id=None,purpose="TUTOR",status="RECEIVED",retry_group_id=uuid.uuid4(),retry_number=0,provider=source.provider,model=source.model,generation_parameters=source.generation_parameters,compiled_prompt_text=source.compiled_prompt_text,request_payload=source.request_payload,request_body_text=source.request_body_text,raw_response_text=source.raw_response_text,response_payload=source.response_payload)
    db.add(call); db.commit()
    print(json.dumps({"call_id":str(call.id),"session_id":str(call.session_id)}))
if __name__=="__main__":main()
