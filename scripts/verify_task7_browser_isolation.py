"""Use independent cookie jars against the live app; verify no browser-session leak."""
from __future__ import annotations
import http.cookiejar,json,urllib.parse,urllib.request,uuid
from sqlalchemy import select
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import Session
BASE="http://127.0.0.1:8000"
def join(tag):
 jar=http.cookiejar.CookieJar(); opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar)); body=urllib.parse.urlencode({"institutional_id":tag,"acknowledged":"on"}).encode(); response=opener.open(urllib.request.Request(BASE+"/join",data=body,method="POST")); page=opener.open(BASE+"/session").read().decode(); return tag, page
def main():
 first="task7-browser-a-"+uuid.uuid4().hex[:10]; second="task7-browser-b-"+uuid.uuid4().hex[:10]
 left,left_page=join(first); right,right_page=join(second)
 cfg=get_settings(); db=make_session_factory(cfg.database_url)(); left_session=db.scalar(select(Session).where(Session.institutional_id==left)); right_session=db.scalar(select(Session).where(Session.institutional_id==right))
 result={"session_ids_differ":str(left_session.id)!=str(right_session.id),"left_rendered":bool(left_page),"right_rendered":bool(right_page),"cross_session_identifier_leak":left not in right_page and right not in left_page}
 assert all(result.values()); (cfg.research_data_dir/"task7_browser_isolation_trace.json").write_text(json.dumps(result,indent=2),encoding="utf-8"); print(json.dumps(result))
if __name__=="__main__":main()
