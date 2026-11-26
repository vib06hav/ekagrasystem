"""Point 6: the Tutor/learner distinction is scoped to C1; C2-C4 keep their previous styling."""
import re
from datetime import datetime
from pathlib import Path

from solo_harness.web import templates

SESSION_CSS = Path("src/solo_harness/templates/session.html").read_text()
NOW = datetime(2026, 1, 1, 12, 0, 0)


def _render(items, subsections=()):
    # The partial's top level needs a full session view, so compile only its `timeline` macro.
    source = Path("src/solo_harness/templates/partials/session_main.html").read_text()
    macro = re.search(r"\{% macro timeline\(view\) %\}.*?\{% endmacro %\}", source, re.S).group(0)
    tpl = templates.env.from_string(macro + "{{ timeline(view) }}")
    return tpl.render(view={"timeline": items, "v051_subsections": list(subsections), "section_number": 1})


def _tutor(seq):
    return {"kind": "message", "role": "TUTOR", "content": "hello", "sequence_no": seq, "timestamp": NOW, "visual": None}


def _learner(seq):
    return {"kind": "message", "role": "LEARNER", "content": "hi", "sequence_no": seq, "timestamp": NOW}


def _divider(sub):
    return {"kind": "subsection", "label": sub, "title": sub, "subsection_id": sub}


def _articles(html):
    return re.findall(r'<article class="message (tutor|learner)"([^>]*)>', html)


def test_tutor_messages_carry_their_own_study_section_and_learner_messages_never_do():
    html = _render([_divider("C1.1"), _tutor(1), _learner(2), _tutor(3), _divider("C2.1"), _tutor(4), _learner(5),
                    _divider("C3.1"), _tutor(6), _divider("C4.1"), _tutor(7)])
    sections = [re.search(r'data-study-section="(\w+)"', a).group(1) if "data-study-section" in a else None
                for role, a in _articles(html) if role == "tutor"]
    assert sections == ["C1", "C1", "C2", "C3", "C4"]
    assert not any("data-study-section" in a for role, a in _articles(html) if role == "learner")


def test_earlier_c1_messages_are_not_restyled_by_a_later_section():
    # The marker comes from the divider that precedes each message, not from the active section.
    html = _render([_divider("C1.4"), _tutor(1), _divider("C2.1"), _tutor(2)])
    tutors = [a for role, a in _articles(html) if role == "tutor"]
    assert 'data-study-section="C1"' in tutors[0] and 'data-study-section="C2"' in tutors[1]


def test_messages_outside_a_controlled_subsection_get_no_marker():
    assert all("data-study-section" not in a for _, a in _articles(_render([_tutor(1), _learner(2)])))


def test_new_tutor_bubble_css_is_scoped_to_c1_and_previous_rules_are_retained():
    rules = [l.strip() for l in SESSION_CSS.splitlines() if ".conversation .message.tutor" in l]
    bubble = [r for r in rules if "border-radius:14px" in r]
    assert len(bubble) == 1 and '[data-study-section="C1"]' in bubble[0]
    assert not any(k in bubble[0] for k in ('"C2"', '"C3"', '"C4"'))
    # The unscoped rules are exactly the pre-change HEAD rules.
    unscoped = [r for r in rules if "[data-study-section" not in r]
    assert any(r.startswith(".conversation .message.tutor{background:transparent;border:0}") for r in unscoped)
    assert any("padding:.1rem 0 .1rem 1rem;border-left:2px solid var(--line)" in r for r in unscoped)
    assert not any("border-radius:14px" in r or "padding:1rem 1.15rem" in r for r in unscoped)
