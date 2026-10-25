"""Run a bounded real-provider Playwright study without Windows capture."""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import Error as PlaywrightError, sync_playwright
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from solo_harness.db.models import Session
from solo_harness.research_export import write_session_export


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/python_fibonacci_memoization/v0.1"

TUTOR_RESPONSES = {
    1: "Fibonacci reduces n through the two predecessor calls until fib(0) and fib(1) return known values, so the recurrence and base cases determine both the relationship and termination.",
    2: "Overlapping branches can request the same Fibonacci input. A shared mapping should be checked before expansion, return a hit immediately, and store a computed input-to-result value for later branches.",
    3: "Memoization changes execution rather than the recurrence: a repeated input is looked up in the same cache and reused, so that branch does not expand again.",
    4: "The invariant is one shared cache mapping each input n to fib(n). Check before expansion, reuse on a hit, and store a new result so sibling recursive calls see the same mapping.",
}

PASSING_ASSESSMENT_RESPONSES = {
    1: "For n greater than 1, fib(n) is fib(n-1) plus fib(n-2). The base cases fib(0)=0 and fib(1)=1 return known values and stop recursion; every larger case follows that same two-predecessor relationship.",
    2: "Recursive branches can request the same input, so one shared memo mapping should store n to fib(n). Each call checks the mapping first and returns a cached hit; otherwise it computes the value, stores it, and later branches reuse it. A fresh mapping per call would not preserve reuse.",
    3: "Naive recursion expands a repeated subproblem again. With memoization, the first result for an input is stored in the shared cache, and a later request checks that cache and returns the stored value before any recursive expansion. The Fibonacci recurrence itself stays unchanged.",
    4: "A correct memoized design preserves the Fibonacci recurrence and base cases while keeping one cache alive across recursive calls. It consistently maps n to fib(n), checks before redundant expansion, returns cache hits, and stores solved values so sibling branches can reuse them.",
}

INCORRECT_ASSESSMENT_RESPONSES = {
    1: "Fibonacci should recurse only to fib(n-1), because fib(n-2) is redundant. The only base case needed is fib(1)=1, and a cache changes the recurrence by replacing recursive results with zero.",
    2: "Each recursive call should create its own empty cache so values cannot accidentally be shared. It is best to compute every branch again, because reusing a prior value would make the Fibonacci result unreliable.",
}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


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
    if enabled(page.get_by_role("button", name="Submit assessment")):
        return "assessment"
    if visible(page.get_by_role("button", name="Next section")) or visible(page.get_by_role("button", name="Finish study")):
        return "section_complete"
    if visible(page.locator('textarea[name="learner_text"]')):
        return "tutor_input"
    if enabled(page.get_by_role("button", name=re.compile(r"^Begin"))):
        return "begin"
    return "processing"


def wait_ready(base_url: str, timeout_seconds: int = 90) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/health/ready", timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.2)
    raise TimeoutError("isolated live-provider app did not become ready")


def wait_stable(page, timeout_seconds: int = 180) -> str:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        current = state(page)
        if current != "processing" and not visible(page.locator("[data-operation-poll]")):
            return current
        page.wait_for_timeout(500)
    raise TimeoutError(f"participant UI did not settle within {timeout_seconds}s")


def tutor_messages(page) -> list[str]:
    return page.locator(".message.tutor").evaluate_all(
        "nodes => nodes.map(n => [...n.childNodes].filter(x => x.nodeType === Node.TEXT_NODE).map(x => x.textContent).join('').trim())"
    )


def intended_answer(section: int, activity: int) -> tuple[str, str]:
    if section == 1 and activity == 1:
        return "intentionally_incorrect", INCORRECT_ASSESSMENT_RESPONSES[1]
    if section == 2 and activity in (1, 2):
        return "intentionally_incorrect", INCORRECT_ASSESSMENT_RESPONSES[2]
    return "intended_passing", PASSING_ASSESSMENT_RESPONSES[section]


