"""Read-only reconstruction of one exported session and its file artifacts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FIELDS = [
    "event_id", "source", "source_record_id", "session_id", "capture_run_id",
    "browser_run_id", "section_number", "transition_id", "teaching_activity_number",
    "attempt_id", "event_type", "description", "original_timestamp", "source_clock",
    "normalized_utc", "relative_elapsed_ms", "ordering_basis", "alignment_method",
    "uncertainty", "confidence",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value) / 1000, timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, OSError, OverflowError):
        return None


def compact_time(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


def read_ndjson(path: Path, errors: list[str]) -> list[tuple[int, dict[str, Any]]]:
    rows = []
    try:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError("row is not an object")
                rows.append((number, item))
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"{path}:{number}: {exc}")
    except OSError as exc:
        errors.append(f"{path}: {exc}")
    return rows


class Reconstruction:
    def __init__(self, export: dict[str, Any], artifact_root: Path, include_content: bool = False):
        self.export = export
        self.data = export["data"]
        self.session = self.data["session"]
        self.session_id = str(export.get("session_id") or self.session["id"])
        self.capture_run_id = self.session.get("capture_run_id")
        self.artifact_root = artifact_root.resolve()
        self.include_content = include_content
        self.events: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.checks: list[tuple[str, str, str]] = []
        self.keyboard_rows: list[dict[str, Any]] = []
        self.media_summary: list[dict[str, Any]] = []
        self.attempts = {str(row["id"]): row for row in self.data.get("attempts", [])}
        transitions = self.data.get("study_version", {}).get("compiled_snapshot", {}).get("protocol", {}).get("transition_ids", ["C1", "C2", "C3", "C4"])
        self.section_by_transition = {item: index + 1 for index, item in enumerate(transitions)}
        self.anchor = utc(self.session.get("started_at")) or utc(self.session.get("created_at"))

    def context(self, attempt_id: Any) -> tuple[Any, Any, Any]:
        attempt = self.attempts.get(str(attempt_id)) if attempt_id else None
        if not attempt:
            return None, None, None
        transition = attempt.get("transition_id")
        return self.section_by_transition.get(transition), transition, attempt.get("sequence_in_transition")

    def add(self, *, source: str, locator: str, event_type: str, timestamp: Any = None,
            source_clock: str = "server_utc", attempt_id: Any = None,
            browser_run_id: Any = None, section: Any = None, transition: Any = None,
            activity: Any = None, description: str = "", ordering: str = "timestamp",
            alignment: str = "direct", uncertainty: str = "source clock not independently calibrated",
            confidence: str = "direct") -> None:
        inferred_section, inferred_transition, inferred_activity = self.context(attempt_id)
        instant = utc(timestamp)
        elapsed = round((instant - self.anchor).total_seconds() * 1000, 3) if instant and self.anchor else None
        self.events.append({
            "event_id": str(uuid.uuid4()), "source": source, "source_record_id": locator,
            "session_id": self.session_id, "capture_run_id": self.capture_run_id,
            "browser_run_id": str(browser_run_id) if browser_run_id else None,
            "section_number": section if section is not None else inferred_section,
            "transition_id": transition if transition is not None else inferred_transition,
            "teaching_activity_number": activity if activity is not None else inferred_activity,
            "attempt_id": str(attempt_id) if attempt_id else None, "event_type": event_type,
            "description": description, "original_timestamp": timestamp,
            "source_clock": source_clock, "normalized_utc": compact_time(instant),
            "relative_elapsed_ms": elapsed, "ordering_basis": ordering,
            "alignment_method": alignment, "uncertainty": uncertainty, "confidence": confidence,
        })

    def content(self, label: str, value: str | None) -> str:
        value = value or ""
        if self.include_content:
            return f"{label}: {value}"
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return f"{label}: [redacted; chars={len(value)}; sha256={digest}]"

    def relational(self) -> None:
        for row in self.data.get("protocol_events", []):
            self.add(source="protocol", locator=f"protocol_events:{row['id']}", event_type=row["event_type"],
                     timestamp=row.get("occurred_at"), attempt_id=row.get("attempt_id"),
                     description=json.dumps(row.get("payload", {}), sort_keys=True),
                     ordering=f"protocol sequence {row['sequence_no']}", confidence="direct")
        for row in self.data.get("messages", []):
            self.add(source="db", locator=f"messages:{row['id']}", event_type=f"{row['role']}_MESSAGE_PERSISTED",
                     timestamp=row.get("created_at"), attempt_id=row.get("attempt_id"),
                     description=self.content(row["role"].title(), row.get("content_text")),
                     ordering=f"message sequence {row['sequence_no']}")
        for row in self.data.get("assessment_responses", []):
            instance = next((item for item in self.data.get("assessment_instances", []) if str(item["id"]) == str(row["assessment_instance_id"])), None)
            self.add(source="db", locator=f"assessment_responses:{row['id']}", event_type="ASSESSMENT_RESPONSE_PERSISTED",
                     timestamp=row.get("submitted_at"), attempt_id=instance.get("attempt_id") if instance else None,
                     description=self.content("Assessment response", row.get("response_text")))
        for row in self.data.get("llm_calls", []):
            retry = f"{row.get('purpose')} retry {row.get('retry_number')} ({row.get('status')})"
            self.add(source="llm", locator=f"llm_calls:{row['id']}:start", event_type="LLM_CALL_STARTED",
                     timestamp=row.get("started_at"), attempt_id=row.get("attempt_id"), description=retry,
                     ordering="call started_at and retry_number")
            if row.get("completed_at"):
                self.add(source="llm", locator=f"llm_calls:{row['id']}:complete", event_type="LLM_CALL_COMPLETED",
                         timestamp=row["completed_at"], attempt_id=row.get("attempt_id"),
                         description=f"{retry}; latency_ms={row.get('latency_ms')}", ordering="call completed_at")
        for row in self.data.get("rubric_evaluations", []):
            self.add(source="db", locator=f"rubric_evaluations:{row['id']}", event_type="RUBRIC_DECISION_PERSISTED",
                     timestamp=row.get("created_at"), attempt_id=row.get("attempt_id"),
                     description=f"passed={row.get('passed')}; reasons={row.get('decision_reasons')}")
        for row in self.data.get("participant_ui_events", []):
            self.add(source="ui", locator=f"participant_ui_events:{row['id']}", event_type=row["event_type"],
                     timestamp=row.get("client_event_at"), source_clock="browser Date.now",
                     attempt_id=row.get("attempt_id"), browser_run_id=row.get("browser_run_id"),
                     section=row.get("section_number"), activity=row.get("teaching_activity_number"),
                     description=f"surface={row.get('surface')}; server_received={row.get('server_received_at')}",
                     ordering=f"browser client sequence {row.get('client_sequence')}",
                     uncertainty="browser wall clock uncalibrated; delivery is best effort")

    def browser(self) -> None:
        base = self.artifact_root / self.session_id / "browser"
        manifest = base / "manifest.json"
        if not manifest.is_file():
            self.warnings.append("Browser manifest is absent")
            return
        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
            runs = document.get("runs", [])
            self.checks.append(("browser manifest parses", "PASS", f"runs={len(runs)}"))
        except (OSError, json.JSONDecodeError) as exc:
            self.errors.append(f"Browser manifest unreadable: {exc}")
            return
        for folder, kind in (("rrweb", "rrweb"), ("keyboard", "keyboard")):
            directory = base / folder
            files = sorted(directory.glob("*.ndjson")) if directory.is_dir() else []
            if not files:
                self.warnings.append(f"No {kind} NDJSON file")
            for path in files:
                previous = 0
                for number, row in read_ndjson(path, self.errors):
                    run = row.get("browser_run_id") or path.stem
                    sequence = row.get("sequence") if kind == "rrweb" else row.get("client_sequence")
                    if isinstance(sequence, int) and sequence != previous + 1:
                        self.warnings.append(f"{path.name}: sequence jump {previous}->{sequence}")
                    if isinstance(sequence, int): previous = sequence
                    if kind == "rrweb":
                        inner = row.get("rrweb_event", {})
                        self.add(source="rrweb", locator=f"{path.relative_to(self.artifact_root)}:{number}",
                                 event_type=f"RRWEB_TYPE_{inner.get('type')}", timestamp=inner.get("timestamp") or row.get("client_emit_utc_ms"),
                                 source_clock="rrweb/browser Date.now", browser_run_id=run,
                                 description=f"rrweb sequence={sequence}", ordering=f"rrweb sequence {sequence}",
                                 uncertainty="browser wall clock uncalibrated; batches may be missing")
                    else:
                        self.keyboard_rows.append(row)
                        self.add(source="keyboard", locator=f"{path.relative_to(self.artifact_root)}:{number}",
                                 event_type=row.get("event_type", "KEYBOARD_EVENT"), timestamp=row.get("client_event_at_utc_ms"),
                                 source_clock="browser Date.now + performance.now", browser_run_id=run,
                                 section=row.get("section_number"), activity=row.get("teaching_activity_number"),
                                 description=f"surface={row.get('surface')}; class={row.get('key_class')}; press_id={row.get('press_id')}",
                                 ordering=f"keyboard client sequence {sequence}",
                                 uncertainty="precise within run; browser wall clock uncalibrated")

    def capture(self) -> None:
        if not self.capture_run_id:
            self.warnings.append("Session has no capture_run_id")
            return
        base = self.artifact_root / "capture-runs" / str(self.capture_run_id)
        manifest = base / "capture_manifest.json"
        if not manifest.is_file():
            self.errors.append(f"Capture manifest absent: {manifest}")
            return
        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.errors.append(f"Capture manifest unreadable: {exc}")
            return
        self.checks.append(("capture id matches session", "PASS" if document.get("capture_run_id") == str(self.capture_run_id) else "FAIL", str(document.get("capture_run_id"))))
        self.checks.append(("capture manifest completed", "PASS" if document.get("status") == "COMPLETED" else "FAIL", str(document.get("status"))))
        checksum = base / "capture_manifest.sha256"
        expected = checksum.read_text(encoding="utf-8").split()[0] if checksum.is_file() else None
        self.checks.append(("capture manifest checksum", "PASS" if expected == sha256(manifest) else "FAIL", f"expected={expected}; actual={sha256(manifest)}"))
        for name, stream in document.get("streams", {}).items():
            media = base / name / str(stream.get("media"))
            actual = sha256(media) if media.is_file() else None
            self.checks.append((f"{name} media hash", "PASS" if actual and actual == stream.get("sha256") else "FAIL", f"bytes={media.stat().st_size if media.is_file() else 0}"))
            metadata = ((stream.get("ffprobe") or {}).get("metadata") or {})
            videos = [item for item in metadata.get("streams", []) if item.get("codec_type") == "video"]
            self.media_summary.append({"stream": name, "duration": metadata.get("format", {}).get("duration"), "video": videos[0] if videos else {}})
            self.checks.append((f"{name} FFprobe video", "PASS" if videos else "FAIL", f"duration={metadata.get('format', {}).get('duration')}; streams={len(videos)}"))
            event_path = base / name / str(stream.get("capture_events", "capture_events.ndjson"))
            for number, row in read_ndjson(event_path, self.errors):
                self.add(source="recorder", locator=f"{event_path.relative_to(self.artifact_root)}:{number}",
                         event_type=f"{name.upper()}_{row.get('event_type')}", timestamp=row.get("observed_at_utc"),
                         source_clock="recorder host UTC + perf_counter_ns", description=f"monotonic_ns={row.get('monotonic_ns')}",
                         ordering="recorder monotonic_ns", alignment="host-wall-clock estimate",
                         uncertainty="FFmpeg observation is not identical to captured frame time")

    def integrity(self) -> None:
        protocol = self.data.get("protocol_events", [])
        sequences = [row.get("sequence_no") for row in protocol]
        expected = list(range(1, len(sequences) + 1))
        self.checks.append(("protocol sequence contiguous", "PASS" if sequences == expected else "FAIL", f"events={len(sequences)}"))
        attempt_rows = self.data.get("attempts", [])
        pairs = [(row.get("transition_id"), row.get("sequence_in_transition")) for row in attempt_rows]
        pedagogy = [(row.get("transition_id"), row.get("pedagogy_id")) for row in attempt_rows]
        self.checks.append(("attempt sequence unique", "PASS" if len(pairs) == len(set(pairs)) else "FAIL", str(pairs)))
        self.checks.append(("pedagogy unique within transition", "PASS" if len(pedagogy) == len(set(pedagogy)) else "FAIL", str(pedagogy)))
        forms = [row.get("assessment_form_id") for row in self.data.get("assessment_instances", [])]
        self.checks.append(("assessment forms session-unique", "PASS" if len(forms) == len(set(forms)) else "FAIL", f"forms={len(forms)}"))
        for row in self.data.get("rubric_evaluations", []):
            if str(row.get("attempt_id")) not in self.attempts:
                self.errors.append(f"Rubric evaluation {row.get('id')} references unknown attempt")

    def run(self) -> None:
        self.relational(); self.browser(); self.capture(); self.integrity()
        self.events.sort(key=lambda item: (item["normalized_utc"] is None, item["normalized_utc"] or "", item["source"], item["source_record_id"]))


def markdown_table(rows: list[tuple[str, str, str]]) -> str:
    lines = ["| Check | Result | Detail |", "|---|---|---|"]
    lines.extend(f"| {a} | **{b}** | {c.replace('|', '/')} |" for a, b, c in rows)
    return "\n".join(lines)


def write_outputs(result: Reconstruction, output: Path, expected_path: Path | None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with (output / "study_timeline.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader(); writer.writerows(result.events)
    (output / "study_timeline.json").write_text(json.dumps({"schema_version": "1.0", "session_id": result.session_id, "events": result.events}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    attempts = result.data.get("attempts", [])
    calls = result.data.get("llm_calls", [])
    durations = []
    for row in calls:
        if row.get("latency_ms") is not None: durations.append(int(row["latency_ms"]))
    created, started, ended = (utc(result.session.get(name)) for name in ("created_at", "started_at", "ended_at"))
    overview = [
        "# Study reconstruction", "", f"- Session: `{result.session_id}`",
        f"- Capture run: `{result.capture_run_id or 'not associated'}`",
        f"- Status: `{result.session.get('status')}` / `{result.session.get('terminal_reason')}`",
        f"- Attempts: {len(attempts)}", f"- Timeline events: {len(result.events)}",
        f"- LLM calls: {len(calls)}; retries: {sum(int(row.get('retry_number', 0)) > 0 for row in calls)}",
        f"- Median successful provider latency: {statistics.median(durations) if durations else 'unavailable'} ms",
        f"- Creation-to-begin: {round((started-created).total_seconds(), 3) if created and started else 'unavailable'} seconds",
        f"- Full study elapsed: {round((ended-started).total_seconds(), 3) if started and ended else 'unavailable'} seconds", "",
        "## Attempts", "", "| Section | Transition | Activity | Pedagogy | Result | Completion |", "|---:|---|---:|---|---|---|",
    ]
    for row in attempts:
        overview.append(f"| {result.section_by_transition.get(row['transition_id'])} | {row['transition_id']} | {row['sequence_in_transition']} | {row['pedagogy_id']} | {'PASS' if row.get('passed') else 'FAIL' if row.get('passed') is False else 'INCOMPLETE'} | {row.get('completion_reason')} |")
    overview += ["", "## Supported durations", "", "| Measurement | Duration | Evidence / limitation |", "|---|---:|---|"]
    for row in attempts:
        assigned, completed_at = utc(row.get("assigned_at")), utc(row.get("completed_at"))
        duration = round((completed_at-assigned).total_seconds(), 3) if assigned and completed_at else None
        overview.append(f"| Section {result.section_by_transition.get(row['transition_id'])} activity {row['sequence_in_transition']} | {duration if duration is not None else 'unavailable'} s | Server timestamps; activity lifecycle, not attention |")
    for row in calls:
        if row.get("completed_at"):
            call_start, call_end = utc(row.get("started_at")), utc(row.get("completed_at"))
            value = round((call_end-call_start).total_seconds(), 3) if call_start and call_end else None
            overview.append(f"| {row.get('purpose')} call `{row.get('id')}` application duration | {value if value is not None else 'unavailable'} s | Start-to-completion; provider latency column={row.get('latency_ms')} ms |")
    downs: dict[tuple[str, Any], float] = {}
    dwells: list[float] = []
    keydowns: list[float] = []
    for row in sorted(result.keyboard_rows, key=lambda item: (str(item.get("browser_run_id")), item.get("client_sequence", 0))):
        key = (str(row.get("browser_run_id")), row.get("press_id"))
        perf = row.get("client_performance_ms")
        if not isinstance(perf, (int, float)): continue
        if row.get("event_type") == "KEYDOWN" and not row.get("flags", {}).get("repeat"):
            downs[key] = float(perf); keydowns.append(float(perf))
        elif row.get("event_type") == "KEYUP" and key in downs:
            dwells.append(float(perf) - downs.pop(key))
    flights = [later-earlier for earlier, later in zip(keydowns, keydowns[1:]) if later >= earlier]
    pauses = [value for value in flights if value >= 500]
    overview += [
        f"| Keyboard median dwell | {round(statistics.median(dwells), 3) if dwells else 'unavailable'} ms | Paired press IDs within browser run |",
        f"| Keyboard median keydown flight | {round(statistics.median(flights), 3) if flights else 'unavailable'} ms | Consecutive keydowns; boundaries between fields are included |",
        f"| Keyboard pauses / derived bursts | {len(pauses)} / {len(pauses)+1 if keydowns else 0} | Pause threshold 500 ms; analytic convention, not cognition |",
    ]
    for media in result.media_summary:
        video = media["video"]
        overview.append(f"| {media['stream']} media | {media['duration']} s | FFprobe; {video.get('codec_name')} {video.get('width')}x{video.get('height')} at {video.get('avg_frame_rate')} |")
    overview += ["", "## Evidence policy", "", "Participant text is redacted by default; timeline descriptions retain length and SHA-256 for comparison. Render telemetry proves DOM state, not attention."]
    (output / "study_reconstruction.md").write_text("\n".join(overview) + "\n", encoding="utf-8")

    integrity = ["# Data integrity report", "", markdown_table(result.checks), "", "## Errors", ""]
    integrity += [f"- {item}" for item in result.errors] or ["- None"]
    integrity += ["", "## Warnings", ""] + ([f"- {item}" for item in result.warnings] or ["- None"])
    (output / "data_integrity_report.md").write_text("\n".join(integrity) + "\n", encoding="utf-8")

    alignment = """# Time alignment report

