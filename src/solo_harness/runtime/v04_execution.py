"""Persistent v0.4 scoring gate.  The Judge scores only the subjective item."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from solo_harness.db.models import AssessmentInstance, AssessmentResponse, Attempt, V04Evaluation, Session
from solo_harness.runtime.v04_grading import evaluate_f1_response
from solo_harness.runtime.v04_native import SubjectiveJudgment


def finalize_v04_evaluation(db, runtime, session_id, result: SubjectiveJudgment, judge_call_id):
    session = db.scalar(select(Session).where(Session.id == session_id).with_for_update()); attempt = db.get(Attempt, session.current_attempt_id)
    assessment = db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id == attempt.id).with_for_update())
    response = db.scalar(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id == assessment.id).with_for_update())
    existing = db.scalar(select(V04Evaluation).where(V04Evaluation.assessment_response_id == response.id))
    if existing is not None:
        return existing
    score = evaluate_f1_response(assessment.frozen_public_snapshot or {}, assessment.frozen_private_snapshot or {}, (response.structured_response or {}).get("mcq_answers", {}), response.response_text, result)
    passed = score.passed; now = datetime.now(timezone.utc)
    evaluation = V04Evaluation(assessment_response_id=response.id, status="FINALIZED", mcq_results=score.mcq_evidence, mcq_score=score.mcq_points, subjective_score=score.subjective_points, judge_findings=score.judge_evidence, judge_llm_call_id=judge_call_id, evaluation_version="v04.native.2", passed=passed, finalized_at=now)
    db.add(evaluation); assessment.status="CLOSED"; assessment.closed_at=now; attempt.passed=passed; attempt.status="PASSED" if passed else "FAILED"; attempt.completed_at=now
    compiled = runtime._compiled(db, session); transition=compiled.knowledge_slices[attempt.transition_id]["transition"]; formal_state_advanced=passed and session.formal_state_id==transition["from_state_id"]
    attempt.formal_state_after_id=transition["target_state_id"] if formal_state_advanced else session.formal_state_id
    runtime._event(db, session, "V04_EVALUATED", {"passed": passed, "formal_state_advanced":formal_state_advanced, "mcq_score": score.mcq_points, "subjective_score": score.subjective_points}, attempt.id)
    if passed:
        if formal_state_advanced: session.formal_state_id=transition["target_state_id"]
        session.phase="SECTION_COMPLETE"; runtime.complete_section(db, session, attempt, "PASSED", formal_state_advanced)
    else:
        if attempt.sequence_in_transition < 3:
            runtime._create_attempt(db, session, compiled, attempt.transition_id)
        else:
            session.phase="SECTION_COMPLETE"
            runtime.complete_section(db,session,attempt,"UNRESOLVED",False)
    db.commit()
