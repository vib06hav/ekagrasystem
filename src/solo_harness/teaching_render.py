"""Presentation-only, allowlisted Markdown for persisted Tutor text.

The original Message.content_text remains immutable and is authoritative for audit.
Learner messages MUST NOT use this renderer. HTML authored by the model is text,
not executable markup. No dynamic HTML, embedded media or user-defined classes.
"""
from __future__ import annotations

import re
import bleach
from markdown_it import MarkdownIt
from markupsafe import Markup

# Support ordinary CommonMark and tables, but never interpret inline HTML.
_PARSER = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False, "breaks": True})
_PARSER.enable("table")
_PARSER.disable(["image", "link", "autolink"])  # No external navigation or embedded media.

# No attributes, styles, links, images, scripts, iframes or externally loaded media.
_ALLOWED_TAGS = frozenset({
    "p", "br", "strong", "em", "s", "del", "code", "pre",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "hr",
    "table", "thead", "tbody", "tr", "th", "td",
})


def _normalize_markdown(text: str) -> str:
    """Normalize flattened or inline markdown lists, blockquotes, and questions."""
    if not text:
        return ""
    # Ensure blockquote (> Key Takeaway:) starts on a new line preceded by a blank line
    text = re.sub(r'(?<=\S)\s*(>\s*(?:\*\*)?(?:Key Takeaway|Takeaway|Rule|Note):?)', r'\n\n\1', text, flags=re.IGNORECASE)
    # Ensure > Key Takeaway: has bold text
    text = re.sub(r'>\s*Key Takeaway:\s*', r'> **Key Takeaway:** ', text, flags=re.IGNORECASE)

    # Ensure bullet lists (* Item or - Item) preceded by punctuation start on a new line
    text = re.sub(r'([:\.!\?])\s+(\*|-)\s+(?=[A-Za-z0-9`"\'\*])', r'\1\n\n\2 ', text)

    # Ensure numbered lists (1. Item) preceded by punctuation start on a new line
    text = re.sub(r'([:\.!\?])\s+(\d+\.)\s+(?=[A-Za-z0-9`"\'\*])', r'\1\n\n\2 ', text)

    # If a contrast/summary sentence follows a bullet item ending with an outcome (e.g. PASS. / FAIL.), split it into its own paragraph
    text = re.sub(r'(\b(?:PASS|FAIL|Detected|Undetected)\b\.?)\s+(?=(?:This contrast|In contrast|Comparing|Notice that|Thus,|Therefore,)\b)', r'\1\n\n', text, flags=re.IGNORECASE)

    # Bold unbolded choice/case labels in bullets like '* Proposed Choice 1 (Correct):' -> '* **Proposed Choice 1 (Correct):**'
    text = re.sub(r'(\*\s+)(Proposed Choice \d+[^:\n]*|Case [A-Za-z0-9]+[^:\n]*|Choice \d+[^:\n]*|Group [A-Za-z0-9]+[^:\n]*):\s+', r'\1**\2:** ', text)

    # Bold unbolded step labels like '1. Step 1 (Group membership):' -> '1. **Step 1 (Group membership):**'
    text = re.sub(r'(\d+\.\s+)(Step \d+[^:\n]*|Stage \d+[^:\n]*):\s+', r'\1**\2:** ', text)

    # Bold unbolded outcomes like 'outcome of PASS' -> 'outcome of **PASS**'
    text = re.sub(r'\b(outcome of|verdict:?|result:?)\s+(PASS|FAIL|Detected|Undetected)\b', r'\1 **\2**', text, flags=re.IGNORECASE)

    # Ensure guided questions (**Question:**) preceded by punctuation start on a new line
    text = re.sub(r'([:\.!\?])\s+(\*\*(?:Question|Prompt|Your turn):\*\*)', r'\1\n\n\2', text, flags=re.IGNORECASE)

    return text


def render_tutor_markdown(value: str | None) -> Markup:
    """Return sanitized HTML for Tutor messages; raw text is never changed."""
    if not value:
        return Markup("")
    normalized = _normalize_markdown(str(value))
    rendered = _PARSER.render(normalized)
    safe = bleach.clean(
        rendered, tags=_ALLOWED_TAGS, attributes={}, protocols=[],
        strip=True, strip_comments=True,
    )
    return Markup(safe)
