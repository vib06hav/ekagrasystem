"""Build the offline-only C3 Phase-3/4 implementation audit archive."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "EKAGRAAI_C3_PHASE3_4_IMPLEMENTATION_AUDIT.zip"
PREFIX = "EKAGRAAI_C3_PHASE3_4_IMPLEMENTATION_AUDIT"
EXCLUDED_DIRS = {".git", ".venv", ".pytest_cache", "__pycache__", "local-artifacts", "research-data", "exports", "graphify-out", "node_modules"}
EXCLUDED_NAMES = {".env", "dev.env", "EKAGRAAI_LATEST_FULL_SOURCE_AND_PROMPT_AUDIT.zip",
                  "EKAGRAAI_C3_PHASE2_IMPLEMENTATION_AUDIT.zip", OUTPUT.name}
TESTS = [
    "tests/test_c3_isolated_pilot_prompts.py", "tests/test_c31_learner_readiness.py",
    "tests/test_c32_learner_readiness.py", "tests/test_controlled_c23_contract_routing.py",
    "tests/test_master_console.py", "tests/test_controlled_c1_full_instructional_prompts.py",
    "tests/test_unified_c1_c4_visuals.py",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts) or relative.parts[:2] == ("tools", "runtime"):
            continue
        if path.is_file() and path.name not in EXCLUDED_NAMES and path.suffix not in {".pyc", ".pyo", ".db"}:
            files.append(path)
    return sorted(files)


def run(command: list[str]) -> str:
    completed = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, check=False)
    if completed.returncode:
        raise SystemExit(completed.stdout)
    return completed.stdout


def write_state_trace(path: Path) -> None:
    from solo_harness.runtime import controlled_executor as executor
    from solo_harness.runtime.controlled_c3_pilot_prompts import new_guided_state, next_guided_turn
    lines = ["# Offline P2 state and visual traces", "", "Synthetic state-machine evidence; no model call was made.", ""]
    for move_id in ("C3.1-P2-M03", "C3.2-P2-M02"):
        subsection, pedagogy, _ = move_id.split("-")
        move = executor.contract("C3")["subsections"][subsection]["moves_by_pedagogy"][pedagogy][int(move_id[-2:]) - 1]
        state = new_guided_state(move_id)
        rows = [("initial", state["stage"], 0, "prompt visual once")]
        for index, reply in enumerate(("Every check passes.", "Still not sure.", "I do not know."), 1):
            state, decision = next_guided_turn(move, state, {"id": f"synthetic-{index}", "content": reply})
            visual = "complete visual once" if state["stage"] == "FINAL" else "no new visual"
            rows.append((decision["classification"], state["stage"], state["hint_count"], visual))
        lines.extend([f"## {move_id}", "", "| Input classification | Stage | Hints | Visual |", "|---|---:|---:|---|"])
        lines.extend(f"| {kind} | {stage} | {count} | {visual} |" for kind, stage, count, visual in rows)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_context(audit: Path, files: list[Path], test_output: str) -> None:
    (audit / "README.md").write_text("""# EkagraAI C3 Phase-3/4 implementation audit

This archive is offline-only: all prompt captures, visual snapshots, state traces, and test results were produced with local deterministic code and mocked responses. No live Tutor or Judge model call was made for this phase.

`EKAGRAAI_SOURCE/` contains the non-secret current working tree. `OFFLINE_EVIDENCE/` contains generated prompt and visual evidence. `FILE_MANIFEST.txt` lists every included working-tree source file with SHA-256.
""", encoding="utf-8")
    (audit / "IMPLEMENTATION_REPORT.md").write_text("""# Phase-3/4 implementation report

## Implemented

- `controlled_c3_pilot_prompts.py` now defines the reviewed word tokenizer (letters/digits, with internal hyphens/apostrophes kept in one word), per-move/per-stage caps, and a compact rewrite instruction. Tutor contexts provide the approved goal, verified facts, pedagogy, dialogue, stage content, and plain scientific context; detailed completion evidence remains Judge-only.
- `ai.py` enforces a C3-pilot ordinary Tutor cap before persistence. An over-cap response gets at most two shorter-rewrite requests. Doubt responses are exempt. An unresolved third over-cap candidate becomes the auditable `WORD_LIMIT_EXHAUSTED` technical hold; it is never truncated or displayed.
- The C3 visual template uses approved learner-facing labels, fixes C3.1 P2-M02 completed panels, renders two—not four—C3.2 M02 completed panels, retains three essential C3.2 M03 panels, removes internal visible/accessibility copy, and preserves prompt-stage answer hiding.
- Offline captures cover all 30 moves, all P2 stages, and every C3 visual mode including no-visual moves. Tests cover P2 state paths, word-cap boundaries/retries/exhaustion, prompt routing, visual rendering, and C1/C2/C4/legacy-C3 regressions.

