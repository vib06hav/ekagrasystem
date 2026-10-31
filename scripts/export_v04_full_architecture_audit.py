"""Read-only source/evidence export for independent architecture review."""
from __future__ import annotations
import hashlib, shutil, subprocess, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"exports"/"EKAGRAAI_F1_V04_FULL_SOURCE_ARCHITECTURE_AUDIT"
ZIP=OUT.with_suffix(".zip")

def text(path, value):
    p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value,encoding="utf-8")
def copy(path):
    target=OUT/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
def git(*args):
    result=subprocess.run(["git",*args],cwd=ROOT,capture_output=True)
    return result.stdout.decode("utf-8",errors="replace")

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    # Entire application source and tests are included, not selected excerpts.
    shutil.copytree(ROOT/"src"/"solo_harness",OUT/"src"/"solo_harness")
    shutil.copytree(ROOT/"tests",OUT/"tests")
    shutil.copytree(ROOT/"studies"/"networks_error_detection_parity_f1"/"v0.4",OUT/"studies"/"networks_error_detection_parity_f1"/"v0.4")
    for name in ("compose.yaml","Dockerfile","pyproject.toml","alembic.ini"):
        if (ROOT/name).is_file(): copy(ROOT/name)
    for folder in ("migrations",):
        if (ROOT/folder).is_dir(): shutil.copytree(ROOT/folder,OUT/folder)
    for evidence in ROOT.glob("exports/EKAGRAAI_F1_V04_*LIVE*EVIDENCE*.zip"):
        copy(evidence)
    text(Path("provenance/git_status.txt"),git("status","--short"))
    text(Path("provenance/git_diff_stat.txt"),git("diff","--stat"))
    text(Path("provenance/git_diff.txt"),git("diff"))
    text(Path("provenance/git_commit.txt"),git("rev-parse","HEAD"))
    text(Path("provenance/docker_env_names.txt"),"DATABASE_URL\nSTUDY_DIR\nAPP_BUILD_ID\nENABLE_F1_V04_DEVELOPMENT\nENABLE_F1_V04_LIVE_DEVELOPMENT\nF1_V04_CONTROLLED_TRANSPORT\nLLM_PROVIDER\nAICREDITS_BASE_URL\nAICREDITS_API_KEY\nLLM_STRUCTURED_OUTPUT_MODE\nTUTOR_MODEL\nJUDGE_MODEL\n")
    text(Path("MODEL_INTERFACE_AUDIT.md"),"""# Model interface audit (current source)

All models and adapters are copied verbatim under `src/solo_harness/`.

| Role | Current model / invocation | Response model | Failure |
|---|---|---|---|
| Tutor | `scientific_v04_live._call(..., Tutor)` via `OpenAICompatibleClient` | `learner_message`, `fidelity_note` | `INVALID_OUTPUT`, raw response retained |
| Assessment | `_call(..., Item)` | `stem`, `correct_option`, `distractors[3]` | same |
| Semantic reviewer | `_call(..., Review)` | verdict, explanation, three booleans | non-ACCEPT returns review hold |
| Judge | `_call(..., Judge)` | gradable status, nullable score/reason, SOLO/evidence text | same |

Provider adapter: `src/solo_harness/runtime/ai.py:OpenAICompatibleClient.prepare/send`; live invocation: `src/solo_harness/runtime/scientific_v04_live.py:_call/run_live`.

The live schemas do not require source IDs or option letters. `correct_option` is a uniform field but current live diagnostic returns it in its API payload—risky and not suitable for learner delivery. No current live fixture fallback is invoked. Controlled fixtures remain in `scientific_v04_dev.py`.

Malformed provider output is saved as `LLMCall.INVALID_OUTPUT`; semantic holds are returned by `run_live`. Current live route does not yet freeze an `AssessmentInstance` or submit learner answers.
""")
    text(Path("SCENARIO_IMPLEMENTATION_AUDIT.md"),"""# Scenario implementation audit

Trace: original slot → backend policy lookup (`scientific_v04_policy.load_policy`) → `resolve_typed_case` → reference oracle → `public`/`oracle` partitions → `scientific_v04_live.run_live` prompts.

The companion mapping is copied at `studies/.../v0.4/EKAGRAAI_F1_V04_TYPED_POLICY_AND_LLM_BOUNDARY_COMPANION_CANDIDATE/`. Original YAML remains authoritative.

Current typed operators implemented: sender/receiver/single/checkbit 1D; full2d single/pair; grouped evasion. Explicit supported live policies: C1-A1-Q2, C2-A1-Q2, C3-A1-Q2, C4-A1-Q3. Other declared mapping operators fail closed.

Risk inventory: legacy `scientific_v04.resolve_scenario` contains slot-ID/text predicate branches and fixed witnesses; it remains copied for review. `scientific_v04_policy.py` is the new intended live resolver, but its live `public` facts are currently passed to Tutor by `run_live`, contaminating assessment and instruction. `run_live` also supplies private oracle facts to the semantic reviewer/Judge, which is appropriate only for their private role.
""")
    text(Path("CURRENT_EXECUTION_TRACE.md"),"""# Current v0.4 execution trace

Docker entry: `Dockerfile` → `python -m solo_harness.main` → `main.create_app` → `web_v04.v04_dev_router`.

Controlled path: `/dev/f1-v04/sessions` → `scientific_v04_dev.start/tutor/_freeze/submit`; uses `CONTROLLED_TEST_ONLY` fixture calls and existing `Session`, `Attempt`, `AssessmentInstance`, `AssessmentResponse`, `Phase2Evaluation`, `LLMCall` tables.

Live diagnostic path: `/dev/f1-v04/live/{contract_id}` → `web_v04.live` → `scientific_v04_live.run_live` → real `OpenAICompatibleClient.send`. It has executed real Tutor/Assessment/Review/Judge calls, evidenced in included live ZIP records. It generates one MCQ, passes the assessment public case to Tutor, exposes `correct_option` in its developer response, and judges the Tutor input—not a frozen subjective response. It does not implement the four-item lifecycle.

Existing original application paths likely reusable: `runtime/ai.py:AIExecutionRuntime`, `runtime/engine.py:SessionRuntime`, `runtime/phase2_persistence.py`, `runtime/phase2_evaluation.py`, `web.py:ParticipantApplication`. They are included in full for independent comparison.
""")
    text(Path("HARDCODING_AND_DUPLICATION_INVENTORY.md"),"""# Hardcoding and duplication inventory

* `scientific_v04.py:resolve_scenario` — slot-ID and English substring branches; scientifically risky legacy candidate resolver.
* `scientific_v04_dev.py:tutor/_meaning/_semantic_review/submit` — canned Tutor, Python prose/options, exact-text fixture review, canned Judge points; fixture-only controlled route, not live behavior.
* `scientific_v04_live.py:SUPPORTED` — bounded live trial allowlist, legitimate temporary live safety gate but not full contract coverage.
* `scientific_v04_live.py:run_live` — one-MCQ diagnostic; assessment-to-Tutor contamination, no frozen package, API returns `correct_option`; risky/development-only.
* `web_v04.py:_page` — manually built frontend and radio grouping defect; duplicates parts of original `web.py` participant UI.
* `runtime/ai.py` and `runtime/engine.py` — original infrastructure has persistence, retry, assessment/Judge and progression machinery; export permits review of reuse versus duplication.

No source files were corrected for this audit. Line numbers should be verified against the copied full files because the worktree is dirty and contains untracked v0.4 files.
""")
    files=[p for p in OUT.rglob("*") if p.is_file()]
    text(Path("SHA256_MANIFEST.txt"),"\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}" for p in sorted(files)))
    if ZIP.exists(): ZIP.unlink()
    shutil.make_archive(str(OUT),"zip",OUT.parent,OUT.name)
    print(ZIP)
if __name__=="__main__": main()
