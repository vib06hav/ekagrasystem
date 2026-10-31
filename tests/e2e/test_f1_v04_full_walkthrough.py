"""Development-only, real-browser F1 v0.4 C1--C4 walkthrough.

This is intentionally runnable as a script, not a unit-test fixture.  It drives
the running FastAPI/Jinja application solely through visible Playwright actions.
The only database access is a read-only development audit used to select the
server-private MCQ key after an assessment is frozen.  It never calls runtime
methods, POSTs application routes directly, or changes database state.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright
ROOT = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get("EKAGRA_BASE_URL", "http://127.0.0.1:8000")
RUN_ID = os.environ.get("EKAGRA_DEMO_ID", f"playwright-c1c4-{uuid.uuid4().hex[:12]}")
OUT = ROOT / "research-data" / "c1_c4_playwright_demo" / RUN_ID
VIDEO_DIR = OUT / "video"
STATE_FILE = OUT / "browser-state.json"
TRACE_FILE = OUT / "interaction-trace.json"
AUDIT_FILE = OUT / "development-audit.json"
APP_CONTAINER = os.environ.get("EKAGRA_APP_CONTAINER", "ekagrasystem-app-1")


def container_db_read(expression: str) -> dict | None:
    """Run a read-only ORM projection inside the app container's DB network."""
    code = """
import json
from sqlalchemy import select
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance, Attempt, LLMCall, Session
db=make_session_factory(get_settings().database_url)()
try:
    result = (%s)
    print(json.dumps(result, default=str))
finally:
    db.close()
""" % expression
    completed = subprocess.run(
        ["docker", "exec", APP_CONTAINER, "python", "-c", code], check=True,
        text=True, capture_output=True,
    )
    raw = completed.stdout.strip()
    return json.loads(raw) if raw and raw != "null" else None


def audit_session_id() -> str | None:
    escaped = json.dumps(RUN_ID)
    return container_db_read(f"str(db.scalar(select(Session.id).where(Session.institutional_id == {escaped}))) if db.scalar(select(Session.id).where(Session.institutional_id == {escaped})) else None")


def private_answers(session_id: str) -> dict[str, str]:
    """Read the private frozen map only in the local development audit."""
    query = json.dumps(session_id)
    result = container_db_read(
        f"(lambda a: {{row['id']: row['correct_option_id'] for row in a.frozen_private_snapshot['mcqs']}} if a and a.frozen_private_snapshot else None)(db.scalar(select(AssessmentInstance).join(Attempt, AssessmentInstance.attempt_id == Attempt.id).where(Attempt.session_id == '{session_id}', AssessmentInstance.status == 'ACTIVE')))"
    )
    if result is None:
        raise RuntimeError("frozen private MCQ map is not available")
    return result


def db_snapshot(session_id: str) -> dict:
    return container_db_read(f"(lambda s, attempts: {{'session_id':str(s.id),'status':s.status,'phase':s.phase,'formal_state':s.formal_state_id,'attempts':[{{'id':str(a.id),'transition':a.transition_id,'ordinal':a.sequence_in_transition,'pedagogy':a.pedagogy_id,'status':a.status,'passed':a.passed,'formal_before':a.formal_state_before_id,'formal_after':a.formal_state_after_id,'assessment_status':(db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id == a.id)).status if db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id == a.id)) else None),'calls':[{{'purpose':c.purpose,'status':c.status,'provider':c.provider,'model':c.model,'error_class':c.error_class}} for c in db.scalars(select(LLMCall).where(LLMCall.attempt_id == a.id).order_by(LLMCall.started_at))]}} for a in attempts]}})(db.get(Session, '{session_id}'), list(db.scalars(select(Attempt).where(Attempt.session_id == '{session_id}').order_by(Attempt.assigned_at))))")


def log(trace: list[dict], event: str, **data) -> None:
    trace.append({"at": datetime.now(timezone.utc).isoformat(), "event": event, **data})
    TRACE_FILE.write_text(json.dumps(trace, indent=2), encoding="utf-8")


def wait_visible(page: Page, selector: str, timeout: int = 300_000):
    return page.locator(selector).wait_for(state="visible", timeout=timeout)


def wait_for_assessment(page: Page, trace: list[dict]) -> None:
    """Wait for the real background generation to render a frozen assessment."""
    page.locator("section.assessment h2").filter(has_text="Answer all four questions").wait_for(
        state="visible", timeout=600_000
    )
    log(trace, "assessment_visible", question_count=page.locator("fieldset.mcq").count())


def advance_from_tutor(page: Page, trace: list[dict]) -> None:
    # Begin once, send a visible real learner message, then use only the labelled
    # development control if the Tutor has not itself completed the activity.
    if page.get_by_role("button", name=re.compile("Begin (study|teaching activity)")).count():
        page.get_by_role("button", name=re.compile("Begin (study|teaching activity)")).click()
        wait_visible(page, "#learner-text", 300_000)
        log(trace, "tutor_started")
    prior_tutor_messages = page.locator("[data-tutor-message-sequence]").count()
    page.locator("#learner-text").fill("I am ready to work through the example carefully. Please explain the key relationship and how to check it.")
    page.locator("#tutor-composer button.send").click()
    # The real Tutor response is rendered before the development advance.
    page.locator("[data-tutor-message-sequence]").nth(prior_tutor_messages).wait_for(state="visible", timeout=300_000)
    log(trace, "tutor_message_completed", visible_tutor_messages=page.locator("[data-tutor-message-sequence]").count())
    advance = page.get_by_role("button", name="Advance to assessment (development only)")
    if advance.count():
        advance.click()
        log(trace, "development_advance_clicked")
    wait_for_assessment(page, trace)


