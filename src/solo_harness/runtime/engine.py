"""Deterministic Version-1 experiment engine; no provider or prompt implementation."""
from dataclasses import dataclass
from datetime import datetime, timezone
import random
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from solo_harness.db.models import AssessmentInstance, AssessmentResponse, Attempt, Judgment, LearnerHistorySnapshot, LLMCall, Message, ProtocolEvent, RubricEvaluation, Session
from solo_harness.studies.catalog import StudyCatalog


@dataclass(frozen=True)
class SelectionDecision:
    eligible_candidate_ids: tuple[str, ...]
    excluded_candidate_ids: tuple[str, ...]
    selected_id: str
    selection_method: str
    selected_at: datetime
    optional_session_seed: str | None = None


class RandomSelector:
    def __init__(self, source=None, method="system_random_choice", seed=None):
        self.source = source or secrets.SystemRandom(); self.method = method; self.seed = seed
    def choose(self, candidates, excluded=()):
        eligible = tuple(sorted(candidates))
        if not eligible: raise ValueError("empty eligible candidate pool")
        selected = self.source.choice(eligible)
        return SelectionDecision(eligible, tuple(sorted(excluded)), selected, self.method, datetime.now(timezone.utc), self.seed)


@dataclass(frozen=True)
class JudgeObservation:
    gradable: bool
    correctness: str
    observed_solo_state_id: str | None
    demonstrated_evidence_ids: tuple[str, ...]
    detected_misconception_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RubricResult:
    passed: bool
    reasons: tuple[str, ...]


class RubricEvaluator:
    def evaluate(self, transition, rubric, observation: JudgeObservation, assessment_form_id=None) -> RubricResult:
        reasons = []
        if not observation.gradable: reasons.append("NOT_GRADABLE")
        if observation.correctness in {"MATERIALLY_INCORRECT", "NOT_GRADABLE"}: reasons.append("CORRECTNESS_GATE_FAILED")
        if observation.observed_solo_state_id is None: reasons.append("NO_OBSERVED_STATE")
        elif observation.observed_solo_state_id not in transition["state_order"]: reasons.append("UNKNOWN_OBSERVED_STATE")
        elif transition["state_order"][observation.observed_solo_state_id] < transition["state_order"][transition["target_state_id"]]: reasons.append("OBSERVED_STATE_BELOW_TARGET")
        rule = rubric["success_rule"]; shown = set(observation.demonstrated_evidence_ids)
        required = set(rule.get("requires", []))
        if required - shown: reasons.append("MISSING_REQUIRED_EVIDENCE")
        if "requires_any" in rule and not shown.intersection(rule["requires_any"]): reasons.append("MISSING_ANY_REQUIRED_EVIDENCE")
        for group in rule.get("requires_any_groups", []):
            if not shown.intersection(group):
                reasons.append("MISSING_REQUIRED_EVIDENCE_GROUP")
        form_required = set(rule.get("required_by_assessment_form", {}).get(assessment_form_id, []))
        if form_required - shown:
            reasons.append("MISSING_ITEM_SPECIFIC_EVIDENCE")
        if len(shown.intersection(rubric["evidence_ids"])) < rule.get("minimum_evidence", 0): reasons.append("INSUFFICIENT_EVIDENCE")
        if set(observation.detected_misconception_ids).intersection(rubric["blocking_misconception_ids"]): reasons.append("BLOCKING_MISCONCEPTION_DETECTED")
        return RubricResult(not reasons, tuple(reasons or ["RULE_SATISFIED"]))


class HistoryBuilder:
    def build(self, db: DbSession, session_id, transition_id, target_attempt_id):
        attempts = db.scalars(select(Attempt).where(Attempt.session_id == session_id, Attempt.transition_id == transition_id, Attempt.id != target_attempt_id).order_by(Attempt.sequence_in_transition)).all()
        entries = []
        for attempt in attempts:
            evaluation = db.scalar(select(RubricEvaluation).where(RubricEvaluation.attempt_id == attempt.id))
            traces = [m.instructional_trace for m in db.scalars(select(Message).where(Message.attempt_id == attempt.id, Message.role == "TUTOR").order_by(Message.sequence_no)).all() if m.instructional_trace]
            assessment = db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id == attempt.id))
            response = db.scalar(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id == assessment.id)) if assessment else None
            judgment = db.scalar(select(Judgment).where(Judgment.assessment_response_id == response.id)) if response else None
            entries.append({"source_attempt_id": str(attempt.id), "sequence_in_transition": attempt.sequence_in_transition, "pedagogy_id": attempt.pedagogy_id, "completion_reason": attempt.completion_reason, "instructional_traces": traces, "judged_evidence": {"gradable": judgment.gradable, "correctness": judgment.correctness, "observed_solo_state_id": judgment.observed_solo_state_id, "kc_evidence": judgment.kc_evidence, "relation_evidence": judgment.relation_evidence, "misconception_ids": judgment.misconception_ids, "evidence_summary": judgment.evidence_summary} if judgment else None, "passed": attempt.passed, "rubric_reasons": evaluation.decision_reasons if evaluation else []})
        return {"schema_version": "1.0", "transition_id": transition_id, "target_attempt_id": str(target_attempt_id), "attempts": entries}


