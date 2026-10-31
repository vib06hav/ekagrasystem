"""Private/public boundary for frozen v0.4 four-item packages."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from solo_harness.db.models import AssessmentInstance, AssessmentResponse, Attempt, Session

V04_RESPONSE_SCHEMA = "v04.1"
DEVELOPMENT_ONLY = "DEVELOPMENT_ONLY"

def is_f1_study(compiled): return bool(compiled.authored.get("v04"))
def is_f1_frozen(item): return bool(item and item.frozen_public_snapshot and item.frozen_private_snapshot)
def is_deliverable_f1(item, settings): return is_f1_frozen(item) and bool(getattr(settings, "enable_f1_v04_development", False))
def public_projection(item):
    if not is_f1_frozen(item): raise ValueError("assessment is not frozen")
    return item.frozen_public_snapshot

def submit_f1_response(db, runtime, session_id, answers: dict[str,str], subjective_response: str, client_action_id: uuid.UUID):
    session=db.scalar(select(Session).where(Session.id==session_id).with_for_update()); attempt=db.get(Attempt,session.current_attempt_id)
    item=db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id==attempt.id).with_for_update()); public=public_projection(item)
    if session.phase != "ASSESSMENT_ACTIVE" or item.status != "ACTIVE": raise ValueError("assessment is not active")
    questions={x["id"]:x for x in public["mcqs"]}
    if set(answers) != {"MCQ1","MCQ2","MCQ3"} or set(questions) != set(answers): raise ValueError("three grouped MCQ answers required")
    if any(answers[q] not in {o["id"] for o in questions[q]["options"]} for q in answers): raise ValueError("answer is not an option for its question")
    if not subjective_response.strip(): raise ValueError("subjective response required")
    if db.scalar(select(AssessmentResponse.id).where(AssessmentResponse.assessment_instance_id==item.id)): raise ValueError("assessment already submitted")
    response=AssessmentResponse(assessment_instance_id=item.id,response_text=subjective_response.strip(),response_format="plain",client_action_id=client_action_id,structured_response={"schema_version":V04_RESPONSE_SCHEMA,"mcq_answers":answers,"subjective_response":subjective_response.strip()},response_schema_version=V04_RESPONSE_SCHEMA)
    db.add(response); item.status="AWAITING_EVALUATION"; item.submitted_at=datetime.now(timezone.utc); attempt.status="AWAITING_EVALUATION"; session.phase="ASSESSMENT_AWAITING_EVALUATION"; runtime._event(db,session,"V04_ASSESSMENT_SUBMITTED",{"assessment_id":str(item.id)},attempt.id); return response
