# Codebase integration handoff — candidate only

Use the existing F1 v0.4 pathways. **Do not replace the running service with these YAMLs by copying them into the v0.4 directory.** This package contains no runtime/database/frontend patch.

Verified baseline pathways in `EKAGRAAI_PROJECT_LATEST_CODE(2).zip`:

| Existing path | What should be extended for v0.5 |
|---|---|
| `src/solo_harness/studies/scientific_v04.py` | Preserve source-hash/versioned-load semantics; extend to ten YAML sources and five prompt sources. Add curriculum subsection, global pedagogy, parent C×P, child Cn.k×P and Conversation Judge resolvers. Maintain existing `compile_assessment` and blind `compile_judge` separation. |
| `src/solo_harness/runtime/v04_native.py` | Replace old one-flag Tutor wire with explicit move/content evidence (provisional schema in `TUTOR_PROMPT.md`); add independent Conversation Judge wire/dispatcher and validated scenario bindings. |
| `src/solo_harness/runtime/ai.py` | Stop treating Tutor's `teaching_complete` alone as an authoritative section completion. Introduce semantically supervised subsection advance, bounded repair and delivery exception events. |
| `src/solo_harness/runtime/engine.py` | Keep `complete_intervention` → `PAAS_PENDING` → Paas response → assessment; call it **only after every required subsection is instructionally complete**, verified and durably persisted. Preserve retry selection and unresolved terminal semantics. |
| Existing scenario generators and reference oracle | Extend to novice cases, full 2D construction, three-flip mimics, C3 reverse inference, and overlapping groups. Use the v0.4 oracle baseline and test suite; ensure actual case facts are checked before Tutor/Writer sees them. |
| Existing assessment generation / review / blind Judge | Preserve 16 blueprint IDs and 64 slot IDs, semantic review and formal Judge isolation. The old C2-A4 and C3-A4 contracts are intentionally replaced. |

## Minimal persisted state and provenance (suggested)

- Attempt: frozen `(section_id, pedagogy_id, protocol_version, curriculum_hash)`.
- Subsection: current ID, index, opened/closed timestamps, required content ledger, move ledger, status, clarification usage, optional final doubt opportunity, verified instructional case IDs.
- Conversation Judge event: reviewed turn IDs, resolved specification/hash, evidence citations, confidence, recommended action, runtime accepted/rejected transition and reason.
- Delivery exception: missing/invalid required facts and whether any repair was attempted; must not increment scientific assessment failures.
- Completion: evidence-backed closed subsections; section complete only when last closes. After that, unchanged Paas and independent assessment path.
- Assessment: exact generated instance, source slot, tested facts, stable option identities and final shuffled display key, reviewer outcome, formal Judge evidence; never exposed to Tutor/Conversation Judge.

## Candidate runtime rule skeleton

1. Resolve one active `(subsection, pedagogy)` child + its parent + its global pedagogy + locked scientific facts.
2. Tutor enacts the next required move or learner-requested clarification using a verified instructional instance; records claims, not authoritative completion.
3. Semantic Conversation Judge receives actual transcript and evidence ledger; interprets learner signal and recommends next action.
4. Deterministic state controller checks permitted move/subsection/assessment transitions, exposure and role isolation; rejects unsupported advancement.
5. If subsection complete, offer/honor its optional final doubt opportunity then advance to the next; a correct learner answer is not a pass.
6. If the last subsection completes, invoke the **existing** Paas gate; only its recorded response permits independent assessment generation.
7. On formal assessment failure, preserve existing next-unused pedagogy retry from the first subsection of the *same* section. Exhausted attempts remain unresolved per existing protocol.

## Mandatory before participant activation

- Human review of all scientific claims, 54 pedagogical cells and all 64 assessment contracts.
- Approval/calibration of candidate `core_tutor_messages_target_range`, P2 guidance rounds, clarification allowance and Judge invocation policy.
- Independent tests for self-reported completion spoofing, skipped mandatory content, learner silence, repeated "I don't know", pedagogical drift, late doubts and invented parity counts.
- Database concurrency/transaction recovery for two simultaneous Tutor/Conversation Judge responses and subsection advancement; source-hash pinning.
- Recheck form reuse/exhaustion and formal scoring reliability; do not treat synthetic demonstrations as measured learner gains.
