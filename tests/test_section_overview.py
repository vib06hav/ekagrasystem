"""Section overview presentation checks; no provider or database required."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape


TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "solo_harness" / "templates"

AUTHORED = {
    1: ("Understanding parity checks", "How can a receiver tell when transmitted data may have changed?"),
    2: ("Exploring 1D and 2D parity", "What can different checking arrangements tell us?"),
    3: ("Connecting parity checks to outcomes", "Why do particular bit changes cause particular check results?"),
    4: ("Applying parity reasoning to new systems", "Can the same checking ideas explain unfamiliar arrangements?"),
}


def _view(section_number: int, *, activity_number: int = 1, assigned=True):
    return SimpleNamespace(
        phase="INTERVENTION_ACTIVE", is_current=True, status="ACTIVE", section_number=section_number,
        section_count=4, sections=[{"number": n, "state": "current" if n == section_number else "locked", "enabled": n <= section_number} for n in range(1, 5)],
        is_final_section=False, timeline=[{"kind": "activity", "label": f"Teaching activity {activity_number}", "activity_number": activity_number, "timestamp": datetime(2026, 11, 2, 12, 0)}],
        pending=False, retryable=False, technical_hold=False, transition_summary=None,
        started_at=None if activity_number == 1 else datetime(2026, 11, 2, 11, 0),
        ended_at=None, attempt_status="ASSIGNED" if assigned else "INTERVENTION_ACTIVE", activity_number=activity_number,
    )


def _render(view):
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))
    env.filters["tutor_markdown"] = lambda value: value
    return env.get_template("partials/session_main.html").render(view=view, new_key="overview-test")


@pytest.mark.parametrize("section_number", [1, 2, 3, 4])
def test_each_section_uses_its_exact_authored_overview(section_number):
    html = _render(_view(section_number))
    title, subtitle = AUTHORED[section_number]
    assert f'data-section-overview="{section_number}"' in html
    assert 'data-section-overview-version="f1-v04-section-overview-v1"' in html
    assert title in html and subtitle in html
    assert f"Section {section_number} overview" in html
    assert "Learning objective" in html and "What you'll explore" in html
    assert "/session/actions/begin" in html


def test_same_section_repeated_activity_keeps_overview_copy_and_updates_activity_label():
    first = _render(_view(1, activity_number=1))
    repeated = _render(_view(1, activity_number=2))
    assert AUTHORED[1][0] in first and AUTHORED[1][0] in repeated
    assert "Teaching activity 1" in first
    assert "Teaching activity 2" in repeated
    assert "Begin study" in first
    assert "Begin teaching activity 2" in repeated


def test_overview_is_rendered_in_an_autoescaped_template_and_hidden_after_begin():
    env = Environment(autoescape=select_autoescape(["html"]))
    assert env.from_string("{{ text }}").render(text="<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    html = _render(_view(1))
    assert "<script" not in html
    active = _render(_view(1, assigned=False))
    assert "data-section-overview" not in active
    assert 'hx-post="/session/actions/tutor-message"' in active
