import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from solo_harness.runtime import controlled_executor as executor
from solo_harness.runtime.ai import AIExecutionRuntime, PreparedLLMRequest, RawLLMResponse
from solo_harness.runtime.controlled_c3_pilot_prompts import (
    C3GuidedFinalInconsistent, _overlay, guided_delivery_stage, new_guided_state, tutor_prompt,
)


def _move(subsection="C3.1", pedagogy="P2", index=2):
    return executor.contract("C3")["subsections"][subsection]["moves_by_pedagogy"][pedagogy][index]


def _payload(prompt):
    return json.loads(prompt.split("[ISOLATED_C3_TUTOR_CONTEXT]\n", 1)[1].split("\n[OUTPUT_SCHEMA]", 1)[0])


def test_no_c3_p2_semantic_matcher_remains():
    source = Path("src/solo_harness/runtime/controlled_c3_pilot_prompts.py").read_text(encoding="utf-8")
    for removed in ("classify_p2_reply", "next_guided_turn", "_component_interpretation",
                    "_classify_p2_reply_stateless", "_status_mentions", "_check_results_agree"):
        assert removed not in source
    assert "tutor_interprets_learner_reply" in source


def test_delivery_state_is_owned_by_tutor_flag_and_two_hint_bound():
    assert guided_delivery_stage("QUESTION", 0, False, False) == "QUESTION"
    assert guided_delivery_stage("QUESTION", 0, True, True) == "FINAL"
    assert guided_delivery_stage("QUESTION", 0, True, False) == "HINT_1"
    assert guided_delivery_stage("HINT_1", 1, True, False) == "HINT_2"
    with pytest.raises(C3GuidedFinalInconsistent):
        guided_delivery_stage("HINT_2", 2, True, False)
    with pytest.raises(C3GuidedFinalInconsistent):
        guided_delivery_stage("FINAL", 2, False, False)


def test_actual_prompt_supplies_question_then_only_the_next_hint_or_final_instruction():
    move = _move()
    approved = _overlay()[move["id"]]
    question = _payload(tutor_prompt(None, {}, [], None, None, move, 2,
                                     p2_stage="QUESTION", p2_hint_count=0, has_learner_reply=False))
    hint_one = _payload(tutor_prompt(None, {}, [{"role": "LEARNER", "content": "answer"}], None, None, move, 2,
                                     p2_stage="QUESTION", p2_hint_count=0, has_learner_reply=True))
    hint_two = _payload(tutor_prompt(None, {}, [{"role": "LEARNER", "content": "answer"}], None, None, move, 2,
                                     p2_stage="HINT_1", p2_hint_count=1, has_learner_reply=True))
    forced_final = _payload(tutor_prompt(None, {}, [{"role": "LEARNER", "content": "answer"}], None, None, move, 2,
                                         p2_stage="HINT_2", p2_hint_count=2, has_learner_reply=True))
    assert question["active_move"]["learner_reply_pending_evaluation"] is False
    assert "authored_hint_if_needed" not in question["active_move"]
    assert hint_one["active_move"]["authored_hint_if_needed"] == approved["hint_1"]
    assert hint_two["active_move"]["authored_hint_if_needed"] == approved["hint_2"]
    assert forced_final["active_move"]["final_explanation_required"] is True


def test_p1_and_p3_prompt_paths_do_not_receive_p2_state():
    for pedagogy in ("P1", "P3"):
        active = _payload(tutor_prompt(None, {}, [], None, None, _move("C3.1", pedagogy, 0), 0))["active_move"]
        assert active["stage"] is None
        assert "hint_count_already_delivered" not in active


