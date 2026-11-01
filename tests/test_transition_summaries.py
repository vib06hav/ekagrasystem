"""Pure content, exact page and gate checks; no provider or PostgreSQL required."""
from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from solo_harness.transition_summaries import (
    TRANSITION_SUMMARY_VERSION, get_transition_summary, post_pass_transition_summary,
)

TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "solo_harness" / "templates"


def _view(transition_id: str, outcome="PASSED", include_summary=True):
    section_no = int(transition_id[1])
    return {
        "phase": "SECTION_COMPLETE", "is_current": True, "status": "ACTIVE",
        "section_number": section_no, "section_count": 4,
        "sections": [
            {"number": index, "state": "completed" if index <= section_no else "locked", "enabled": index <= section_no}
            for index in range(1, 5)
        ],
        "is_final_section": section_no == 4, "timeline": [], "pending": False,
        "retryable": False, "technical_hold": False, "section_scientific_outcome": outcome,
        "transition_summary": get_transition_summary(transition_id) if include_summary else None,
        "started_at": None, "ended_at": None,
    }


def _render(view):
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))
    env.filters["tutor_markdown"] = lambda value: value
    return env.get_template("partials/session_main.html").render(view=view)


@pytest.mark.parametrize("transition_id", ["C1", "C2", "C3", "C4"])
def test_post_pass_screen_renders_authored_copy(transition_id):
    view = _view(transition_id)
    html = _render(view)
    assert f'data-transition-summary="{transition_id}"' in html
    assert TRANSITION_SUMMARY_VERSION in html
    assert get_transition_summary(transition_id)["title"] in html
    assert "01 / KEY IDEAS" in html
    assert "02 / CHECKED EXAMPLE" in html
    assert "<table" in html
    assert 'class="conversation"' not in html
    assert ("/session/actions/finish" if transition_id == "C4" else "/session/actions/next") in html
    assert ("Finish study" if transition_id == "C4" else "Continue to section") in html


@pytest.mark.parametrize("outcome,phase,is_current,f1_v04", [
    ("UNRESOLVED", "SECTION_COMPLETE", True, True),
    ("PASSED", "JUDGING", True, True),
    ("PASSED", "ASSESSMENT_ACTIVE", True, True),
    (None, "INTERVENTION_ACTIVE", True, True),
    ("PASSED", "SECTION_COMPLETE", False, True),
    ("PASSED", "SECTION_COMPLETE", True, False),
])
def test_summary_gate_denies_nonpassing_or_other_context(outcome,phase,is_current,f1_v04):
    assert post_pass_transition_summary(f1_v04=f1_v04,is_current=is_current,phase=phase,outcome=outcome,transition_id="C1") is None


def test_gating_passed_and_unresolved_ui_are_distinct():
    assert post_pass_transition_summary(f1_v04=True,is_current=True,phase="SECTION_COMPLETE",outcome="PASSED",transition_id="C2")
    html = _render(_view("C2", outcome="UNRESOLVED", include_summary=False))
    assert "transition unresolved" in html
    assert 'data-transition-summary="C2"' not in html
    assert "/session/actions/next" in html


def test_authored_copy_is_scoped_not_pedagogy_specific():
    for transition_id in ("C1","C2","C3","C4"):
        recap = get_transition_summary(transition_id)
        assert recap is not None and recap["version"] == TRANSITION_SUMMARY_VERSION
        assert len(recap["points"]) == 3
        assert not any("you mastered" in item["text"].lower() for item in recap["points"])
        assert recap["science_refs"]
        assert "pedagogy" not in recap
    copy = get_transition_summary("C1")
    copy["points"][0]["text"] = "MODIFIED"
    assert get_transition_summary("C1")["points"][0]["text"] != "MODIFIED"


def test_c1_example_even_parity_and_single_flip():
    items = get_transition_summary("C1")["frame_rows"]
    data,check,clean,corrupted=(row["value"] for row in items)
    assert clean == data+check
    assert clean.count("1")%2 == 0
    assert len(clean) == len(corrupted)
    assert sum(a != b for a,b in zip(clean,corrupted)) == 1
    assert corrupted.count("1")%2 == 1


def test_c3_grid_syndrome_matches_documented_single_flip():
    recap = get_transition_summary("C3")
    rows = recap["grid_rows"]
    full = [[int(bit) for bit in row["values"]] for row in rows]
    assert len(full) == 4 and all(len(row) == 5 for row in full)
    assert [("Pass" if sum(row)%2 == 0 else "Fail") for row in full] == [r["status"] for r in rows]
    assert [("Pass" if sum(row[col] for row in full)%2 == 0 else "Fail") for col in range(5)] == list(recap["grid_column_results"])
    r,c=recap["grid_flip"]
    assert (r,c)==(1,2)
    full[r][c] ^= 1
    assert all(sum(row)%2==0 for row in full)
    assert all(sum(row[col] for row in full)%2==0 for col in range(5))


def test_c4_check_groups_and_new_group_examples():
    group1={1,2,4}; group2={2,3,5}; group3={1,3}
    undetected={1,4}; detected={1,2}
    assert len(undetected & group1)%2==0 and len(undetected & group2)%2==0
    assert len(detected & group1)%2==0 and len(detected & group2)%2==1
    assert len(undetected & group3)%2==1
    recap=get_transition_summary("C4")
    assert recap["patterns"][0]["outcome"] == "Undetected"
    assert recap["patterns"][1]["outcome"] == "Detected"


def test_all_summary_claim_references_exist_in_frozen_scientific_knowledge():
    """Keep references anchored in v0.4's authored scientific content."""
    import yaml
    f = Path(__file__).resolve().parents[1] / "studies" / "networks_error_detection_parity_f1" / "v0.4" / "08_SCIENTIFIC_YAML" / "knowledge.yaml"
    knowledge = yaml.safe_load(f.read_text(encoding="utf-8"))
    scientific_ids = {row["id"] for row in knowledge["components"] + knowledge["relations"]}
    for c in ("C1", "C2", "C3", "C4"):
        assert set(get_transition_summary(c)["science_refs"]) <= scientific_ids
