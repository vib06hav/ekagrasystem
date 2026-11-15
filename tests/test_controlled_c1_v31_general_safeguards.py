"""V3.1: generic model safeguards without schema or context expansion."""  # CHANGED
from __future__ import annotations  # CHANGED

import json  # CHANGED

import pytest  # CHANGED

from solo_harness.runtime.v051_conversation import (  # CHANGED
    ConversationJudgeOutput, V051TutorOutput,  # CHANGED
    controlled_c1_tutor_prompt, controlled_c1_judge_prompt,  # CHANGED
)  # CHANGED
from solo_harness.studies.controlled_c1 import contract  # CHANGED


def _all_moves():  # CHANGED
    for block in contract()["subsections"].values():  # CHANGED
        for moves in block["moves_by_pedagogy"].values():  # CHANGED
            for i, move in enumerate(moves):  # CHANGED
                yield i, move  # CHANGED


@pytest.mark.parametrize("index,move", list(_all_moves()), ids=lambda x: x["id"] if isinstance(x, dict) else str(x))  # CHANGED
def test_generic_safeguards_apply_to_every_move(index, move):  # CHANGED
    tutor = controlled_c1_tutor_prompt(None, {}, [], None, None, move, index)  # CHANGED
    judge = controlled_c1_judge_prompt(None, {}, [], None, move, index, False, {})  # CHANGED
    assert "Before agreeing with a learner's claim" in tutor  # CHANGED
    assert "do not invent values, causal explanations, or guarantees" in tutor  # CHANGED
    assert "If they ask WHY" in tutor  # CHANGED
    assert "against learner-visible teaching" in judge  # CHANGED
    assert "contradictory acknowledgments" in judge  # CHANGED
    assert "A required contrast needs" in judge  # CHANGED
    for prompt, marker in ((tutor, "[CONTROLLED_C1_CURRENT_TUTOR_CONTEXT_V3]"),  # CHANGED
                           (judge, "[CONTROLLED_C1_CURRENT_JUDGE_CONTEXT_V3]")):  # CHANGED
        payload = json.loads(prompt.split(marker + "\n", 1)[1].split("\n[OUTPUT_SCHEMA]", 1)[0])  # CHANGED
        assert payload["prompt_revision"] == "C1_MOVE_SCOPED_FLEXIBLE_V3_2"  # CHANGED
        assert payload["active_move"]["id"] == move["id"]  # CHANGED
        assert "locked_knowledge" not in payload  # CHANGED
        assert "exact_delivery" not in payload  # CHANGED


def test_wire_schemas_remain_the_same_and_no_new_ids_required():  # CHANGED
    assert set(ConversationJudgeOutput.model_fields) == {"decision", "guidance"}  # CHANGED
    assert set(V051TutorOutput.model_fields) == {"learner_message", "ready_for_judge"}  # CHANGED
    decision_field = ConversationJudgeOutput.model_json_schema()["properties"]["decision"]  # CHANGED
    assert set(decision_field["enum"]) == {"ADVANCE", "CONTINUE", "HOLD"}  # CHANGED


def test_judge_why_question_is_general_not_hard_coded():  # CHANGED
    move = contract()["subsections"]["C1.3"]["moves_by_pedagogy"]["P2"][0]  # CHANGED
    judge = controlled_c1_judge_prompt(None, {}, [], None, move, 0, False, {})  # CHANGED
    rules = judge.split("[CONTROLLED_C1_CURRENT_JUDGE_CONTEXT_V3]", 1)[0]  # CHANGED
    assert "For WHY questions" in rules  # CHANGED
    assert "For a learner question like 'why count them?'" not in rules  # CHANGED
    assert "Return ONLY the schema's decision" in rules  # CHANGED