def type_participant_text(field, value: str) -> None:
    field.click()
    field.press_sequentially(value, delay=8)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default="postgresql+psycopg://solo_test:solo_test@127.0.0.1:55432/solo_test")
    parser.add_argument("--output-root", type=Path, default=ROOT / "reports/live-reconstruction")
    parser.add_argument("--max-manual-retries", type=int, default=3)
    args = parser.parse_args()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    root = (args.output_root / f"run-{run_id}").resolve()
    research_data, artifacts = root / "research-data", root / "playwright"
    research_data.mkdir(parents=True)
    artifacts.mkdir()
    participant_id = f"PLAYWRIGHT-LIVE-{run_id}"
    trace = {"run_id": run_id, "participant_id": participant_id, "sections": [], "actions": [], "manual_retries": [], "completed": False}
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    app = None

    environment = os.environ.copy()
    environment.update({
        "DATABASE_URL": args.database_url,
        "STUDY_DIR": str(STUDY),
        "RESEARCH_DATA_DIR": str(research_data),
        "REQUIRE_ACTIVE_CAPTURE": "false",
        "APP_BUILD_ID": "live-switching-reconstruction-e2e",
    })

    def action(page, label: str, locator):
        started = datetime.now(timezone.utc).isoformat()
        locator.click()
        resulting = wait_stable(page)
        trace["actions"].append({"action": label, "clicked_at_utc": started, "resulting_state": resulting})
        return resulting

    try:
        with (artifacts / "app.log").open("w", encoding="utf-8") as app_log:
            app = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "solo_harness.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
                cwd=ROOT, env=environment, stdout=app_log, stderr=subprocess.STDOUT,
            )
            wait_ready(base_url)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.goto(f"{base_url}/join", wait_until="networkidle")
                page.get_by_label("University ID").fill(participant_id)
                page.get_by_role("checkbox").check()
                page.get_by_role("button", name="Continue").click()
                page.wait_for_url(re.compile(r".*/session$"))
                wait_stable(page)

                for section in range(1, 5):
                    page.get_by_role("heading", name=f"Section {section}").wait_for()
                    activity = 1
                    record = {"section": section, "activities": []}
                    current = state(page)
                    while current != "section_complete":
                        activity_record = {"activity": activity, "tutor_messages_before": [], "tutor_messages_after": []}
                        if current == "begin":
                            current = action(page, f"section_{section}_activity_{activity}_begin", page.get_by_role("button", name=re.compile(r"^Begin")))
                            activity_record["tutor_messages_before"] = tutor_messages(page)
                        while current == "tutor_input":
                            learner_response = TUTOR_RESPONSES[section]
                            type_participant_text(page.locator('textarea[name="learner_text"]'), learner_response)
                            activity_record.setdefault("tutor_responses", []).append(learner_response)
                            current = action(page, f"section_{section}_activity_{activity}_tutor_submit", page.get_by_role("button", name="Send"))
                            activity_record["tutor_messages_after"] = tutor_messages(page)
                        if current == "assessment":
                            prompt = page.locator(".assessment-prompt").inner_text()
                            answer_kind, answer = intended_answer(section, activity)
                            activity_record.update({"assessment_prompt": prompt, "assessment_answer_kind": answer_kind, "assessment_answer": answer})
                            type_participant_text(page.locator('textarea[name="response_text"]'), answer)
                            current = action(page, f"section_{section}_activity_{activity}_assessment", page.get_by_role("button", name="Submit assessment"))
                            record["activities"].append(activity_record)
                            if current == "begin":
                                activity += 1
                                if activity > 3:
                                    raise AssertionError("a fourth teaching activity was exposed")
                            continue
                        if current == "retry":
                            if len(trace["manual_retries"]) >= args.max_manual_retries:
                                raise AssertionError("manual retry cap reached")
                            trace["manual_retries"].append({"section": section, "activity": activity})
                            current = action(page, f"section_{section}_activity_{activity}_manual_retry", page.get_by_role("button", name="Retry"))
                            continue
                        if current not in ("tutor_input", "assessment", "section_complete"):
                            current = wait_stable(page)

                    page.get_by_text("Section completed", exact=True).wait_for()
                    page.screenshot(path=str(artifacts / f"section_{section}_complete.png"), full_page=True)
                    trace["sections"].append(record)
                    if section < 4:
                        current = action(page, f"section_{section}_next", page.get_by_role("button", name="Next section"))
                        if current != "begin":
                            raise AssertionError(f"next section did not open at begin state: {current}")
                    else:
                        current = action(page, "finish_study", page.get_by_role("button", name="Finish study"))
                        if current != "finished":
                            raise AssertionError(f"study did not finish: {current}")

                page.screenshot(path=str(artifacts / "study_complete.png"), full_page=True)
                page.wait_for_timeout(6500)  # allow telemetry batchers to persist their final events
                browser.close()
                trace["completed"] = True
        (artifacts / "expected_execution.json").write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")

        factory = sessionmaker(create_engine(args.database_url), expire_on_commit=False)
        with factory() as db:
            session = db.scalar(select(Session).where(Session.institutional_id == participant_id))
            if session is None:
                raise RuntimeError("live participant session was not persisted")
            session_id = session.id
        export_path = root / "session_export.json"
        write_session_export(args.database_url, session_id, export_path, research_data_root=research_data)
        report_dir = root / "reconstruction"
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/research/reconstruct_session.py"), "--export", str(export_path), "--research-data", str(research_data), "--output", str(report_dir), "--expected", str(artifacts / "expected_execution.json"), "--include-content"],
            cwd=ROOT, capture_output=True, text=True,
        )
        (artifacts / "reconstruction_console.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"reconstruction failed: {result.stdout}{result.stderr}")
        summary = {"run_id": run_id, "session_id": str(session_id), "output": str(root), "reconstruction": json.loads(result.stdout)}
        (root / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        (artifacts / "expected_execution.json").write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
        if app and app.poll() is None:
            app.terminate()
            try:
                app.wait(timeout=20)
            except subprocess.TimeoutExpired:
                app.kill()


if __name__ == "__main__":
    raise SystemExit(main())
