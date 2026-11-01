"""Focused browser verification: Tutor -> Paas -> frozen C1 assessment.

The participant-visible development advance is intentionally hidden. This
development verifier uses the same signed browser session to POST that already
enabled endpoint after a real Tutor exchange, then resumes visible Playwright
interaction for Paas and assessment rendering.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research-data" / "paas-evidence" / "playwright-c1-trace.json"


def main() -> None:
    trace: list[dict] = []
    learner = f"paas-playwright-{uuid.uuid4().hex[:12]}"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        try:
            page.goto("http://127.0.0.1:8000/join", wait_until="domcontentloaded")
            page.locator("#participant-code").fill(learner)
            page.locator("input[name='acknowledged']").check()
            page.get_by_role("button", name="Continue").click()
            page.locator("#session-main").wait_for(state="visible")

            page.get_by_role("button", name="Begin study").click()
            page.locator("#learner-text").wait_for(state="visible", timeout=300_000)
            before = page.locator("[data-tutor-message-sequence]").count()
            page.locator("#learner-text").fill(
                "I understand that the sender sets the parity check bit and the receiver counts every bit to test the frame."
            )
            page.locator("#tutor-composer button.send").click()
            page.locator("[data-tutor-message-sequence]").nth(before).wait_for(state="visible", timeout=300_000)
            trace.append({"event": "real_tutor_exchange", "tutor_messages": page.locator("[data-tutor-message-sequence]").count()})

            # The control is purposefully absent from the participant DOM. This
            # same-origin request uses its Playwright browser session/cookie.
            key = str(uuid.uuid4())
            result = page.evaluate(
                """async ({key}) => {
                  const body = new FormData(); body.set('idempotency_key', key);
                  const response = await fetch('/session/actions/development-advance', {method:'POST', body});
                  return {status: response.status, html: await response.text()};
                }""",
                {"key": key},
            )
            if result["status"] != 200:
                raise RuntimeError(f"development end-of-teaching request failed: {result['status']}")
            page.goto("http://127.0.0.1:8000/session", wait_until="domcontentloaded")
            page.locator("[data-paas-screen]").wait_for(state="visible", timeout=60_000)
            choices = page.locator("[data-paas-screen] input[name='rating']")
            assert choices.count() == 9
            trace.append({"event": "paas_visible", "choice_count": choices.count()})
            choices.nth(4).check()
            page.get_by_role("button", name="Continue to assessment").click()
            trace.append({"event": "paas_submitted", "rating": 5})

            page.locator("section.assessment h2").filter(has_text="Answer all four questions").wait_for(
                state="visible", timeout=600_000
            )
            mcqs = page.locator("fieldset.mcq").count()
            subjective = page.locator("#assessment-response").count() == 1
            if mcqs != 3 or not subjective:
                raise AssertionError(f"unexpected frozen assessment: mcqs={mcqs}, subjective={subjective}")
            trace.append({"event": "frozen_assessment_visible", "mcqs": mcqs, "subjective": subjective})
        finally:
            context.close()
            browser.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"learner": learner, "trace": trace}, indent=2), encoding="utf-8")
    print(json.dumps({"learner": learner, "trace": trace}))


if __name__ == "__main__":
    main()
