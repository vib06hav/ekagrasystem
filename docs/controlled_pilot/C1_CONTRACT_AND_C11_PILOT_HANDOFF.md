# EkagraAI controlled-adaptive C1 — Phase 1 + C1.1 Phase 2 handoff

**Base snapshot:** `EKAGRAAI_CODEBASE_80BCF0B.zip` (v0.5 candidate source).  
**Deliverable:** An opt-in internal controlled C1.1 vertical slice, plus an authored, source-aligned move contract for all C1 subsections.  
**Status:** Code authored; **not integrated in the user's active repository, not deployed, and NO TESTS RUN**. Python files were syntax-parsed, the JSON contract was parsed, and the source-move order was inspected. These are NOT behavioral, database, integration, scientific-outcome, or browser validations.

## Ownership

- **Assistant:** scientific/move contract, verified C1.1 fixed instance, scoped Tutor and Conversation Judge prompt assembly, backend move sequencing/evidence, passive frontend rendering, source patch and handoff.
- **Codex:** apply patch to user's current working repository; reconcile changes since snapshot; check packaging of JSON contract; perform lint/migrations/environment setup and run automated and live/manual validation; inspect telemetry, research provenance and treatment fidelity; do not silently change scientific definitions, moves or examples.
- **User/research lead:** decide acceptance after watching P1/P2/P3 sessions, approve research fidelity and controls before wider collection. Neither the new pilot nor v0.5 candidate is approved for participant deployment by this patch.

## Phase 1 — all four C1 subsections

The **authoritative proposed execution contract** is at:

`src/solo_harness/studies/controlled_c1_contracts.json`

It contains **52 source-aligned moves**: C1.1 (4/5/4), C1.2 (4/5/4), C1.3 (4/5/4), C1.4 (4/5/4), ordered P1/P2/P3. Every move has:

1. Original exact `source_instructional_action` and original source `required_content_refs`.
2. Precise, authored `exact_delivery` scientific content and flow.
3. `visual` (either `null` or a small passive visual component with mode).
4. `learner_response_policy` (explain/model/guided/compare/conditional).
5. Human-reviewable `completion_evidence` requirement.

Verified, scoped cases and boundaries are listed in `fixed_cases`. C1.2–C1.4 are **DESIGN ONLY** in this patch; the runtime never consumes or executes them yet. The original scientific package files and source SHA manifests have not been edited.

### Approved science/design details

- **C1.1:** Yes=1 / No=0, main Yes–Yes–No → `110` (three bits, two ones), P3 contrast Yes–No–No → `100` (one change at position 2, one one). Max two passive components: representation mapping and numbered bit sequence. No numeric-base conversion, encoding, architecture or physical-level explanations.
- **C1.2:** sender/channel/receiver, sent `10110`, intact `10110`, corrupted `10010` (`1 → 0` at one-based position 3). One passive transmission diagram. Receiver ordinarily lacks the original; no non-transmission error models.
- **C1.3:** payload `10110` plus symbolic `p`; **do not assign a numeric value to p**. One static check-bit slot. Introduce redundancy and shared data-dependent rule, NOT even/odd computation.
- **C1.4:** payload `10110` has three ones; even adds `1` → `101101` (four ones); odd adds `0` → `101100` (three ones); even received `101101` passes, `100101` fails. One passive bit strip; concise odd receiver confirmation, not another guided question round. Do not teach the C2 odd/even count-of-FLIPS theorem.

## Phase 2 — C1.1 only

### Opt-in and isolation

Set `ENABLE_CONTROLLED_C11_PILOT=true` **only in the internal v0.5 test environment**, alongside the existing internal-candidate access settings. When the staff-only `/internal/v051/session` route creates an internal session, it persists `runtime_config_snapshot.controlled_c11_pilot=true` and seeds C1.1's `SubsectionProgress.instructional_state.controlled_c11` with a versioned contract hash and move index `0`.

Default is `false`. Ordinary enrollment remains disabled for v0.5 candidate studies and unaffected. Existing v0.5 internal sessions without the opt-in marker stay on the existing conversation path. All later subsections, including C1.2–C1.4, remain on the existing v0.5 path after the pilot C1.1 finishes.

### Controlled Tutor and Judge lifecycle

1. The backend resolves the **one current C1.1 authored move**, its fixed scientific information, response policy and optional visual, validating its ID, source action, required content refs, and persisted contract hash against v0.5 scientific source.
2. It compiles a pilot-specific Tutor prompt for that move only (not the entire setlist), using the existing `V051TutorOutput` JSON schema. The Tutor is still conversational and can address doubts.
3. A Tutor message is persisted with an auditable `pilot_move_id`, `pilot_contract_sha256` and, only when applicable, a backend-created `pilot_visual` descriptor in `Message.instructional_trace`.
4. The existing Conversation Judge role is used for **move-scoped** review; it can `CONTINUE`, `ADVANCE` or `HOLD`. The model's `ready_for_judge` remains a non-authoritative request.
5. On reviewed `ADVANCE`, the backend atomically records persisted Tutor-message IDs for the move and its source-listed content refs, emits `CONTROLLED_C11_MOVE_REVIEWED`, and advances the move index. On the **final move**, the Judge also reviews whole-subsection delivery and the backend requires all move/content evidence before allowing the existing subsection advancement.
6. `CONTINUE` keeps the same move and supplies Judge guidance. `HOLD` follows the existing delivery-exception path. C1.1 never treats correct learner answers as mastery evidence or a gate.

