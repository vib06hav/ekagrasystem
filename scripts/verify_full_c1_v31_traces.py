"""Derive readable trace files and verify the completed live C1 V3.1 run."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("EKAGRAAI_FULL_C1_V3_1_FINAL_COMPLETE_TRACES")
PEDAGOGIES = ("P1", "P2", "P3")
MOVE_TOTALS = {"P1": 16, "P2": 20, "P3": 16}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_designated_challenge(label: str) -> bool:
    return label.startswith("challenge_") and (
        label.endswith("_doubt") or label.endswith("_incorrect") or label.endswith("_incorrect_guided_m02")
    )


def main() -> None:
    reports = []
    total_moves = total_doubts = total_incorrect = total_handoffs = 0
    for pedagogy in PEDAGOGIES:
        base = ROOT / pedagogy
        document = load(base / "raw" / "session_export.json")
        data = document["data"]
        actions = load(base / "automation" / "actions.json")
        raw = base / "raw"
        dump(raw / "transcript.json", data["messages"])
        dump(raw / "llm_calls.json", data["llm_calls"])
        dump(raw / "events.json", data["protocol_events"])
        dump(raw / "decisions.json", {"judgments": data["judgments"], "rubric_evaluations": data["rubric_evaluations"]})

        events = data["protocol_events"]
        moves = [event["payload"]["move_id"] for event in events if event["event_type"] == "CONTROLLED_C11_MOVE_APPROVED"]
        handoffs = [event for event in events if event["event_type"] == "CONTROLLED_C1_ASSESSMENT_HANDOFF"]
        challenges = [action for action in actions if is_designated_challenge(action["label"])]
        doubts = [action for action in challenges if action["label"].endswith("_doubt")]
        incorrect = [action for action in challenges if "_incorrect" in action["label"]]
        processed = {action["label"].removesuffix("_processed") for action in actions if action["label"].endswith("_processed") and action.get("status") == 200}
        missing_processed = [action["label"] for action in challenges if action["label"] not in processed]
        failures = [call for call in data["llm_calls"] if call["status"] != "SUCCEEDED"]

        assert len(moves) == MOVE_TOTALS[pedagogy], (pedagogy, moves)
        assert len(challenges) == 8 and len(doubts) == len(incorrect) == 4, (pedagogy, challenges)
        assert not missing_processed, (pedagogy, missing_processed)
        assert len(handoffs) == 1, (pedagogy, handoffs)
        assert not failures, (pedagogy, failures)
        assert actions[-1]["label"] == "pedagogy_complete", pedagogy

        reports.append({
            "pedagogy": pedagogy,
            "session_id": document["session_id"],
            "moves_approved": len(moves),
            "move_ids": moves,
            "designated_doubts": len(doubts),
            "designated_incorrect_answers": len(incorrect),
            "assessment_handoffs": len(handoffs),
            "learner_messages": sum(message["role"] == "LEARNER" for message in data["messages"]),
            "llm_calls": len(data["llm_calls"]),
            "failed_llm_calls": len(failures),
            "export_sha256": document["data_sha256"],
        })
        total_moves += len(moves); total_doubts += len(doubts); total_incorrect += len(incorrect); total_handoffs += len(handoffs)

    assert (total_moves, total_doubts, total_incorrect, total_handoffs) == (52, 12, 12, 3)
    report = {"verified": True, "totals": {"moves": total_moves, "doubts": total_doubts, "incorrect_answers": total_incorrect, "assessment_handoffs": total_handoffs}, "pedagogies": reports}
    dump(ROOT / "coverage_report.json", report)
    lines = ["# Verified C1 V3.1 coverage", "", "| Requirement | Saved-trace result |", "| --- | ---: |", "| Instructional moves | 52 / 52 |", "| Conceptual doubts | 12 / 12 |", "| Incorrect answers | 12 / 12 |", "| Assessment handoffs | 3 / 3 |", "", "All counts were derived from the three `session_export.json` files, their normal-route action logs, and persisted protocol events. The P2 designated incorrect answer in each subsection was submitted at guided M02; corrective guided responses remain separately visible in P2's verbatim transcript.", ""]
    for item in reports:
        lines.append(f"- {item['pedagogy']}: {item['moves_approved']} moves, {item['designated_doubts']} doubts, {item['designated_incorrect_answers']} incorrect answers, {item['assessment_handoffs']} handoff; session `{item['session_id']}`; {item['llm_calls']} successful LLM calls.")
    (ROOT / "COVERAGE_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
