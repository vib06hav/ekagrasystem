"""Run the controlled C1 V3.1 live protocol through the participant routes.

This is deliberately an HTTP client, rather than a database driver: every Tutor
message and continuation goes through the same browser-session endpoints used by
the participant UI.  It leaves an incremental action log so an interrupted run
can be audited and resumed from its exported session data.
"""
from __future__ import annotations

import json
import re
import sys
import time
import uuid
from pathlib import Path

import httpx


BASE_URL = "http://127.0.0.1:8016"
TOKEN = "controlled-c11-browser-test"
ROOT = Path("EKAGRAAI_FULL_C1_V3_1_FINAL_COMPLETE_TRACES")
SUBSECTIONS = ("C1.1", "C1.2", "C1.3", "C1.4")

CHALLENGES = {
    "P1": {
        "C1.1": ("Why does the order of the bits matter, rather than only the number of 1s?", "I think 110 and 101 mean the same thing because they each contain two 1s."),
        "C1.2": ("Why cannot a receiver simply compare what arrived with the sender's original?", "The receiver normally has the clean sent copy too, so it can compare directly."),
        "C1.3": ("Why add a parity bit instead of just choosing any extra bit?", "p is a literal character sent with the data, and its value can be chosen randomly."),
        "C1.4": ("Does an even-parity pass prove that the data was not corrupted?", "Even parity always adds 0, because the rule says even."),
    },
    "P2": {
        "C1.1": ("Why do we need the Yes/No mapping before we can work with a bit sequence?", "The single bit 1 has several bits, while 110 has only one."),
        "C1.2": ("Why is the received sequence not enough by itself to reveal the original message?", "Position 2 changed between 10110 and 10010."),
        "C1.3": ("Why is the added checking position separate from the original data?", "The payload is p and 10110 is the extra checking bit."),
        "C1.4": ("Why must we count the full frame rather than only the original data?", "For even parity we should add 0 to 10110."),
    },
    "P3": {
        "C1.1": ("Why can two bit strings with the same number of 1s still represent different information?", "101 and 110 must mean the same thing because both have two 1s."),
        "C1.2": ("Why does comparing an intact and changed transmission matter for the receiver?", "A receiver can normally see both the clean sent 10110 and the changed 10010."),
        "C1.3": ("Why does the parity value need to depend on the data rather than on the channel?", "The parity bit can be random because the receiver already knows what was sent."),
        "C1.4": ("Why does a parity check distinguish a failed rule from a guaranteed error-free message?", "If a frame passes even parity, that guarantees there was no error and also locates any error."),
    },
}

# P2 has compulsory guided moves after its designated wrong answer.  These are
# normal learner answers needed to complete the authored workflow, not the 24
# designated doubt/misconception challenges above.
P2_FOLLOWUP_ANSWERS = {
    "C1.1": ["110", "2"],
    "C1.2": ["The receiver normally has the received sequence, 10010."],
    "C1.3": ["It could not reliably check the data, because the extra bit must be based on that data.", "The sender and receiver could disagree about whether the frame passes."],
    "C1.4": ["0", "It fails because 100101 has three 1s, including the last bit."],
}
MOVE_COUNTS = {"P1": 4, "P2": 5, "P3": 4}


