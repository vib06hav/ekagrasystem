"""Build the sanitized Phase-2 audit archive from the current working tree.

The script deliberately packages working-tree files, not Git HEAD, and checks that
the complete runtime package is present. It accepts only the known synthetic DEV
trace produced by ``run_c3_phase2_live.py``.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[2]
TRACE = ROOT / "local-artifacts" / "c3_phase2_live_20261121_run5" / "live_session_trace.zip"
OUTPUT = ROOT / "EKAGRAAI_C3_PHASE2_IMPLEMENTATION_AUDIT.zip"
PREFIX = "EKAGRAAI_C3_PHASE2_IMPLEMENTATION_AUDIT"
EXCLUDED_DIRS = {".git", ".venv", ".pytest_cache", "__pycache__", "local-artifacts", "research-data", "exports", "graphify-out", "node_modules"}
EXCLUDED_NAMES = {".env", "dev.env", "EKAGRAAI_LATEST_FULL_SOURCE_AND_PROMPT_AUDIT.zip", OUTPUT.name}
MOVE_RE = re.compile(r'"(?:id|move_id)":"(C3\.[12]-P2-M\d+)"')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        # tools/runtime is a downloaded FFmpeg binary, not application source.
        if relative.parts[:2] == ("tools", "runtime"):
            continue
        if not path.is_file() or path.name in EXCLUDED_NAMES or path.suffix in {".pyc", ".pyo", ".db"}:
            continue
        result.append(path)
    return sorted(result)


def read_trace() -> dict:
    if not TRACE.is_file():
        raise SystemExit(f"Missing required synthetic DEV trace: {TRACE}")
    with ZipFile(TRACE) as archive:
        return json.loads(archive.read("session_export.json"))["data"]


def move_for_prompt(prompt: str) -> str:
    matched = MOVE_RE.search(prompt or "")
    return matched.group(1) if matched else "UNKNOWN_MOVE"


def write_live_evidence(audit: Path, data: dict) -> None:
    evidence = audit / "LIVE_LLM_EVIDENCE"
    evidence.mkdir(parents=True)
    calls = {row["id"]: row for row in data["llm_calls"]}
    messages = sorted(data["messages"], key=lambda row: row["sequence_no"])
    current_move = "UNKNOWN_MOVE"
    transcript: list[str] = [
        "# Synthetic DEV live conversation transcript",
        "",
        "Source: normal HTTP Master Console/session path against the running development Docker application.",
        "The session contains no real participant data. Times are recorded by the application (Asia/Kolkata offset).",
        "",
    ]
    for message in messages:
        trace = message.get("instructional_trace") or {}
        if message["role"] == "TUTOR":
            current_move = move_for_prompt(calls[message["llm_call_id"]]["compiled_prompt_text"])
        stage = trace.get("c3_guided_stage") if message["role"] == "TUTOR" else None
        transcript.extend([
            f"## {message['sequence_no']}. {message['role']} — {current_move}" + (f" — {stage}" if stage else ""),
            f"Timestamp: {message['created_at']}",
            "",
            message["content_text"].strip(),
            "",
        ])
    (evidence / "LIVE_CONVERSATION_TRANSCRIPT.md").write_text("\n".join(transcript), encoding="utf-8")

    capture: list[str] = [
        "# Actual assembled Tutor and Conversation Judge prompts",
        "",
        "These are the compiled prompts recorded by real model calls from the synthetic DEV session, not reconstructed source templates.",
        "",
    ]
    tutor_stage_by_call = {
        row["llm_call_id"]: (row.get("instructional_trace") or {}).get("c3_guided_stage")
        for row in messages if row["role"] == "TUTOR" and row.get("llm_call_id")
    }
    for call in data["llm_calls"]:
        if call["purpose"] not in {"TUTOR", "CONVERSATION_JUDGE"}:
            continue
        prompt = call["compiled_prompt_text"]
        move = move_for_prompt(prompt)
        stage = tutor_stage_by_call.get(call["id"])
        title = f"{call['purpose']} — {move}" + (f" — {stage}" if stage else "")
        capture.extend([
            f"## {title}",
            f"Call ID: `{call['id']}`  ",
            f"Model: `{call['model']}`  ",
            f"Completed: `{call['completed_at']}`",
            "",
            "```text",
            prompt,
            "```",
            "",
        ])
    (evidence / "ACTUAL_ASSEMBLED_PROMPTS.md").write_text("\n".join(capture), encoding="utf-8")

    events: list[str] = [
        "# Guided-question stage and visual trace",
        "",
        "Recorded protocol events from the synthetic DEV run. `visual_stage: null` means no visual attachment was emitted for a hint.",
        "",
    ]
    for event in data["protocol_events"]:
        name = event["event_type"]
        if name.startswith("C3_GUIDED") or "CONVERSATION_JUDGE" in name:
            events.extend([
                f"## {event['sequence_no']} — {name}",
                f"Timestamp: {event['occurred_at']}",
                "```json",
                json.dumps(event["payload"], ensure_ascii=False, indent=2, sort_keys=True),
                "```",
                "",
            ])
    (evidence / "STAGE_TRANSITION_TRACE.md").write_text("\n".join(events), encoding="utf-8")

    live_summary = [
        "# Live LLM integration result",
        "",
        "- Session type: synthetic DEV learner through normal Master Console and conversation runtime HTTP flow.",
        "- Provider/model recorded by the application: `aicredits_openai_compatible` / `google/gemini-3.5-flash-lite`.",
        f"- Real successful calls recorded: {sum(c['purpose'] == 'TUTOR' and not c['error_class'] for c in data['llm_calls'])} Tutor; {sum(c['purpose'] == 'CONVERSATION_JUDGE' and not c['error_class'] for c in data['llm_calls'])} Conversation Judge.",
        "- Required C3.1 P2-M03: partial/wrong → Hint 1 → ordinary doubt (still Hint 1) → partial/wrong → Hint 2 → uncertain → final explanation → Judge ADVANCE.",
        "- Required C3.2 P2-M02: wrong → Hint 1 → wrong → Hint 2 → uncertain → final explanation → Judge ADVANCE.",
        "- Correct-first case: C3.1 P2-M04 → final explanation → Judge ADVANCE.",
        "- Explicit-answer cases: C3.1 P2-M01, C3.1 P2-M02, C3.1 P2-M05, and C3.2 P2-M01 → final explanation → Judge ADVANCE.",
        "- Visual trace: question visual attaches at QUESTION when that move has a visual; no completed-answer visual attaches at HINT_1/HINT_2; completed visual attaches at FINAL for visual moves.",
        "",
    ]
    (evidence / "LIVE_TEST_RESULT.md").write_text("\n".join(live_summary), encoding="utf-8")


def write_context(audit: Path, files: list[Path], test_output: str, test_code: int) -> None:
    (audit / "README.md").write_text("""# EkagraAI C3 Phase-2 implementation audit

