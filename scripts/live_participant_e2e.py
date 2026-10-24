"""Drive one real participant journey through the live browser and LLM stack."""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError, sync_playwright


BASE_URL = os.getenv("LIVE_E2E_BASE_URL", "http://127.0.0.1:8000")
PARTICIPANT_ID = os.environ["LIVE_E2E_PARTICIPANT_ID"]
ARTIFACT_DIR = Path(os.getenv("LIVE_E2E_ARTIFACT_DIR", "artifacts/live_e2e"))

TUTOR_RESPONSES = {
    1: "For n greater than 1, Fibonacci follows F(n) = F(n-1) + F(n-2). The calls keep reducing n until n is 0 or 1, where the known value is returned and recursion terminates.",
    2: "The recursive tree asks for the same inputs in different branches. A shared dictionary can map each input n to its computed Fibonacci value. Each call should check it first, return a hit, and store a newly computed result for later calls.",
    3: "Without memoization, a repeated subproblem expands recursively again. With one shared cache, the first result is stored and a later request returns that value before expanding. The Fibonacci recurrence itself is unchanged; memoization changes reuse, not the mathematics.",
    4: "The invariant is that one shared cache consistently maps an input to its correct result. Check before recursive expansion, reuse on a hit, and store after solving. Variable names and whether base cases are cached are incidental; cache lifetime and input-result identity are essential.",
}

ASSESSMENT_RESPONSES = {
    1: "For every n > 1, return fib(n - 1) + fib(n - 2). For example, fib(6) first depends on fib(5) and fib(4), and the same two-predecessor relationship continues recursively. The base cases fib(0)=0 and fib(1)=1 provide known values and stop the recursion.",
    2: "Repeated requests occur because branches overlap: for example fib(4) can be requested from more than one branch. Recomputing it repeats work. Use one shared memo mapping, such as 4 -> 3. Before expanding a call, check whether n is present and return the stored value on a hit; otherwise compute it, store memo[n], and let all recursive calls share that same mapping. Merely creating a new empty dictionary in every call would lose prior results.",
    3: "The naive version expands a repeated subproblem again. In the memoized version, the first computation of an input is stored as input -> result. A later request checks the same shared cache and immediately reuses the result, avoiding the entire recursive expansion. The recurrence remains fib(n-1)+fib(n-2); only the execution avoids duplicate work. A valid structure is: check cache, return on hit, handle base cases, compute both smaller calls using the same cache, store the result, then return it.",
    4: "A correct design preserves the Fibonacci base cases and recurrence while maintaining one cache whose lifetime spans the relevant recursive calls. The cache must use a consistent n -> fib(n) identity. Each call looks up n before redundant expansion, returns a cached hit, and stores a newly solved result. A fresh dictionary inside every recursive call is ineffective because sibling branches cannot reuse entries. Different variable names, code organization, and choosing not to cache base cases are fine when these invariants remain true.",
}


def visible(locator) -> bool:
    try:
        return locator.count() > 0 and locator.first.is_visible(timeout=200)
    except PlaywrightError:
        return False


def enabled(locator) -> bool:
    try:
        return visible(locator) and locator.first.is_enabled(timeout=200)
    except PlaywrightError:
        return False


def state(page) -> str:
    if enabled(page.get_by_role("button", name="Retry")):
        return "retry"
    if visible(page.get_by_role("heading", name="Thank you")):
        return "finished"
    if visible(page.get_by_role("button", name="Submit assessment")):
        return "assessment"
    if visible(page.get_by_role("button", name="Next section")) or visible(page.get_by_role("button", name="Finish study")):
        return "section_complete"
    if visible(page.locator('textarea[name="learner_text"]')):
        return "tutor_input"
    if visible(page.get_by_role("button", name=re.compile(r"^Begin"))):
        return "begin"
    return "processing"


def wait_stable(page, timeout_seconds=150) -> str:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        current = state(page)
        if current != "processing" and not visible(page.locator("[data-operation-poll]")):
            return current
        page.wait_for_timeout(500)
    raise TimeoutError(f"participant UI did not settle within {timeout_seconds}s")