class LiveRun:
    def __init__(self, pedagogy: str):
        self.pedagogy = pedagogy
        self.out = ROOT / pedagogy
        (self.out / "automation").mkdir(parents=True, exist_ok=True)
        self.actions: list[dict] = []
        self.retried_call_states: set[tuple[str | None, int]] = set()
        self.client = httpx.Client(base_url=BASE_URL, timeout=30.0, follow_redirects=False)

    def record(self, label: str, response: httpx.Response | None = None, **extra):
        item = {"at_unix": time.time(), "label": label, **extra}
        if response is not None:
            item.update({"status": response.status_code, "path": response.request.url.path})
        self.actions.append(item)
        (self.out / "automation" / "actions.json").write_text(json.dumps(self.actions, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def state(html: str) -> dict:
        approval = re.search(r'name="approval_version" value="(\d+)"', html)
        subsection = re.search(r'data-active-subsection-id="([^"]*)"', html)
        return {
            "approval_version": int(approval.group(1)) if approval else None,
            "subsection": subsection.group(1) if subsection else None,
            "needs_learner": '<textarea id="learner-text"' in html,
            "pending": '<div data-operation-poll' in html,
            "retryable": '<div class="action-card" data-generation-error>' in html,
            "technical_hold": '<div class="action-card" data-technical-hold>' in html,
            "paas_pending": '<section class="paas-screen" data-paas-screen' in html,
            "tutor_messages": len(re.findall(r'data-tutor-message-sequence=', html)),
        }

    def page(self) -> tuple[httpx.Response, dict]:
        response = self.client.get("/session")
        if response.status_code != 200:
            raise RuntimeError(f"session page returned {response.status_code}")
        return response, self.state(response.text)

    def wait_for(self, label: str, predicate, timeout: float = 180.0) -> dict:
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            response, last = self.page()
            if last["retryable"]:
                retry_key = (last["subsection"], last["tutor_messages"])
                if retry_key in self.retried_call_states:
                    raise RuntimeError(f"operation remained retryable after its one automatic retry: {last}")
                self.retried_call_states.add(retry_key)
                retry = self.client.post("/session/actions/retry", data={"idempotency_key": str(uuid.uuid4())})
                self.record("automatic_retry", retry, state=last)
            elif last["technical_hold"]:
                raise RuntimeError("technical hold requires researcher-only requeue")
            elif predicate(last):
                self.record(label, response, state=last)
                return last
            time.sleep(1)
        raise TimeoutError(f"timed out waiting for {label}; last={last}")

    def post(self, label: str, path: str, data: dict) -> None:
        response = self.client.post(path, data=data)
        self.record(label, response, payload={k: v for k, v in data.items() if k != "idempotency_key"})
        # A duplicate/stale request is only acceptable if the prior operation
        # has already reached the state the caller is about to wait for.
        if response.status_code not in (200, 303, 409):
            raise RuntimeError(f"{label} returned HTTP {response.status_code}: {response.text[:500]}")

    def begin(self) -> None:
        response = self.client.post("/internal/v051/session", headers={
            "X-Ekagra-Internal-Test-Token": TOKEN,
            "X-Ekagra-Internal-Pedagogy": self.pedagogy,
            "X-Ekagra-Internal-Full-C1": "true",
        })
        self.record("create_internal_full_c1_session", response)
        if response.status_code != 303:
            raise RuntimeError(f"create session failed: {response.status_code} {response.text[:500]}")
        open_path = response.headers.get("X-Ekagra-Internal-Open-Path")
        if not open_path:
            raise RuntimeError("session creation omitted browser handoff")
        opened = self.client.get(open_path)
        self.record("claim_browser_handoff", opened)
        if opened.status_code != 303:
            raise RuntimeError(f"handoff failed: {opened.status_code}")
        self.post("begin", "/session/actions/begin", {"idempotency_key": str(uuid.uuid4())})
        self.wait_for("initial_move_ready", lambda s: s["approval_version"] is not None and s["subsection"] == "C1.1")

    def learner(self, label: str, text: str, subsection: str) -> None:
        self.post(label, "/session/actions/tutor-message", {"learner_text": text, "idempotency_key": str(uuid.uuid4())})
        self.wait_for(label + "_processed", lambda s: s["approval_version"] is not None and s["subsection"] == subsection)

    def next_move(self, label: str, final: bool = False) -> dict:
        _, current = self.page()
        if current["approval_version"] is None:
            raise RuntimeError(f"{label}: continuation unavailable: {current}")
        self.post(label, "/session/actions/c11-next", {"approval_version": str(current["approval_version"]), "idempotency_key": str(uuid.uuid4())})
        if final:
            return self.wait_for(label + "_assessment_handoff", lambda s: s["paas_pending"])
        return self.wait_for(label + "_settled", lambda s: s["approval_version"] is not None or s["needs_learner"])

    def run_subsection(self, subsection: str, is_last: bool) -> None:
        doubt, incorrect = CHALLENGES[self.pedagogy][subsection]
        self.learner(f"challenge_{subsection}_doubt", doubt, subsection)
        if self.pedagogy != "P2":
            self.learner(f"challenge_{subsection}_incorrect", incorrect, subsection)
        else:
            # M01 is explanatory. M02 is the first authored guided question,
            # where the required misconception is supplied as an actual answer.
            state = self.next_move(f"next_{subsection}_to_guided_m02")
            if not state["needs_learner"]:
                raise RuntimeError(f"{subsection}: expected P2 guided M02, got {state}")
            self.learner(f"challenge_{subsection}_incorrect_guided_m02", incorrect, subsection)

        followups = list(P2_FOLLOWUP_ANSWERS.get(subsection, [])) if self.pedagogy == "P2" else []
        # P1/P3 are still on M01 after their two challenges.  P2 deliberately
        # consumed M01 to reach its required wrong guided answer on M02.
        moves_completed = 1 if self.pedagogy == "P2" else 0
        while True:
            _, state = self.page()
            if state["approval_version"] is None:
                if state["needs_learner"] and followups:
                    self.learner(f"guided_followup_{subsection}_{len(P2_FOLLOWUP_ANSWERS[subsection]) - len(followups) + 1}", followups.pop(0), subsection)
                    continue
                raise RuntimeError(f"{subsection}: no approved continuation and no scripted guided response: {state}")
            # The assessment handoff is valid only after the final authored
            # move, not after C1.4's first approved response.
            if is_last and moves_completed == MOVE_COUNTS[self.pedagogy] - 1:
                self.next_move(f"next_{subsection}_assessment_handoff", final=True)
                if followups:
                    raise RuntimeError(f"{subsection}: unused guided responses {followups}")
                return
            state = self.next_move(f"next_{subsection}")
            moves_completed += 1
            if state["subsection"] != subsection:
                if followups:
                    raise RuntimeError(f"{subsection}: advanced with unused guided responses {followups}")
                self.record(f"subsection_{subsection}_complete", state=state)
                return

    def run(self) -> None:
        self.begin()
        for index, subsection in enumerate(SUBSECTIONS):
            self.run_subsection(subsection, is_last=index == len(SUBSECTIONS) - 1)
        self.record("pedagogy_complete")


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    for pedagogy in ("P1", "P2", "P3"):
        run = LiveRun(pedagogy)
        try:
            run.run()
        except Exception as exc:
            run.record("fatal", error=repr(exc))
            raise
        finally:
            run.client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