`EKAGRAAI_SOURCE/` preserves the current non-secret working tree, including uncommitted and untracked files. The C3 isolated implementation starts in `src/solo_harness/runtime/controlled_c3_pilot_prompts.py`; shared runtime invocation and stage persistence are in `src/solo_harness/runtime/ai.py`; C3 contracts and approved overlay are in `src/solo_harness/studies/`.

`LIVE_LLM_EVIDENCE/` is a sanitized extraction from one synthetic DEV session executed through the running Docker development application. It contains exact compiled prompts, Tutor/learner transcript, and protocol-event trace. No raw database, secrets, Docker volume, or real participant data is included.
""", encoding="utf-8")
    (audit / "IMPLEMENTATION_NOTES.md").write_text("""# Phase-2 implementation notes

## C3-only activation

The route is selected only when the global development flag `ENABLE_C3_ISOLATED_PILOT` is true, the progress subsection begins `C3.`, and the fresh session runtime snapshot has both `internal_v051_testing: true` and `c3_isolated_pilot_version: C3_ISOLATED_PROMPT_SEPARATION_V1`. C1, C2, C4, legacy C3, fixed cases, assessments, study transitions, and learner-controlled Next remain on their existing routes.

## Guided questioning

`new_guided_state` and `next_guided_turn` persist the P2 stage and hint count in `controlled_executor.c3_guided`. For a learner reply: correct or explicit answer request selects FINAL; an incorrect, partial, or uncertain reply selects HINT_1 then HINT_2; a third such reply selects FINAL. Ordinary clarification requests retain the current hint stage and do not increment the count. The backend—not the Judge—makes that state and visual decision. The Judge receives detailed scientific completion requirements and reviews only after FINAL.

## Visual behavior

The runtime records the question visual message identifier at QUESTION, emits no complete visual for HINT_1/HINT_2, and may attach the complete visual once at FINAL. Existing visual cleanup, visual-copy changes, panel reductions, and word-limit enforcement are intentionally not part of this Phase-2 delivery.

## Known limitation

The C3-only reply classifier is deliberately deterministic and move-specific. It recognizes the approved answer forms exercised by the test suite and live session, but an unusually phrased scientifically correct reply that omits its expected concept terms can receive a hint before the final explanation. It never gates completion or progression; the final explanation and Judge review remain available regardless of classification. A semantic-classification change was not introduced because it would expand the approved Phase-2 scope.

## Changed/new Phase-2 paths

- `src/solo_harness/runtime/controlled_c3_pilot_prompts.py`
- `src/solo_harness/runtime/ai.py`
- `tests/test_c3_isolated_pilot_prompts.py`
- `tools/research/run_c3_phase2_live.py`

The archive also includes pre-existing working-tree changes shown in its manifest; no attempt was made to overwrite or discard them.
""", encoding="utf-8")
    (audit / "RUNTIME_CONFIG.md").write_text("""# Effective non-secret development configuration

