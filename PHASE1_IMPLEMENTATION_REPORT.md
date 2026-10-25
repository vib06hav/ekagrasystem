# Phase 1 implementation report

## Baseline and isolation

- Baseline commit: `822914348447119ed10ab7295e4656a02c50bfad`.
- Work branch: `phase1-hardening`.
- The checkout was dirty before this work. Pre-existing modified/untracked items remain preserved; this report does not claim they are Phase 1 changes.
- No external provider calls, participant sessions, historical records, recordings, or frozen study-version rows were created or modified.

## Implemented requirements

### F1 — exact-once Judge evidence

`validate_judge_evidence_scope` in `src/solo_harness/runtime/ai.py` now requires a gradable response to contain exactly one criterion and misconception object for every assessment-scoped ID. Missing, extra, and duplicate IDs are invalid. `NOT_GRADABLE` requires both arrays to be empty. The check runs before a call is marked successful or `SessionRuntime.apply_judgment` is called.

### F2 — strict Judge gradability contract

`JudgeOutput.validate_gradability_fields` rejects aliases and inconsistent fields instead of normalizing them. Gradable correctness values require a SOLO state and null not-gradable reason; `NOT_GRADABLE` requires an allowed reason and null state. Raw provider material remains on the `LLMCall`; invalid output uses the existing retry path.

### F3 — forward-only scoped Judge guidance

New compiler contract `3.1` and prompt contract `2.1` add `[AUTHORED_JUDGE_CONTRACT]` and `[SELECTED_RUBRIC_GUIDANCE]`, composed only from the selected authored contract/rubric fields. C1–C4 prompt tests check the sections, treatment blindness, and character budget. Contract `3.0` continues to compile its legacy prompt shape.

### F4 — authoring validation and candidate pack

`studies/python_fibonacci_memoization/v0.5` is a separate candidate. `study.yaml` changes its content version to `v0.5`; its assessment files remove only blank `required_response_features`; its protocol prose records administrative continuation after `UNRESOLVED`. The `v0.1` source pack remains unchanged.

`studies/validation.py` now checks transition/rubric alignment, scoped evidence/misconception references, duplicate identity lists, success-rule references/form ownership, feasibility against mandatory rule gates, target-state alignment, and blank features in non-legacy packs. The exact legacy `v0.4` blank feature condition remains readable only as grandfathered content.

### F5 — generated-assessment gate

`validate_generated_assessment` runs before an assessment becomes active. It rejects blank/placeholder content, unclosed code fences, explicit leakage markers, leaked long required features, and the narrow defined-function/hidden-return mismatch. Offline fixtures are in `tests/fixtures/generated_assessments.json`; the human-review boundary is documented in `docs/assessment_human_review_checklist.md`.

### F6 — scientific unresolved versus administration

The existing engine's persisted `scientific_outcome=UNRESOLVED` continuation path is retained. `web.py` derives section state from `SECTION_COMPLETED.scientific_outcome`; the participant template displays neutral unresolved continuation wording and a distinct unresolved terminal message. Research export schema `1.2` retains raw events and adds derived `derived_transition_scientific_outcomes` without deriving unknown old events as pass.

### F7 — Tutor move boundaries and scoped treatment context

Tutor execution now checks that the output move matches the persisted requested move, checks authored outgoing edges, forbids a next move on `COMPLETE`, and requires a next move for non-budget-ending `CONTINUE`. New-contract Tutor prompts include selected cell/pedagogy/shared-envelope treatment fields and explicit move-boundary instruction; no assessment or Judge material is inserted.

### S1, S2, S3

- `loader.source_bundle` creates a relative-path UTF-8 text/SHA-256 source bundle; bootstrap persists it on only new activations. Programmatic activation remains supported with `NOT_CAPTURED` provenance.
- Assessment resolution now accepts explicit transition context and verifies the blueprint belongs to that family; it no longer parses a transition from the form ID.
- New-contract JSON decoding requires one complete JSON object. New-contract citation grounding is literal contiguous matching; legacy calls retain legacy decoder/citation compatibility. Technical retries copy the stored messages, schema, payload and request body rather than recompiling them.

