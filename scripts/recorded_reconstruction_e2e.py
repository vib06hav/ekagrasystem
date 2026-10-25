"""Run one headed deterministic study with real Windows webcam/screen capture."""
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from solo_harness.config import get_settings
from solo_harness.db.models import Session
from solo_harness.main import create_app
from solo_harness.research_export import write_session_export
from solo_harness.runtime.ai import AIExecutionRuntime, PreparedLLMRequest, RawLLMResponse
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.studies.catalog import StudyCatalog

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/python_fibonacci_memoization/v0.1"


class DeterministicClient:
    def prepare(self, request):
        body = {"model": request.model, "messages": [message.model_dump() for message in request.messages]}
        return PreparedLLMRequest(request, body, json.dumps(body), {"Authorization": "Bearer [DETERMINISTIC-TEST]"})

    async def send(self, prepared):
        request = prepared.request
        system = request.messages[0].content
        if request.logical_role == "TUTOR":
            opening = request.messages[-1].content.startswith("Begin with the current move")
            output = {
                "schema_version": "1.0",
                "learner_message": "Inspect how the program relates smaller recursive cases, stopping conditions, and reuse. Explain the relationship you observe." if opening else "Your explanation connects the required ideas. Continue to the independent assessment.",
                "disposition": "CONTINUE" if opening else "COMPLETE",
                "current_move_id": request.audit_context["move_id"],
                "next_move_id": None,
                "progress_summary": "The deterministic participant response addressed the scoped relationship.",
            }
        elif request.logical_role == "ASSESSMENT":
            output = {
                "schema_version": "1.0",
                "learner_prompt": "In this new recursive Fibonacci situation, explain the smaller-case relationship, stopping conditions, and how one shared cache prevents repeated expansion where relevant.",
                "hidden_scoring_context": "Use only the supplied scoped rubric and evidence identifiers.",
            }
        else:
            scoped = json.loads(re.search(r"\[SCOPED_EVALUATION_COMPONENTS\]\n(.*?)\n\n\[OUTPUT_RULES\]", system, re.S).group(1))
            answer = request.messages[-1].content
            rubric = scoped["rubric"]
            output = {
                "schema_version": "1.0", "not_gradable_reason": None, "correctness": "CORRECT",
                "observed_solo_state_id": rubric["target_state_id"],
                "criterion_evidence": [{"criterion_id": item, "status": "DEMONSTRATED", "citations": [{"excerpt": answer}], "concise_summary": "The response demonstrates the scoped criterion."} for item in rubric["evidence_ids"]],
                "misconception_evidence": [{"misconception_id": item, "status": "NOT_DETECTED", "citations": [], "concise_summary": "The response does not assert this misconception."} for item in rubric["blocking_misconception_ids"]],
                "confidence": 1.0, "ambiguity_summary": None,
                "overall_evidence_summary": "All scoped evidence required for this transition is demonstrated.",
            }
        text = json.dumps(output)
        payload = {"choices": [{"message": {"content": text}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 20, "completion_tokens": 20, "total_tokens": 40}}
        return RawLLMResponse("recorded-e2e", 200, json.dumps(payload), payload, text, "stop", False, payload["usage"], 2)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_file(path: Path, timeout: float, predicate=lambda _: True):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if predicate(value): return value
            except (OSError, json.JSONDecodeError):
                pass
        time.sleep(0.2)
    raise TimeoutError(f"timed out waiting for {path}")


def wait_progress(root: Path, capture_id: str, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    pending = {"webcam", "screen"}
    while pending and time.monotonic() < deadline:
        for stream in list(pending):
            path = root / "capture-runs" / capture_id / stream / "capture_events.ndjson"
            if path.is_file() and "FIRST_PROGRESS_OBSERVED" in path.read_text(encoding="utf-8", errors="replace"):
                pending.remove(stream)
        time.sleep(0.2)
    if pending:
        raise TimeoutError(f"no first FFmpeg progress for: {sorted(pending)}")


def stop_recorder(process: subprocess.Popen, timeout: float = 90) -> None:
    if process.poll() is not None:
        return
    process.send_signal(signal.CTRL_BREAK_EVENT)
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill(); process.wait(timeout=10)
        raise RuntimeError("recorder did not finalize after CTRL_BREAK_EVENT")


def type_with_dynamics(field, text: str) -> None:
    first, second = text[: len(text) // 2], text[len(text) // 2 :]
    field.press_sequentially(first, delay=18)
    time.sleep(0.24)
    field.press_sequentially(second + "x", delay=12)
    field.press("Backspace")
    field.press("Shift+Digit1")


def action(trace: dict, name: str, locator, wait_for) -> None:
    before = datetime.now(timezone.utc).isoformat()
    locator.click()
    wait_for()
    trace["actions"].append({"action": name, "clicked_at_utc": before, "observed_at_utc": datetime.now(timezone.utc).isoformat()})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default="postgresql+psycopg://solo_test:solo_test@127.0.0.1:55432/solo_test")
    parser.add_argument("--output-root", type=Path, default=ROOT / "reports/reconstruction")
    parser.add_argument("--headless", action="store_true", help="Debug only; recorded validation should remain headed")
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    staging = args.output_root.resolve() / f"run-{run_id}"
    research_data = staging / "research-data"
    artifacts = staging / "playwright"
    staging.mkdir(parents=True); research_data.mkdir(); artifacts.mkdir()
    expected_path = artifacts / "expected_execution.json"
    recorder_log = artifacts / "recorder_console.log"
    preflight_path = artifacts / "recorder_preflight.json"
    participant_id = f"PLAYWRIGHT-RECORDED-{run_id}"
    trace = {"schema_version": "1.0", "run_id": run_id, "participant_id": participant_id, "actions": [], "sections": [], "completed": False}
    recorder = None; server = None; thread = None; browser = None; session_id = None; capture_id = None
    log_queue: queue.Queue[str] = queue.Queue()
    try:
        preflight = subprocess.run([sys.executable, str(ROOT / "tools/windows_capture/record.py"), "preflight"], cwd=ROOT, capture_output=True, text=True, check=True)
        preflight_path.write_text(preflight.stdout, encoding="utf-8")

        settings = get_settings()
        settings.database_url = args.database_url
        settings.study_dir = STUDY
        settings.research_data_dir = research_data
        settings.require_active_capture = True
        settings.app_build_id = "recorded-reconstruction-e2e"
        execution = AIExecutionRuntime(SessionRuntime(StudyCatalog()), DeterministicClient(), settings)
        app = create_app(execution=execution)
        import uvicorn
        port = free_port(); server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        thread = threading.Thread(target=server.run, daemon=True); thread.start()
        deadline = time.monotonic() + 60
        while not server.started and time.monotonic() < deadline: time.sleep(0.1)
        if not server.started: raise RuntimeError("isolated application did not become ready")

        command = [sys.executable, "-u", str(ROOT / "tools/windows_capture/record.py"), "record", "--research-data", str(research_data)]
        recorder = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        def drain():
            assert recorder and recorder.stdout
            with recorder_log.open("w", encoding="utf-8") as handle:
                for line in recorder.stdout:
                    handle.write(line); handle.flush(); log_queue.put(line.rstrip())
        threading.Thread(target=drain, daemon=True).start()
        marker = wait_file(research_data / "active_capture.json", 45, lambda item: item.get("status") == "RECORDING")
        capture_id = marker["capture_run_id"]
        wait_progress(research_data, capture_id)

        with sync_playwright() as api:
            browser = api.chromium.launch(headless=args.headless)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"http://127.0.0.1:{port}/join", wait_until="networkidle")
            page.get_by_label("University ID").fill(participant_id)
            page.get_by_role("checkbox").check()
            action(trace, "join", page.get_by_role("button", name="Continue"), lambda: page.wait_for_url(re.compile(r".*/session$")))
            tutor_text = "The recursion combines smaller predecessor cases, reaches defined base cases, and a shared cache checks, reuses, and stores results to avoid repeated expansion"
            assessment_text = "The method preserves the two-predecessor recurrence and base cases. One shared mapping checks n before expansion, returns cached hits, and stores each newly computed n-to-result value for sibling calls"
            for section in range(1, 5):
                section_trace = {"section": section, "activity": 1}
                page.get_by_role("heading", name=f"Section {section}").wait_for()
                action(trace, f"section_{section}_activity_1_begin", page.get_by_role("button", name=re.compile(r"^Begin")), lambda: page.locator("#learner-text").wait_for(timeout=15000))
                tutor = page.locator("#learner-text"); type_with_dynamics(tutor, tutor_text)
                section_trace["learner_response"] = tutor.input_value()
                section_trace["opening_tutor_messages"] = page.locator(".message.tutor").evaluate_all("nodes => nodes.map(n => [...n.childNodes].filter(x => x.nodeType === Node.TEXT_NODE).map(x => x.textContent).join('').trim())")
                action(trace, f"section_{section}_activity_1_tutor_submit", page.get_by_role("button", name="Send"), lambda: page.locator("#assessment-response").wait_for(timeout=15000))
                prompt = page.locator(".assessment-prompt").inner_text(); section_trace["assessment_prompt"] = prompt
                assessment = page.locator("#assessment-response"); type_with_dynamics(assessment, assessment_text)
                section_trace["assessment_response"] = assessment.input_value()
                page.mouse.wheel(0, 500); page.wait_for_timeout(150); page.mouse.wheel(0, -500)
                action(trace, f"section_{section}_activity_1_assessment", page.get_by_role("button", name="Submit assessment"), lambda: page.get_by_text("Section completed", exact=True).wait_for(timeout=15000))
                section_trace["tutor_messages"] = page.locator(".message.tutor").evaluate_all("nodes => nodes.map(n => [...n.childNodes].filter(x => x.nodeType === Node.TEXT_NODE).map(x => x.textContent).join('').trim())")
                trace["sections"].append(section_trace)
                page.screenshot(path=str(artifacts / f"section_{section}_complete.png"), full_page=True)
                if section < 4:
                    action(trace, f"section_{section}_next", page.get_by_role("button", name="Next section"), lambda s=section: page.get_by_role("heading", name=f"Section {s + 1}").wait_for(timeout=15000))
                else:
                    action(trace, "finish_study", page.get_by_role("button", name="Finish study"), lambda: page.get_by_role("heading", name="Thank you").wait_for(timeout=15000))
            trace["completed"] = True
            page.screenshot(path=str(artifacts / "study_complete.png"), full_page=True)
            page.wait_for_timeout(6500)
            browser.close(); browser = None
        expected_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")

        factory = sessionmaker(create_engine(args.database_url), expire_on_commit=False)
        with factory() as db:
            session = db.scalar(select(Session).where(Session.institutional_id == participant_id))
            if not session: raise RuntimeError("recorded participant session was not persisted")
            session_id = session.id
            if str(session.capture_run_id) != str(capture_id):
                raise RuntimeError(f"capture association mismatch: session={session.capture_run_id} recorder={capture_id}")

        stop_recorder(recorder); recorder = None
        manifest_path = research_data / "capture-runs" / str(capture_id) / "capture_manifest.json"
        wait_file(manifest_path, 15, lambda item: item.get("status") == "COMPLETED")
        if (research_data / "active_capture.json").exists(): raise RuntimeError("active capture marker remained after recorder shutdown")

        export_path = staging / "session_export.json"
        write_session_export(args.database_url, session_id, export_path, research_data_root=research_data)
        report_dir = staging / "reconstruction"
        completed = subprocess.run([sys.executable, str(ROOT / "tools/research/reconstruct_session.py"), "--export", str(export_path), "--research-data", str(research_data), "--output", str(report_dir), "--expected", str(expected_path)], cwd=ROOT, text=True, capture_output=True)
        (artifacts / "reconstruction_console.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
        if completed.returncode: raise RuntimeError(f"reconstruction validation failed: {completed.stdout}{completed.stderr}")
        summary = {"run_id": run_id, "session_id": str(session_id), "capture_run_id": str(capture_id), "output": str(staging), "reconstruction": json.loads(completed.stdout)}
        (staging / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        expected_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
        if browser:
            try: browser.close()
            except Exception: pass
        if recorder:
            try: stop_recorder(recorder)
            except Exception as exc: print(f"recorder cleanup failed: {exc}", file=sys.stderr)
        if server:
            server.should_exit = True
        if thread:
            thread.join(timeout=15)


if __name__ == "__main__":
    raise SystemExit(main())
