# EkagraAI — F1 Scientific Foundation v0.4 (candidate)

**Scope:** ONE topic, parity-based error detection within the inherited F1 bounds. NOT an implementation and NOT approved for research participants. The complete scientific specs and prompts here are candidate authoring artifacts for Codex to wire into the existing application.

## Read first

1. `01_SCIENTIFIC_DECISION_REGISTER.md` — scientific and architectural decisions.
2. `02_KNOWLEDGE_PACK.md`, `03_SOLO_TRANSITION_SPEC.md` — domain truth and observed outcome criteria.
3. `04_INTERVENTION_PACK.md` — three distinct pedagogical mechanisms × four SOLO transitions.
4. `05_ASSESSMENT_PACK.md` — **all 64 individually authored reusable item contracts**, not a bank of fixed questions.
5. `06_JUDGE_RUBRIC_PACK.md` — meaning-based judgment.
6. `07_PROMPT_CONTRACTS/` — actual LLM-facing instruction templates, using resolved scientific content.
7. `08_SCIENTIFIC_YAML/` — seven concise authoritative machine-readable files and validated references.
8. `09_REFERENCE_AND_TEST_CASES/` — mathematical verifier, independent examples and adversarial oracles.
9. `10_CONSISTENCY_VALIDATION.md` — checks actually run and remaining gates.
10. `11_CODEX_IMPLEMENTATION_HANDOFF.md` — engineering guidance: reuse infrastructure, integrate Docker soon, test with real LLM.

## Non-negotiable responsibility boundary

- Science authors fix question **family, conceptual evidence, possible scenarios, misconception meanings and general correctness rule**.
- Scenario generation chooses new parameters within F1 limits; an independent verifier computes the outcome for THAT instance.
- LLM realizes actual question and four options in natural prose; it MUST NOT define its own answer truth.
- Model-based semantic review checks meaning; syntactic checks/regex/ID equality cannot prove equivalence.
- The true answer is bound to one of four actual realized propositions, **after** validation and before freezing. No reusable contract has a correct letter or prescribed bit string.
- Learner's subjective reasoning is interpreted by a treatment-blind LLM Judge; no expected exact answer sentences.
- Backend alone applies inherited objective >=2/3 AND subjective >=1/2 gate, currently provisional.

## Exact counts

- 4 transitions (C1–C4), 3 pedagogies (P1–P3), 12 teaching cells.
- 16 blueprint families (four per transition).
- **48 independently specified MCQ contracts + 16 subjective contracts = 64.**
- Contracts are **reusable types**, not limits on how many questions the generator can create.

## No disposal of history

This ZIP intentionally contains the new scientific foundation only. Codex should move superseded historical candidate files to `old/` **after replacement integration succeeds**, preserving any production references, migrations and participant records. Do not delete files or add old packs to the new source-of-truth loader.

## Source provenance

Original pre-v0.3 `phase2.yaml` under `networks_error_detection_parity_checksum/v0.1` provides four family roles and the sixteen blueprint themes. The four attached full-length Phase 2 knowledge/intervention/assessment/judge Markdown drafts provide conceptual substance. v0.3's knowledge, SOLO, fidelity and Judge content provide candidate refinements. **This package changes their authority wherever they fixed examples, scoring, or prompts improperly.** No human scientific approval is implied.
