"""Presentation-only, allowlisted Markdown for persisted Tutor text.

The original Message.content_text remains immutable and is authoritative for audit.
Learner messages MUST NOT use this renderer. HTML authored by the model is text,
not executable markup. No dynamic HTML, embedded media or user-defined classes.
"""
from __future__ import annotations

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


def render_tutor_markdown(value: str | None) -> Markup:
    """Return sanitized HTML for Tutor messages; raw text is never changed."""
    if not value:
        return Markup("")
    rendered = _PARSER.render(str(value))
    safe = bleach.clean(
        rendered, tags=_ALLOWED_TAGS, attributes={}, protocols=[],
        strip=True, strip_comments=True,
    )
    return Markup(safe)