def subjective_response(page: Page, strong: bool) -> str:
    prompt = page.locator("label[for='assessment-response']").inner_text()
    if not strong:
        return "I am not sure. I would choose an answer without checking the relationship."
    if "case a" in prompt.lower() and "case b" in prompt.lower() and ("2d" in prompt.lower() or "row-column" in prompt.lower()):
        two_errors = "two errors" in prompt.lower() or "two bit errors" in prompt.lower()
        one_d = re.search(r"(?:received the frame|received frame|frame)\s+([01]{4,})", prompt, re.I)
        case_a = (
            f"In Case A, the received 1D frame {one_d.group(1)} has {one_d.group(1).count('1')} one(s); "
            "the receiver counts the whole frame and compares that count to the agreed parity, so a single flip is detected. "
            if one_d else "In Case A, 1D parity detects a single-bit flip because it changes the total parity. "
        )
        case_b = (
            "In Case B, a single changed grid bit makes exactly its row check and its column check fail; their intersection "
            "identifies the error position."
            if not two_errors else
            "In Case B, two flips in one row restore that row's parity, but each changed column has one flip and fails its "
            "column check. The two failed columns therefore detect the pair even though the row check itself passes."
        )
        return case_a + case_b
    if "1d" in prompt.lower() and "2d" in prompt.lower():
        if "four" in prompt.lower() and ("rectangle" in prompt.lower() or "corner" in prompt.lower()):
            return (
                "For the 1D even-parity transmission, four flips change the number of 1s by an even amount, so the "
                "overall parity can be restored and the final single parity check may accept the corrupted frame. "
                "For the 2D rectangular four-corner pattern, each affected row has two flips and each affected column "
                "has two flips. Every row and column parity is therefore restored, so full row-column parity has the "
                "same undetected-pattern limitation for that rectangle."
            )
        return (
            "For the 1D case, the receiver checks the parity of the entire received frame; one flip changes it and is "
            "detected, whereas an even number of flips can restore the parity. For the 2D row-column case, a single "
            "changed cell causes its row and its column checks to fail, and their intersection identifies the cell. "
            "More structured even-error patterns can restore all affected row and column counts, which is the limitation "
            "of 2D parity."
        )
    frame = re.search(r"(?:frame is|received as|received frame|frame|bit string)\s+([01]{4,})", prompt, re.I)
    if frame and "parity" in prompt.lower():
        received = frame.group(1)
        convention = "odd" if "odd-parity" in prompt.lower() or "odd parity" in prompt.lower() else "even"
        total_ones = received.count("1")
        parity_ok = total_ones % 2 == (1 if convention == "odd" else 0)
        outcome = "passes" if parity_ok else "fails"
        return (
            f"With {convention} parity, the sender selects the check bit so the complete transmitted frame has an "
            f"{'odd' if convention == 'odd' else 'even'} total number of 1s. The receiver does not guess from one bit: "
            f"it counts every 1 in the received frame, including the designated check-bit position, and accepts only "
            f"if that total has {convention} parity. Frame {received} contains {total_ones} one(s), which is "
            f"{'odd' if total_ones % 2 else 'even'}, so it {outcome} the stated {convention}-parity test."
        )
    data = re.search(r"data string\s+([01]{3,})", prompt, re.I)
    if data and "parity" in prompt.lower():
        bits = data.group(1)
        convention = "odd" if "odd parity" in prompt.lower() else "even"
        ones = bits.count("1")
        required_check = "1" if (ones % 2 == 0 if convention == "odd" else ones % 2 == 1) else "0"
        total = ones + int(required_check)
        return (
            f"The claim about frame length is not correct. {convention.title()} parity concerns the number of 1s, "
            f"not whether the number of bit positions is even. The data bits {bits} contain {ones} one(s), so the sender "
            f"chooses check bit {required_check}; the completed frame then contains {total} one(s), which has {convention} "
            f"parity. The receiver counts all data bits and the check bit and accepts only if that count has {convention} parity."
        )
    if "1d" in prompt.lower() and "2d" in prompt.lower() and "parity" in prompt.lower():
        return (
            "For the 1D even-parity case, two flipped bits change the number of 1s by an even amount. "
            "The overall parity is therefore restored, so a single 1D parity check can accept that two-bit error. "
            "For the full 2D row-column case, two flips in the same row also restore that row's parity, but they "
            "occur in two different columns. Each affected column has one changed bit and therefore fails its column "
            "parity check. Thus 2D parity detects the same-row pair through the two failed columns even though the row check passes."
        )
    # Uses the participant-visible prompt only; it makes the required reasoning
    # explicit without looking at a hidden subjective answer or Judge output.
    return (
        "I would first identify the quantities and the rule stated in the question, then apply the rule to every relevant "
        "part of the example rather than relying on a single surface feature. I would check that the resulting values preserve "
        "the required relationship and explain why an alternative violates that rule. This connects the calculation, the "
        "structure of the representation, and the final conclusion. Prompt considered: " + prompt
    )