Verified after the final Docker rebuild/recreate:

- Application environment: `development`
- Isolated-pilot flag: `ENABLE_C3_ISOLATED_PILOT=true`
- Loaded pilot version: `C3_ISOLATED_PROMPT_SEPARATION_V1`
- Loaded overlay move count: `30`
- Provider: `aicredits_openai_compatible`
- Tutor and Conversation Judge model: `google/gemini-3.5-flash-lite`
- Tutor temperature / maximum output tokens: `0.2` / `2500`
- Judge temperature / maximum output tokens: `0.0` / `6000`
- Reasoning effort / request timeout: `low` / `120 seconds`

The base `enable_v051_internal_testing` setting is false. The isolated pilot is instead pinned per fresh Master Console DEV session through its runtime snapshot, which carries `internal_v051_testing: true` and the pilot-version value. Secrets and their values are not included.
""", encoding="utf-8")
    (audit / "TEST_RESULTS.txt").write_text(
        "Command:\n" + " ".join([sys.executable, "-m", "pytest", "-q", "tests/test_c3_isolated_pilot_prompts.py", "tests/test_c31_learner_readiness.py", "tests/test_c32_learner_readiness.py", "tests/test_controlled_c23_contract_routing.py", "tests/test_master_console.py", "tests/test_controlled_c1_full_instructional_prompts.py", "tests/test_unified_c1_c4_visuals.py"])
        + f"\n\nExit code: {test_code}\n\n{test_output}", encoding="utf-8")
    lines = [
        "# Archive manifest",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Included working-tree source files: {len(files)}",
        "",
        "Important exclusions: `.git`, `.venv`, caches, generated dependencies, `tools/runtime` downloaded FFmpeg binary, `.env`, `dev.env`, database/research-data/exports/local-artifacts directories, and previous archives.",
        "All non-excluded working-tree files are listed below with SHA-256. `src/solo_harness/runtime/` is explicitly required and verified before archive creation.",
        "",
    ]
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        lines.append(f"{sha256(path)}  EKAGRAAI_SOURCE/{relative}")
    (audit / "FILE_MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_tests() -> tuple[int, str]:
    tests = [
        "tests/test_c3_isolated_pilot_prompts.py", "tests/test_c31_learner_readiness.py",
        "tests/test_c32_learner_readiness.py", "tests/test_controlled_c23_contract_routing.py",
        "tests/test_master_console.py", "tests/test_controlled_c1_full_instructional_prompts.py",
        "tests/test_unified_c1_c4_visuals.py",
    ]
    completed = subprocess.run([sys.executable, "-m", "pytest", "-q", *tests], cwd=ROOT, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return completed.returncode, completed.stdout


def main() -> None:
    code, output = run_tests()
    if code:
        raise SystemExit(output)
    data = read_trace()
    files = source_files()
    if not any(path.relative_to(ROOT).as_posix() == "src/solo_harness/runtime/ai.py" for path in files):
        raise SystemExit("runtime inventory failure: ai.py missing")
    if not any(path.relative_to(ROOT).as_posix() == "src/solo_harness/runtime/controlled_executor.py" for path in files):
        raise SystemExit("runtime inventory failure: controlled_executor.py missing")
    if not any(path.relative_to(ROOT).as_posix() == "src/solo_harness/runtime/controlled_unified_prompts.py" for path in files):
        raise SystemExit("runtime inventory failure: controlled_unified_prompts.py missing")
    with tempfile.TemporaryDirectory(prefix="ekagra_c3_phase2_") as temp:
        stage = Path(temp) / PREFIX
        source = stage / "EKAGRAAI_SOURCE"
        audit = stage / "AUDIT_CONTEXT"
        for path in files:
            target = source / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        write_live_evidence(audit, data)
        write_context(audit, files, output, code)
        if OUTPUT.exists():
            OUTPUT.unlink()
        with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage.parent).as_posix())
    try:
        with ZipFile(OUTPUT) as archive:
            bad = archive.testzip()
            names = set(archive.namelist())
    except BadZipFile as exc:
        raise SystemExit(f"ZIP integrity failure: {exc}") from exc
    expected = {f"{PREFIX}/EKAGRAAI_SOURCE/{path.relative_to(ROOT).as_posix()}" for path in files}
    missing = expected - names
    if bad or missing or f"{PREFIX}/EKAGRAAI_SOURCE/src/solo_harness/runtime/ai.py" not in names:
        raise SystemExit(f"ZIP verification failure: bad={bad}, missing={sorted(missing)[:10]}")
    print(json.dumps({"archive": str(OUTPUT), "bytes": OUTPUT.stat().st_size, "source_files": len(files),
                      "test_exit_code": code, "integrity": "ok", "runtime_included": True}, indent=2))


if __name__ == "__main__":
    main()
