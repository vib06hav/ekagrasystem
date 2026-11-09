"""Controlled PostgreSQL integration tests for the v0.5 semantic Judge path."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance, Attempt, ConversationJudgeDecision, LLMCall, Message, Session, StudyVersion, V04Evaluation
from solo_harness.runtime.ai import AIExecutionRuntime, PreparedLLMRequest, RawLLMResponse
from solo_harness.runtime.engine import RandomSelector, SessionRuntime
from solo_harness.studies.activation import activate
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051
from solo_harness.web import _internal_v051_candidate


DATABASE_URL = os.environ.get("EKAGRA_STAGE3_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="set EKAGRA_STAGE3_DATABASE_URL for PostgreSQL integration")
ROOT = Path("studies/networks_error_detection_parity_f1/v0.5")


class _First:
    def choice(self, values): return sorted(values)[0]


class _Client:
    def __init__(self, payload): self.payload = payload
    def prepare(self, request): return PreparedLLMRequest(request, {}, "{}", {})
    async def send(self, prepared):
        return RawLLMResponse(None, 200, json.dumps(self.payload), {"choices": [{"message": {"parsed": self.payload}}]}, self.payload, "stop", False, {}, 1)


class _WorkflowClient:
    """Controlled model outputs that use production call reservation and parsing."""
    @staticmethod
    def _context(message, marker):
        body = message.content.split(marker, 1)[1]
        return json.loads(body.split("\n\n[", 1)[0])

    def __init__(self, decision="ADVANCE", guidance="The subsection is complete and scientifically sound."):
        self.decision, self.guidance = decision, guidance

    def prepare(self, request): return PreparedLLMRequest(request, {}, "{}", {})

    async def send(self, prepared):
        request = prepared.request
        if request.logical_role == "TUTOR":
            payload = {"learner_message": "Here is the active subsection's treatment-faithful explanation. What would you like clarified?", "ready_for_judge": True}
        elif request.logical_role == "CONVERSATION_JUDGE":
            payload = {"decision": self.decision, "guidance": self.guidance}
        elif request.logical_role == "ASSESSMENT_WRITER":
            payload = ({"stem": "Which conclusion follows from the displayed verified parity case?", "correct_option": "The oracle-backed conclusion.", "distractors": ["Unsupported A.", "Unsupported B.", "Unsupported C."]}
                       if request.response_schema_name == "MCQProse" else {"question": "Explain the displayed parity result using its stated facts."})
        elif request.logical_role == "SEMANTIC_REVIEW":
            payload = ({"verdict": "ACCEPT", "stem_matches_contract": True, "assumptions_visible": True, "exactly_one_defensible_option": True,
                        "option_assessments": [{"truth_status": "TRUE", "matches_intended_meaning": True, "scientific_reason": "Verified."}, *[{"truth_status": "FALSE", "matches_intended_meaning": True, "scientific_reason": "Unsupported."} for _ in range(3)]], "rationale": "Verified contract."}
                       if request.response_schema_name == "SemanticReview" else {"verdict": "ACCEPT", "elicits_slot_evidence": True, "assumes_only_visible_facts": True, "scientifically_consistent": True, "does_not_reveal_answer": True, "rationale": "Verified contract."})
        else:  # Formal blind Subjective Judge is intentionally unchanged.
            context = self._context(request.messages[0], "[V051_BLIND_SUBJECTIVE_JUDGE_CONTEXT]\n")
            quote = context["learner_response"]
            payload = {"gradable_status": "GRADABLE", "subjective_points": 1, "observed_solo_structure": "controlled", "material_correctness": "CORRECT", "criterion_evidence": [{"criterion": "controlled", "learner_quote": quote, "interpretation": "controlled valid response"}], "misconception_evidence": [], "verbatim_quotes": [quote], "alternative_reasoning_used": False, "unverified_claims": [], "review_reason": None, "score_justification": "Controlled valid response."}
        return RawLLMResponse(None, 200, json.dumps(payload), {"choices": [{"message": {"parsed": payload}}]}, payload, "stop", False, {}, 1)


def _settings():
    return SimpleNamespace(llm_provider="test", judge_model="judge", tutor_model="tutor", judge_temperature=0,
                           tutor_temperature=0, judge_max_output_tokens=1000, tutor_max_output_tokens=1000,
                           llm_request_timeout_seconds=10)


def _output(action, guidance="Use the next treatment-faithful instructional move."):
    return {"decision": action, "guidance": guidance}


def _setup(db, with_history=True):
    compiled = compile_v051(load_scientific_v051(ROOT)); version = activate(db, compiled)
    runtime = SessionRuntime(SimpleNamespace(load=lambda _db, _id: compiled), selector=RandomSelector(_First()))
    session = Session(study_version_id=version.id, status="ACTIVE", phase="INTERVENTION_ACTIVE", formal_state_id="P", current_attempt_number=0, application_build_id="stage6-test", runtime_config_snapshot={})
    db.add(session); db.flush(); attempt = runtime._create_attempt(db, session, compiled, "C1"); db.flush()
    progress = runtime.inspect_v051_subsections(db, session.id)[0]
    tutor = Message(attempt_id=attempt.id, sequence_no=1, role="TUTOR", content_text="A visible, accurate explanation.", content_format="plain", instructional_trace={"subsection_id": progress.subsection_id}, material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])
    learner = Message(attempt_id=attempt.id, sequence_no=2, role="LEARNER", content_text="I do not know why.", content_format="plain", material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])
    reply = Message(attempt_id=attempt.id, sequence_no=3, role="TUTOR", content_text="Here is a clarification responding to your doubt.", content_format="plain", instructional_trace={"subsection_id": progress.subsection_id}, material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])
    if with_history:
        db.add_all([tutor, learner, reply])
    db.commit()
    return runtime, session.id, progress, tutor.id if with_history else None


def _historical_version(db, current):
    """A legacy immutable row only used to exercise the audit-only policy."""
    existing = db.scalar(select(StudyVersion).where(
        StudyVersion.study_id == current.study_id,
        StudyVersion.content_version == "v0.5.1",
    ))
    if existing is not None:
        return existing
    version = StudyVersion(
        study_id=current.study_id, content_version="v0.5.1", study_schema_version=current.study_schema_version,
        content_canonicalization_version=current.content_canonicalization_version, content_hash="1" * 64,
        canonical_authored_definition=b"{}", source_bundle={"status": "historical-test"}, source_provenance={},
        compiler_contract_version=current.compiler_contract_version, snapshot_schema_version=current.snapshot_schema_version,
        snapshot_hash=uuid.uuid4().hex * 2, compiled_snapshot=current.compiled_snapshot,
    )
    db.add(version); db.flush()
    return version


@pytest.mark.parametrize("action", ["CONTINUE", "ADVANCE", "HOLD"])
def test_conversation_judge_minimal_decisions_persist_and_apply(action):
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        runtime, session_id, _, _ = _setup(db)
        ai = AIExecutionRuntime(runtime, _Client(_output(action)), _settings())
        call_id = ai.reserve_conversation_judge(db, session_id, commit=True)
        asyncio.run(ai.execute(db, call_id))
        decision = db.scalar(select(ConversationJudgeDecision).where(ConversationJudgeDecision.llm_call_id == call_id))
        assert decision.action == action and decision.application_status == "APPLIED"
        rows = runtime.inspect_v051_subsections(db, session_id)
        if action == "ADVANCE":
            assert rows[0].status == "COMPLETED" and rows[1].status == "ACTIVE"
            assert rows[0].move_evidence == {} and rows[0].content_evidence == {}
        elif action == "HOLD":
            assert rows[0].status == "DELIVERY_EXCEPTION"
        else:
            assert rows[0].status == "ACTIVE"
        assert db.get(LLMCall, call_id).status == "SUCCEEDED"


def test_invalid_or_stale_judge_output_is_audited_and_freshly_retryable():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        runtime, session_id, _, _ = _setup(db)
        ai = AIExecutionRuntime(runtime, _Client({"not": "the required schema"}), _settings())
        malformed = ai.reserve_conversation_judge(db, session_id, commit=True); asyncio.run(ai.execute(db, malformed))
        assert db.get(LLMCall, malformed).status == "INVALID_OUTPUT"
        assert runtime.inspect_v051_subsections(db, session_id)[0].status == "ACTIVE"

        ai = AIExecutionRuntime(runtime, _Client(_output("ADVANCE")), _settings())
        stale = ai.reserve_conversation_judge(db, session_id, commit=True)
        attempt = db.get(Attempt, runtime.inspect_v051_subsections(db, session_id)[0].attempt_id)
        db.add(Message(attempt_id=attempt.id, sequence_no=4, role="LEARNER", content_text="A newer real learner turn.", content_format="plain", material_ids=[], exposed_kc_ids=[], exposed_relation_ids=[])); db.commit()
        asyncio.run(ai.execute(db, stale))
        stale_call = db.get(LLMCall, stale)
        assert stale_call.status == "INVALID_OUTPUT" and stale_call.error_class == "STALE_CONTEXT"
        retry = ai.reserve_manual_retry(db, session_id, commit=True)
        assert retry != stale and db.get(LLMCall, retry).request_payload["retry_of"] == str(stale)
        assert db.get(LLMCall, retry).purpose == "TUTOR"


def test_failed_advance_application_rolls_back_before_marking_a_transient_failure(monkeypatch):
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        runtime, session_id, _, _ = _setup(db)
        ai = AIExecutionRuntime(runtime, _Client(_output("ADVANCE")), _settings())
        call_id = ai.reserve_conversation_judge(db, session_id, commit=True)
        original = runtime.advance_v051_subsection

        def fail_after_decision(*args, **kwargs):
            raise RuntimeError("controlled database interruption after decision persistence")

        monkeypatch.setattr(runtime, "advance_v051_subsection", fail_after_decision)
        asyncio.run(ai.execute(db, call_id))
        failed = db.get(LLMCall, call_id)
        assert failed.status == "RECEIVED" and failed.error_class == "APPLICATION_FAILURE"
        assert db.scalar(select(func.count()).select_from(ConversationJudgeDecision).where(ConversationJudgeDecision.llm_call_id == call_id)) == 0
        rows = runtime.inspect_v051_subsections(db, session_id)
        assert rows[0].status == "ACTIVE" and rows[1].status == "PENDING"
        assert "last_action" not in (rows[0].instructional_state or {})

        monkeypatch.setattr(runtime, "advance_v051_subsection", original)
        assert ai.reserve_manual_retry(db, session_id, commit=True) == call_id
        asyncio.run(ai.execute(db, call_id))
        assert db.get(LLMCall, call_id).status == "SUCCEEDED"
        assert db.scalar(select(ConversationJudgeDecision).where(ConversationJudgeDecision.llm_call_id == call_id)).application_status == "APPLIED"
        assert runtime.inspect_v051_subsections(db, session_id)[1].status == "ACTIVE"


def test_historical_v051_judge_response_is_held_for_audit_without_reinterpretation():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        runtime, session_id, _, _ = _setup(db)
        session = db.get(Session, session_id)
        historical = _historical_version(db, db.get(StudyVersion, session.study_version_id))
        session.study_version_id = historical.id; db.commit()
        legacy = {"decision": "ADVANCE_SUBSECTION", "active_subsection_id": "C1.1"}
        ai = AIExecutionRuntime(runtime, _Client(legacy), _settings())
        call_id = ai.reserve_conversation_judge(db, session_id, commit=True)
        asyncio.run(ai.execute(db, call_id))
        call = db.get(LLMCall, call_id)
        assert call.status == "TECHNICAL_HOLD" and call.error_class == "HISTORICAL_CONTRACT_INCOMPATIBLE"
        assert "ADVANCE_SUBSECTION" in call.raw_response_text
        assert db.scalar(select(func.count()).select_from(ConversationJudgeDecision).where(ConversationJudgeDecision.llm_call_id == call_id)) == 0
        with pytest.raises(ValueError, match="audit-only"):
            ai.reserve_manual_retry(db, session_id, commit=True, authorized_requeue=True)


def test_internal_candidate_selection_uses_configured_v05_not_registration_order():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        runtime, session_id, _, _ = _setup(db)
        current = db.get(StudyVersion, db.get(Session, session_id).study_version_id)
        _historical_version(db, current)
        selected = _internal_v051_candidate(db, SimpleNamespace(v051_internal_candidate_version="v0.5"))
        assert selected.id == current.id and selected.content_version == "v0.5"


def test_real_persisted_tutor_judge_flow_advances_without_forced_learner_turns_to_paas_and_assessment():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        runtime, session_id, _, _ = _setup(db, with_history=False)
        ai = AIExecutionRuntime(runtime, _WorkflowClient(), _settings())
        initial_tutor = ai.reserve_tutor(db, session_id, commit=True)
        asyncio.run(ai.execute(db, initial_tutor))
        assert db.scalar(select(func.count()).select_from(Message).where(Message.attempt_id == db.get(Session, session_id).current_attempt_id, Message.role == "LEARNER")) == 0
        session = db.get(Session, session_id)
        assert session.phase == "PAAS_PENDING"
        assert all(row.status == "COMPLETED" for row in runtime.inspect_v051_subsections(db, session_id))
        assert db.scalar(select(func.count()).select_from(LLMCall).where(LLMCall.attempt_id == session.current_attempt_id, LLMCall.purpose == "CONVERSATION_JUDGE")) == 4
        build = ai.reserve_paas_assessment(db, session_id, 5, commit=True)
        asyncio.run(ai.execute(db, build))
        assessment = db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id == session.current_attempt_id))
        from solo_harness.runtime.v04_persistence import submit_f1_response
        answers = {item["id"]: next(option["id"] for option in item["options"] if option["id"] == next(private["correct_option_id"] for private in assessment.frozen_private_snapshot["mcqs"] if private["id"] == item["id"])) for item in assessment.frozen_public_snapshot["mcqs"]}
        response = submit_f1_response(db, runtime, session_id, answers, "The stated parity rule explains the shown result.", uuid.uuid4())
        db.commit(); judge = ai.reserve_f1_judge(db, session_id, response, commit=True); asyncio.run(ai.execute(db, judge))
        assert db.get(Session, session_id).phase == "SECTION_COMPLETE"
        assert db.scalar(select(V04Evaluation.evaluation_version)) == "v051.native.1"


def test_continue_guidance_is_compiled_into_the_next_tutor_turn():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        runtime, session_id, _, _ = _setup(db)
        guidance = "Address the stated doubt with the next P1 move."
        ai = AIExecutionRuntime(runtime, _WorkflowClient("CONTINUE", guidance), _settings())
        judge = ai.reserve_conversation_judge(db, session_id, commit=True)
        asyncio.run(ai.execute(db, judge))
        next_tutor = db.scalar(select(LLMCall).where(LLMCall.session_id == session_id, LLMCall.purpose == "TUTOR").order_by(LLMCall.started_at.desc()))
        assert guidance in next_tutor.compiled_prompt_text
        assert "previous_conversation_judge_guidance" in next_tutor.compiled_prompt_text


class _ReadinessClient(_WorkflowClient):
    """Tutor first awaits a learner; its next response requests review."""
    def __init__(self, ready_sequence):
        super().__init__()
        self.ready_sequence = iter(ready_sequence)

    async def send(self, prepared):
        if prepared.request.logical_role == "TUTOR":
            ready = next(self.ready_sequence, False)
            payload = {"learner_message": "This is instruction, not a mastery check.", "ready_for_judge": ready}
            return RawLLMResponse(None, 200, json.dumps(payload), {"choices": [{"message": {"parsed": payload}}]}, payload, "stop", False, {}, 1)
        return await super().send(prepared)


def test_learner_question_reaches_tutor_before_judge_review():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        runtime, session_id, _, _ = _setup(db, with_history=False)
        ai = AIExecutionRuntime(runtime, _ReadinessClient([False, True, False]), _settings())
        initial = ai.reserve_tutor(db, session_id, commit=True)
        asyncio.run(ai.execute(db, initial))
        assert db.scalar(select(func.count()).select_from(LLMCall).where(LLMCall.session_id == session_id, LLMCall.purpose == "CONVERSATION_JUDGE")) == 0
        reply = ai.reserve_tutor(db, session_id, learner_text="I am confused about bit positions.", commit=True)
        assert db.get(LLMCall, reply).purpose == "TUTOR"
        asyncio.run(ai.execute(db, reply))
        calls = db.scalars(select(LLMCall).where(LLMCall.session_id == session_id, LLMCall.purpose == "CONVERSATION_JUDGE")).all()
        assert len(calls) == 1 and calls[0].status == "SUCCEEDED"
        messages = db.scalars(select(Message).where(Message.attempt_id == db.get(Session, session_id).current_attempt_id).order_by(Message.sequence_no)).all()
        assert messages[-3].role == "LEARNER" and messages[-2].role == "TUTOR" and messages[-1].role == "TUTOR"


def test_unattended_continue_reviews_have_a_bound():
    factory = make_session_factory(DATABASE_URL)
    with factory() as db:
        runtime, session_id, _, _ = _setup(db, with_history=False)
        ai = AIExecutionRuntime(runtime, _WorkflowClient("CONTINUE", "Finish the contrast before advancing."), _settings())
        initial = ai.reserve_tutor(db, session_id, commit=True)
        asyncio.run(ai.execute(db, initial))
        judge_count = db.scalar(select(func.count()).select_from(LLMCall).where(LLMCall.session_id == session_id, LLMCall.purpose == "CONVERSATION_JUDGE"))
        assert judge_count == 6
        assert runtime.inspect_v051_subsections(db, session_id)[0].status == "ACTIVE"
