"""C1 prompt-layer checks: all 52 source moves, no provider/database required."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from solo_harness.runtime.v051_conversation import (
    controlled_c1_tutor_prompt,
    controlled_c1_judge_prompt,
    controlled_c11_tutor_prompt,
    controlled_c11_judge_prompt,
)
from solo_harness.runtime.controlled_c1_prompt_context import (
    C1PromptContractError, execution_overlay, execution_overlay_hash,
    canonical_move, delivery_spec, science_library, selected_facts, validate_move,
)
from solo_harness.studies.controlled_c1 import contract

TUTOR_MARKER = "[CONTROLLED_C1_CURRENT_TUTOR_CONTEXT_V3]\n"
JUDGE_MARKER = "[CONTROLLED_C1_CURRENT_JUDGE_CONTEXT_V3]\n"


def _moves():
    for sub, block in contract()["subsections"].items():
        for pedagogy, moves in block["moves_by_pedagogy"].items():
            for index, move in enumerate(moves):
                yield sub, pedagogy, index, move


ALL_MOVES = list(_moves())
GUIDED_MOVES = [entry for entry in ALL_MOVES if entry[3]["learner_response_policy"] == "guided"]


def _context(prompt, marker):
    return json.loads(prompt.split(marker, 1)[1].split("\n[OUTPUT_SCHEMA]", 1)[0])


def _tutor(move, index, dialogue=None, **kwargs):
    prompt = controlled_c1_tutor_prompt(SimpleNamespace(), {}, dialogue or [], None, None, move, index, **kwargs)
    return prompt, _context(prompt, TUTOR_MARKER)


def _judge(move, index, dialogue=None, **kwargs):
    prompt = controlled_c1_judge_prompt(SimpleNamespace(), {}, dialogue or [], None, move,
                                        index, index == 3 if move["id"].split("-")[1] != "P2" else index == 4,
                                        {}, **kwargs)
    return prompt, _context(prompt, JUDGE_MARKER)


def _exchange(move, learner_text):
    return [
        {"id": "t01", "role": "TUTOR", "content": "One clear teaching explanation.",
         "instructional_trace": {"pilot_move_id": move["id"]}},
        {"id": "l01", "role": "LEARNER", "content": learner_text},
    ]


def test_all_52_source_moves_present_and_39_separate_overlay_entries():
    assert len(ALL_MOVES) == 52
    assert len({m["id"] for _, _, _, m in ALL_MOVES}) == 52
    assert len(execution_overlay()["moves"]) == 39
    assert len(execution_overlay_hash()) == 64
    assert [sum(m["learner_response_policy"] == "guided" for m in contract()["subsections"][s]["moves_by_pedagogy"]["P2"])
            for s in ("C1.1", "C1.2", "C1.3", "C1.4")] == [3, 2, 3, 3]


@pytest.mark.parametrize("sub,pedagogy,index,move", ALL_MOVES,
                         ids=[m["id"] for *_, m in ALL_MOVES])
def test_all_52_tutor_and_judge_prompts_are_buildable_and_scoped(sub, pedagogy, index, move):
    ttext, t = _tutor(move, index)
    jtext, j = _judge(move, index)
    assert t["subsection"] == j["subsection"] == sub
    assert t["pedagogy"] == j["pedagogy"] == pedagogy
    assert t["active_move"]["id"] == j["active_move"]["id"] == move["id"]
    assert t["source_contract_sha256"] == j["source_contract_sha256"]
    assert t["delivery_overlay_sha256"] == j["delivery_overlay_sha256"]
    assert t["first_move_of_subsection"] == j["first_move_of_subsection"] == (index == 0)
    assert t["verified_facts_for_this_turn"]
    assert j["verified_facts_FOR_REVIEW_NOT_PROOF_OF_DELIVERY"]
    assert "exact_delivery" not in ttext
    assert "exact_delivery" not in jtext
    assert "source_instructional_action" not in ttext
    assert "locked_knowledge" not in ttext
    assert "complete_subsection_plan" not in ttext
    assert "never advance" in ttext.lower() or "tutor_never_advances_moves" in ttext
    assert "Do not infer" in jtext
    assert len(ttext) < 14000
    assert len(jtext) < 14000


@pytest.mark.parametrize("sub,pedagogy,index,move", GUIDED_MOVES,
                         ids=[m["id"] for *_, m in GUIDED_MOVES])
def test_every_guided_question_has_a_separate_initial_nonanswer_facts(sub, pedagogy, index, move):
    _, t = _tutor(move, index)
    spec = delivery_spec(move)
    assert t["first_guided_question_turn"] is True
    assert t["active_move"]["guided_question"] == spec["guided_question"]
    assert t["verified_facts_for_this_turn"] == selected_facts(move, first_guided_turn=True)
    assert len(t["verified_facts_for_this_turn"]) < len(selected_facts(move))
    assert "Do not reveal the answer" in t["active_move"]["scope_avoidances"]
    _, j = _judge(move, index)
    assert j["active_move"]["required_guided_question"] == spec["guided_question"]


def test_specific_guided_answer_hiding_boundaries():
    def full(sub, ped, idx):
        move = contract()["subsections"][sub]["moves_by_pedagogy"][ped][idx]
        return _tutor(move, idx)[0]
    assert "position 3" not in full("C1.2", "P2", 1)
    assert "101101" not in full("C1.4", "P2", 1)
    assert "101100" not in full("C1.4", "P2", 2)
    assert "FAIL" not in full("C1.4", "P2", 3)
    assert "data-dependent" not in full("C1.3", "P2", 2)
    assert "Yes, No, No" not in full("C1.1", "P3", 0)
    assert "100" not in full("C1.1", "P3", 0)


def test_science_is_locked_to_verified_examples_and_checks():
    s1, s2, s3, s4 = (science_library(s) for s in ("C1.1", "C1.2", "C1.3", "C1.4"))
    assert "position 2" in s1["changed_position"]
    assert "not a measure of numerical magnitude" in s1["count_purpose"]
    assert "position 3" in s2["changed_position"]
    assert "1 → 0" in s2["changed_position"]
    assert "not a literal transmitted letter" in s3["symbolic_p"]
    assert "not" in s3["symbolic_p"]
    assert "101101" in s4["even_sender"] and "101100" in s4["odd_sender"]
    assert "PASS" in s4["even_receive_pass"] and "FAIL" in s4["even_receive_fail"]
    assert "NOT prove" in s4["pass_meaning"]


def test_c11_p3_first_move_has_first_subsection_opening_and_rule_check():
    move = canonical_move("C1.1-P3-M01")
    prompt, payload = _tutor(move, 0)
    assert payload["first_move_of_subsection"]
    assert "Yes=1" in json.dumps(payload["verified_facts_for_this_turn"])
    assert "On the FIRST move of EACH subsection" in prompt
    _, judge = _judge(move, 0)
    assert any("Yes=1" in item for item in judge["active_move"]["critical_checks_must_be_visible_not_assumed"])


def test_why_count_doubt_is_explicitly_reviewable_even_inside_p2_guided_move():
    move = canonical_move("C1.1-P2-M04")
    dialogue = _exchange(move, "why count them")
    tutor, data = _tutor(move, 3, dialogue=dialogue)
    assert "count_purpose" in data["small_related_science_guard_ONLY_for_expressed_question"]
    assert data["first_guided_question_turn"] is False
    judge, jdata = _judge(move, 3, dialogue=dialogue)
    assert jdata["expressed_learner_questions_to_evaluate"][0]["text"] == "why count them"
    assert "For WHY questions" in judge  # V3.1 generic why-question safeguard
    assert "a later correct" in judge


def test_c11_numeric_value_misinterpretation_is_prohibited_in_tutor_and_judge():
    move = canonical_move("C1.1-P3-M03")
    tutor, _ = _tutor(move, 2)
    judge, data = _judge(move, 2)
    assert "numerical total value" in tutor
    assert "total numerical values" in judge
    assert any("numeric" in item or "numerical" in item for item in data["active_move"]["critical_checks_must_be_visible_not_assumed"])


def test_interrupted_guided_question_remains_visible_and_doubt_is_a_separate_obligation():
    move = canonical_move("C1.2-P2-M03")
    dialogue = [
        {"id": "t01", "role": "TUTOR", "content": "We can see both sequences. Which one would the receiver normally have?",
         "instructional_trace": {"pilot_move_id": move["id"]}},
        {"id": "l01", "role": "LEARNER", "content": "Why can't it see the sent bits?"},
    ]
    tutor, data = _tutor(move, 2, dialogue=dialogue)
    judge, jdata = _judge(move, 2, dialogue=dialogue)
    assert data["first_guided_question_turn"] is False
    assert data["current_move_dialogue_only"][0]["content"].endswith("normally have?")
    assert "SAME pending" in tutor
    assert jdata["expressed_learner_questions_to_evaluate"][0]["text"].startswith("Why")
    assert "later correct" in judge


def test_post_approval_doubt_keeps_move_and_requires_its_own_review():
    move = canonical_move("C1.1-P1-M01")
    dialogue = _exchange(move, "Why would moving a binary one left double its value?")
    pending = {"move_id": move["id"], "learner_message_id": "l01", "text": dialogue[-1]["content"]}
    t, tp = _tutor(move, 0, dialogue=dialogue, response_mode="DOUBT", pending_doubt=pending)
    j, jp = _judge(move, 0, dialogue=dialogue, review_mode="DOUBT_REVIEW", pending_doubt=pending)
    assert tp["response_mode"] == "DOUBT"
    assert tp["pending_post_approval_doubt"] == pending
    assert tp["small_related_science_guard_ONLY_for_expressed_question"] is not None
    assert jp["review_mode"] == "DOUBT_REVIEW"
    assert jp["pending_post_approval_doubt"] == pending
    assert "ALREADY approved" in j
    with pytest.raises(ValueError):
        _tutor(move, 0, response_mode="DOUBT")
    with pytest.raises(ValueError):
        _judge(move, 0, review_mode="DOUBT_REVIEW")


def test_conditional_c12_move_m04_does_not_require_new_reply_or_quiz():
    move = canonical_move("C1.2-P2-M04")
    _, data = _tutor(move, 3)
    assert data["active_move"]["response_policy"] == "conditional"
    assert data["active_move"]["guided_question"] is None
    assert "earlier claimed" in data["active_move"]["teaching_goal"]


def test_c13_parity_p_placeholder_remains_symbolic_and_c14_parity_is_complete_frame():
    move = canonical_move("C1.3-P1-M02")
    _, payload = _tutor(move, 1)
    assert "symbolic_p" in payload["verified_facts_for_this_turn"]
    assert "not a literal" in payload["verified_facts_for_this_turn"]["symbolic_p"]
    move = canonical_move("C1.4-P1-M03")
    _, payload = _tutor(move, 2)
    assert "INCLUDING parity bit" in payload["verified_facts_for_this_turn"]["even_rule"]
    assert "101101" in payload["verified_facts_for_this_turn"]["even_receive_pass"]


def test_reject_wrong_move_indices_and_tampered_contracts():
    move = canonical_move("C1.2-P1-M02")
    with pytest.raises(C1PromptContractError):
        validate_move(move, 0)
    tampered = dict(move, learner_response_policy="guided")
    with pytest.raises(C1PromptContractError):
        _tutor(tampered, 1)


def test_c11_compatibility_entrypoints_preserve_signature_and_scope():
    move = canonical_move("C1.1-P1-M01")
    assert _context(controlled_c11_tutor_prompt(None, {}, [], None, None, move, 0), TUTOR_MARKER)["subsection"] == "C1.1"
    assert _context(controlled_c11_judge_prompt(None, {}, [], None, move, 0, False, {}), JUDGE_MARKER)["subsection"] == "C1.1"
    with pytest.raises(ValueError):
        controlled_c11_tutor_prompt(None, {}, [], None, None, canonical_move("C1.2-P1-M01"), 0)


def test_c12_conditional_move_receives_only_earlier_guided_exchange_when_available():
    move = canonical_move("C1.2-P2-M04")
    dialogue = [
        {"id": "t1", "role": "TUTOR", "content": "Which sequence does receiver know?",
         "instructional_trace": {"pilot_move_id": "C1.2-P2-M03"}},
        {"id": "l1", "role": "LEARNER", "content": "It must know the clean original too."},
        {"id": "t2", "role": "TUTOR", "content": "The receiver normally sees only the received bits.",
         "instructional_trace": {"pilot_move_id": "C1.2-P2-M03"}},
    ]
    _, t = _tutor(move, 3, dialogue=dialogue)
    _, j = _judge(move, 3, dialogue=dialogue)
    assert t["prior_exchange_ONLY_for_conditional_misconception_check"][1]["content"].startswith("It must")
    assert j["prior_exchange_ONLY_for_conditional_misconception_check"] == t["prior_exchange_ONLY_for_conditional_misconception_check"]
    assert not t["current_move_dialogue_only"]
    assert not t["first_guided_question_turn"]
