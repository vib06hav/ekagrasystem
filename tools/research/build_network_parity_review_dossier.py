"""Build a self-contained reviewer dossier for the completed network-parity C1-C4 session.

Input is the read-only database export produced by solo_harness.research_export.
All quoted transcript, assessment, and LLM material is copied verbatim.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shade = OxmlElement("w:shd")
    shade.set(qn("w:fill"), fill)
    tc_pr.append(shade)


def add_label(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(31, 78, 121)


def add_verbatim(doc: Document, text, *, small: bool = False) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.keep_together = False
    r = p.add_run("[not persisted]" if text is None else str(text))
    r.font.name = "Consolas"
    r._element.rPr.rFonts.set(qn("w:ascii"), "Consolas")
    r._element.rPr.rFonts.set(qn("w:hAnsi"), "Consolas")
    r.font.size = Pt(7.5 if small else 8.5)


def add_kv_table(doc: Document, rows) -> None:
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.autofit = False
    table.columns[0].width = Inches(1.7)
    table.columns[1].width = Inches(4.95)
    for cell, text in zip(table.rows[0].cells, ("Field", "Value")):
        cell.text = text
        set_cell_shading(cell, "1F4E79")
        for run in cell.paragraphs[0].runs:
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.bold = True
    for key, value in rows:
        cells = table.add_row().cells
        cells[0].text = str(key)
        cells[1].text = str(value)
        for cell in cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(1)
                for run in p.runs:
                    run.font.size = Pt(8)


def add_call(doc: Document, call: dict, *, include_payload: bool = False) -> None:
    doc.add_heading(f"{call['purpose']} call {call['id']}", level=3)
    add_kv_table(doc, [
        ("Status", call.get("status")), ("Provider", call.get("provider")),
        ("Model", call.get("model")), ("Started", call.get("started_at")),
        ("Completed", call.get("completed_at")), ("Attempt", call.get("attempt_id")),
        ("Assessment", call.get("assessment_instance_id")), ("Retry", call.get("retry_number")),
    ])
    add_label(doc, "Exact compiled prompt sent")
    add_verbatim(doc, call.get("compiled_prompt_text"), small=True)
    add_label(doc, "Exact raw provider response")
    add_verbatim(doc, call.get("raw_response_text"), small=True)
    add_label(doc, "Parsed response")
    add_verbatim(doc, json_text(call.get("parsed_response")), small=True)
    if include_payload:
        add_label(doc, "Exact request body")
        add_verbatim(doc, call.get("request_body_text"), small=True)
        add_label(doc, "Exact request payload")
        add_verbatim(doc, json_text(call.get("request_payload")), small=True)


def main() -> int:
    source = Path(sys.argv[1]).resolve()
    destination = Path(sys.argv[2]).resolve()
    evaluation_source = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None
    export = json.loads(source.read_text(encoding="utf-8"))
    data = export["data"]
    session = data["session"]
    attempts = sorted(data["attempts"], key=lambda x: (x.get("assigned_at") or "", x.get("sequence_in_transition") or 0))
    by_attempt = {x["id"]: x for x in attempts}
    messages = defaultdict(list)
    for item in data["messages"]:
        messages[item["attempt_id"]].append(item)
    for items in messages.values():
        items.sort(key=lambda x: (x.get("sequence_no", 0), x.get("created_at", "")))
    assessments = {x["attempt_id"]: x for x in data["assessment_instances"]}
    responses = {x["assessment_instance_id"]: x for x in data["assessment_responses"]}
    evals = defaultdict(list)
    evaluation_rows = data.get("phase2_evaluations", [])
    if evaluation_source and evaluation_source.is_file():
        evaluation_rows = json.loads(evaluation_source.read_text(encoding="utf-8"))
    for item in evaluation_rows:
        evals[item["assessment_response_id"]].append(item)
    calls_by_attempt = defaultdict(list)
    all_calls = sorted(data["llm_calls"], key=lambda x: (x.get("started_at") or "", x["id"]))
    for item in all_calls:
        if item.get("attempt_id"):
            calls_by_attempt[item["attempt_id"]].append(item)

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)
    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9.5)
    for name in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        styles[name].font.name = "Aptos Display"
        styles[name].font.color.rgb = RGBColor(0, 0, 0)

    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Network Parity C1 to C4 Complete Session Review")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Consolidated exact evidence dossier").italic = True

    doc.add_heading("What this dossier contains", level=1)
    doc.add_paragraph(
        "This is a verbatim review artifact for the completed network error-detection and parity session. "
        "It combines the exact stored tutor and learner messages, each frozen learner-visible assessment package, "
        "the submitted assessment answers, evaluation records, and all persisted LLM inputs and outputs. "
        "The material is ordered by actual session chronology; no response text or prompts have been rewritten."
    )
    add_kv_table(doc, [
        ("Session ID", session["id"]), ("Status", session.get("status")),
        ("Terminal result", session.get("terminal_reason")), ("Formal state", session.get("formal_state_id")),
        ("Started UTC", session.get("started_at")), ("Ended UTC", session.get("ended_at")),
        ("Study version", session.get("study_version_id")), ("DB export SHA256", export.get("data_sha256")),
        ("Source export", source.name), ("Attempts", len(attempts)), ("Persisted LLM calls", len(all_calls)),
    ])
    doc.add_paragraph(
        "Reading note: the session has retries where an assessment did not pass. Every attempt is retained, so the progression from C1 through C4 can be audited end to end. "
        "Appendix A is the complete raw LLM ledger, including assessment construction and evaluation operations that do not appear in the visible dialogue."
    )

    for attempt in attempts:
        doc.add_page_break()
        transition = attempt.get("transition_id")
        seq = attempt.get("sequence_in_transition")
        doc.add_heading(f"{transition} attempt {seq}", level=1)
        add_kv_table(doc, [
            ("Attempt ID", attempt["id"]), ("Pedagogy", attempt.get("pedagogy_id")),
            ("Assigned", attempt.get("assigned_at")), ("Completed", attempt.get("completed_at")),
            ("Passed", attempt.get("passed")), ("Completion reason", attempt.get("completion_reason")),
        ])
        doc.add_heading("Exact visible teaching transcript", level=2)
        visible = messages.get(attempt["id"], [])
        if not visible:
            doc.add_paragraph("No persisted teaching messages for this attempt.")
        for message in visible:
            role = "Teacher" if message.get("role") == "TUTOR" else "Student" if message.get("role") == "LEARNER" else message.get("role")
            doc.add_heading(f"{role} message {message.get('sequence_no')}", level=3)
            add_verbatim(doc, message.get("content_text"))
            add_kv_table(doc, [("Persisted at", message.get("created_at")), ("Message ID", message.get("id")), ("Linked LLM call", message.get("llm_call_id"))])

        tutor_calls = [x for x in calls_by_attempt.get(attempt["id"], []) if x.get("purpose") == "TUTOR"]
        doc.add_heading("Exact teacher model prompts and outputs", level=2)
        if not tutor_calls:
            doc.add_paragraph("No persisted Tutor provider calls for this attempt.")
        for call in tutor_calls:
            add_call(doc, call)

        assessment = assessments.get(attempt["id"])
        doc.add_heading("Exact assessment delivered", level=2)
        if not assessment:
            doc.add_paragraph("No assessment instance was persisted for this attempt.")
            continue
        add_kv_table(doc, [
            ("Assessment ID", assessment["id"]), ("Form", assessment.get("assessment_form_id")),
            ("Frozen at", assessment.get("frozen_at")), ("Package fingerprint", assessment.get("frozen_package_fingerprint")),
            ("Delivery status", assessment.get("delivery_status")),
        ])
        add_label(doc, "Frozen learner-visible package including exact MCQ stems options and subjective question")
        add_verbatim(doc, json_text(assessment.get("frozen_public_snapshot")))
        response = responses.get(assessment["id"])
        doc.add_heading("Exact student assessment submission", level=2)
        add_verbatim(doc, json_text(response) if response else None)
        doc.add_heading("Exact evaluation record", level=2)
        related_evals = evals.get(response["id"], []) if response else []
        add_verbatim(doc, json_text(related_evals) if related_evals else None)

    doc.add_page_break()
    doc.add_heading("Appendix A Complete raw LLM ledger", level=1)
    doc.add_paragraph(
        "Every persisted LLM call is reproduced below, in timestamp order. This includes Tutor, assessment construction, writer, semantic review, and Judge calls. "
        "The request body and payload are included because they are persisted exact records; they may repeat the compiled prompt."
    )
    for call in all_calls:
        doc.add_page_break()
        add_call(doc, call, include_payload=True)

    doc.add_page_break()
    doc.add_heading("Appendix B Protocol event ledger", level=1)
    doc.add_paragraph("Exact persisted protocol events in sequence order.")
    add_verbatim(doc, json_text(data.get("protocol_events", [])), small=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    doc.save(destination)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
