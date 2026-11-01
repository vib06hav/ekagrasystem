"""Tutor presentation regression tests. No database or real LLM required."""
from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader, select_autoescape

from solo_harness.teaching_render import render_tutor_markdown
from solo_harness.runtime.tutor_presentation import (
    TUTOR_PRESENTATION_GUIDANCE,
    TUTOR_PRESENTATION_VERSION,
)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _text(value):
    parser = _TextExtractor()
    parser.feed(str(value))
    return "".join(parser.parts)


def test_markdown_supports_readable_instructions_and_comparisons():
    source = """### Even parity

**Rule:** count `1` bits.

1. Start with `010`.
2. Append bit `1`.

| Case | Frame | Result |
| --- | --- | --- |
| Sent | `0101` | even |
| Received | `0001` | odd |

> **Your turn**
> Why check the entire frame?"""
    html = str(render_tutor_markdown(source))
    assert "<h3>Even parity</h3>" in html
    assert "<strong>Rule:</strong>" in html
    assert "<code>0101</code>" in html
    assert "<ol>" in html and "<li>" in html
    assert "<table>" in html and "<th>" in html and "<td>" in html
    assert "<blockquote>" in html
    assert "Why check the entire frame?" in html
    assert "style=" not in html


def test_unsafe_markup_cannot_execute_or_create_links():
    raw = '''<script>alert(1)</script>
<img src=x onerror=alert(2)>
<a href="javascript:alert(3)">click me</a>

[phishing](https://example.com)
![image description](https://example.com/image.png)

**Actual lesson**'''
    html = str(render_tutor_markdown(raw))
    assert "<script" not in html
    assert "<img" not in html
    assert "<a " not in html
    assert "onerror=" not in html.split("<", 1)[-1].split(">", 1)[0]  # no injected attribute
    assert "<strong>Actual lesson</strong>" in html
    assert "click me" in html and "image description" in html


def test_previous_unformatted_tutor_paragraph_is_kept_and_not_fabricated():
    raw = "Even parity: data 010 has one 1. The check bit is 1. The frame is 0101. Why?"
    html = str(render_tutor_markdown(raw))
    assert _text(html).strip() == raw
    assert "<h" not in html and "<blockquote>" not in html
    assert raw == "Even parity: data 010 has one 1. The check bit is 1. The frame is 0101. Why?"


def test_original_six_tutor_examples_remain_readable_without_content_rewrite():
    path = Path(__file__).resolve().parents[1] / "tests/fixtures/legacy_tutor_outputs.md"
    assert path.is_file()  # Regression fixture ships with the test.
    content = path.read_text(encoding="utf-8")
    records = content.split("## Tutor message ")[1:]
    assert len(records) == 6
    for record in records:
        raw = record.split("\n\n", 1)[1].strip()
        html = render_tutor_markdown(raw)
        assert _text(html).strip() == raw
        assert "<script" not in str(html)


def test_template_is_tutor_only_and_escapes_learner_text():
    templates = Path(__file__).resolve().parents[1] / "src/solo_harness/templates"
    env = Environment(loader=FileSystemLoader(str(templates)), autoescape=select_autoescape(["html"]))
    env.filters["tutor_markdown"] = render_tutor_markdown
    fragment = env.from_string(
        "{% from 'partials/session_main.html' import timeline with context %}{{ timeline(view) }}"
    )
    view = SimpleNamespace(timeline=[
        {"kind":"message", "role":"TUTOR", "content":"### Key idea\n\n**Even parity**",
         "sequence_no":1, "timestamp":datetime(2026,11,1,12,0)},
        {"kind":"message", "role":"LEARNER", "content":"<script>alert(1)</script> **literal**",
         "sequence_no":2, "timestamp":datetime(2026,11,1,12,1)},
    ])
    rendered = fragment.render(view=view)
    assert '<h3>Key idea</h3>' in rendered
    assert 'data-teaching-render="markdown-v1"' in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt; **literal**" in rendered
    assert '<script>alert(1)</script>' not in rendered
    assert rendered.count('data-teaching-render="markdown-v1"') == 1


def test_presentation_contract_is_versioned_and_not_a_scientific_override():
    assert TUTOR_PRESENTATION_VERSION == "tutor-markdown-v1"
    assert TUTOR_PRESENTATION_VERSION in TUTOR_PRESENTATION_GUIDANCE
    assert "Guided Questioning" in TUTOR_PRESENTATION_GUIDANCE
    assert "Contrasting Cases" in TUTOR_PRESENTATION_GUIDANCE
    assert "Scient" in TUTOR_PRESENTATION_GUIDANCE
    assert "assessment" in TUTOR_PRESENTATION_GUIDANCE.lower()
