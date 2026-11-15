from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader
from pydantic import SecretStr

from solo_harness.runtime.assessment_persistence import is_deliverable_f1, is_f1_study
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051
from solo_harness.web import _internal_v051_access_enabled, _operation_refresh_required, _v051_subsection_projection


ROOT = Path("studies/networks_error_detection_parity_f1/v0.5")


def _compiled():
    return compile_v051(load_scientific_v051(ROOT))


def _view(**overrides):
    view = {
        "phase": "INTERVENTION_ACTIVE", "status": "ACTIVE", "is_current": True,
        "sections": [{"enabled": True, "state": "current", "number": 1}],
        "section_number": 1, "section_count": 4,
        "section_title": "Fundamentals of Error Detection", "timeline": [],
        "started_at": None, "ended_at": None, "pending": False, "retryable": False,
        "technical_hold": False, "delivery_exception": False, "transition_summary": None,
        "attempt_status": "INTERVENTION_ACTIVE", "activity_number": 1,
        "is_final_section": False, "section_scientific_outcome": None,
        "paas_instrument": None, "assessment_prompt": None,
        "f1_public_assessment": None, "f1_assessment_submitted": False,
        "f1_assessment_unavailable": False, "active_subsection": None,
        "v051_subsections": [],
    }
    view.update(overrides)
    return view


def test_projection_uses_the_current_attempt_persisted_order_and_titles():
    rows = [
        SimpleNamespace(subsection_id="C2.2", order_in_attempt=2, status="ACTIVE"),
        SimpleNamespace(subsection_id="C2.1", order_in_attempt=1, status="COMPLETED"),
        SimpleNamespace(subsection_id="C2.3", order_in_attempt=3, status="PENDING"),
    ]
    projected = _v051_subsection_projection(_compiled(), SimpleNamespace(id="current"), rows)
    assert [(item["id"], item["state"]) for item in projected] == [
        ("C2.1", "COMPLETED"), ("C2.2", "ACTIVE"), ("C2.3", "PENDING"),
    ]
    assert projected[1]["title"] == "Introduction and Construction of Two-Dimensional Parity"


def test_subsection_titles_and_transcript_marker_are_visible_but_not_links():
    rows = _v051_subsection_projection(_compiled(), SimpleNamespace(id="current"), [
        SimpleNamespace(subsection_id="C2.1", order_in_attempt=1, status="COMPLETED"),
        SimpleNamespace(subsection_id="C2.2", order_in_attempt=2, status="ACTIVE"),
        SimpleNamespace(subsection_id="C2.3", order_in_attempt=3, status="PENDING"),
        SimpleNamespace(subsection_id="C2.4", order_in_attempt=4, status="PENDING"),
    ])
    view = _view(section_number=2, sections=[{"enabled": True, "state": "current", "number": 2}],
                 section_title="Capabilities and Limitations of Parity-Based Error Detection",
                 v051_subsections=rows, active_subsection=rows[1],
                 timeline=[{"kind": "subsection", "subsection_id": "C2.2", "title": "Two-Dimensional Parity Construction"}])
    html = Environment(loader=FileSystemLoader("src/solo_harness/templates")).get_template("partials/session_main.html").render(
        view=view, settings=SimpleNamespace(enable_f1_v04_development=False, enable_v051_internal_testing=False), new_key="key"
    )
    assert "Part 2 of 4 — Introduction and Construction of Two-Dimensional Parity" in html
    assert 'data-subsection-marker="C2.2"' in html
    assert rows[0]["title"] in html and rows[3]["title"] in html
    assert ">C2.1 ·" not in html and ">C2.4 ·" not in html and "C2.2 —" not in html
    assert '/session/sections/2' in html
    assert 'href="/session/subsections/' not in html


def test_pending_poll_refreshes_after_authoritative_subsection_change_only():
    assert not _operation_refresh_required(True, "C2.2", "C2.2")
    assert _operation_refresh_required(True, "C2.2", "C2.3")
    assert _operation_refresh_required(False, "C2.2", "C2.2")


def test_delivery_exception_is_not_rendered_as_a_live_composer():
    view = _view(delivery_exception=True, v051_subsections=[
        {"id": "C2.2", "title": "Two-Dimensional Parity Construction", "order": 2, "state": "DELIVERY_EXCEPTION"},
    ])
    html = Environment(loader=FileSystemLoader("src/solo_harness/templates")).get_template("partials/session_main.html").render(
        view=view, settings=SimpleNamespace(enable_f1_v04_development=False, enable_v051_internal_testing=False), new_key="key"
    )
    assert "data-delivery-exception" in html
    assert 'hx-post="/session/actions/tutor-message"' not in html