## Compatibility and activation

`snapshot_identity` now accepts explicit compiler/schema versions. `StudyCatalog.load` hashes snapshots using the versions persisted on the `StudyVersion`, so `3.0` rows remain verifiable. Bootstrap no longer replaces an existing active version unless `ACTIVATE_STUDY_ON_BOOTSTRAP=true`; the v0.5 activation is explicit. `.env.example` and README document that choice.

## Tests run

```text
python -m pytest tests/test_ai_contracts.py tests/test_studies.py tests/test_engine.py -q
58 passed in 19.66s

TEST_DATABASE_URL=postgresql+psycopg://solo_test:solo_test@127.0.0.1:55432/solo_test \
  python -m pytest tests/integration/test_ai_operations.py tests/integration/test_experiment_engine.py \
  tests/test_reliability.py tests/test_reconstruction.py tests/test_telemetry.py \
  tests/test_research_time.py tests/test_app.py -q
26 passed in 39.67s
```

The full `pytest -q` command was started after the targeted runs and exceeded the 120-second local command limit without a final result. Its child process was stopped after timeout. Browser E2E and hardware/capture tests are therefore **NOT VERIFIED** in this Phase 1 run.

## Limitations

- Deterministic assessment validation intentionally does not establish semantic answerability, scientific validity, equivalent difficulty, or semantic leakage; the checklist is for offline human review.
- No live model, webcam/screen capture, or participant flow was executed.
- The worktree has preserved pre-existing changes, so the final Git diff includes both prior and Phase 1 modifications. No commit was created.

## Final Git status and diff summary

`git diff --stat` reports 25 tracked files changed, 513 insertions and 83 deletions before untracked Phase 1 files are included. The exact final short status is:

```text
 M .gitignore
 M README.md
 M migrations/versions/0004_institutional_id.py
 M migrations/versions/0005_capture_run_id.py
 M pyproject.toml
 M src/solo_harness/bootstrap.py
 M src/solo_harness/config.py
 M src/solo_harness/research_export.py
 M src/solo_harness/runtime/ai.py
 M src/solo_harness/static/telemetry/participant_keyboard.js
 M src/solo_harness/static/telemetry/participant_telemetry.js
 M src/solo_harness/studies/activation.py
 M src/solo_harness/studies/canonicalization.py
 M src/solo_harness/studies/catalog.py
 M src/solo_harness/studies/loader.py
 M src/solo_harness/studies/validation.py
 M src/solo_harness/telemetry.py
 M src/solo_harness/templates/partials/session_main.html
 M src/solo_harness/web.py
 M tests/e2e/test_participant_browser.py
 M tests/integration/test_ai_operations.py
 M tests/test_ai_contracts.py
 M tests/test_reliability.py
 M tests/test_studies.py
 M tools/windows_capture/record.py
?? EkagraAI_Phase1_Codex_Implementation_Brief.md
?? EkagraAI_Phase1_Source_Verified_Decision_Register_2026-10-25.md
?? PHASE1_IMPLEMENTATION_REPORT.md
?? docs/STUDY_TERMINOLOGY_AND_RECONSTRUCTION_AUDIT.md
?? docs/assessment_human_review_checklist.md
?? scripts/live_switching_reconstruction_e2e.py
?? scripts/recorded_reconstruction_e2e.py
?? studies/python_fibonacci_memoization/v0.5/
?? tests/fixtures/
?? tests/test_reconstruction.py
?? tools/research/
```

The current worktree includes Phase 1 paths (`studies/python_fibonacci_memoization/v0.5`, `src/solo_harness/{runtime/ai.py,studies/*,bootstrap.py,web.py,research_export.py}`, focused tests/fixtures/checklist) plus the pre-existing files listed by Git before the Phase 1 branch was created.