def test_runtime_rejects_false_final_then_retries_without_extra_visual_or_judge():
    from test_unified_c1_c4_sqlite_runtime import SCIENTIFIC, _close_db, _db, _settings
    from solo_harness.db.models import LLMCall, Message, SubsectionProgress
    from solo_harness.runtime.engine import SessionRuntime
    from solo_harness.studies.activation import activate
    from solo_harness.studies.scientific_v051 import load_scientific_v051
    from solo_harness.studies.v051_native_compiler import compile_v051

    class ScriptedClient:
        def __init__(self):
            self.tutor_outputs = iter((
                {"learner_message": "Which checks are affected?", "ready_for_judge": False},
                {"learner_message": "Look at the changed bits in each complete check.", "ready_for_judge": False},
                {"learner_message": "Now compare the number of changes in row 1 and each column.", "ready_for_judge": False},
                {"learner_message": "Row 1 has two changes and passes; columns 1 and 2 each have one and fail.", "ready_for_judge": False},
                {"learner_message": "Row 1 has two changes and passes; columns 1 and 2 each have one and fail.", "ready_for_judge": True},
            ))
            self.judge_outputs = iter((
                {"decision": "ADVANCE", "guidance": "Complete."},
                {"decision": "CONTINUE", "guidance": "Repair the explanation."},
            ))

        def prepare(self, request):
            return PreparedLLMRequest(request, {}, "{}", {})

        async def send(self, prepared):
            payload = (next(self.tutor_outputs) if prepared.request.logical_role == "TUTOR"
                       else next(self.judge_outputs))
            return RawLLMResponse(None, 200, json.dumps(payload), {}, payload, "stop", False, {}, 1)

    db = _db()
    try:
        compiled = compile_v051(load_scientific_v051(SCIENTIFIC))
        version = activate(db, compiled, make_active=True, allow_unified_candidate=True)
        runtime = SessionRuntime(SimpleNamespace(load=lambda *_: compiled))
        session = runtime.create_v051_internal_test_session(
            db, version.id, unified_controlled_study=True, starting_transition_id="C3",
            initial_pedagogy_id="P2", c3_isolated_pilot=True,
        )
        progress = db.scalar(select(SubsectionProgress).where(SubsectionProgress.session_id == session.id,
                                                               SubsectionProgress.subsection_id == "C3.1"))
        controlled = dict(progress.instructional_state["controlled_executor"])
        controlled["move_index"] = 2
        progress.instructional_state = {**progress.instructional_state, "controlled_executor": controlled}
        db.commit()
        ai = AIExecutionRuntime(runtime, ScriptedClient(), _settings())

        for learner_text in (None, "Every check passes.", "Still every check passes.", "I do not know."):
            call = ai.reserve_tutor(db, session.id, learner_text=learner_text)
            asyncio.run(ai.execute(db, call))
            if learner_text is None:
                asyncio.run(ai.execute(db, call))
        db.refresh(progress)
        guided = progress.instructional_state["controlled_executor"]["c3_guided"]
        assert guided["stage"] == "HINT_2" and guided["hint_count"] == 2
        failed = db.scalar(select(LLMCall).where(
            LLMCall.attempt_id == session.current_attempt_id,
            LLMCall.purpose == "TUTOR",
            LLMCall.error_class == "C3_FINAL_READY_FLAG_INCONSISTENT",
        ))
        assert (failed.status, failed.error_class) == ("INVALID_OUTPUT", "C3_FINAL_READY_FLAG_INCONSISTENT")
        messages = db.scalars(select(Message).where(Message.attempt_id == session.current_attempt_id,
                                                     Message.role == "TUTOR").order_by(Message.sequence_no)).all()
        assert [m.instructional_trace.get("c3_guided_stage") for m in messages] == ["QUESTION", "HINT_1", "HINT_2"]
        assert [m.instructional_trace.get("pilot_visual", {}).get("stage") for m in messages
                if m.instructional_trace.get("pilot_visual")] == ["prompt"]

        retry = ai.reserve_manual_retry(db, session.id)
        asyncio.run(ai.execute(db, retry))
        db.refresh(progress)
        guided = progress.instructional_state["controlled_executor"]["c3_guided"]
        assert guided["stage"] == "FINAL" and guided["hint_count"] == 2
        assert progress.instructional_state["controlled_executor"]["status"] == "APPROVED_AWAITING_NEXT"
        messages = db.scalars(select(Message).where(Message.attempt_id == session.current_attempt_id,
                                                     Message.role == "TUTOR").order_by(Message.sequence_no)).all()
        assert [m.instructional_trace.get("c3_guided_stage") for m in messages] == ["QUESTION", "HINT_1", "HINT_2", "FINAL"]
        visuals = [m.instructional_trace.get("pilot_visual", {}).get("stage") for m in messages
                   if m.instructional_trace.get("pilot_visual")]
        assert visuals == ["prompt", "complete"]
        assert len(messages) == len({m.llm_call_id for m in messages})

        tutor_calls_before = db.scalars(select(LLMCall).where(
            LLMCall.attempt_id == session.current_attempt_id, LLMCall.purpose == "TUTOR",
        )).all()
        controlled = dict(progress.instructional_state["controlled_executor"])
        controlled["status"] = "REVIEWING_MOVE"
        progress.instructional_state = {**progress.instructional_state, "controlled_executor": controlled}
        db.commit()
        bounded_judge = ai.reserve_conversation_judge(db, session.id, auto_reviews_since_learner=6)
        asyncio.run(ai.execute(db, bounded_judge))
        db.refresh(progress)
        assert progress.status == "DELIVERY_EXCEPTION"
        assert progress.delivery_exception["reason"] == "C3 move Judge repair limit exhausted"
        tutor_calls_after = db.scalars(select(LLMCall).where(
            LLMCall.attempt_id == session.current_attempt_id, LLMCall.purpose == "TUTOR",
        )).all()
        assert len(tutor_calls_after) == len(tutor_calls_before)
    finally:
        _close_db(db)
