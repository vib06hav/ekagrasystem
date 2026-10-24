"""A genuine Chromium/Jinja/HTMX journey through all four transitions."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import re
import uuid
from pathlib import Path

import pytest

from solo_harness.config import get_settings
from solo_harness.main import create_app
from solo_harness.runtime.ai import AIExecutionRuntime, PreparedLLMRequest, RawLLMResponse
from solo_harness.runtime.engine import SessionRuntime
from solo_harness.studies.catalog import StudyCatalog

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="requires TEST_DATABASE_URL PostgreSQL")
STUDY = Path(__file__).parents[2] / "studies/python_fibonacci_memoization/v0.1"


def _port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class PassingStudyClient:
    def prepare(self, request):
        body = {"model": request.model, "messages": [message.model_dump() for message in request.messages]}
        return PreparedLLMRequest(request, body, json.dumps(body), {"Authorization": "Bearer [TEST]"})

    async def send(self, prepared):
        request = prepared.request; system = request.messages[0].content
        if request.logical_role == "TUTOR":
            opening = request.messages[-1].content.startswith("Begin with the current move")
            output = {"schema_version":"1.0", "learner_message":"Consider how the current program breaks its work into smaller cases. Explain the relationship you notice." if opening else "Good. Your explanation connects the smaller cases and stopping conditions, so we can move to an independent question.", "disposition":"CONTINUE" if opening else "COMPLETE", "current_move_id":request.audit_context["move_id"], "next_move_id":None, "progress_summary":"The learner described the scoped relationship and is ready for an independent response."}
        elif request.logical_role == "ASSESSMENT":
            output = {"schema_version":"1.0", "learner_prompt":"In a new recursive-programming situation, explain how the computation uses smaller cases, reaches its stopping conditions, and avoids unnecessary repeated work where relevant.", "hidden_scoring_context":"Evaluate the response against only the supplied scoped evidence criteria and misconception definitions."}
        else:
            scoped = json.loads(re.search(r"\[SCOPED_EVALUATION_COMPONENTS\]\n(.*?)\n\n\[OUTPUT_RULES\]", system, re.S).group(1)); answer = request.messages[-1].content; rubric = scoped["rubric"]
            output = {"schema_version":"1.0", "not_gradable_reason":None, "correctness":"CORRECT", "observed_solo_state_id":rubric["target_state_id"], "criterion_evidence":[{"criterion_id":item,"status":"DEMONSTRATED","citations":[{"excerpt":answer}],"concise_summary":"The response demonstrates this criterion."} for item in rubric["evidence_ids"]], "misconception_evidence":[{"misconception_id":item,"status":"NOT_DETECTED","citations":[],"concise_summary":"The response does not endorse this misconception."} for item in rubric["blocking_misconception_ids"]], "confidence":1.0, "ambiguity_summary":None, "overall_evidence_summary":"The response demonstrates all scoped evidence required for this transition."}
        text = json.dumps(output); payload = {"choices":[{"message":{"content":text},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":10,"total_tokens":20}}
        return RawLLMResponse("e2e-test",200,json.dumps(payload),payload,text,"stop",False,payload["usage"],1)


class MalformedTutorOnceClient(PassingStudyClient):
    def __init__(self):
        self.failed = False

    async def send(self, prepared):
        if prepared.request.logical_role == "TUTOR" and not self.failed:
            self.failed = True
            payload = {"choices":[{"message":{"content":"not-json"},"finish_reason":"stop"}],"usage":{}}
            return RawLLMResponse("e2e-malformed",200,json.dumps(payload),payload,"not-json","stop",False,{},1)
        return await super().send(prepared)


def _start_server(client, research_data_dir=None):
    import uvicorn
    settings = get_settings()
    settings.database_url = URL
    settings.study_dir = STUDY
    settings.require_active_capture = False
    if research_data_dir is not None:
        settings.research_data_dir = research_data_dir
    app = create_app(execution=AIExecutionRuntime(SessionRuntime(StudyCatalog()), client, settings))
    port = _port(); server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True); thread.start()
    deadline = time.time() + 60
    while not server.started and time.time() < deadline: time.sleep(0.05)
    assert server.started
    return server, thread, port


def _create_session():
    institutional_id = f"test-{uuid.uuid4()}"
    return {"institutional_id": institutional_id}


def test_complete_study_in_real_browser():
    playwright = pytest.importorskip("playwright.sync_api")
    server, thread, port = _start_server(PassingStudyClient())
    session = _create_session()
    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{port}/join")
            page.get_by_label("University ID").fill(session["institutional_id"]); page.locator('input[name="acknowledged"]').check()
            page.get_by_role("button", name="Continue").click()
            assert "/session" in page.url and session["institutional_id"] not in page.url
            for transition in range(4):
                page.get_by_role("button", name="Begin").click()
                page.get_by_label("Your response").wait_for(timeout=15000)
                assert page.locator(".message.tutor").count() == 1
                page.get_by_label("Your response").fill("The smaller recursive cases combine, stopping conditions terminate the recursion, and saved results avoid repeated work.")
                page.get_by_role("button", name="Send").click()
                page.get_by_role("heading", name="Respond in your own words").wait_for(timeout=15000)
                assert page.locator('form[action="/session/actions/tutor-message"]').count() == 0
                page.get_by_label("Your response").fill("The computation combines the two smaller predecessor cases, stops at its defined base cases, and reuses cached results so overlapping calls are not recomputed.")
                page.get_by_role("button", name="Submit assessment").click()
                page.get_by_text("Section completed", exact=True).wait_for(timeout=15000)
                if transition == 3:
                    page.get_by_role("button", name="Finish study").click()
                    page.get_by_role("heading", name="Thank you").wait_for(timeout=15000)
                else:
                    page.get_by_role("button", name="Next section").click()
                    page.get_by_role("heading", name=f"Section {transition + 2}").wait_for(timeout=15000)
            html = page.content()
            for hidden in ("pedagogy_id", "candidate_form_ids", "hidden_scoring_context", "observed_solo_state_id", "compiled_prompt_text", "raw_response_text", "openai/gpt-5-nano", "google/gemini-3.5-flash-lite"):
                assert hidden not in html
            browser.close()
    finally:
        server.should_exit = True; thread.join(timeout=10)


def test_malformed_tutor_requires_visible_participant_retry():
    playwright = pytest.importorskip("playwright.sync_api")
    server, thread, port = _start_server(MalformedTutorOnceClient())
    session = _create_session()
    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch(headless=True); page = browser.new_page()
            page.goto(f"http://127.0.0.1:{port}/join")
            page.get_by_label("University ID").fill(session["institutional_id"]); page.locator('input[name="acknowledged"]').check(); page.get_by_role("button", name="Continue").click()
            page.get_by_role("button", name="Begin").click()
            page.get_by_role("heading", name="That step could not be completed").wait_for(timeout=15000)
            retry = page.get_by_role("button", name="Retry"); assert retry.is_enabled(); retry.click()
            page.get_by_label("Your response").wait_for(timeout=15000)
            assert page.locator(".message.tutor").count() == 1
            browser.close()
    finally:
        server.should_exit = True; thread.join(timeout=10)


def test_rrweb_masks_typed_sentinel_and_uses_local_asset(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    server, thread, port = _start_server(PassingStudyClient(), tmp_path)
    session = _create_session(); requests = []
    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch(headless=True); page = browser.new_page()
            page.on("request", lambda request: requests.append(request.url))
            page.goto(f"http://127.0.0.1:{port}/join")
            page.get_by_label("University ID").fill(session["institutional_id"]); page.locator('input[name="acknowledged"]').check(); page.get_by_role("button", name="Continue").click()
            page.get_by_role("button", name="Begin").click(); page.get_by_label("Your response").wait_for(timeout=15000)
            sentinel = "TELEMETRY_PLAINTEXT_SENTINEL_7f9e"
            page.get_by_label("Your response").fill(sentinel); page.wait_for_timeout(6000)
            artifact = next((next(tmp_path.iterdir()) / "browser" / "rrweb").glob("*.ndjson"))
            assert sentinel not in artifact.read_text(encoding="utf-8")
            page.get_by_role("button", name="Send").click()
            page.get_by_role("heading", name="Respond in your own words").wait_for(timeout=15000)
            page.wait_for_timeout(6000)
            assert sentinel not in artifact.read_text(encoding="utf-8")
            assert any(url == f"http://127.0.0.1:{port}/static/vendor/rrweb/2.1.7/record.umd.min.cjs" for url in requests)
            assert not any("rrweb" in url and "/static/vendor/rrweb/" not in url and "/session/telemetry/rrweb" not in url for url in requests)
            browser.close()
    finally:
        server.should_exit = True; thread.join(timeout=10)


def test_keyboard_artifact_is_field_scoped_paired_and_private(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    server, thread, port = _start_server(PassingStudyClient(), tmp_path)
    session = _create_session()
    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch(headless=True); page = browser.new_page()
            page.goto(f"http://127.0.0.1:{port}/join")
            page.get_by_label("University ID").fill(session["institutional_id"]); page.locator('input[name="acknowledged"]').check(); page.get_by_role("button", name="Continue").click()
            page.get_by_role("button", name="Begin").click(); response = page.get_by_label("Your response"); response.wait_for(timeout=15000)
            tutor_secret = "KEYBOARD_PRIVATE_SENTINEL_84C12"
            response.press_sequentially(tutor_secret); response.press("Backspace"); response.press("Shift+KeyA")
            page.wait_for_timeout(6000); page.get_by_role("button", name="Send").click()
            page.get_by_role("heading", name="Respond in your own words").wait_for(timeout=15000)
            assessment = page.locator("#assessment-response"); assessment.wait_for(timeout=15000)
            assessment_secret = "KEYBOARD_PRIVATE_SENTINEL_B41D8"
            assessment.press_sequentially(assessment_secret); assessment.press("Enter"); page.wait_for_timeout(6000)
            keyboard = next((next(tmp_path.iterdir()) / "browser" / "keyboard").glob("*.ndjson"))
            rows = [json.loads(line) for line in keyboard.read_text(encoding="utf-8").splitlines()]
            assert {row["event_type"] for row in rows} == {"KEYDOWN", "KEYUP"}
            assert {row["surface"] for row in rows} == {"TUTOR_RESPONSE", "ASSESSMENT_RESPONSE"}
            assert all(set(row).isdisjoint({"key", "code", "value"}) for row in rows)
            assert tutor_secret not in keyboard.read_text(encoding="utf-8") and assessment_secret not in keyboard.read_text(encoding="utf-8")
            down = {row["press_id"] for row in rows if row["event_type"] == "KEYDOWN"}
            up = {row["press_id"] for row in rows if row["event_type"] == "KEYUP"}
            assert up <= down and all(row["client_performance_ms"] >= 0 for row in rows)
            browser.close()
    finally:
        server.should_exit = True; thread.join(timeout=10)


def test_fallback_reload_and_telemetry_failure_do_not_block_study(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    server, thread, port = _start_server(PassingStudyClient(), tmp_path)
    session = _create_session()
    try:
        with playwright.sync_playwright() as api:
            browser = api.chromium.launch(headless=True); page = browser.new_page()
            page.route("https://unpkg.com/htmx.org@2.0.4", lambda route: route.fulfill(content_type="application/javascript", body="window.htmx=undefined;"))
            page.route("**/session/telemetry/keyboard", lambda route: route.abort())
            page.goto(f"http://127.0.0.1:{port}/join")
            page.get_by_label("University ID").fill(session["institutional_id"]); page.locator('input[name="acknowledged"]').check(); page.get_by_role("button", name="Continue").click()
            page.get_by_role("button", name="Begin").click(); response = page.locator("#learner-text"); response.wait_for(timeout=15000)
            response.press_sequentially("telemetry failure must not block submission")
            page.get_by_role("button", name="Send").click()
            page.get_by_role("heading", name="Respond in your own words").wait_for(timeout=15000)
            page.unroute("**/session/telemetry/keyboard")
            page.reload(); page.locator("#assessment-response").wait_for(timeout=15000)
            page.locator("#assessment-response").press_sequentially("run two"); page.wait_for_timeout(6000)
            browser_dir = next(tmp_path.iterdir()) / "browser"
            assert len(list((browser_dir / "rrweb").glob("*.ndjson"))) >= 2
            assert len(list((browser_dir / "keyboard").glob("*.ndjson"))) >= 1
            browser.close()
    finally:
        server.should_exit = True; thread.join(timeout=10)
