"""V2.2 prompt-contract regression tests. No LLM or database calls required."""
import json
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.skip(
    reason="Superseded by V3's all-52-move prompt contract tests; V3 intentionally changes the prompt marker and payload schema."
)

from solo_harness.runtime.v051_conversation import (
    controlled_c11_judge_prompt,
    controlled_c11_tutor_prompt,
)
from solo_harness.studies.controlled_c1 import contract

MARKER_T = "[CONTROLLED_C11_CURRENT_TUTOR_CONTEXT_V2]\n"
MARKER_J = "[CONTROLLED_C11_CURRENT_JUDGE_CONTEXT_V2]\n"


def _instance(pedagogy):
    cases = contract()["fixed_cases"]["C1.1"]
    primary = {"answers": cases["primary_answers"], "bit_sequence": cases["primary_bits"],
               "position_labels": cases["positions"], "number_of_ones": cases["one_counts"]["110"]}
    contrast = {"answers": cases["contrast_answers"], "bit_sequence": cases["contrast_bits"],
                "position_labels": cases["positions"], "number_of_ones": cases["one_counts"]["100"]}
    return {"public": {"rule": cases["rule"], "cases": [primary, contrast] if pedagogy == "P3" else [primary]}}


def _move(pedagogy, number):
    return contract()["subsections"]["C1.1"]["moves_by_pedagogy"][pedagogy][number - 1]


def _tutor_payload(pedagogy, number, *, dialogue=None, response_mode="MOVE", pending_doubt=None):
    move = _move(pedagogy, number)
    prompt = controlled_c11_tutor_prompt(SimpleNamespace(), {}, dialogue or [], None,
                                         _instance(pedagogy), move, number - 1,
                                         response_mode=response_mode, pending_doubt=pending_doubt)
    return prompt, json.loads(prompt.split(MARKER_T, 1)[1].split("\n[OUTPUT_SCHEMA]", 1)[0])


def _judge_payload(pedagogy, number, *, dialogue=None, mode="MOVE_REVIEW", pending=None):
    prompt = controlled_c11_judge_prompt(SimpleNamespace(), {}, dialogue or [], _instance(pedagogy),
                                          _move(pedagogy, number), number - 1, False, {},
                                          review_mode=mode, pending_doubt=pending)
    return prompt, json.loads(prompt.split(MARKER_J, 1)[1].split("\n[OUTPUT_SCHEMA]", 1)[0])


@pytest.mark.parametrize("pedagogy,count", [("P1", 4), ("P2", 5), ("P3", 4)])
def test_all_13_tutor_prompts_are_unscripted_and_move_scoped(pedagogy, count):
    for number in range(1, count + 1):
        prompt, payload = _tutor_payload(pedagogy, number)
        active = payload["active_move"]
        assert "exact_delivery" not in active
        assert "completion_evidence" not in active
        assert "source_instructional_action" not in active
        assert "post_reply_teaching_requirements" not in active
        assert "already_taught_one_sentence_bridge" not in payload
        assert payload["position_vs_binary_value_reference_ONLY_if_learner_asks"] is None
        assert payload["prompt_revision"] == "C11_FLEXIBLE_DELIVERY_V2_2"
        assert "YOUR OWN simple, natural English" in prompt
        assert payload["pedagogy"] == pedagogy
        assert payload["active_move"]["id"] == _move(pedagogy, number)["id"]


@pytest.mark.parametrize("number", [2, 3, 4])
def test_p2_initial_guided_questions_do_not_expose_target_answers(number):
    _, payload = _tutor_payload("P2", number)
    move = _move("P2", number)
    assert payload["turn_is_first_guided_question"] is True
    assert payload["active_move"]["required_guided_question"] == move["delivery_controls"]["guided_question"]
    assert payload["verified_facts_for_this_turn"].keys() == {2: {"bits"}, 3: {"rule"}, 4: {"primary_mapping"}}[number]
    assert "Do not reveal the intended answer" in payload["active_move"]["avoid"]
    if number == 3:
        assert "110" not in json.dumps(payload)
    if number == 4:
        assert "primary_count" not in payload["verified_facts_for_this_turn"]


