"""Offline V3.2 invariants; these tests do NOT simulate Tutor/Judge correctness."""
from __future__ import annotations

import json
import pytest

from solo_harness.runtime.v051_conversation import (
    ConversationJudgeOutput, V051TutorOutput, controlled_c1_tutor_prompt, controlled_c1_judge_prompt,
)
from solo_harness.studies.controlled_c1 import contract


def all_moves():
    for sub, block in contract()["subsections"].items():
        for ped, moves in block["moves_by_pedagogy"].items():
            for index, move in enumerate(moves):
                yield sub, ped, index, move


def payload(prompt: str, marker: str):
    return json.loads(prompt.split(marker + "\n", 1)[1].split("\n[OUTPUT_SCHEMA]", 1)[0])


ALL = list(all_moves())


@pytest.mark.parametrize("sub,ped,index,move", ALL, ids=[item[3]["id"] for item in ALL])
def test_v32_all_moves_keep_same_simple_schema_and_context(sub, ped, index, move):
    t = controlled_c1_tutor_prompt(None, {}, [], None, None, move, index)
    j = controlled_c1_judge_prompt(None, {}, [], None, move, index, False, {})
    tdata = payload(t, "[CONTROLLED_C1_CURRENT_TUTOR_CONTEXT_V3]")
    jdata = payload(j, "[CONTROLLED_C1_CURRENT_JUDGE_CONTEXT_V3]")
    assert tdata["prompt_revision"] == jdata["prompt_revision"] == "C1_MOVE_SCOPED_FLEXIBLE_V3_2"
    assert tdata["active_move"]["id"] == jdata["active_move"]["id"] == move["id"]
    assert "locked_knowledge" not in tdata and "exact_delivery" not in tdata
    assert "critical_checks_must_be_visible_not_assumed" in jdata["active_move"]
    assert "EVERY mandatory critical check" in j
    assert "after a wrong attempt" in j and "do NOT" in j
    assert len(t) < 14000 and len(j) < 14000


@pytest.mark.parametrize("sub,ped,index,move", [entry for entry in ALL if entry[0] == "C1.3"],
                         ids=[entry[3]["id"] for entry in ALL if entry[0] == "C1.3"])
def test_v32_c13_nonimplication_available_to_tutor_and_judge(sub, ped, index, move):
    t = payload(controlled_c1_tutor_prompt(None, {}, [], None, None, move, index),
                "[CONTROLLED_C1_CURRENT_TUTOR_CONTEXT_V3]")
    j = payload(controlled_c1_judge_prompt(None, {}, [], None, move, index, False, {}),
                "[CONTROLLED_C1_CURRENT_JUDGE_CONTEXT_V3]")
    guard = "Do not claim checking information detects every possible data change; it can help reveal corruption but is no guarantee."
    assert guard in t["science_scope_guards"]
    assert guard in j["scientific_nonimplications"]
    assert "even_rule" not in t["verified_facts_for_this_turn"]


@pytest.mark.parametrize("sub", ["C1.1", "C1.2", "C1.4"])
def test_v32_c13_guard_is_not_leaked_to_other_subsections(sub):
    move = contract()["subsections"][sub]["moves_by_pedagogy"]["P1"][0]
    t = payload(controlled_c1_tutor_prompt(None, {}, [], None, None, move, 0),
                "[CONTROLLED_C1_CURRENT_TUTOR_CONTEXT_V3]")
    assert not any("every possible data change" in rule for rule in t["science_scope_guards"])


def test_v32_no_new_judge_ids_or_mastery_gate():
    assert set(ConversationJudgeOutput.model_fields) == {"decision", "guidance"}
    assert set(V051TutorOutput.model_fields) == {"learner_message", "ready_for_judge"}
    move = contract()["subsections"]["C1.4"]["moves_by_pedagogy"]["P2"][1]
    j = controlled_c1_judge_prompt(None, {}, [], None, move, 1, False, {})
    assert "one genuine learner" in j
    assert "and the required move content" in j
    assert "do NOT" in j and "confirmation" in j
    assert "a second attempt" in j and "request THAT repair" in j
    assert "A learner QUESTION interrupting" in j
