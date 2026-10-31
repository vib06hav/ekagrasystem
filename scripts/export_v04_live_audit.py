"""Create a redacted current-source and real-provider v0.4 audit bundle."""
from __future__ import annotations
import hashlib, json, subprocess, zipfile
from pathlib import Path
from sqlalchemy import select
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance, AssessmentResponse, Attempt, LLMCall, Message, ProtocolEvent, Session, V04Evaluation

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'EKAGRAAI_F1_V04_LIVE_END_TO_END_AUDIT.zip'
SKIP={'.git','.env','.pytest-tmp','__pycache__','.venv','venv','EKAGRAAI_F1_V04_LIVE_END_TO_END_AUDIT.zip'}
def plain(value):
    if value is None or isinstance(value,(str,int,float,bool)): return value
    if isinstance(value,dict): return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [plain(v) for v in value]
    return str(value)
def audit(db):
    sessions=db.scalars(select(Session).where(Session.institutional_id.like('audit-%')).order_by(Session.created_at)).all()
    result=[]
    for s in sessions:
        attempts=db.scalars(select(Attempt).where(Attempt.session_id==s.id).order_by(Attempt.assigned_at)).all()
        items=db.scalars(select(AssessmentInstance).where(AssessmentInstance.session_id==s.id)).all()
        calls=db.scalars(select(LLMCall).where(LLMCall.session_id==s.id).order_by(LLMCall.started_at)).all()
        responses=db.scalars(select(AssessmentResponse).join(AssessmentInstance).where(AssessmentInstance.session_id==s.id)).all()
        evaluations=db.scalars(select(V04Evaluation).join(AssessmentResponse).join(AssessmentInstance).where(AssessmentInstance.session_id==s.id)).all()
        result.append({'session':{'id':str(s.id),'synthetic_label':s.institutional_id,'phase':s.phase},'attempts':[{'id':str(a.id),'transition':a.transition_id,'pedagogy':a.pedagogy_id,'status':a.status,'passed':a.passed,'completion_reason':a.completion_reason,'details':plain(a.outcome_details)} for a in attempts],'assessments':[{'id':str(i.id),'blueprint':i.assessment_form_id,'status':i.status,'public':plain(i.frozen_public_snapshot),'private':plain(i.frozen_private_snapshot),'metadata':plain(i.frozen_metadata_snapshot),'fingerprint':i.frozen_package_fingerprint} for i in items],'calls':[{'id':str(c.id),'role':c.purpose,'status':c.status,'prompt':c.compiled_prompt_text,'request':plain(c.request_payload),'response':c.raw_response_text,'parsed':plain(c.parsed_response),'error_class':c.error_class,'error':c.error_message,'usage':{'input':c.input_tokens,'output':c.output_tokens,'total':c.total_tokens}} for c in calls],'messages':[{'role':m.role,'text':m.content_text,'trace':plain(m.instructional_trace)} for a in attempts for m in db.scalars(select(Message).where(Message.attempt_id==a.id).order_by(Message.sequence_no)).all()],'responses':[{'id':str(r.id),'exact_subjective_response':r.response_text,'structured':plain(r.structured_response)} for r in responses],'evaluations':[{'passed':e.passed,'mcq_score':e.mcq_score,'subjective_score':e.subjective_score,'judge':plain(e.judge_findings)} for e in evaluations],'events':[{'type':e.event_type,'payload':plain(e.payload),'attempt_id':str(e.attempt_id) if e.attempt_id else None} for e in db.scalars(select(ProtocolEvent).where(ProtocolEvent.session_id==s.id).order_by(ProtocolEvent.sequence_no)).all()]})
    return result
def main():
    settings=get_settings(); db=make_session_factory(settings.database_url)(); evidence=audit(db)
    def git(args):
        try: return subprocess.run(args,cwd=ROOT,capture_output=True,text=True,check=False).stdout
        except FileNotFoundError: return "git unavailable in audit container\n"
    results=['# Live Results','', '| Session | Natural Tutor complete | Dev advance | Frozen | Judge | Score |', '|---|---:|---:|---:|---:|---|']
    for x in evidence:
        attempts=x['attempts']; ev=x['evaluations'][-1] if x['evaluations'] else {}; results.append(f"| {x['session']['synthetic_label']} | {any(a['completion_reason']=='TUTOR_COMPLETE' for a in attempts)} | {any(a['completion_reason']=='DEVELOPMENT_ONLY_MANUAL_ADVANCE' for a in attempts)} | {bool(x['assessments'] and x['assessments'][0]['fingerprint'])} | {bool(ev)} | {ev.get('mcq_score','-')}/3 + {ev.get('subjective_score','-')}/2 |")
    results += ['', 'All sessions are synthetic development records. The development advance marks the unresolved natural Tutor completion condition and is disabled unless development mode is enabled.']
    generated={'evidence/real_provider_audit.json':json.dumps(evidence,indent=2,ensure_ascii=False,default=str),'LIVE_RESULTS.md':'\n'.join(results)+'\n','git_status.txt':git(['git','status','--short']),'git_diff.txt':git(['git','diff','--','.']), 'git_commit.txt':git(['git','rev-parse','HEAD'])}
    files=[]
    for p in ROOT.rglob('*'):
        if not p.is_file() or any(part in SKIP for part in p.relative_to(ROOT).parts): continue
        if p.suffix in {'.pyc','.log'} or p.name.startswith('.env'): continue
        files.append(p)
    manifest=[]
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in generated.items(): z.writestr(name,data); manifest.append(f"{hashlib.sha256(data.encode()).hexdigest()}  {name}")
        for p in files:
            rel=p.relative_to(ROOT).as_posix(); z.write(p,rel); manifest.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
        z.writestr('MANIFEST.sha256','\n'.join(manifest)+'\n')
    print(OUT)
if __name__=='__main__': main()