def submit_assessment(page: Page, session_id: str, trace: list[dict], *, pass_attempt: bool) -> None:
    keys = private_answers(session_id)
    for index, (question_id, answer) in enumerate(keys.items(), start=1):
        value = answer
        if not pass_attempt:
            options = page.locator(f"input[name='{question_id.lower()}_answer']")
            option_values = options.evaluate_all("els => els.map(e => e.value)")
            value = next(option for option in option_values if option != answer)
        page.locator(f"input[name='{question_id.lower()}_answer'][value='{value}']").check()
    page.locator("#assessment-response").fill(subjective_response(page, pass_attempt))
    page.get_by_role("button", name="Submit assessment").click()
    log(trace, "assessment_submitted", mode="passing" if pass_attempt else "deliberately_weak")
    # The actual Judge result must replace the submitted state.  Reloading is a
    # real browser navigation fallback when a CDN-provided HTMX poll is delayed;
    # every decision still comes from the rendered participant page.
    deadline = datetime.now().timestamp() + 600
    while datetime.now().timestamp() < deadline:
        try:
            page.goto(f"{BASE_URL}/session", wait_until="domcontentloaded", timeout=15_000)
        except PlaywrightTimeoutError:
            continue
        if page.locator("[data-section-complete], #learner-text, .begin-state button, [data-generation-error], [data-technical-hold]").count():
            return
        page.wait_for_timeout(1000)
    raise PlaywrightTimeoutError("Judge result did not render within ten minutes")


def complete_section(page: Page, session_id: str, trace: list[dict], *, expect_pass: bool) -> None:
    submit_assessment(page, session_id, trace, pass_attempt=expect_pass)
    snapshot = db_snapshot(session_id)
    current = next(attempt for attempt in reversed(snapshot["attempts"]) if attempt["passed"] is not None)
    log(trace, "judge_finished", transition=current["transition"], passed=current["passed"], formal_after=current["formal_after"])
    if current["passed"] is not expect_pass:
        raise AssertionError(f"Judge outcome was {current['passed']}, expected {expect_pass}; preserved actual run for audit")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); VIDEO_DIR.mkdir(exist_ok=True)
    trace: list[dict] = []
    with sync_playwright() as pw:
        # Headed Chromium is deliberate.  Video remains the authoritative record
        # when an unattended Windows desktop cannot present the browser to Codex.
        browser = pw.chromium.launch(headless=False, slow_mo=125)
        context = browser.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(VIDEO_DIR), record_video_size={"width": 1280, "height": 720})
        page = context.new_page()
        try:
            page.goto(f"{BASE_URL}/join", wait_until="networkidle")
            page.locator("#participant-code").fill(RUN_ID)
            page.locator("input[name='acknowledged']").check()
            page.get_by_role("button", name="Continue").click()
            page.locator("#session-main").wait_for(state="visible", timeout=30_000)
            session_id = audit_session_id()
            if not session_id:
                raise RuntimeError("frontend join did not create a development session")
            log(trace, "joined", session_id=session_id, institutional_id=RUN_ID)

            # C1 pass.
            advance_from_tutor(page, trace)
            complete_section(page, session_id, trace, expect_pass=True)
            page.get_by_role("button", name="Next section").click(); log(trace, "next_section", from_transition="C1")

            # C2 deliberately fails once, yielding a new authorized attempt.
            advance_from_tutor(page, trace)
            complete_section(page, session_id, trace, expect_pass=False)
            wait_visible(page, ".begin-state button, #learner-text", 120_000)
            log(trace, "c2_retry_attempt_visible")

            # C2 retry passes under the independently selected pedagogy.
            advance_from_tutor(page, trace)
            complete_section(page, session_id, trace, expect_pass=True)
            page.get_by_role("button", name="Next section").click(); log(trace, "next_section", from_transition="C2")

            # C3 and C4 pass.
            advance_from_tutor(page, trace); complete_section(page, session_id, trace, expect_pass=True)
            page.get_by_role("button", name="Next section").click(); log(trace, "next_section", from_transition="C3")
            advance_from_tutor(page, trace); complete_section(page, session_id, trace, expect_pass=True)
            page.get_by_role("button", name="Finish study").click()
            page.locator("[data-study-complete]").wait_for(state="visible", timeout=60_000)
            snapshot = db_snapshot(session_id); log(trace, "study_finished", status=snapshot["status"], formal_state=snapshot["formal_state"])
            AUDIT_FILE.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            if snapshot["status"] != "COMPLETED" or snapshot["formal_state"] != "EA":
                raise AssertionError("frontend journey did not reach completed EA state")
        finally:
            context.storage_state(path=str(STATE_FILE))
            context.close(); browser.close()


if __name__ == "__main__":
    main()
