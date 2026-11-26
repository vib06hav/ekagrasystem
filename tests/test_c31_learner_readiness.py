"""C3.1 learner-readiness integration: authored words, scoped prompts and grids."""
from __future__ import annotations

import json
import re
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from solo_harness.runtime.controlled_executor import contract, instance, visual_descriptor
from solo_harness.runtime.controlled_unified_prompts import judge_prompt, tutor_prompt


def _moves():
    return [move for pedagogy in ("P1", "P2", "P3")
            for move in contract("C3")["subsections"]["C3.1"]["moves_by_pedagogy"][pedagogy]]


def _template():
    return Environment(loader=FileSystemLoader("src/solo_harness/templates"),
                       undefined=StrictUndefined).get_template(
                           "partials/session/controlled_c11_visual.html")


def _context(prompt, marker):
    return json.loads(prompt.split(marker, 1)[1].split("\n[OUTPUT_SCHEMA]", 1)[0])


def test_all_fifteen_c31_moves_use_natural_coordinate_language_only():
    moves = _moves()
    assert len(moves) == 15
    compact = re.compile(r"\b(?:R[1-3]C[1-4]|R[1-3]|C[1-4])\b")
    for move in moves:
        for field in ("source_instructional_action", "exact_delivery", "completion_evidence"):
            assert not compact.search(move[field]), (move["id"], field)
    assert "highlighted bit?" in next(m for m in moves if m["id"] == "C3.1-P2-M01")["exact_delivery"]


def test_c31_prompt_addenda_are_scoped_and_keep_delivery_reference_out_of_payloads():
    move = contract("C3")["subsections"]["C3.1"]["moves_by_pedagogy"]["P2"][0]
    tutor = tutor_prompt(None, {}, [], None, None, move, 0)
    judge = judge_prompt(None, {}, [], None, move, 0, False, {})
    tutor_context = _context(tutor, "[ACTIVE_MOVE_CONTEXT]\n")
    assert tutor_context["active_move"]["guided_question"] == (
        "Which row and column checks contain the highlighted bit?")
    assert tutor_context["first_guided_question_turn"] is True
    assert "exact_delivery" not in tutor and "exact_delivery" not in judge
    assert "row 1, column 1" in tutor
    assert "smallest complete explanation" in tutor
    assert "40–80 spoken words" in tutor
    assert "column 1 fails" in judge

    c32 = contract("C3")["subsections"]["C3.2"]["moves_by_pedagogy"]["P1"][0]
    assert "LEARNER-FACING DELIVERY QUALITY" not in tutor_prompt(None, {}, [], None, None, c32, 0)
    assert "INDEPENDENT INSTRUCTIONAL REVIEW" not in judge_prompt(None, {}, [], None, c32, 0, False, {})


def test_every_c31_prompt_is_buildable_scoped_and_guards_case_d_against_false_failure():
    for index, move in enumerate(_moves()):
        tutor = tutor_prompt(None, {}, [], None, None, move, index % 5)
        judge = judge_prompt(None, {}, [], None, move, index % 5, False, {})
        assert '"exact_delivery"' not in tutor
        assert '"exact_delivery"' not in judge
        assert _context(tutor, "[ACTIVE_MOVE_CONTEXT]\n")["active_move"]["id"] == move["id"]
        assert _context(judge, "[CURRENT_MOVE_JUDGE_CONTEXT]\n")["active_move"]["id"] == move["id"]

    case_d = contract("C3")["subsections"]["C3.1"]["moves_by_pedagogy"]["P2"][3]
    dialogue = [{"role": "TUTOR", "content": "Column 1 fails after the two changes.",
                 "instructional_trace": {"pilot_move_id": case_d["id"]}}]
    adversarial_review = judge_prompt(None, {}, dialogue, None, case_d, 3, False, {})
    assert "Column 1 fails after the two changes." in adversarial_review
    assert "such as \"column 1 fails\" in the same-column two-change example" in adversarial_review


