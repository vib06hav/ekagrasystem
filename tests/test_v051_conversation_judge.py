"""Controlled PostgreSQL integration tests for the real Conversation Judge path."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import Attempt, ConversationJudgeDecision, LLMCall, Message, Session, V04Evaluation
from solo_harness.runtime.ai import AIExecutionRuntime, PreparedLLMRequest, RawLLMResponse
from solo_harness.runtime.engine import RandomSelector, SessionRuntime
from solo_harness.studies.activation import activate
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051


DATABASE_URL = os.environ.get("EKAGRA_STAGE3_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="set EKAGRA_STAGE3_DATABASE_URL for PostgreSQL integration")
ROOT = Path("studies/networks_error_detection_parity_f1/v0.5.1")


class _First:
    def choice(self, values): return sorted(values)[0]


class _Client:
    def __init__(self, payload): self.payload = payload
    def prepare(self, request): return PreparedLLMRequest(request, {}, "{}", {})
    async def send(self, prepared):
        return RawLLMResponse(None, 200, "{}", {"choices": [{"message": {"parsed": self.payload}}]}, self.payload, "stop", False, {}, 1)


class _Stage5Client:
    """Controlled semantic model which still exercises production call storage."""
    @staticmethod
    def _context(message, marker):
        body = message.content.split(marker, 1)[1]
        return json.loads(body.split("\n\n[", 1)[0])

    def prepare(self, request): return PreparedLLMRequest(request, {}, "{}", {})

    async def send(self, prepared):
        request = prepared.request
        prompt = request.messages[0]
        if request.logical_role == "TUTOR":
            context = self._context(prompt, "[V051_ACTIVE_SUBSECTION_TUTOR_CONTEXT]\n")
            payload = {"learner_message": "Visible required teaching for the active subsection.",
                       "proposed_move_ids": context["required_move_ids"], "proposed_content_ids": context["required_content_ids"],
                       "proposes_subsection_close": True, "fidelity_note": "Controlled pedagogy-specific delivery."}
        elif request.logical_role == "CONVERSATION_JUDGE":
            context = self._context(prompt, "[V051_CONVERSATION_JUDGE_CONTEXT]\n")
            tutor = next(turn for turn in reversed(context["dialogue_turn_ids_and_text"]) if turn["role"] == "TUTOR")
            moves, contents = context["persisted_evidence_ledger"]["required_move_ids"], context["persisted_evidence_ledger"]["required_content_ids"]
            claims = lambda values: [{"obligation_id": value, "message_id": tutor["id"], "supporting_excerpt": "Visible required teaching"} for value in values]
            payload = {"active_subsection_id": context["active_subsection"]["id"], "decision": "ADVANCE_SUBSECTION", "completed_move_ids": moves,
                       "required_content_status": [{"ref": value, "status": "DELIVERED", "supporting_excerpt_or_reason": "Visible required teaching"} for value in contents],
                       "pedagogy_fidelity": "SATISFIED", "learner_signal": "No mastery inference; optional doubt opportunity was provided.", "open_doubts": [],
                       "evidence_refs": [tutor["id"]], "move_evidence": claims(moves), "content_evidence": claims(contents),
                       "next_allowed_instruction": "Proceed only under the active authored pedagogy.", "delivery_exception_reason": None, "confidence": "HIGH"}
        elif request.logical_role == "ASSESSMENT_WRITER":
            payload = ({"stem": "Which conclusion follows from the displayed verified parity case?", "correct_option": "The oracle-backed conclusion.", "distractors": ["Unsupported A.", "Unsupported B.", "Unsupported C."]}
                       if request.response_schema_name == "MCQProse" else {"question": "Explain the displayed parity result using its stated facts."})
        elif request.logical_role == "SEMANTIC_REVIEW":
            payload = ({"verdict": "ACCEPT", "stem_matches_contract": True, "assumptions_visible": True, "exactly_one_defensible_option": True,
                        "option_assessments": [{"truth_status": "TRUE", "matches_intended_meaning": True, "scientific_reason": "Verified."}, *[{"truth_status": "FALSE", "matches_intended_meaning": True, "scientific_reason": "Unsupported."} for _ in range(3)]], "rationale": "Verified contract."}
                       if request.response_schema_name == "SemanticReview" else {"verdict": "ACCEPT", "elicits_slot_evidence": True, "assumes_only_visible_facts": True, "scientifically_consistent": True, "does_not_reveal_answer": True, "rationale": "Verified contract."})
        else:  # Formal blind subjective Judge.
            context = self._context(prompt, "[V051_BLIND_SUBJECTIVE_JUDGE_CONTEXT]\n")
            quote = context["learner_response"]
            payload = {"gradable_status": "GRADABLE", "subjective_points": 1, "observed_solo_structure": "controlled", "material_correctness": "CORRECT", "criterion_evidence": [{"criterion": "controlled", "learner_quote": quote, "interpretation": "controlled valid response"}], "misconception_evidence": [], "verbatim_quotes": [quote], "alternative_reasoning_used": False, "unverified_claims": [], "review_reason": None, "score_justification": "Controlled valid response."}
        return RawLLMResponse(None, 200, json.dumps(payload), {"choices": [{"message": {"parsed": payload}}]}, payload, "stop", False, {}, 1)


def _settings():
    return SimpleNamespace(llm_provider="test", judge_model="judge", tutor_model="tutor", judge_temperature=0,
                           tutor_temperature=0, judge_max_output_tokens=1000, tutor_max_output_tokens=1000,
                           llm_request_timeout_seconds=10)


def _output(progress, action, evidence_id=None):
    statuses = [{"ref": ref, "status": "DELIVERED" if action == "ADVANCE_SUBSECTION" else "MISSING", "supporting_excerpt_or_reason": "Tutor turn" if action == "ADVANCE_SUBSECTION" else "remaining instruction"} for ref in progress.required_content_ids]
    claims = ([{"obligation_id": value, "message_id": str(evidence_id), "supporting_excerpt": "visible, accurate explanation"} for value in progress.required_move_ids] if action == "ADVANCE_SUBSECTION" else [])
    content_claims = ([{"obligation_id": value, "message_id": str(evidence_id), "supporting_excerpt": "visible, accurate explanation"} for value in progress.required_content_ids] if action == "ADVANCE_SUBSECTION" else [])
    return {"active_subsection_id": progress.subsection_id, "decision": action,
            "completed_move_ids": progress.required_move_ids if action == "ADVANCE_SUBSECTION" else [],
            "required_content_status": statuses, "pedagogy_fidelity": "SATISFIED", "learner_signal": "controlled learner signal",
            "open_doubts": [], "evidence_refs": [str(evidence_id)] if evidence_id else [], "move_evidence": claims, "content_evidence": content_claims,
            "next_allowed_instruction": "Use the next authored move.",
            "delivery_exception_reason": "controlled delivery defect" if action == "DELIVERY_EXCEPTION" else None,
            "confidence": "HIGH"}


def _setup(db):
    compiled = compile_v051(load_scientific_v051(ROOT)); version = activate(db, compiled)
    runtime = SessionRuntime(SimpleNamespace(load=lambda _db, _id: compiled), selector=RandomSelector(_First()))
    session = Session(study_version_id=version.id, status="ACTIVE", phase="INTERVENTION_ACTIVE", formal_state_id="P", current_attempt_number=0, application_build_id="stage4-test", runtime_config_snapshot={})
    db.add(session); db.flush(); attempt = runtime._create_attempt(db, session, compiled, "C1"); db.flush()
    progress = runtime.inspect_v051_subsections(db, session.id)[0]
    tutor = Message(attempt_id=attempt.id, sequence_no=1, role="TUTOR", content_text="A visible, accurate explanation.", content_format="plain", instructional_trace={"subsection_id": progress.subsection_id}, material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])
    learner = Message(attempt_id=attempt.id, sequence_no=2, role="LEARNER", content_text="I do not know why.", content_format="plain", material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])
    db.add_all([tutor, learner]); db.commit()
    return compiled, runtime, session.id, progress, tutor.id


@pytest.mark.parametrize("action", ["CONTINUE_TEACHING", "CLARIFY_OR_SCAFFOLD", "CONSOLIDATE", "ADVANCE_SUBSECTION", "DELIVERY_EXCEPTION"])
def test_conversation_judge_reserves_validates_persists_and_applies_actions(action):
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        compiled, runtime, session_id, progress, tutor_id = _setup(db)
        ai = AIExecutionRuntime(runtime, _Client(_output(progress, action, tutor_id)), _settings())
        call_id = ai.reserve_conversation_judge(db, session_id, commit=True)
        asyncio.run(ai.execute(db, call_id))
        decision = db.get(ConversationJudgeDecision, db.scalar(__import__("sqlalchemy").select(ConversationJudgeDecision.id).where(ConversationJudgeDecision.llm_call_id == call_id)))
        assert decision.action == action and decision.application_status == "APPLIED"
        if action == "ADVANCE_SUBSECTION":
            assert runtime.inspect_v051_subsections(db, session_id)[0].status == "COMPLETED"
        if action == "DELIVERY_EXCEPTION":
            assert runtime.inspect_v051_subsections(db, session_id)[0].status == "DELIVERY_EXCEPTION"
        assert db.get(LLMCall, call_id).status == "SUCCEEDED"


def test_conversation_judge_rejects_stale_or_malformed_output_without_advancing():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        compiled, runtime, session_id, progress, tutor_id = _setup(db)
        ai = AIExecutionRuntime(runtime, _Client({"not": "the required schema"}), _settings())
        invalid = ai.reserve_conversation_judge(db, session_id, commit=True); asyncio.run(ai.execute(db, invalid))
        assert db.get(LLMCall, invalid).status == "INVALID_OUTPUT"
        assert runtime.inspect_v051_subsections(db, session_id)[0].status == "ACTIVE"
        ai = AIExecutionRuntime(runtime, _Client(_output(progress, "ADVANCE_SUBSECTION", tutor_id)), _settings())
        stale = ai.reserve_conversation_judge(db, session_id, commit=True)
        attempt = db.get(Attempt, runtime.inspect_v051_subsections(db, session_id)[0].attempt_id)
        db.add(Message(attempt_id=attempt.id, sequence_no=3, role="LEARNER", content_text="newer turn", content_format="plain", material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])); db.commit()
        asyncio.run(ai.execute(db, stale))
        assert db.get(LLMCall, stale).error_class == "APPLICATION_FAILURE"
        assert runtime.inspect_v051_subsections(db, session_id)[0].status == "ACTIVE"


def test_stage5_real_persisted_candidate_loop_reaches_paas_and_blind_assessment():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        compiled, runtime, session_id, _, _ = _setup(db)
        ai = AIExecutionRuntime(runtime, _Stage5Client(), _settings())
        # Execution follows its persisted chain: Tutor close checkpoint →
        # Conversation Judge → next Tutor. No test-only transition helper is
        # used to reach Paas.
        tutor_call = ai.reserve_tutor(db, session_id, commit=True)
        asyncio.run(ai.execute(db, tutor_call))
        assert db.get(Session, session_id).phase == "PAAS_PENDING"
        assert all(row.status == "COMPLETED" for row in runtime.inspect_v051_subsections(db, session_id))
        build = ai.reserve_paas_assessment(db, session_id, 5, commit=True)
        asyncio.run(ai.execute(db, build))
        session = db.get(Session, session_id)
        assert session.phase == "ASSESSMENT_ACTIVE"
        assessment = db.scalar(__import__("sqlalchemy").select(__import__("solo_harness.db.models", fromlist=["AssessmentInstance"]).AssessmentInstance).where(__import__("solo_harness.db.models", fromlist=["AssessmentInstance"]).AssessmentInstance.attempt_id == session.current_attempt_id))
        from solo_harness.runtime.v04_persistence import submit_f1_response
        answers = {item["id"]: next(option["id"] for option in item["options"] if option["id"] == next(private["correct_option_id"] for private in assessment.frozen_private_snapshot["mcqs"] if private["id"] == item["id"])) for item in assessment.frozen_public_snapshot["mcqs"]}
        response = submit_f1_response(db, runtime, session_id, answers, "The stated parity rule explains the shown result.", __import__("uuid").uuid4())
        db.commit(); judge = ai.reserve_f1_judge(db, session_id, response, commit=True); asyncio.run(ai.execute(db, judge))
        assert db.get(Session, session_id).phase == "SECTION_COMPLETE"
        assert db.scalar(__import__("sqlalchemy").select(V04Evaluation.evaluation_version)) == "v051.native.1"
        assert "global_pedagogy" not in db.get(LLMCall, judge).compiled_prompt_text


def test_stage5_judge_guidance_is_compiled_into_the_next_tutor_turn():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        _, runtime, session_id, progress, tutor_id = _setup(db)
        payload = _output(progress, "CLARIFY_OR_SCAFFOLD", tutor_id)
        payload["next_allowed_instruction"] = "Address the stated doubt with the next P1 move."
        ai = AIExecutionRuntime(runtime, _Client(payload), _settings())
        judge = ai.reserve_conversation_judge(db, session_id, commit=True)
        asyncio.run(ai.execute(db, judge))
        next_tutor = ai.reserve_tutor(db, session_id, commit=True)
        prompt = db.get(LLMCall, next_tutor).compiled_prompt_text
        assert "Address the stated doubt with the next P1 move." in prompt
        assert "previous_conversation_judge_guidance" in prompt