def perform(page, locator, action_name, records):
    started = time.monotonic()
    locator.click()
    page.wait_for_timeout(700)
    resulting_state = wait_stable(page)
    duration = round(time.monotonic() - started, 3)
    record = {"action": action_name, "duration_seconds": duration, "resulting_state": resulting_state}
    records.append(record)
    print(json.dumps(record), flush=True)
    return resulting_state


def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    assessments = []
    retries = 0
    started_at = datetime.now(timezone.utc)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{BASE_URL}/join", wait_until="networkidle")
        page.get_by_label("University ID").fill(PARTICIPANT_ID)
        page.get_by_role("checkbox").check()
        page.get_by_role("button", name="Continue").click()
        page.wait_for_url(re.compile(r".*/session$"))
        print(json.dumps({"joined": True, "url": page.url}), flush=True)

        section_heading = page.locator(".panel-head h1").inner_text()
        first_section = int(re.search(r"Section (\d+)", section_heading).group(1))
        print(json.dumps({"resuming_at_section": first_section}), flush=True)
        for section in range(first_section, 5):
            page.get_by_role("heading", name=f"Section {section}").wait_for()
            activity = 1
            tutor_turn = 0
            current = state(page)
            while current != "section_complete":
                if current == "begin":
                    current = perform(page, page.get_by_role("button", name=re.compile(r"^Begin")), f"section_{section}_activity_{activity}_begin", records)
                elif current == "tutor_input":
                    tutor_turn += 1
                    page.locator('textarea[name="learner_text"]').fill(TUTOR_RESPONSES[section])
                    current = perform(page, page.get_by_role("button", name="Send"), f"section_{section}_activity_{activity}_tutor_turn_{tutor_turn}", records)
                elif current == "assessment":
                    prompt = page.locator(".assessment-prompt").inner_text()
                    assessments.append({"section": section, "activity": activity, "prompt": prompt})
                    page.locator('textarea[name="response_text"]').fill(ASSESSMENT_RESPONSES[section])
                    current = perform(page, page.get_by_role("button", name="Submit assessment"), f"section_{section}_activity_{activity}_assessment", records)
                    if current == "begin":
                        activity += 1
                        tutor_turn = 0
                        if activity > 3:
                            raise AssertionError("a fourth teaching activity was exposed")
                elif current == "retry":
                    retries += 1
                    if retries > 10:
                        raise AssertionError("too many participant retries")
                    current = perform(page, page.get_by_role("button", name="Retry"), f"section_{section}_manual_retry_{retries}", records)
                else:
                    current = wait_stable(page)

            page.get_by_text("Section completed", exact=True).wait_for()
            page.screenshot(path=str(ARTIFACT_DIR / f"section_{section}_complete.png"), full_page=True)
            if section < 4:
                current = perform(page, page.get_by_role("button", name="Next section"), f"section_{section}_next", records)
                if current != "begin":
                    raise AssertionError(f"next section did not open at its begin state: {current}")
                page.get_by_role("link", name=f"Section {section}").click()
                page.get_by_text("This completed section is available for review.").wait_for()
                if page.locator("textarea").count():
                    raise AssertionError("completed section review exposed an input")
                page.get_by_role("link", name=f"Section {section + 1}").click()
            else:
                current = perform(page, page.get_by_role("button", name="Finish study"), "finish_study", records)
                if current != "finished":
                    raise AssertionError(f"study did not reach completion: {current}")

        page.screenshot(path=str(ARTIFACT_DIR / "study_complete.png"), full_page=True)
        final_html = page.content()
        forbidden = ["pedagogy_id", "candidate_form_ids", "hidden_scoring_context", "observed_solo_state_id", "compiled_prompt_text", "raw_response_text", "google/gemini-3.5-flash-lite"]
        leaked = [item for item in forbidden if item in final_html]
        if leaked:
            raise AssertionError(f"participant HTML leaked internal fields: {leaked}")
        browser.close()

    report = {
        "participant_id": PARTICIPANT_ID,
        "started_at": started_at.isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "actions": records,
        "assessment_prompts": assessments,
        "manual_retries": retries,
        "actions_over_60_seconds": [item for item in records if item["duration_seconds"] > 60],
        "completed": True,
    }
    (ARTIFACT_DIR / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"complete": True, "report": str(ARTIFACT_DIR / "report.json")}), flush=True)


if __name__ == "__main__":
    main()