def test_c31_prompt_stage_withholds_answers_and_complete_stage_reports_case_d_correctly():
    template = _template()
    guided = contract("C3")["subsections"]["C3.1"]["moves_by_pedagogy"]["P2"]
    for move in guided[:4]:
        prompt = template.render(item={"visual": visual_descriptor(
            move, instance("C3.1", "P2"), "prompt")})
        assert "R1C1" not in prompt and "C1 fails" not in prompt
        assert "FAIL" not in prompt and "PASS" not in prompt

    membership_prompt = template.render(item={"visual": visual_descriptor(
        guided[0], instance("C3.1", "P2"), "prompt")})
    assert 'aria-label="Highlighted data cell, value 0"' in membership_prompt
    assert 'aria-label="Row 1, column 2, data cell' not in membership_prompt

    case_d = template.render(item={"visual": visual_descriptor(
        guided[3], instance("C3.1", "P2"), "complete")})
    assert case_d.count('class="c31-cell') == 24
    assert "Column 1: <strong class=\"result-pass\">PASS" in case_d
    assert "Row 1: <strong class=\"result-fail\">FAIL" in case_d
    assert "Row 2: <strong class=\"result-fail\">FAIL" in case_d
    assert case_d.count("All other checks pass.") == 2


def test_c31_complete_grid_uses_all_twelve_coloured_cells_and_natural_accessible_labels():
    move = contract("C3")["subsections"]["C3.1"]["moves_by_pedagogy"]["P1"][1]
    html = _template().render(item={"visual": visual_descriptor(
        move, instance("C3.1", "P1"), "complete")})
    assert html.count('class="c31-cell') == 24
    assert all(token in html for token in ("c31-data", "c31-row-check", "c31-column-check", "c31-corner-check"))
    assert 'aria-label="Row 1, column 2, data cell, value 1, outlined as a change used in this example"' in html
    assert "R1C2" not in html


def test_c31_result_density_keeps_m01_complete_and_other_panels_causal():
    template = _template()
    p1 = contract("C3")["subsections"]["C3.1"]["moves_by_pedagogy"]["P1"]
    m01 = template.render(item={"visual": visual_descriptor(
        p1[0], instance("C3.1", "P1"), "complete")})
    assert m01.count('class="result-pass"') == 7
    assert "All other checks pass." not in m01

    same_row = template.render(item={"visual": visual_descriptor(
        p1[2], instance("C3.1", "P1"), "complete")})
    assert "Row 1: <strong class=\"result-pass\">PASS" in same_row
    assert "Column 1: <strong class=\"result-fail\">FAIL" in same_row
    assert "Column 2: <strong class=\"result-fail\">FAIL" in same_row
    assert same_row.count("All other checks pass.") == 1

    p3 = contract("C3")["subsections"]["C3.1"]["moves_by_pedagogy"]["P3"]
    comparison = template.render(item={"visual": visual_descriptor(
        p3[2], instance("C3.1", "P3"), "complete")})
    assert comparison.count('class="c31-results"') == 2
    assert comparison.count("All other checks pass.") == 2


def test_c31_p2_prediction_visuals_hide_answers_then_reveal_once_without_empty_figures():
    p2 = contract("C3")["subsections"]["C3.1"]["moves_by_pedagogy"]["P2"]
    question = _template().render(item={"visual": visual_descriptor(
        p2[1], instance("C3.1", "P2"), "prompt")})
    complete = _template().render(item={"visual": visual_descriptor(
        p2[1], instance("C3.1", "P2"), "complete")})
    assert "One bit changes — what fails?" in question
    assert question.count('class="c31-grid-panel"') == 1
    assert "result-fail" not in question
    assert complete.count('class="c31-grid-panel"') == 2
    assert "One data bit changes" in complete and "The corner checking bit changes" in complete
