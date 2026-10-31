# Codex engineering handoff — implement F1 v0.4 as written

## 0. Boundary and instruction

This archive is a CANDIDATE scientific-authoring package, not an existing plugin-ready YAML schema. Your job is to wire it into the actual current Python API, database, browser and Docker environment without inventing SOLO evidence, scenario truth, rubric meanings or treatment decisions. Do not claim model behavior from stub tests. Preserve the existing working-tree changes.

## 1. Reuse valid work; replace the wrong assessment abstraction

Retain functional: YAML validation, transit/model adapters, treatment-blind role boundaries, frozen package/persistence, deterministic MCQ scoring, technical-failure handling, development activation gates and existing UI/API wiring. Replace v0.3's fixed `authored_stem_intent`, fixed semantic-option sentences, fixed `private_correct_option_id` and text-equality validator. These MAY exist as fixed *generated attempt* data only after generation, verification and freezing, never as reusable-family authority.

## 2. Loader/authoritative scientific source

- Load exactly seven v0.4 YAML files under `08_SCIENTIFIC_YAML`; validate schema and all 16 blueprint IDs, 64 slot records, 12 cells, K/R/M references and oracle names.
- Compile one slot's relevant definitions, actual pedagogical constraints and verified instance, not the entire YAML dump. Every meaningful authoring field either affects a relevant prompt or an explicit runtime invariant; publish a field consumption matrix.
- Include source files, all behavior-affecting prompt templates, scenario generators and oracle code in immutable study-version hashing. Keep instance-specific randomness/seeds/scenarios and actual prompt/output hashes in immutable records; different generated instances should have distinct instance IDs, not different scientific version IDs.

## 3. Question instance pipeline (real generation, not fixed bank)

1. Select approved unexposed blueprint independently of pedagogy (and without model access to learner history).
2. For each of three MCQ contracts generate fresh parameters within approved scenario family and F1 load limits (never mandatory 7-bit pattern/three ones or fixed answer B). Generate a suitable instance-specific subjective scenario as well.
3. Use independent oracle (`reference_parity_oracle.py`) or an equivalent verified algorithm to compute all scientific facts for actual generated parameters, including error universe and relevant assumptions.
4. Derive one correct and three distinct misconception-targeted **meanings** from the actual case. The LLM writes learner-facing stem/options natural prose and may vary them substantially. Do not let the LLM invent the correctness or select the correct index.
5. Run structural, numerical and semantic quality checks on the realized item; one true unambiguous option. Use another review model call or human review on uncertain concepts. Literal text equality or stable matching IDs are not proof of semantic equivalence. A changed correct option that becomes false must BLOCK grading.
6. Shuffle the 4 validated propositions' displayed position per instance; bind the new position to the verified correct semantic identity and freeze private key. Public UI receives only question/options; not oracle/private key or semantic-grade diagnostics.
7. Freeze all four realized tasks before display. Subsequent calls and retries may not silently overwrite an administered form; idempotent freeze and once-only grading rules.

## 4. Actual multi-turn Tutor

Compile one of 12 distinct treatment cells with resolved scientific text. Tutor receives real learner turn and dialogue history, correct generated instruction-only facts, no assessment materials. The Tutor adapts to learner reasoning under assigned P1/P2/P3. Do NOT advance through `required_moves` on every model call regardless of response; moves are fidelity checks, not a rigid script. Require human review of real Tutor transcripts for mechanistic fidelity.

## 5. Independent blind subjective Judge

Judge receives exact frozen generated subjective question and verified scenario key, learner's actual answer, one slot's specific evidence criteria and correct transition anchors. NEVER assigned pedagogy, Tutor transcript, MCQ answers/score, prior results. The real provider must return a structured explanation that preserves observed SOLO structure, criterion evidence, material correctness, misconception evidence, uncertainty and points. Treat provider failures and review-required cases as technical/review status, not learner failure. Backend scoring gate remains MCQ >=2 AND subjective >=1.

## 6. Runtime and testing order — DOCKER EARLY

**Gate A (brief):** Run YAML/schema/reference-oracle tests and small synthetic path to confirm wiring, private key handling, paraphrase acceptance and meaning-change rejection. Do not endlessly expand isolated stubs.

**Gate B (next mandatory milestone):** Start existing Docker Compose stack, build API/database/browser; route F1 v0.4 into genuine development-only session creation, multi-turn tutoring, frozen assessment delivery, submission, Judge endpoint and persisted progression. Exercise with controlled transport and browser/API calls, evidence of database rows, restarts, non-leakage, errors, and feature flags. Do not activate real research participants.

**Gate C (real provider):** Configure permitted model credentials through existing safe environment mechanism. Make small real-provider schema preflights, then real Tutor, generative Assessment and blind Judge calls from Docker-backed development route; retain redacted actual prompts/responses and final frozen public/private views. Demonstrate diverse underlying scenario values and correct positions, not merely 16 fixture restatements.

**Gate D (scientific review):** Scientific audit of real model outputs; adversarial semantic drift, human item-quality review and preliminary Judge calibration. Do not confuse test PASS with study validity.

Report each stage distinctly as IMPLEMENTED / EXECUTED / NOT TESTED. Include raw execution logs, exact commands, redacted provider outputs and source diffs. A Docker container merely starting is not proof of participant-flow integration.

## 7. Archiving strategy — NOT deletion

After successful replacement and smoke test, move historical F1 v0.1/v0.3 pack versions, obsolete prompt dumps and superseded candidate-only code into `old/` with README and provenance manifest. Do not move files still needed by imports, migrations, older frozen records or operational history until dependencies are safely redirected. Do not delete participant records, DB tables, historical releases or unrelated studies. Ensure only v0.4 can become the new dev scientific authority when selected; old archive is inert.

## 8. Acceptance evidence

- Exactly 16 blueprint families, 48 unique MCQ contracts and 16 subjective contracts in source and compiler, all item-specific and inspectable.
- One family yields genuinely different legal bit patterns, 1s counts (as feasible), parity outcomes and prose; correct position not biased fixed B.
- All generated MCQs verified independently; a swapped true option meaning is rejected while an equivalent paraphrase is allowed after semantic review.
- Distinct actual P1/P2/P3 tutoring behavior; real learner-response contingent followup.
- Judge demonstrably evaluates real learner language with no treatment or MCQ leakage, including legitimate alternate explanations and uncertain cases.
- Docker UI + API + database + real provider through one full development-only session demonstrated, not a script that returns canned model output.
- Existing 2/3 + 1/2 gate applied only after valid question freezing and gradable Judge response.
- Everything stays F1-only. No professor three-topic experiment, no fake extension of workload limit, no premature production activation.
