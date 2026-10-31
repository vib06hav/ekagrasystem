from __future__ import annotations
import json
from sqlalchemy import select
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import LLMCall, Message

CALL_ID="32610733-4ed4-41fe-8102-b7f41643e81b"
def main():
    cfg=get_settings(); db=make_session_factory(cfg.database_url)(); call=db.get(LLMCall,CALL_ID)
    result={"call_id":CALL_ID,"status":call.status,"error_class":call.error_class,"message_count":len(list(db.scalars(select(Message).where(Message.llm_call_id==call.id)).all())),"provider_request_id":call.provider_request_id}
    assert result["status"]=="SUCCEEDED" and result["message_count"]==1 and result["provider_request_id"] is None
    (cfg.research_data_dir/"task7_restart_recovery_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result))
if __name__=="__main__":main()
