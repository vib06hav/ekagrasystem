# EkagraAI F1 — C1–C4 Coordinated Scientific Specification (v0.5.1 CORRECTED CANDIDATE)

**Status:** `CANDIDATE_UNAPPROVED_REQUIRES_HUMAN_REVIEW_AND_RUNTIME_INTEGRATION` — correction details in `CORRECTION_REPORT.md`.  
**Source of content:** `CURRICULUM_SOURCE_LOCKED.md` (the locked course v1.0, 8 November 2026).  
**Baseline consulted:** `EKAGRAAI_PROJECT_LATEST_CODE(2).zip`, F1 v0.4 scientific YAML, four prompt contracts and its reference parity oracle.  
**Scope:** parity-only F1 pilot, NOT the broader professor three-topic Experiment 1.  
**No codebase modified:** this is a standalone, candidate authoring/validation package, **not** an executable upgrade to the existing service.

## Inventory

`08_SCIENTIFIC_YAML/`: 10 files — `curriculum.yaml`, `knowledge.yaml`, `transitions.yaml`, `interventions.yaml`, `subsection_interventions.yaml`, `conversation_judge.yaml`, `scenario_rules.yaml`, `assessment_families.yaml`, `judge.yaml`, `protocol.yaml`.

`07_PROMPT_CONTRACTS/`: 5 role contracts — `TUTOR_PROMPT.md`, `CONVERSATION_JUDGE_PROMPT.md`, `ASSESSMENT_GENERATION_PROMPT.md`, `SEMANTIC_REVIEW_PROMPT.md`, `SUBJECTIVE_JUDGE_PROMPT.md`.

Teaching: 3 global P1/P2/P3 mechanisms; 12 section×pedagogy cells; 39 subsection×pedagogy cells, each tied to every applicable locked content bullet. **54 treatment-specific teaching specifications**, not 54 duplicated system prompts. The Tutor file is a thin technical execution contract, **not a fourth general teaching pedagogy**.

Assessment: **16 blueprints, 64 item contracts** (48 MCQs, 16 subjective), preserving the inherited IDs and slot structure. Assessment items are **not** fixed learner-visible questions.

`09_REFERENCE_AND_VALIDATION/`: executable mathematical/structural check, source parity-oracle copy and reports.

## Source vs design status

- **LOCKED content:** source Markdown → `curriculum.yaml` verbatim content bullet text, section order and teaching goals; pedagogical/assessment specifications must not override.
- **Inherited research controls:** one formal major-section assessment (3 MCQs + 1 subjective); Paas before assessment; treatment-blind Subjective Judge; initial pedagogy assignment and without-replacement fallback from old protocol; unresolved exhausted treatment behavior preserved.
- **New agreed teaching architecture:** fixed pedagogy across an attempted major section, in-order subsections, content-specific teaching moves, semantic LLM Conversation Judge, no subsection mastery gate.
- **Candidate unapproved choices:** numeric exposure ranges, clarification caps, Judge invocation after every meaningful learner turn and on close, technical-recovery details. Their inclusion makes them inspectable; it **does not** constitute experimental approval or empirical calibration.
- **Assessment reauthoring:** legacy C2-A4 four-flip rectangle moved OUT of C2; C2-A4 now tests distinct two-bit detection versus correction. Former C3-A4 cost/overhead focus replaced by familiar-grid reverse-inference ambiguity and undetected rectangle. C4-A1 explicitly introduces overlapping groups. Other inherited assessment slots remain subject to item-by-item human semantic review.

## How the three teaching layers combine

1. The locked subsection/knowledge/verified scenario resolves **what** is scientifically permitted.
2. The selected global pedagogy `P1/P2/P3` resolves **how reasoning is disclosed and scaffolded**.
3. The parent `Cn-Pm` section cell resolves **the section-level instructional trajectory and SOLO boundary**.
4. The child `Cn.k-Pm` cell resolves **ordered, observable local teaching moves, clarification/fallback and completion evidence**.
5. The Tutor realizes learner-facing wording and valid scenario choices. The **LLM Conversation Judge** interprets dialogue and audits delivery; the runtime enforces state legality/budgets. Neither conducts or preempts formal SOLO assessment.

**Authority in a conflict:** locked course scientific truth > scientific invariants/oracle > protocol/role isolation > global pedagogy > section×pedagogy > subsection×pedagogy > generated instance/conversational styling. The system must flag unresolved conflicts rather than silently rewriting curriculum or study protocol.

## Candidate teaching process

1. At each subsection the Tutor enacts the authored `core_moves` through the assigned pedagogy. A move is **not** a fixed number of messages. P2 may require more learner dialogue than P1.
2. The Conversation Judge semantically assesses the learner's actual utterances and observable substantive explanation; it may recommend `CONTINUE_TEACHING`, `CLARIFY_OR_SCAFFOLD`, `CONSOLIDATE`, `ADVANCE_SUBSECTION`, `DELIVERY_EXCEPTION`.
3. A learner saying "I don't know" triggers bounded pedagogy-compliant support and eventual explicit accurate consolidation, not a hidden quiz or automatic early formal assessment.
4. A subsection can advance only after ALL required facts/moves have been substantively delivered and optional final doubt opportunity handled. Learner correctness **never** provides this evidence.
5. After the last subsection, use **Paas → independent formal assessment**. If formal assessment fails, retry the same major section with the next available pedagogy according to inherited without-replacement protocol. Failure to deliver essential instruction is a **technical hold**, not a learner failure.

## Why this is NOT drop-in compatible

The v0.4 loader expects **7 YAML files + 4 prompt files**, has no persistent subsection record and no Conversation Judge invocation/state. Its Tutor wire response allows `teaching_complete: bool`, which does not implement evidence-backed move completion. Integration needs a new versioned loader/parser, science/compiler resolvers, schema and state machine, scenario-oracle extension, LLM role dispatch and UI/DB state. **Do not overwrite v0.4 or claim the research study has been validated by this package.**

## Integration acceptance gates

1. Cross-file stable ID/reference completeness and scientific scope validation.
2. Mathematical exhaustive tests for 1D parity, full-grid single/two-flip results, rectangle misses, three-flip syndrome mimic and grouped checks.
3. Human content review of all 54 teaching specifications and 64 item slots, including unstated prerequisites and natural-language ambiguity.
4. Tutor + Conversation Judge controlled transcript tests across all subsection/pedagogy combinations and repeated learner confusion.
5. Human assessment item audits and formal Subjective Judge calibration; confirm published study protocol, bias/latency/exposure and technical-hold behavior.
6. Only thereafter consider participant-facing activation.

## How to validate

From this package directory: `python 09_REFERENCE_AND_VALIDATION/validate_package.py`. Requires Python + PyYAML. Writes a text report next to the script. The audit checks internal candidate coherence; it is **not** proof of treatment fidelity in actual LLM sessions or validity of generated assessment items.