def test_candidate_assessment_delivery_requires_its_own_internal_flag():
    item = SimpleNamespace(frozen_public_snapshot={"mcqs": []}, frozen_private_snapshot={"mcqs": []})
    compiled = _compiled()
    assert is_f1_study(compiled)
    assert not is_deliverable_f1(item, SimpleNamespace(enable_f1_v04_development=True, enable_v051_internal_testing=False), candidate_only=True)
    assert is_deliverable_f1(item, SimpleNamespace(enable_f1_v04_development=False, enable_v051_internal_testing=True), candidate_only=True)


def test_internal_candidate_entry_is_disabled_without_both_settings():
    disabled = SimpleNamespace(enable_v051_internal_testing=False, v051_internal_testing_token=SecretStr("staff-secret"))
    enabled = SimpleNamespace(enable_v051_internal_testing=True, v051_internal_testing_token=SecretStr("staff-secret"))
    assert not _internal_v051_access_enabled(disabled, "staff-secret")
    assert not _internal_v051_access_enabled(enabled, None)
    assert not _internal_v051_access_enabled(enabled, "wrong")
    assert _internal_v051_access_enabled(enabled, "staff-secret")


def test_controlled_c11_visual_is_passive_and_comes_from_server_descriptor():
    visual = {
        "component": "mapping", "mode": "guided_mapping", "stage": "complete",
        "rule": {"Yes": "1", "No": "0"},
        "cases": [{"name": "primary", "answers": ["Yes", "Yes", "No"], "bit_sequence": "110", "number_of_ones": 2}],
    }
    environment = Environment(loader=FileSystemLoader("src/solo_harness/templates"))
    environment.filters["tutor_markdown"] = lambda value: value
    html = environment.get_template("partials/session_main.html").render(
        view=_view(timeline=[{"kind": "message", "role": "TUTOR", "content": "Fixed explanation.",
                              "sequence_no": 1, "timestamp": datetime.now(timezone.utc), "visual": visual}]),
        settings=SimpleNamespace(enable_f1_v04_development=False, enable_v051_internal_testing=False), new_key="key"
    )
    assert 'data-controlled-c11-visual="mapping"' in html
    assert "Yes = 1, No = 0" in html and "Ordered sequence: <code>110</code>" in html
    assert "<script" not in html


def test_controlled_c11_next_is_a_single_chat_flow_control_without_internal_label():
    environment = Environment(loader=FileSystemLoader("src/solo_harness/templates"))
    environment.filters["tutor_markdown"] = lambda value: value
    subsection = {"id": "C1.1", "title": "Digital Representation", "order": 1, "state": "ACTIVE"}
    html = environment.get_template("partials/session_main.html").render(
        view=_view(active_subsection=subsection, v051_subsections=[subsection],
                   controlled_c11={"status": "APPROVED_AWAITING_NEXT", "approval_version": 3,
                                   "move_index": 0, "is_final_move": False},
                   timeline=[{"kind": "message", "role": "TUTOR", "content": "A short explanation.",
                              "sequence_no": 1, "timestamp": datetime.now(timezone.utc), "visual": None}]),
        settings=SimpleNamespace(enable_f1_v04_development=False, enable_v051_internal_testing=False), new_key="key"
    )
    assert html.count('hx-post="/session/actions/c11-next"') == 1
    assert ">Next<" in html and ">C1.1 ·" not in html and "· C1.1 —" not in html


def test_controlled_c11_boundary_uses_neutral_completion_wording():
    environment = Environment(loader=FileSystemLoader("src/solo_harness/templates"))
    subsection = {"id": "C1.1", "title": "Digital Representation", "order": 1, "state": "ACTIVE"}
    html = environment.get_template("partials/session_main.html").render(
        view=_view(active_subsection=subsection, v051_subsections=[subsection],
                   controlled_c11={"status": "PILOT_BOUNDARY_HANDOFF", "move_index": 3,
                                   "is_final_move": True}),
        settings=SimpleNamespace(enable_f1_v04_development=False, enable_v051_internal_testing=False), new_key="key"
    )
    assert "This subsection is complete." in html
    assert "C1.1 is complete" not in html and "C1.2" not in html and "pilot" not in html.lower()