- PostgreSQL/protocol/LLM timestamps are normalized from their stored offsets to UTC.
- Browser UI, rrweb, and keyboard wall times are normalized from `Date.now`; `performance.now` and `performance.timeOrigin` preserve precise within-run ordering.
- Recorder observations use Windows host UTC plus `perf_counter_ns`; FFmpeg progress and media PTS remain stream-local evidence.
- Browser and recorder ran on the same Windows host for the recorded procedure, but no explicit clock calibration or protocol synchronization marker exists.
- Natural landmarks (Begin, Send, Submit, Next, Finish and resulting screen mutations) support approximate visual alignment only.
- Process start, first FFmpeg progress, and first encoded/captured frame are not treated as identical.

Therefore sequence and within-source durations are direct; browser/server/recorder correspondence is approximate and frame-level accuracy is unavailable.
"""
    (output / "time_alignment_report.md").write_text(alignment, encoding="utf-8")

    comparison = ["# Expected versus reconstructed", ""]
    if expected_path and expected_path.is_file():
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        comparison += [f"- Playwright completed: `{expected.get('completed')}`", f"- Playwright actions: {len(expected.get('actions', []))}", f"- Reconstructed attempts: {len(attempts)}", f"- Reconstructed final status: `{result.session.get('status')}`", "", "## Action evidence", ""]
        protocol_types = {row.get("event_type") for row in result.data.get("protocol_events", [])}
        for action in expected.get("actions", []):
            kind = action.get("action", "")
            required = "SESSION_CREATED" if kind == "join" else "SESSION_COMPLETED" if kind == "finish_study" else "PARTICIPANT_ADVANCED_SECTION" if kind.endswith("_next") else "ASSESSMENT_SUBMITTED" if kind.endswith("_assessment") else "LLM_CALL_STARTED"
            comparison.append(f"- `{kind}`: {'exact/semantic match' if required in protocol_types else 'missing expected protocol evidence'} ({required})")
        comparison += ["", "## Content and outcome comparison", ""]
        messages_by_attempt = {}
        for row in result.data.get("messages", []): messages_by_attempt.setdefault(str(row["attempt_id"]), []).append(row)
        instances = {str(row["attempt_id"]): row for row in result.data.get("assessment_instances", [])}
        responses = {str(row["assessment_instance_id"]): row for row in result.data.get("assessment_responses", [])}
        ordered_attempts = sorted(attempts, key=lambda row: (result.section_by_transition.get(row["transition_id"], 99), row["sequence_in_transition"]))
        expected_sections = expected.get("sections", [])
        comparison.append(f"- Section count: {'exact match' if len(expected_sections) == len({row['transition_id'] for row in attempts}) else 'DISCREPANCY'}")
        for item, attempt in zip(expected_sections, ordered_attempts):
            messages = sorted(messages_by_attempt.get(str(attempt["id"]), []), key=lambda row: row["sequence_no"])
            learners = [row["content_text"] for row in messages if row["role"] == "LEARNER"]
            tutors = [row["content_text"] for row in messages if row["role"] == "TUTOR"]
            instance = instances.get(str(attempt["id"]), {})
            response = responses.get(str(instance.get("id")), {})
            checks = [
                ("learner response", "EXACT" if learners == [item.get("learner_response")] else "DISCREPANCY"),
                ("Tutor display sequence", "EXACT" if item.get("tutor_messages") and tutors == item.get("tutor_messages") else "DISCREPANCY" if item.get("tutor_messages") else "NOT IN INDEPENDENT TRACE"),
                ("assessment prompt", "EXACT" if instance.get("prompt_snapshot") == item.get("assessment_prompt") else "DISCREPANCY"),
                ("assessment response", "EXACT" if response.get("response_text") == item.get("assessment_response") else "DISCREPANCY"),
                ("rubric result", "EXACT" if attempt.get("passed") is True else "DISCREPANCY"),
            ]
            comparison.append(f"- Section {item.get('section')}: " + "; ".join(f"{name}={status}" for name, status in checks))
        required_ui = {"SESSION_PAGE_RENDERED", "SECTION_RENDERED", "TEACHING_ACTIVITY_RENDERED", "BEGIN_CLICKED", "PROCESSING_SHOWN", "PROCESSING_HIDDEN", "TUTOR_MESSAGE_RENDERED", "TUTOR_RESPONSE_SUBMIT_CLICKED", "ASSESSMENT_RENDERED", "ASSESSMENT_RESPONSE_SUBMIT_CLICKED", "SECTION_COMPLETE_RENDERED", "NEXT_CLICKED", "FINISH_CLICKED", "STUDY_COMPLETE_RENDERED"}
        observed_ui = {row.get("event_type") for row in result.data.get("participant_ui_events", [])}
        comparison.append(f"- Semantic UI lifecycle: {'EXACT expected set present' if required_ui <= observed_ui else 'MISSING ' + str(sorted(required_ui-observed_ui))}")
        comparison.append(f"- Capture association: {'EXACT' if result.capture_run_id else 'MISSING'}")
        comparison += ["", "Realized pedagogy assignments are intentionally hidden from Playwright and are compared as persisted internal-only evidence, not copied into the independent action log."]
    else:
        comparison.append("No independent Playwright trace was supplied.")
    (output / "reconstruction_comparison.md").write_text("\n".join(comparison) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--research-data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--include-content", action="store_true", help="Researcher-access mode: include response text")
    args = parser.parse_args()
    export = json.loads(args.export.read_text(encoding="utf-8"))
    result = Reconstruction(export, args.research_data, args.include_content)
    result.run(); write_outputs(result, args.output, args.expected)
    print(json.dumps({"session_id": result.session_id, "events": len(result.events), "errors": len(result.errors), "warnings": len(result.warnings), "output": str(args.output.resolve())}, sort_keys=True))
    return 1 if result.errors or any(status == "FAIL" for _, status, _ in result.checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