## Deliberately not implemented

No fallback Tutor scripts were activated. The approved pack explicitly says they are not authored or approved. Therefore hard-cap recovery cannot guarantee automatic instructional continuation after three over-cap candidates; the safe technical hold is the remaining limitation. No live LLM validation was run, and no model provider was contacted.

Phase-2's deterministic reply classifier was preserved unchanged.
""", encoding="utf-8")
    (audit / "NO_APPROVED_FALLBACK.md").write_text("""# Word-limit fallback review

No fallback wording is included or activated. The approved review explicitly states that scientifically verified short fallback messages have not been authored or approved. The runtime consequently refuses to display an over-cap message after two rewrite requests and records `WORD_LIMIT_EXHAUSTED`. This is strict enforcement without invented instructional content, but it can require an operator retry; it is not represented as automatic recovery.
""", encoding="utf-8")
    (audit / "TEST_RESULTS.txt").write_text("Command:\n" + " ".join([sys.executable, "-m", "pytest", "-q", *TESTS]) + "\n\n" + test_output, encoding="utf-8")
    manifest = ["# Archive manifest", "", f"Generated: {datetime.now(timezone.utc).isoformat()}",
                f"Included working-tree source files: {len(files)}", "",
                "Excluded: secrets (`.env`, `dev.env`), databases, participant/research data, Docker volumes, virtual environments, caches, generated dependencies, prior archives, and tools/runtime downloaded FFmpeg.",
                "The complete `src/solo_harness/runtime/` package is required and verified.", ""]
    manifest.extend(f"{sha256(path)}  EKAGRAAI_SOURCE/{path.relative_to(ROOT).as_posix()}" for path in files)
    (audit / "FILE_MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")


def main() -> None:
    test_output = run([sys.executable, "-m", "pytest", "-q", *TESTS])
    files = source_files()
    required = {"src/solo_harness/runtime/ai.py", "src/solo_harness/runtime/engine.py",
                "src/solo_harness/runtime/controlled_executor.py", "src/solo_harness/runtime/controlled_unified_prompts.py"}
    available = {path.relative_to(ROOT).as_posix() for path in files}
    if not required <= available:
        raise SystemExit(f"runtime inventory failure: {sorted(required - available)}")
    with tempfile.TemporaryDirectory(prefix="ekagra_c3_phase34_") as temp:
        stage = Path(temp) / PREFIX
        source, audit = stage / "EKAGRAAI_SOURCE", stage / "AUDIT_CONTEXT"
        for path in files:
            target = source / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        evidence = audit / "OFFLINE_EVIDENCE"
        run([sys.executable, "tools/research/capture_c3_isolated_pilot_prompts.py", str(evidence / "PROMPT_CAPTURES")])
        run([sys.executable, "tools/research/capture_c3_visual_snapshots.py", str(evidence / "VISUAL_SNAPSHOTS")])
        write_state_trace(evidence / "SYNTHETIC_P2_STATE_VISUAL_TRACES.md")
        write_context(audit, files, test_output)
        if OUTPUT.exists(): OUTPUT.unlink()
        with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file(): archive.write(path, path.relative_to(stage.parent).as_posix())
    try:
        with ZipFile(OUTPUT) as archive:
            bad, names = archive.testzip(), set(archive.namelist())
    except BadZipFile as exc:
        raise SystemExit(f"ZIP integrity failure: {exc}") from exc
    expected = {f"{PREFIX}/EKAGRAAI_SOURCE/{path.relative_to(ROOT).as_posix()}" for path in files}
    missing = expected - names
    if bad or missing or not all(f"{PREFIX}/EKAGRAAI_SOURCE/{path}" in names for path in required):
        raise SystemExit(f"ZIP verification failure: bad={bad}, missing={sorted(missing)[:10]}")
    print(json.dumps({"archive": str(OUTPUT), "bytes": OUTPUT.stat().st_size, "source_files": len(files),
                      "integrity": "ok", "offline_only": True}, indent=2))


if __name__ == "__main__":
    main()
