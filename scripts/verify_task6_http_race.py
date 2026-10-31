"""Hit the live participant HTTP adapter concurrently with distinct keys."""
from __future__ import annotations
import http.cookiejar
import json
import threading
import urllib.parse
import urllib.request
import uuid
from sqlalchemy import select
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import LLMCall, Session

BASE = "http://127.0.0.1:8000"

def post(opener, path, values):
    body=urllib.parse.urlencode(values).encode()
    try:
        response=opener.open(urllib.request.Request(BASE+path, data=body, method="POST"), timeout=20)
        return response.status
    except urllib.error.HTTPError as exc:
        return exc.code

def main():
    tag="task6-http-"+uuid.uuid4().hex[:12]
    jar=http.cookiejar.CookieJar()
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), urllib.request.HTTPRedirectHandler())
    # Do not follow the join redirect manually: the session cookie is still set.
    join=post(opener, "/join", {"institutional_id":tag,"acknowledged":"on"})
    barrier=threading.Barrier(2); statuses=[]
    def submit(key):
        local=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        barrier.wait(timeout=10)
        statuses.append(post(local,"/session/actions/begin",{"idempotency_key":key}))
    threads=[threading.Thread(target=submit,args=("task6-http-a",)),threading.Thread(target=submit,args=("task6-http-b",))]
    [x.start() for x in threads]; [x.join() for x in threads]
    cfg=get_settings(); db=make_session_factory(cfg.database_url)(); session=db.scalar(select(Session).where(Session.institutional_id==tag)); calls=list(db.scalars(select(LLMCall).where(LLMCall.session_id==session.id,LLMCall.purpose=="TUTOR")).all())
    result={"join_status":join,"submission_statuses":statuses,"tutor_calls":len(calls),"statuses":[call.status for call in calls]}
    assert len(calls)==1 and 409 in statuses
    (cfg.research_data_dir/"task6_http_race_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result))
if __name__=="__main__": main()