def test_post_approval_doubt_gets_narrow_correct_position_reference_and_same_move():
    move = _move("P1", 1)
    dialogue = [
        {"id": "t1", "role": "TUTOR", "content": "A bit can be 0 or 1.",
         "instructional_trace": {"pilot_move_id": move["id"]}},
        {"id": "l1", "role": "LEARNER", "content": "Why does a bit double if moved one place left?"},
    ]
    pending = {"learner_message_id": "l1", "text": dialogue[-1]["content"], "move_id": move["id"]}
    prompt, payload = _tutor_payload("P1", 1, dialogue=dialogue, response_mode="DOUBT", pending_doubt=pending)
    guard = payload["position_vs_binary_value_reference_ONLY_if_learner_asks"]
    assert guard is not None
    assert "numerical place weight" in guard["answer_order"]
    assert "double" in guard["binary_numeral_only"]
    assert payload["review_scope"] == "DOUBT"
    assert payload["active_move"]["id"] == move["id"]
    assert "primary_mapping" not in payload["verified_facts_for_this_turn"]
    assert "address what THEY actually wrote" in prompt
    jprompt, jpayload = _judge_payload("P1", 1, dialogue=dialogue, mode="DOUBT_REVIEW", pending=pending)
    assert jpayload["position_vs_binary_value_reference_ONLY_if_learner_asks"]
    assert jpayload["review_mode"] == "DOUBT_REVIEW"
    assert "DIRECTLY answered it" in jprompt


def test_guided_question_interrupted_by_doubt_stays_in_move_and_is_visible_to_judge():
    move = _move("P2", 2)
    dialogue = [
        {"id": "t1", "role": "TUTOR", "content": "Which has several bits: 1 or 110?",
         "instructional_trace": {"pilot_move_id": move["id"]}},
        {"id": "l1", "role": "LEARNER", "content": "What does the order of bit positions mean?"},
    ]
    prompt, payload = _tutor_payload("P2", 2, dialogue=dialogue)
    assert payload["turn_is_first_guided_question"] is False
    assert payload["position_vs_binary_value_reference_ONLY_if_learner_asks"]
    assert payload["active_move"]["required_guided_question"] == "Which has several bits: 1 or 110?"
    assert len(payload["current_move_dialogue_only"]) == 2
    assert "same targeted question" in prompt.lower() or "SAME targeted question" in prompt
    _, jpayload = _judge_payload("P2", 2, dialogue=dialogue)
    assert jpayload["required_guided_question_if_any"] == "Which has several bits: 1 or 110?"
    assert len(jpayload["current_move_dialogue_only"]) == 2
    assert jpayload["position_vs_binary_value_reference_ONLY_if_learner_asks"]
    assert "exact_delivery" in jpayload["active_move"]


def test_unrelated_guided_reply_does_not_receive_binary_number_guard():
    move = _move("P2", 2)
    dialogue = [
        {"id": "t1", "role": "TUTOR", "content": "Which has several bits: 1 or 110?",
         "instructional_trace": {"pilot_move_id": move["id"]}},
        {"id": "l1", "role": "LEARNER", "content": "Example B"},
    ]
    _, payload = _tutor_payload("P2", 2, dialogue=dialogue)
    assert payload["position_vs_binary_value_reference_ONLY_if_learner_asks"] is None
    assert payload["visible_example_labels_if_relevant"] == {"Example A": "1", "Example B": "110"}


def test_v22_is_only_the_controlled_prompt_path():
    _, payload = _tutor_payload("P3", 2)
    assert "contrast_count" not in payload["verified_facts_for_this_turn"]
    assert "contrast_mapping" in payload["verified_facts_for_this_turn"]
    assert payload["previously_covered_topic_for_context_only"] == "single bit versus ordered sequence"
