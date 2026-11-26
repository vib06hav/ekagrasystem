"""Run the approved synthetic-DEV C3 Phase 2 scenarios through the HTTP runtime."""
from __future__ import annotations

import argparse
import re
import time
import uuid
from pathlib import Path

import httpx


def wait_for_page(client: httpx.Client, *, timeout: int = 240) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        page = client.get("/session").text
        if "<div data-operation-poll" not in page:
            return page
        time.sleep(1)
    raise TimeoutError("operation did not complete")


def post_and_wait(client: httpx.Client, path: str, data: dict[str, str]) -> str:
    response = client.post(path, data=data)
    response.raise_for_status()
    return wait_for_page(client)


def next_move(client: httpx.Client, page: str) -> str:
    match = re.search(r'name="approval_version" value="(\d+)"', page)
    if not match:
        raise RuntimeError("expected approved learner-controlled Next action")
    return post_and_wait(client, "/session/actions/c11-next", {
        "approval_version": match.group(1), "idempotency_key": str(uuid.uuid4()),
    })


def learner_turn(client: httpx.Client, text: str) -> str:
    return post_and_wait(client, "/session/actions/tutor-message", {
        "learner_text": text, "idempotency_key": str(uuid.uuid4()),
    })


def main(base_url: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    with httpx.Client(base_url=base_url, follow_redirects=True, timeout=300) as client:
        master = client.get("/internal/master")
        master.raise_for_status()
        csrf = re.search(r'name="csrf" value="([^"]+)"', master.text)
        if not csrf:
            raise RuntimeError("development Master Console CSRF token not found")
        launch = client.post("/internal/master/launch", data={
            "section": "C3", "pedagogy": "P2", "mode": "teaching", "assessment_set": "random",
            "csrf": csrf.group(1),
        })
        launch.raise_for_status()
        page = client.get("/session").text

        def start_or_reply(text: str | None = None) -> str:
            if text is None:
                return post_and_wait(client, "/session/actions/begin", {"idempotency_key": str(uuid.uuid4())})
            return learner_turn(client, text)

        # C3.1 M01 and M02: explicit-answer paths, then C3.1 M03 full hint path.
        page = start_or_reply()
        page = start_or_reply("Please tell me the answer.")
        page = next_move(client, page)
        page = start_or_reply("Please tell me the answer.")
        page = next_move(client, page)
        page = start_or_reply("Every check passes.")                 # Hint 1
        page = start_or_reply("Why does row 1 pass with two changes?")  # ordinary doubt; no hint consumed
        page = start_or_reply("Every check still passes.")           # Hint 2
        page = start_or_reply("I do not know.")                       # FINAL + Judge
        page = next_move(client, page)

        # C3.1 M04 provides a correct-first-attempt path; M05 is expedited.
        page = start_or_reply("Column 1 passes.")
        page = next_move(client, page)
        page = start_or_reply("Please tell me the answer.")
        page = next_move(client, page)

        # C3.2 M01 expedited, then M02 full incorrect/hint/final path.
        page = start_or_reply("Please tell me the answer.")
        page = next_move(client, page)
        page = start_or_reply("The bits changed randomly everywhere.")
        page = start_or_reply("I still think every row fails.")
        page = start_or_reply("I am not sure.")

        latest = client.get("/internal/master")
        latest.raise_for_status()
        trace = re.search(r'/internal/master/trace/([0-9a-f-]{36})', latest.text)
        if not trace:
            raise RuntimeError("synthetic DEV trace link not found")
        trace_response = client.get(trace.group(0))
        trace_response.raise_for_status()
        (output / "live_session_trace.zip").write_bytes(trace_response.content)
        (output / "session_id.txt").write_text(trace.group(1) + "\n", encoding="utf-8")
        (output / "README.txt").write_text(
            "Synthetic DEV session, executed through the running HTTP application with configured Tutor and Judge models.\n"
            "Scenarios: C3.1 P2 M03 wrong→H1→doubt→wrong→H2→unsure→FINAL; "
            "C3.2 P2 M02 wrong→H1→wrong→H2→unsure→FINAL; correct-first C3.1 P2 M04; explicit-answer requests.\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    args = parser.parse_args()
    main(args.base_url, args.output)
