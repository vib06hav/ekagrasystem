"""C3.2 evidence-first contract, prompts and receiver/instructor visual boundaries."""
from __future__ import annotations

import json
import re

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from solo_harness.runtime.controlled_executor import contract, instance, visual_descriptor
from solo_harness.runtime.controlled_unified_prompts import judge_prompt, tutor_prompt


def _template():
    return Environment(loader=FileSystemLoader("src/solo_harness/templates"),
                       undefined=StrictUndefined).get_template(
                           "partials/session/controlled_c11_visual.html")


def _context(prompt, marker):
    return json.loads(prompt.split(marker, 1)[1].split("\n[OUTPUT_SCHEMA]", 1)[0])


def _move(pedagogy, index):
    return contract("C3")["subsections"]["C3.2"]["moves_by_pedagogy"][pedagogy][index]


def test_c32_prompts_are_subsection_scoped_and_keep_design_references_private():
    move = _move("P2", 2)
    tutor = tutor_prompt(None, {}, [], None, None, move, 2)
    judge = judge_prompt(None, {}, [], None, move, 2, False, {})
    assert "learner-readiness and evidence-first teaching" in tutor
    assert "TARGET MAXIMUMS" in tutor
    assert "Conversation Judge supplement" in judge
    assert '"exact_delivery"' not in tutor and '"exact_delivery"' not in judge
    assert _context(tutor, "[ACTIVE_MOVE_CONTEXT]\n")["active_move"]["guided_question"] == (
        "Row 2 and column 1 fail in this received grid. Can those results prove how many bits changed?")

    c31 = contract("C3")["subsections"]["C3.1"]["moves_by_pedagogy"]["P1"][0]
    assert "evidence-first teaching" not in tutor_prompt(None, {}, [], None, None, c31, 0)


def test_c32_p2_prompts_show_given_observations_but_not_teacher_histories():
    template = _template()
    for index in range(5):
        move = _move("P2", index)
        html = template.render(item={"visual": visual_descriptor(
            move, instance("C3.2", "P2"), "prompt")})
        assert 'data-c32-parity-grid' in html
        assert "R1C1" not in html
        assert "instructor-constructed possible history" not in html
        assert "Valid original:" not in html
        assert "Different valid original:" not in html
        assert "is-changed" not in html

    two_bit = template.render(item={"visual": visual_descriptor(
        _move("P2", 1), instance("C3.2", "P2"), "prompt")})
    assert "Column 1: <strong class=\"result-fail\">FAIL" in two_bit
    assert "All other checks pass." in two_bit


def test_c32_one_vs_three_complete_view_keeps_both_distinct_valid_originals_and_same_observation():
    html = _template().render(item={"visual": visual_descriptor(
        _move("P3", 2), instance("C3.2", "P3"), "complete")})
    assert "Received grid — same in both examples" in html
    assert "Possible starting grid A — one change" in html
    assert "Possible starting grid B — three changes" in html
    assert html.count("All other checks pass.") == 1
    assert html.count("is-changed") == 4  # one highlighted change plus three highlighted changes


def test_c32_fixed_cases_preserve_same_received_grid_and_verified_outcomes():
    facts = contract("C3")["fixed_cases"]["C3.2"]
    one = facts["case_D_same_received_grid_one_flip_history"]
    three = facts["case_E_same_received_grid_three_flip_history"]
    rectangle = facts["case_F_four_corner_rectangle"]
    assert one["original_grid_for_instructor_explanation"] != three["original_grid_for_instructor_explanation"]
    assert one["received_grid"] == three["received_grid"] == ["0110", "0001", "1111"]
    assert one["failed_rows"] == three["failed_rows"] == ["R2"]
    assert one["failed_columns"] == three["failed_columns"] == ["C1"]
    assert rectangle["failed_rows"] == rectangle["failed_columns"] == []
    assert len(rectangle["flipped_positions"]) == 4
    compact = re.compile(r"\b(?:R[1-3]C[1-4]|R[1-3]|C[1-4])\b")
    for pedagogy in ("P1", "P2", "P3"):
        for move in contract("C3")["subsections"]["C3.2"]["moves_by_pedagogy"][pedagogy]:
            assert not compact.search(move["exact_delivery"]), move["id"]


def test_c32_reviewed_visual_copy_has_no_internal_labels_or_duplicate_completed_grids():
    two_bit = _template().render(item={"visual": visual_descriptor(
        _move("P2", 1), instance("C3.2", "P2"), "complete")})
    histories = _template().render(item={"visual": visual_descriptor(
        _move("P2", 2), instance("C3.2", "P2"), "complete")})
    prompt = _template().render(item={"visual": visual_descriptor(
        _move("P2", 1), instance("C3.2", "P2"), "prompt")})
    assert two_bit.count('class="c31-grid-panel c32-grid-panel"') == 2
    assert histories.count('class="c31-grid-panel c32-grid-panel"') == 3
    assert "shared row" not in prompt.lower()
    for html in (two_bit, histories, prompt):
        assert "instructor explanation" not in html.lower()
        assert "instructor-known" not in html.lower()