class SessionRuntime:
    def __init__(self, catalog: StudyCatalog, selector=None, evaluator=None, history_builder=None):
        self.catalog = catalog; self.selector = selector or RandomSelector(); self.evaluator = evaluator or RubricEvaluator(); self.history_builder = history_builder or HistoryBuilder()
    def _event(self, db, session, event_type, payload, attempt_id=None):
        session.last_event_sequence += 1
        db.add(ProtocolEvent(session_id=session.id, sequence_no=session.last_event_sequence, event_type=event_type, event_version=1, attempt_id=attempt_id, actor="SYSTEM", correlation_id=uuid.uuid4(), payload=payload))
    def complete_section(self, db, session, attempt, scientific_outcome, formal_state_advanced):
        """Canonical, once-only scientific outcome for a completed transition."""
        prior=db.scalar(select(ProtocolEvent.id).where(ProtocolEvent.session_id==session.id,ProtocolEvent.event_type=="SECTION_COMPLETED",ProtocolEvent.payload["transition_id"].as_string()==attempt.transition_id))
        if prior is not None:
            raise ValueError("transition already has a completion outcome")
        self._event(db,session,"SECTION_COMPLETED",{"transition_id":attempt.transition_id,"scientific_outcome":scientific_outcome,"formal_state_advanced":formal_state_advanced},attempt.id)
    def _compiled(self, db, session): return self.catalog.load(db, session.study_version_id)
    def create_session(self, db: DbSession, study_version_id, build_id="test", runtime_config=None, institutional_id=None, capture_run_id=None, commit=True):
        compiled = self.catalog.load(db, study_version_id)
        session = Session(study_version_id=study_version_id, institutional_id=institutional_id, capture_run_id=capture_run_id, status="ACTIVE", phase="TRANSITION_READY", formal_state_id=compiled.protocol["initial_state_id"], current_attempt_number=0, application_build_id=build_id, runtime_config_snapshot=runtime_config or {})
        db.add(session); db.flush(); self._event(db, session, "SESSION_CREATED", {"study_version_id": str(study_version_id), "capture_run_id": str(capture_run_id) if capture_run_id else None}); self._create_attempt(db, session, compiled, compiled.protocol["transition_ids"][0]);
        if commit: db.commit()
        return session
    def _create_attempt(self, db, session, compiled, transition_id):
        used = db.scalars(select(Attempt.pedagogy_id).where(Attempt.session_id == session.id, Attempt.transition_id == transition_id)).all()
        decision = self.selector.choose([p for p in compiled.protocol["pedagogy_ids"] if p not in used], used)
        ordinal = len(used) + 1
        attempt = Attempt(session_id=session.id, transition_id=transition_id, sequence_in_transition=ordinal, pedagogy_id=decision.selected_id, status="ASSIGNED", formal_state_before_id=session.formal_state_id)
        db.add(attempt); db.flush(); session.current_transition_id=transition_id; session.current_attempt_id=attempt.id; session.current_attempt_number=ordinal; session.phase="INTERVENTION_ACTIVE"
        self._event(db, session, "PEDAGOGY_SELECTED", {"eligible_candidate_ids": decision.eligible_candidate_ids, "excluded_used_ids": decision.excluded_candidate_ids, "selected_id": decision.selected_id, "selection_method": decision.selection_method, "timestamp": decision.selected_at.isoformat()}, attempt.id)
        self._event(db, session, "ATTEMPT_CREATED", {"transition_id": transition_id, "pedagogy_id": decision.selected_id}, attempt.id)
        if ordinal > 1:
            history = self.history_builder.build(db, session.id, transition_id, attempt.id)
            db.add(LearnerHistorySnapshot(session_id=session.id, target_attempt_id=attempt.id, transition_id=transition_id, source_attempt_ids=[uuid.UUID(entry["source_attempt_id"]) for entry in history["attempts"]], summary=history, generation_method="DETERMINISTIC"))
        return attempt
    def complete_intervention(self, db: DbSession, session_id, reason="TUTOR_COMPLETE", commit=True):
        session = db.get(Session, session_id); attempt = db.get(Attempt, session.current_attempt_id)
        if session.phase != "INTERVENTION_ACTIVE": raise ValueError("intervention is not active")
        compiled = self._compiled(db, session); family = compiled.assessment_families[attempt.transition_id]
        seen = db.scalars(select(AssessmentInstance.assessment_form_id).where(AssessmentInstance.session_id == session.id)).all()
        decision = self.selector.choose([form["id"] for form in family["forms"] if form["id"] not in seen], seen)
        form = next(item for item in family["forms"] if item["id"] == decision.selected_id)
        attempt.status="ASSESSMENT_GENERATING"; attempt.completion_reason=reason; attempt.intervention_completed_at=datetime.now(timezone.utc)
        component_ids={"kc_ids":form["target_kc_ids"],"relation_ids":form["target_relation_ids"],"evidence_ids":form["target_evidence_ids"],"misconception_ids":form["relevant_misconception_ids"]}
        assessment = AssessmentInstance(session_id=session.id, attempt_id=attempt.id, transition_id=attempt.transition_id, assessment_family_id=family["id"], assessment_form_id=form["id"], status="GENERATING", candidate_form_ids=list(decision.eligible_candidate_ids), selection_method=decision.selection_method, selection_audit={"eligible_candidate_ids": decision.eligible_candidate_ids, "excluded_used_ids": decision.excluded_candidate_ids, "selected_id": decision.selected_id, "timestamp": decision.selected_at.isoformat()}, blueprint_snapshot=form, resolved_component_ids=component_ids, prompt_snapshot=None, hidden_scoring_context_snapshot=None)
        db.add(assessment); db.flush(); session.phase="ASSESSMENT_GENERATING"; self._event(db, session, "INTERVENTION_COMPLETED", {"reason":reason}, attempt.id); self._event(db, session, "ASSESSMENT_SELECTED", assessment.selection_audit, attempt.id)
        if commit: db.commit()
        return assessment
    def submit_assessment(self, db: DbSession, session_id, response_text, client_action_id=None, commit=True):
        session=db.get(Session,session_id); attempt=db.get(Attempt,session.current_attempt_id)
        assessment=db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id==attempt.id))
        if session.phase!="ASSESSMENT_ACTIVE" or not response_text.strip(): raise ValueError("assessment is not active or response is empty")
        response=AssessmentResponse(assessment_instance_id=assessment.id,response_text=response_text,response_format="plain",client_action_id=client_action_id or uuid.uuid4())
        db.add(response); db.flush(); assessment.status="SUBMITTED"; assessment.submitted_at=datetime.now(timezone.utc); attempt.status="JUDGING"; session.phase="JUDGING"; self._event(db,session,"ASSESSMENT_SUBMITTED",{"assessment_id":str(assessment.id)},attempt.id)
        if commit: db.commit()
        return response
    def apply_judgment(self, db: DbSession, session_id, observation: JudgeObservation, llm_call_id, parsed_judgment=None):
        session=db.get(Session,session_id); attempt=db.get(Attempt,session.current_attempt_id)
        if session.phase!="JUDGING": raise ValueError("session is not judging")
        compiled=self._compiled(db,session); transition=compiled.knowledge_slices[attempt.transition_id]["transition"]; rubric=compiled.rubrics[attempt.transition_id]
        assessment=db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id==attempt.id)); response=db.scalar(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id==assessment.id))
        result=self.evaluator.evaluate(transition,rubric,observation,assessment.assessment_form_id)
        call = db.get(LLMCall, llm_call_id)
        if call is None or call.purpose != "JUDGE" or call.status != "SUCCEEDED" or call.session_id != session.id:
            raise ValueError("judgment requires the successful persisted Judge LLMCall for this session")
        judgment=Judgment(assessment_response_id=response.id,llm_call_id=llm_call_id,rubric_id=rubric["id"],gradable=observation.gradable,correctness=observation.correctness,observed_solo_state_id=observation.observed_solo_state_id,kc_evidence={"demonstrated_evidence_ids":observation.demonstrated_evidence_ids},relation_evidence={},misconception_ids=list(observation.detected_misconception_ids),evidence_summary=parsed_judgment or {},confidence=None,ambiguity=None)
        db.add(judgment); db.flush()
        can_advance_formally = result.passed and session.formal_state_id == transition["from_state_id"]
        formal_state_after = transition["target_state_id"] if can_advance_formally else session.formal_state_id
        reasons = list(result.reasons)
        if result.passed and not can_advance_formally:
            reasons.append("FORMAL_ADVANCEMENT_BLOCKED_BY_PRIOR_UNRESOLVED_SECTION")
        evaluation=RubricEvaluation(judgment_id=judgment.id,attempt_id=attempt.id,transition_id=attempt.transition_id,rubric_id=rubric["id"],rule_snapshot=rubric["success_rule"],input_evidence_snapshot={"evidence_ids":observation.demonstrated_evidence_ids},passed=result.passed,decision_reasons=reasons,formal_state_before_id=session.formal_state_id,formal_state_after_id=formal_state_after)
        db.add(evaluation); assessment.status="CLOSED"; assessment.closed_at=datetime.now(timezone.utc); attempt.passed=result.passed; attempt.formal_state_after_id=evaluation.formal_state_after_id; attempt.status="PASSED" if result.passed else "FAILED"; attempt.completed_at=datetime.now(timezone.utc)
        self._event(db,session,"RUBRIC_EVALUATED",{"passed":result.passed,"reasons":result.reasons},attempt.id)
        if result.passed:
            session.formal_state_id=formal_state_after
            session.phase="SECTION_COMPLETE"
            self.complete_section(db,session,attempt,"PASSED",can_advance_formally)
        else:
            used=db.scalars(select(Attempt.pedagogy_id).where(Attempt.session_id==session.id,Attempt.transition_id==attempt.transition_id)).all()
            if len(used)<compiled.protocol["max_attempts_per_transition"]: self._create_attempt(db,session,compiled,attempt.transition_id)
            else:
                attempt.outcome_details={**(attempt.outcome_details or {}),"administrative_outcome":"PEDAGOGIES_EXHAUSTED_CONTINUE","scientific_outcome":"UNRESOLVED"}
                session.phase="SECTION_COMPLETE"
                self._event(db,session,"SECTION_CONTINUATION_ALLOWED",{"transition_id":attempt.transition_id,"reason":"PEDAGOGIES_EXHAUSTED_CONTINUE","scientific_outcome":"UNRESOLVED","formal_state_id":session.formal_state_id},attempt.id)
                self.complete_section(db,session,attempt,"UNRESOLVED",False)
        db.commit(); return result

    def advance_section(self, db: DbSession, session_id, commit=True):
        """Open the next participant section after its explicit completion gate."""
        session = db.get(Session, session_id)
        if not session or session.status != "ACTIVE" or session.phase != "SECTION_COMPLETE":
            raise ValueError("section is not ready to advance")
        compiled = self._compiled(db, session)
        transitions = compiled.protocol["transition_ids"]
        index = transitions.index(session.current_transition_id)
        if index >= len(transitions) - 1:
            raise ValueError("final section must be finished, not advanced")
        completed_transition = session.current_transition_id
        attempt = self._create_attempt(db, session, compiled, transitions[index + 1])
        self._event(db, session, "PARTICIPANT_ADVANCED_SECTION", {"from_transition_id":completed_transition,"to_transition_id":attempt.transition_id}, attempt.id)
        if commit: db.commit()
        return attempt

    def finish_session(self, db: DbSession, session_id, commit=True):
        """Finish after the final section gate while preserving unresolved science."""
        session = db.get(Session, session_id)
        if not session or session.status != "ACTIVE" or session.phase != "SECTION_COMPLETE":
            raise ValueError("session is not ready to finish")
        transitions = self._compiled(db, session).protocol["transition_ids"]
        if session.current_transition_id != transitions[-1]:
            raise ValueError("only the final section can finish the session")
        unresolved = db.scalar(select(ProtocolEvent.id).where(ProtocolEvent.session_id == session.id, ProtocolEvent.event_type == "SECTION_COMPLETED", ProtocolEvent.payload["scientific_outcome"].as_string() == "UNRESOLVED").limit(1)) is not None
        session.status = "UNRESOLVED" if unresolved else "COMPLETED"
        session.phase = "TERMINAL"
        session.terminal_reason = "COMPLETED_WITH_UNRESOLVED_SECTIONS" if unresolved else "COMPLETED_EA"
        session.ended_at = datetime.now(timezone.utc)
        self._event(db, session, "SESSION_COMPLETED", {"reason":session.terminal_reason,"scientific_outcome":"UNRESOLVED" if unresolved else "COMPLETED"}, session.current_attempt_id)
        if commit: db.commit()
        return session