P2's guided moves M02–M04 **require a real learner turn after the guided prompt** before the backend permits move-level advancement. The LLM responds after the learner (including IDK and incorrect replies); user correctness is irrelevant to permission to proceed. If the Tutor prematurely claims readiness, the system does not create a review call until a learner reply arrives.

The backend additionally supplies an optional deterministic, *formative-only* check for exact literal chat replies `110` (P2 M03) or a small ones-count numeral (P2 M04); all other natural language is interpreted by the Tutor. No separate interactive visual response workflow is added.

### Frontend

`src/solo_harness/templates/partials/session/controlled_c11_visual.html` renders **two** simple, passive, server-owned visual templates from persisted, verified data. There is no new JavaScript. It uses the existing conversation timeline; the visual is linked to the corresponding Tutor message, not a detached full-page lesson. No diagrams or HTML are generated by the Tutor.

- P1: M02 mapping, M03 numbered sequence/count.
- P2: M02 single-bit vs sequence; M03 mapping prompt/resolution; M04 numbered sequence with hidden count until correct explanation. No learner clicks: chat remains the input.
- P3: M01 single-bit vs sequence; M02 matched mappings; M03 matched numbered strips/counts.

Visual exposure is capped and optional, and the Judge explicitly **does not accept a shown visual by itself as proof of teaching**.

### Runtime files modified

- `src/solo_harness/config.py` — opt-in flag.
- `src/solo_harness/runtime/engine.py` — durable pilot initialization, reviewed move evidence, last-move gate and advancement.
- `src/solo_harness/runtime/ai.py` — pilot-aware Tutor/Judge requests, stable verified instance, response hints, visual traces, review reservation.
- `src/solo_harness/runtime/v051_conversation.py` — scoped pilot Tutor and Judge prompts.
- `src/solo_harness/studies/controlled_c1.py` — fixed case/contract validation, visual descriptor, optional formative literal-reply hint.
- `src/solo_harness/studies/controlled_c1_contracts.json` — all C1 scientific delivery contracts (C1.1 executable).
- `src/solo_harness/web.py`, `src/solo_harness/templates/partials/session_main.html`, `src/solo_harness/templates/partials/session/controlled_c11_visual.html`, `src/solo_harness/templates/session.html` — internal session flag and passive timeline visuals.
- `tests/test_controlled_c11_pilot_contract.py` — test cases **written but not executed**.

No DB migrations are added: existing JSON instructional state, move/content evidence, message traces and Conversation Judge decision records are reused.

## Codex integration instructions

1. Apply the supplied patch against the **matching uploaded snapshot**; if the working repo has evolved, review and merge hunks rather than overwriting changes. Preserve v0.4, existing v0.5 and current participant authorization controls.
2. Confirm `controlled_c1_contracts.json` is included in the built wheel/container. Validate the contract ID and SHA against the persisted active attempt; do not silently hot-edit a contract during a session.
3. Do not modify the original v0.5 scientific YAML or its SHA manifest; this is an opt-in runtime pilot, not a silently revised scientific package.
4. Run the newly provided unit tests plus all pertinent existing v0.5 integration/Conversation Judge/frontend/lifecycle tests **after integration**. The author did not execute tests.
5. Exercise internal test sessions for P1, P2 and P3. Verify exact move order, Tutor–Judge cycles, correct Yes/No facts and positions, no premature P2 reveal, learner IDK/wrong/tangential responses, `CONTINUE`/`ADVANCE`/`HOLD`, resumption after interruption, and restart/recovery from a persisted active move.
6. Confirm that direct `advance_v051_subsection` cannot bypass the pilot's required reviewed move evidence even if given a Judge decision. Check concurrency, duplicate deliveries, audit hashes and transaction rollback/retry.
7. Confirm all visual text is **server-generated**, accessible, semantically correct and displayed in the proper timeline position. Check responsive layout and absence of model-supplied markup. Check pilot visual content is not erroneously shown for later subsections.
8. Verify the assessment generator does not reuse the **exposed** fixed C1.1 examples in a scientifically consequential way. The current fingerprinting logic differs across scenario families, so collision avoidance across changed representations deserves explicit independent checking before a real study.
9. Check the research export path. The existing `research_export.py` exports messages, LLM calls and protocol events but does not currently export `SubsectionProgress` or `ConversationJudgeDecision` as dedicated tables. Expand the export with a schema version bump **if** the pilot's evaluation will rely on those detailed records; PostgreSQL already persists them.
10. Do not deploy to participants until scientific fidelity review and researcher approval. Staff-only internal endpoint and candidate status must stay intact.

## Known limitations requiring validation

- The assistant did not run any tests or live LLM sessions; provider-specific structured-output support, DB recovery, concurrent calls, real UX and the prompt's scientific behavior are unverified.
- A move can require multiple turns. The Judge is an LLM and its approval is **semantic evidence**, not an independently proven mathematical theorem. For C1.1, the fixed mapping/count facts are deterministic, but teaching-quality and learner-doubt judgments remain fallible.
- With the pilot enabled, a P2 guided move must await an actual learner chat turn. A silent learner has no automated fallback timer in this patch. Avoid interpreting the absence of a reply as a failure; staff should decide whether and how to offer an explicit "show me" affordance later.
- No end-of-section assessment behavior was altered. Pilot example exposure and assessment equivalence require explicit review.
- No treatment-independent measured fidelity, exposure duration, cognitive load, or learning outcome has yet been established by this source patch.

## Acceptance criterion for this handoff

The patch is ready for **Codex to integrate and test**, not for scientific deployment. The immediate success criterion is a verified internal C1.1 P1/P2/P3 conversation in which all authored moves receive real judged delivery evidence and the minimal static illustrations appear correctly, with all non-pilot paths unchanged.
