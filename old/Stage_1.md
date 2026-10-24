# Stage 1 — Core Data and Software Structure Design

**System:** SOLO-Transition AI Learning Harness  
**Initial study:** Recursive Fibonacci with Memoization  
**Status:** Proposed technical design for human review  
**Scope:** Repository, operational study representation, domain models, validation, compilation, persistence, version freezing, startup, and Stage-1 tests. No implementation is included.

---

## 1. Understanding of the current system

The system is a local-first FastAPI/PostgreSQL modular monolith that executes an externally authored, versioned learning study.

The authority boundaries are:

1. `AI_Harness_Study_Pack_Specification.md` defines the research architecture and invariants.
2. `01_Knowledge_Pack.md` through `05_Protocol_Config.md` define the concrete Fibonacci study.
3. `AI_Harness_High_Level_Design.md` defines runtime subsystem boundaries.
4. `README.md` and `MANIFEST.md` describe the package and its inventory.

The supplied manifest hashes match the current Markdown study files.

The authority and runtime distinction is:

```text
Human-readable Markdown
    provenance and research/design authority
            ↓ reviewed transcription
Operational YAML
    reviewed/frozen executable source of truth for one study version
            ↓ validation and compilation
CompiledStudy
    compiler-specific immutable runtime representation
            ↓ frozen snapshot
Immutable StudyVersion in PostgreSQL
    contains authored identity + compiled runtime snapshot identity
            ↓
Session
    permanently bound through study_version_id
```

Once an operational YAML package has been reviewed and frozen, runtime behavior is defined by that package. The Markdown documents remain provenance and design authority; they are not a second runtime input and need not be kept dynamically synchronized with an already frozen operational version. A later approved content change produces a new operational study version.

### Fixed study invariants

The design preserves:

- Knowledge Pack as semantic authority.
- Five ordered SOLO states: P, U, M, R, EA.
- Four transitions: C1 through C4.
- Three pedagogy families.
- Twelve transition × pedagogy intervention cells.
- One assessment family and four forms per transition.
- Assessment selection independent of pedagogy.
- One transition-specific Judge rubric per transition.
- At most three pedagogies per transition, without replacement.
- No renewed pedagogy cycle.
- Formal advancement by exactly one transition.
- Judge blindness to intervention and attempt history.
- Backend/database authority over runtime state.
- Preservation of raw learner and model evidence.
- Separation of protocol configuration from environment configuration.

### Architectural shape

This is a modular monolith, not a microservice system. Domain rules, study loading, persistence, and the later AI runtime remain separate modules inside one application process.

SQLAlchemy is used directly through focused query/service modules. A generic repository framework is unnecessary for the POC.

### Known inconsistencies or unresolved points

No direct contradiction was found in the core experimental design. The following wording and completeness issues require explicit treatment:

- The Assessment Pack says forms “should not” be reused, while the specification, HLD, protocol, and requested invariants effectively require no reuse. This design applies the stronger rule: **an assessment form MUST NOT be reused in a session**.
- Exact intervention budgets are not defined.
- Baseline/pre-transition assessments remain undecided.
- Whether technical LLM failures consume an experimental attempt remains undecided.
- Assessment equivalence and treatment fidelity cannot be proven entirely by schema validation; they still require human review.
- The one-time workflow for reviewing and freezing an operational YAML version from the Markdown provenance is not specified. After that freeze, YAML alone is executable for that version.

---

## 2. Proposed repository structure

```text
ekagrasystem/
├── pyproject.toml
├── alembic.ini
├── compose.yaml
├── Dockerfile
├── .dockerignore
├── .env.example
├── README.md
│
├── src/
│   └── solo_harness/
│       ├── __init__.py
│       ├── main.py
│       ├── bootstrap.py
│       ├── config.py
│       │
│       ├── web/
│       │   ├── __init__.py
│       │   ├── dependencies.py
│       │   └── routers/
│       │       ├── __init__.py
│       │       ├── health.py
│       │       └── sessions.py
│       │
│       ├── studies/
│       │   ├── __init__.py
│       │   ├── authored/
│       │   │   ├── __init__.py
│       │   │   ├── common.py
│       │   │   ├── manifest.py
│       │   │   ├── knowledge.py
│       │   │   ├── intervention.py
│       │   │   ├── assessment.py
│       │   │   ├── judge.py
│       │   │   └── protocol.py
│       │   ├── compiled/
│       │   │   ├── __init__.py
│       │   │   ├── models.py
│       │   │   ├── indexes.py
│       │   │   └── serialization.py
│       │   ├── loader.py
│       │   ├── compiler.py
│       │   ├── canonicalization.py
│       │   ├── catalog.py
│       │   ├── activation.py
│       │   └── validation/
│       │       ├── __init__.py
│       │       ├── errors.py
│       │       ├── local.py
│       │       ├── references.py
│       │       ├── completeness.py
│       │       ├── protocol.py
│       │       └── knowledge_boundaries.py
│       │
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── identifiers.py
│       │   ├── enums.py
│       │   ├── session_state.py
│       │   ├── attempts.py
│       │   └── protocol_rules.py
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── study_service.py
│       │   ├── session_service.py
│       │   └── event_service.py
│       │
│       ├── db/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── engine.py
│       │   ├── unit_of_work.py
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   ├── study.py
│       │   │   ├── session.py
│       │   │   ├── attempt.py
│       │   │   ├── interaction.py
│       │   │   ├── assessment.py
│       │   │   ├── judgment.py
│       │   │   ├── llm.py
│       │   │   └── audit.py
│       │   └── queries/
│       │       ├── studies.py
│       │       ├── sessions.py
│       │       ├── attempts.py
│       │       └── events.py
│       │
│       ├── runtime/
│       │   ├── __init__.py
│       │   ├── ports.py
│       │   └── placeholders.py
│       │
│       ├── templates/
│       │   └── .gitkeep
│       └── static/
│           └── .gitkeep
│
├── studies/
│   └── python_fibonacci_memoization/
│       └── v0.1/
│           ├── study.yaml
│           ├── knowledge.yaml
│           ├── intervention/
│           │   ├── pedagogies.yaml
│           │   └── cells/
│           │       ├── c1.yaml
│           │       ├── c2.yaml
│           │       ├── c3.yaml
│           │       └── c4.yaml
│           ├── assessment/
│           │   ├── c1.yaml
│           │   ├── c2.yaml
│           │   ├── c3.yaml
│           │   └── c4.yaml
│           ├── judge/
│           │   ├── contract.yaml
│           │   └── rubrics.yaml
│           └── protocol.yaml
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── scripts/
│   ├── validate_study.py
│   └── inspect_study.py
│
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   └── studies/
    │       ├── valid_minimal/
    │       ├── duplicate_ids/
    │       ├── broken_reference/
    │       ├── incomplete_matrix/
    │       └── insufficient_assessments/
    ├── unit/
    │   ├── studies/
    │   │   ├── test_parsing.py
    │   │   ├── test_local_validation.py
    │   │   ├── test_cross_pack_validation.py
    │   │   ├── test_compilation.py
    │   │   └── test_hashing.py
    │   └── domain/
    │       └── test_session_state.py
    └── integration/
        └── db/
            ├── test_study_versions.py
            ├── test_session_binding.py
            ├── test_constraints.py
            └── test_events.py
```

### Responsibilities

| Area | Responsibility |
|---|---|
| `studies/authored` | Strict Pydantic models representing exactly what authors may write. |
| `studies/compiled` | Immutable resolved runtime representation and snapshot schema. |
| `studies/validation` | Local, reference, completeness, protocol, and knowledge-boundary checks. |
| `studies/loader.py` | Reads only files declared by `study.yaml`; performs safe YAML parsing. |
| `studies/compiler.py` | Resolves IDs, materializes knowledge slices, and constructs indexes. |
| `studies/canonicalization.py` | Produces separate deterministic authored-content and compiled-snapshot canonical bytes/hashes. |
| `studies/catalog.py` | Provides CompiledStudy objects from the Session-bound StudyVersion. |
| `studies/activation.py` | Inserts immutable StudyVersion records and changes the active-version pointer. |
| `domain` | Study-independent identifiers, session states, and protocol invariants. |
| `services` | Application transaction boundaries and orchestration. |
| `db/models` | SQLAlchemy 2 persistence mappings. |
| `db/queries` | Focused database operations without a generic repository abstraction. |
| `runtime/ports.py` | Minimal future-facing interfaces for Tutor/Judge/provider services. |
| `studies/` | External declarative study data; no Python code. |
| `migrations/` | Linear, reviewed Alembic schema history. |
| `templates` / `static` | Empty placeholders for later UI stages. |
| `tests/fixtures/studies` | Small purpose-built valid and invalid operational study packages. |

`config.py` contains infrastructure settings only: database URL, study directory, logging, AICredits credentials/endpoint settings through the provider-neutral adapter, and model configuration. It must not contain protocol rules.

---

## 3. Operational study-definition format

### 3.1 Format choice

Use **YAML 1.2** parsed with a safe `ruamel.yaml` configuration.

Reasons:

- Better reviewability than JSON for long instructional prose and code.
- Natural multiline block scalars.
- Declarative structure without executable behavior.
- Duplicate mapping keys can be rejected.
- YAML 1.2 avoids several YAML 1.1 implicit-boolean surprises.

Restrictions:

- No custom YAML tags.
- No executable constructors.
- No merge keys or aliases.
- No duplicate mapping keys.
- No implicit timestamps.
- IDs and version values must be quoted.
- Multiline instructional text uses `|-` or `|`.
- All Pydantic models use `extra="forbid"`.

### 3.2 File organization

The five study components remain logically separate:

- Knowledge: `knowledge.yaml`
- Intervention: `intervention/`
- Assessment: `assessment/`
- Judge: `judge/`
- Protocol: `protocol.yaml`

Large repeated collections are divided by transition for reviewability. `study.yaml` explicitly lists every file; discovery by unrestricted directory glob is prohibited.

This makes the package closed and hashable: an unlisted file cannot silently become runtime content.

### 3.3 Stable IDs and references

IDs are case-sensitive strings matching:

```text
^[A-Za-z][A-Za-z0-9._-]*$
```

Examples: `K5`, `R3`, `C3`, `P2`, `C3-A1`, `C3-E4`.

Rules:

- Semantic IDs are globally unique within a study.
- IDs remain stable across study versions when their semantic identity remains the same.
- Published IDs are never recycled for different meanings.
- If an entity changes meaning materially, it receives a new ID.
- References are IDs in type-specific fields such as `target_kc_ids`; arbitrary JSON pointers are not used.
- Material tags have a separate namespace because they identify examples or surfaces, not semantic entities.

### 3.4 Version metadata

`study.yaml` owns atomic study version metadata. Individual component files do not have independently activatable versions.

```yaml
schema_version: "1.0"

study:
  id: "python_fibonacci_memoization"
  content_version: "0.1"
  title: "Recursive Fibonacci with Memoization"
  domain: "Python Programming"
  topic: "Recursive Fibonacci with Memoization"

sources:
  markdown_manifest_sha256: "..."
  notes: |-
    Operational transcription of the v0.1 Markdown study package. Once this
    YAML package is reviewed and frozen, it is the executable source of truth
    for this study version.

components:
  knowledge: "knowledge.yaml"
  pedagogy_families: "intervention/pedagogies.yaml"
  intervention_cells:
    - "intervention/cells/c1.yaml"
    - "intervention/cells/c2.yaml"
    - "intervention/cells/c3.yaml"
    - "intervention/cells/c4.yaml"
  assessment_families:
    - "assessment/c1.yaml"
    - "assessment/c2.yaml"
    - "assessment/c3.yaml"
    - "assessment/c4.yaml"
  judge_contract: "judge/contract.yaml"
  judge_rubrics: "judge/rubrics.yaml"
  protocol: "protocol.yaml"
```

The architecture has no `draft`/`runnable` research-approval gate. An operational package may execute when it is frozen, structurally valid, and contains every runtime-required configuration value. Descriptive labels in the source Markdown do not control activation.

### 3.5 Representative Knowledge Pack content

```yaml
pack_id: "knowledge.python_fibonacci_memoization"

prerequisites:
  - id: "PREREQ_PYTHON_FUNCTIONS"
    statement: "Can read a basic Python function definition and return statement."

frontier:
  - id: "SCOPE_REPEATED_SUBPROBLEMS"
    classification: "in_scope"
    statement: "Repeated subproblems in naive recursive Fibonacci."
  - id: "OUT_TABULATION"
    classification: "out_of_scope"
    statement: "Bottom-up tabulation."

knowledge_components:
  - id: "K5"
    title: "Repeated subproblems"
    definition: |-
      During naive recursive evaluation, the same smaller input such as
      fib(3) can be requested from more than one branch.

knowledge_relations:
  - id: "R3"
    title: "Repeated subproblems cause repeated computation"
    premise_kc_ids: ["K5"]
    result_kc_ids: ["K6"]
    statement: |-
      If earlier solved results are not retained, a repeated request for the
      same subproblem causes its recursive computation to be performed again.

misconceptions:
  - id: "M4"
    title: "Memoization changes the Fibonacci recurrence"
    description: |-
      The learner claims that memoization changes the mathematical definition
      of Fibonacci.
    conflicts_with_kc_ids: ["K2", "K10"]
    conflicts_with_relation_ids: ["R8"]

solo_states:
  - id: "R"
    rank: 3
    title: "Relational"
    definition: |-
      The learner integrates repeated subproblems, storage, lookup, reuse,
      and avoided recomputation into one coherent causal mechanism.

transitions:
  - id: "C3"
    ordinal: 3
    from_state_id: "M"
    to_state_id: "R"
    structural_change: |-
      Multiple correct but partly separate pieces become one integrated
      causal memoization mechanism.
    assumed_kc_ids: ["K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9"]
    target_kc_ids: ["K10", "K11"]
    target_relation_ids: ["R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"]
    relevant_misconception_ids: ["M3", "M4", "M5", "M6", "M7", "M8", "M9"]
    not_yet_required_kc_ids: ["K12", "K13", "K14"]
```

### 3.6 Representative pedagogy family

```yaml
pedagogy_families:
  - id: "P2"
    title: "Guided Questioning"
    delivery_mode: "guided_questioning"
    core_mechanism: |-
      Guide the learner to construct the missing organization through
      bounded, sequenced questions.
    permissions:
      - "Ask targeted prediction and justification questions."
      - "Provide minimal factual clarification."
    prohibitions:
      - "Present the complete target reasoning before the learner constructs it."
      - "Switch to a worked-example treatment."
    fidelity_test: |-
      The learner must perform the relation-building cognitive work.
```

### 3.7 Representative intervention cell

```yaml
intervention_cells:
  - id: "C3-P2"
    transition_id: "C3"
    pedagogy_id: "P2"

    knowledge_refs:
      assumed_kc_ids: ["K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9"]
      target_kc_ids: ["K10", "K11"]
      target_relation_ids: ["R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"]
      misconception_ids: ["M3", "M4", "M5", "M6", "M7", "M8", "M9"]
      prohibited_kc_ids: ["K12", "K13", "K14"]
      prohibited_scope_ids: ["OUT_TABULATION"]

    instructional_intent: |-
      Guide the learner to construct the integrated causal memoization
      mechanism while preserving the Fibonacci recurrence.

    missing_structure: |-
      The learner has relevant pieces but has not causally connected repeated
      requests, recomputation, storage, lookup, and reuse.

    procedure:
      - id: "C3-P2-S1"
        function: "establish_repetition"
        guidance: "Ask which fib(k) occurs in more than one branch."
      - id: "C3-P2-S2"
        function: "establish_recomputation"
        guidance: "Ask what happens when no earlier result is retained."
      - id: "C3-P2-S3"
        function: "integrate"
        guidance: |-
          Ask the learner to connect repeated request, storage, later lookup,
          reuse, and avoided recursive work.

    material:
      material_ids: ["c3_gq_call_tree_01"]
      prohibited_material_tags:
        - "c3_code_alpha"
        - "c3_explanations_beta"
        - "c3_second_request_gamma"
        - "c3_mechanism_delta"

    completion:
      condition: |-
        The learner has substantially constructed the causal mechanism, or
        the hard intervention budget is reached.
      budget:
        max_tutor_turns: 8
        max_elapsed_seconds: 900
```

Where the runtime requires hard limits, the operational study must provide explicit positive values. The numbers above illustrate the schema; the actual values are study-configuration decisions that must be chosen before that operational version is frozen. Missing required budgets are configuration-validation errors, not research-approval or document-status failures.

### 3.8 Representative assessment family and form

```yaml
assessment_families:
  - id: "AF-C3"
    transition_id: "C3"
    target_kc_ids: ["K10", "K11"]
    target_relation_ids: ["R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"]
    required_observations:
      - "Connect repeated subproblems to otherwise repeated computation."
      - "Explain storage and later lookup/reuse."
      - "Preserve the Fibonacci recurrence."
    equivalence_envelope:
      conceptual_demand: "causal_integration"
      python_burden: "basic"
      explanation_required: true
      prohibited_scope_ids: ["OUT_TABULATION"]
    forms:
      - id: "C3-A1"
        active: true
        material_tags: ["c3_code_alpha"]
        prompt: |-
          During the calculation of fib(6), some smaller Fibonacci values are
          requested more than once. Explain what happens the first time one is
          calculated and when it is requested later. Explain why this performs
          less repeated work and whether the recurrence changes.
        hidden_scoring_context: |-
          Expected: repeated subproblem, first computation, stored mapping,
          later lookup, reuse, avoided expansion, recurrence unchanged.
```

Assessment models contain no pedagogy ID or pedagogy-specific selector metadata.

### 3.9 Representative Judge rubric

```yaml
rubrics:
  - id: "JR-C3"
    transition_id: "C3"
    target_state_id: "R"
    required_kc_ids: ["K10", "K11"]
    blocking_misconception_ids: ["M3", "M4", "M5", "M6", "M7", "M8", "M9"]

    evidence_criteria:
      - id: "C3-E1"
        description: "Connects repeated requests to redundant computation."
        kc_ids: ["K5", "K6"]
        relation_ids: ["R3"]
      - id: "C3-E2"
        description: "Explains correct input-to-result storage."
        kc_ids: ["K7"]
        relation_ids: ["R4"]
      - id: "C3-E3"
        description: "Explains lookup and reuse before redundant expansion."
        kc_ids: ["K8", "K9"]
        relation_ids: ["R5"]
      - id: "C3-E4"
        description: "Integrates the elements into one causal chain."
        kc_ids: ["K10", "K11"]
        relation_ids: ["R6", "R7"]
      - id: "C3-E5"
        description: "Recognizes that the recurrence remains unchanged."
        relation_ids: ["R8"]

    success_rule:
      requires_gradable: true
      correctness_requirement: "materially_sound"
      observed_state_at_least: "R"
      evidence_all_of: ["C3-E1", "C3-E2", "C3-E3", "C3-E4"]
      evidence_any_of_groups: []
      minimum_evidence_count: null
      reject_detected_misconception_ids:
        - "M3"
        - "M4"
        - "M5"
        - "M6"
        - "M7"
        - "M8"
        - "M9"

    form_requirements:
      "C3-A1":
        evidence_all_of: ["C3-E5"]
```

The success rule is a restricted declarative structure, not an expression language and not executable Python.

### 3.10 Representative protocol configuration

```yaml
protocol_id: "PROTO-SOLO-POC-1"

initial_state_id: "P"
transition_order: ["C1", "C2", "C3", "C4"]
pedagogy_ids: ["P1", "P2", "P3"]

pedagogy_selection:
  strategy: "random_without_replacement"
  reset_scope: "per_transition"
  max_attempts_per_transition: 3
  renewed_cycle: false

assessment_selection:
  strategy: "random_unseen"
  family_scope: "current_transition"
  exclude_seen_in_session: true
  pedagogy_may_influence_selection: false
  assessment_after_each_intervention: true
  max_post_intervention_assessments: 3
  minimum_reserve_forms: 1

progression:
  formal_advance: "exactly_one_transition"
  on_success: "next_transition"
  on_failure_with_unused_pedagogy: "next_attempt"
  on_pedagogies_exhausted: "mark_unresolved_and_stop"

history:
  include_prior_attempt_summaries: true
  expose_future_assessments: false
  expose_hidden_scoring_context: false
  expose_judge_hidden_reasoning: false
```

---

## 4. Pydantic/domain model design

### 4.1 Authored models

All authored models inherit from a common Pydantic v2 base configured with:

- `extra="forbid"`
- strict scalar validation
- whitespace-preserving natural-language fields
- required IDs without inferred defaults
- immutable instances after validation

Important models and fields:

| Model | Principal fields |
|---|---|
| `StudyManifest` | `schema_version`, `study`, `sources`, `components` |
| `StudyMetadata` | `id`, `content_version`, `title`, `domain`, `topic` |
| `ComponentPaths` | Explicit paths/lists for all five components |
| `KnowledgePack` | `pack_id`, `prerequisites`, `frontier`, `knowledge_components`, `knowledge_relations`, `misconceptions`, `solo_states`, `transitions` |
| `KnowledgeComponent` | `id`, `title`, `definition` |
| `KnowledgeRelation` | `id`, `title`, `premise_kc_ids`, `result_kc_ids`, `statement` |
| `Misconception` | `id`, `title`, `description`, conflicting KC/relation IDs |
| `SoloState` | `id`, `rank`, `title`, `definition` |
| `Transition` | `id`, `ordinal`, states, assumed/target/future IDs, misconceptions, structural change |
| `PedagogyFamily` | `id`, `title`, `delivery_mode`, mechanism, permissions, prohibitions, fidelity test |
| `InterventionCell` | `id`, transition/pedagogy IDs, `knowledge_refs`, intent, procedure, material, completion |
| `AssessmentFamily` | `id`, `transition_id`, target references, required observations, equivalence envelope, forms |
| `AssessmentForm` | `id`, `active`, `material_tags`, `prompt`, `hidden_scoring_context` |
| `JudgeContract` | Generic obligations, prohibitions, and output concepts |
| `JudgeRubric` | Transition/state IDs, criteria, blocking misconceptions, success rule, form requirements |
| `EvidenceCriterion` | `id`, description, KC/relation references |
| `SuccessRule` | Gradability, correctness, state threshold, evidence groups/counts, blocking misconceptions |
| `ProtocolConfiguration` | State/transition order, pedagogy set, selection, capacity, progression, history policies |
| `AuthoredStudy` | Aggregate of the manifest and all five parsed components |

Lists remain lists in authored models because author order is reviewable and sometimes meaningful.

### 4.2 Typed identifiers

Implementation should define constrained identifier types such as:

```text
EntityId
KnowledgeComponentId
RelationId
MisconceptionId
SoloStateId
TransitionId
PedagogyId
AssessmentFamilyId
AssessmentFormId
RubricId
EvidenceCriterionId
```

At runtime these may all serialize as strings, but distinct Python types reduce accidental cross-namespace use.

### 4.3 Compiled/resolved models

Compiled models are immutable domain objects. Collections exposed to runtime services are tuples or read-only mappings.

Important compiled types:

| Model | Resolved content |
|---|---|
| `CompiledKnowledgeRelation` | Direct references to premise/result `KnowledgeComponent` objects |
| `CompiledTransition` | Direct references to source/target states, KCs, relations, and misconceptions |
| `KnowledgeSlice` | Transition-specific assumed, target, relation, misconception, and future boundaries |
| `CompiledInterventionCell` | Resolved transition, pedagogy, Knowledge Slice, and referenced semantic objects |
| `CompiledAssessmentFamily` | Resolved transition and target semantic objects; forms indexed by ID |
| `CompiledJudgeRubric` | Resolved transition, state, KCs, misconceptions, evidence rules, and form requirements |
| `CompiledTransitionPlan` | One transition plus its three cells, assessment family, rubric, and protocol position |
| `CompiledStudy` | Complete immutable aggregate and all indexes |

### 4.4 Authored versus compiled distinction

Authored models retain ID references because they correspond directly to YAML and produce meaningful validation locations.

Compilation resolves:

- Transition state IDs into `SoloState` objects.
- KC, relation, and misconception IDs into their objects.
- Cell transition and pedagogy references.
- Assessment transition references.
- Judge criteria and assessment-form references.
- Protocol order into `CompiledTransitionPlan` objects.
- Transition-specific Knowledge Slices.
- The complete intervention matrix.
- Active assessment pools and their capacity.
- Rubric evidence lookup tables.

Runtime services do not repeatedly scan lists or reload YAML.

---

## 5. Study loading and validation

### 5.1 Lifecycle

```text
study.yaml
    ↓
resolve declared paths safely inside study root
    ↓
safe YAML parsing
    ↓
strict Pydantic validation
    ↓
cross-pack validation
    ↓
canonical compilation
    ↓
authored-content canonicalization + content SHA-256
    ↓
compiled-snapshot canonicalization + snapshot SHA-256
    ↓
immutable StudyVersion insertion/reuse, including compiled snapshot
    ↓
activation for new sessions
```

A path may not escape the study root after resolution. Symlinks resolving outside the mounted root are rejected.

### 5.2 Local validation

Local validation occurs before cross-reference resolution:

- YAML syntax.
- Duplicate mapping keys.
- Missing required fields.
- Unknown fields.
- Incorrect scalar/list/object types.
- Invalid or empty IDs.
- Invalid enum literals.
- Empty required prose.
- Duplicate IDs within one collection.
- Invalid state ranks or transition ordinals.
- Negative/zero capacities and budgets.
- Invalid success-rule shape.
- Invalid form or cell structure for its declared type.
- Missing or non-positive runtime budgets when the selected protocol requires hard limits.
- Pedagogy-specific structural requirements:
  - Guided Questioning requires a question-driven procedure.
  - Contrasting Cases requires at least two aligned cases or a declared contrast structure.
  - Worked Example requires modeled reasoning material.

The last checks confirm structural presence, not pedagogical quality.

### 5.3 Cross-pack validation

Global validation runs only after all component files parse.

It verifies:

1. **ID integrity**
   - All semantic IDs are globally unique.
   - IDs are present where required.
   - No ID is defined with two entity types.

2. **Reference integrity**
   - All typed references exist.
   - Reference target types are correct.
   - Transition, pedagogy, KC, relation, misconception, state, form, rubric, and evidence references resolve.

3. **SOLO topology**
   - Exactly five states exist for the POC profile.
   - State ranks are contiguous.
   - Exactly four ordered transitions connect adjacent states.
   - Protocol order starts at the configured initial state.
   - Every transition’s target state is the next transition’s source state.
   - No transition is repeated or skipped.

4. **Intervention matrix**
   - Exactly one cell exists for every configured transition/pedagogy pair.
   - The POC matrix is exactly 4 × 3.
   - No duplicate pair or unconfigured extra cell exists.
   - Cell target knowledge is consistent with its transition.
   - Cell pedagogy mechanism matches the referenced family.

5. **Assessment completeness**
   - Exactly one active family exists per transition.
   - Every active form has a unique ID and material tags.
   - Number of active unseen forms is at least:
     `max_post_intervention_assessments + minimum_reserve_forms`.
   - For the current POC, this requires at least four active forms per transition.
   - Assessment data has no pedagogy-specific selection field.

6. **Judge completeness**
   - Exactly one rubric exists per transition.
   - Every success-rule evidence ID belongs to that rubric.
   - Every form requirement references a form in the corresponding assessment family.
   - Blocking misconceptions exist in the Knowledge Pack.
   - Target state is compatible with the transition.

7. **Protocol integrity**
   - All transitions and pedagogies exist.
   - `max_attempts_per_transition` does not exceed the number of configured pedagogies.
   - Without-replacement selection is compatible with maximum attempts.
   - `renewed_cycle` is false for this POC.
   - Assessment capacity supports all possible attempts.
   - Progression is exactly one transition at a time.

8. **Knowledge boundaries**
   - Assumed, target, future, and prohibited KC sets do not overlap illegally.
   - A cell cannot target a KC assigned only to a future transition.
   - An assessment cannot require a future KC.
   - Structured out-of-scope IDs cannot appear as required instructional or assessment content.
   - Intervention material tags cannot equal reserved assessment material tags.

Natural-language semantic leakage cannot be proven mechanically. Structured references and material-tag collisions are enforced; prose still requires human review.

### 5.4 Error reporting

Validation collects all safely discoverable errors rather than failing after the first one.

Each issue contains:

```text
severity
code
file
line/column when available
model path
entity ID when available
message
related IDs
suggested author action
```

Example:

```text
ERROR ASSESSMENT_CAPACITY
assessment/c3.yaml
assessment_families[0].forms
transition=C3
Expected at least 4 active forms; found 3.
Protocol permits 3 attempts and requires 1 reserve form.
```

Errors block compilation or activation. Warnings never cause automatic correction. The loader must not invent IDs, drop invalid entries, reuse assessment forms, or fill missing matrix cells.

---

## 6. CompiledStudy design

`CompiledStudy` is the sole runtime entry point to study content.

Conceptually it contains:

```text
CompiledStudy
├── identity
│   ├── study_id
│   ├── content_version
│   ├── schema_version
│   ├── content_hash
│   ├── compiler_contract_version
│   ├── snapshot_schema_version
│   └── snapshot_hash
├── authored_definition
├── knowledge_pack
├── pedagogy_families
├── intervention_cells
├── assessment_families
├── judge_contract
├── judge_rubrics
├── protocol
├── transition_plans
├── knowledge_slices
└── indexes
```

### Precomputed indexes

At minimum:

- `entity_by_id`
- `state_by_id`
- `kc_by_id`
- `relation_by_id`
- `misconception_by_id`
- `transition_by_id`
- `pedagogy_by_id`
- `cell_by_transition_and_pedagogy`
- `assessment_family_by_transition`
- `assessment_form_by_id`
- `assessment_forms_by_transition`
- `rubric_by_transition`
- `evidence_criterion_by_id`
- `transition_plan_by_id`
- `transition_position_by_id`

### Knowledge Slices

Each transition gets a materialized immutable `KnowledgeSlice`:

```text
transition
source and target states
assumed KCs
target KCs
target relations
relevant misconceptions
not-yet-required KCs
prohibited scope items
structural-change description
```

This information could be derived, but materializing it once:

- centralizes precedence rules;
- prevents different runtime components deriving subtly different slices;
- makes snapshot inspection easier;
- keeps prompt composition deterministic later.

### Immutability

Compiled models must be deeply immutable:

- frozen objects;
- tuples instead of mutable lists;
- read-only mappings instead of dictionaries;
- no setter or mutation APIs.

Runtime access is through a process-level `StudyCatalog` keyed by database `study_version_id`. A cache miss loads the compiled snapshot stored inside that immutable StudyVersion, verifies its snapshot hash and schema, and reconstructs the immutable object. Runtime code never reads study YAML directly during participant execution.

---

## 7. Study versioning and freezing

### 7.1 Authored content identity and hash

The immutable authored-content `content_hash` is SHA-256 over canonical UTF-8 bytes representing:

- study semantic metadata, including `study_id` and `content_version`;
- all five frozen operational YAML components;
- all declared entities and protocol values;
- `study_schema_version`;
- the authored-content canonicalization version.

It deliberately excludes compiler version, compiled indexes, resolved-object layout, and other runtime implementation details. It also excludes:

- YAML comments;
- YAML formatting and key order;
- physical filenames after assembly into the aggregate;
- infrastructure/environment configuration;
- README and Markdown prose;
- source-control metadata.

Authored-content canonicalization rules:

1. Parse and validate the frozen YAML into `AuthoredStudy`.
2. Dump every authored model with defaults made explicit.
3. Normalize strings to Unicode NFC and LF newlines.
4. Forbid floating-point numbers in study definitions.
5. Sort object keys lexicographically.
6. Preserve array order.
7. Serialize integers, booleans, and null in standard JSON form.
8. Emit no insignificant whitespace.
9. Prefix the bytes with the authored canonicalization version, not the compiler version.
10. Compute SHA-256.

A separate source-bundle inventory stores exact YAML file text and per-file hashes for audit. Formatting-only changes may alter source-bundle hashes without changing `content_hash`.

### 7.2 Compiler/runtime snapshot identity and hash

Compilation produces the immutable runtime snapshot stored in StudyVersion. Its `snapshot_hash` is SHA-256 over canonical bytes containing:

- the referenced authored `content_hash`;
- `compiler_contract_version`;
- `snapshot_schema_version`;
- the complete compiled representation, including resolved transition plans, Knowledge Slices, and serialized indexes.

`content_hash`, `compiler_contract_version`, and `snapshot_hash` are separate fields with separate meanings even though they are stored together in one immutable StudyVersion record. Recompilation does not change authored content identity; it creates another immutable StudyVersion record containing the same `content_hash` and a different compiler/runtime identity. Existing sessions remain bound to their original record.

### 7.3 PostgreSQL storage

Each immutable StudyVersion stores:

- study identity and content version;
- canonical authored-definition bytes;
- exact operational YAML source bundle;
- authored `content_hash`;
- study schema and canonicalization versions;
- `compiler_contract_version`;
- `snapshot_schema_version`;
- compiled runtime snapshot;
- `snapshot_hash`;
- Markdown/design provenance;
- creation timestamp.

The authored content hash identifies what the frozen YAML says. The snapshot hash identifies the exact compiler-specific runtime representation. Neither identity is overloaded to serve the other purpose.

### 7.4 Version collision policy

Constraints enforce:

```text
unique(study_id, content_version, compiler_contract_version, snapshot_schema_version)
unique(snapshot_hash)
```

Before insertion, activation rejects a different `content_hash` for an existing `(study_id, content_version)` label. Authors must increment the content version when operational semantics change.

If content, compiler contract, and snapshot schema are unchanged, the existing StudyVersion is reused.

Compiling the same content with a different compiler contract creates another immutable StudyVersion record with the same `content_hash` and a different `compiler_contract_version` and `snapshot_hash`.

### 7.5 Session binding

`Session.study_version_id` is non-null and immutable after creation.

All study content used by that session is loaded from the compiled snapshot stored inside that StudyVersion. The active filesystem package is never consulted to continue an existing session.

Therefore:

> Editing study files after a session starts cannot change the study experienced by that session.

### 7.6 Study changes

When valid study files change and the content version is incremented:

- A new immutable StudyVersion containing the authored definition and compiled snapshot is inserted.
- The active-version pointer changes atomically.
- Existing sessions remain bound to their old StudyVersion.
- New sessions use the newly active StudyVersion.

If only the compiler or snapshot schema changes, a new immutable StudyVersion record may be created with the same content hash and activated for new sessions.

Files are not hot-reloaded. Changes take effect only after explicit activation or application restart.

If the changed study is invalid:

- No StudyVersion is inserted.
- The active pointer is not changed.
- Startup/activation fails visibly.
- Existing data remains intact.

---

## 8. PostgreSQL schema

All timestamps use `timestamptz`. UUIDs are application-generated UUIDv4 values. Research records use `ON DELETE RESTRICT`; routine application behavior does not delete session evidence.

### 8.1 PostgreSQL enums

Native enums are appropriate only for closed infrastructure lifecycle values:

- `session_status`
- `session_phase`
- `attempt_status`
- `message_role`
- `assessment_status`
- `llm_call_purpose`
- `llm_call_status`
- `correctness_status`

Study-defined IDs—SOLO states, transitions, pedagogies, forms, rubrics—remain text because they belong to versioned external study data.

Event types remain text with application validation because the audit vocabulary may grow without altering existing event semantics.

### 8.2 `study_versions`

Owns the immutable reviewed/frozen operational YAML content together with one exact compiled runtime snapshot.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `study_id` | text not null |
| `content_version` | text not null |
| `study_schema_version` | text not null |
| `content_canonicalization_version` | text not null |
| `content_hash` | char(64) not null |
| `canonical_authored_definition` | bytea not null |
| `source_bundle` | jsonb not null |
| `source_provenance` | jsonb not null |
| `compiler_contract_version` | text not null |
| `snapshot_schema_version` | text not null |
| `snapshot_hash` | char(64) not null |
| `compiled_snapshot` | jsonb not null |
| `created_at` | timestamptz not null |

Constraints and indexes:

- Unique `(study_id, content_version, compiler_contract_version, snapshot_schema_version)`.
- Unique `snapshot_hash`.
- Check lowercase 64-character hexadecimal hashes.
- Activation validation rejects a different `content_hash` for an existing `(study_id, content_version)` label.
- Index `(study_id, content_version)`.
- Index `(study_id, content_hash)`.
- Index `(study_id, created_at desc)`.
- Database trigger rejects `UPDATE` and `DELETE`.

### 8.3 `active_study_versions`

Mutable pointer used only when creating new sessions.

| Column | Type and constraints |
|---|---|
| `study_id` | text PK |
| `study_version_id` | UUID FK → `study_versions.id`, not null |
| `activated_at` | timestamptz not null |
| `activated_by` | text nullable |

Updating this pointer does not affect existing sessions.

### 8.4 `sessions`

Owns current session state for fast retrieval.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `participant_code` | text unique, nullable |
| `study_version_id` | UUID FK → `study_versions.id`, not null |
| `status` | `session_status`, not null |
| `phase` | `session_phase`, not null |
| `formal_state_id` | text not null |
| `current_transition_id` | text nullable |
| `current_attempt_id` | UUID nullable, deferred FK → `attempts.id` |
| `current_attempt_number` | smallint not null default 0 |
| `terminal_reason` | text nullable |
| `lock_version` | integer not null default 0 |
| `last_event_sequence` | bigint not null default 0 |
| `application_build_id` | text not null |
| `runtime_config_snapshot` | jsonb not null |
| `started_at` | timestamptz nullable |
| `ended_at` | timestamptz nullable |
| `created_at` | timestamptz not null |
| `updated_at` | timestamptz not null |

Indexes:

- `(study_version_id)`.
- `(status, updated_at)`.
- Partial index for active/nonterminal sessions.

`study_version_id` cannot be updated after insertion.

### 8.5 `attempts`

Owns one assigned-pedagogy attempt at one transition.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `session_id` | UUID FK → `sessions.id`, not null |
| `transition_id` | text not null |
| `sequence_in_transition` | smallint not null, check 1–3 |
| `pedagogy_id` | text not null |
| `status` | `attempt_status`, not null |
| `formal_state_before_id` | text not null |
| `formal_state_after_id` | text nullable |
| `completion_reason` | text nullable |
| `passed` | boolean nullable |
| `outcome_details` | jsonb nullable |
| `assigned_at` | timestamptz not null |
| `intervention_started_at` | timestamptz nullable |
| `intervention_completed_at` | timestamptz nullable |
| `completed_at` | timestamptz nullable |

Constraints:

- Unique `(session_id, transition_id, sequence_in_transition)`.
- Unique `(session_id, transition_id, pedagogy_id)`.
- Unique `(id, session_id)` to support composite child FKs.
- Partial unique index allowing at most one nonterminal attempt per session.
- `passed` remains null until deterministic rubric evaluation.

### 8.6 `learner_history_snapshots`

Stores the exact structured history supplied to a later attempt.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `session_id` | UUID FK, not null |
| `target_attempt_id` | UUID FK → `attempts.id`, unique, not null |
| `transition_id` | text not null |
| `source_attempt_ids` | UUID[] not null |
| `summary` | jsonb not null |
| `generation_method` | text not null |
| `llm_call_id` | UUID nullable |
| `created_at` | timestamptz not null |

This table is append-only. Attempt 1 may have no row or an explicitly empty deterministic snapshot.

### 8.7 `messages`

Owns participant-visible Tutor/learner conversation messages.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `attempt_id` | UUID FK → `attempts.id`, not null |
| `sequence_no` | integer not null |
| `role` | `message_role`, not null |
| `content_text` | text not null |
| `content_format` | text not null default `markdown` |
| `llm_call_id` | UUID nullable |
| `instructional_trace` | jsonb nullable |
| `material_ids` | text[] not null default empty |
| `exposed_kc_ids` | text[] not null default empty |
| `exposed_relation_ids` | text[] not null default empty |
| `created_at` | timestamptz not null |

Constraints:

- Unique `(attempt_id, sequence_no)`.
- Append-only trigger.
- Index `(attempt_id, sequence_no)`.

`instructional_trace` supports future Tutor output without defining its final contract in Stage 1.

### 8.8 `assessment_instances`

Owns the selected, frozen assessment presentation for one attempt.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `session_id` | UUID not null |
| `attempt_id` | UUID not null |
| `transition_id` | text not null |
| `assessment_family_id` | text not null |
| `assessment_form_id` | text not null |
| `status` | `assessment_status`, not null |
| `candidate_form_ids` | text[] not null |
| `selection_method` | text not null |
| `selection_audit` | jsonb not null |
| `prompt_snapshot` | text not null |
| `hidden_scoring_context_snapshot` | text not null |
| `selected_at` | timestamptz not null |
| `submitted_at` | timestamptz nullable |
| `closed_at` | timestamptz nullable |

Constraints:

- Composite FK `(attempt_id, session_id)` → `attempts(id, session_id)`.
- Unique `attempt_id`.
- Unique `(session_id, assessment_form_id)` to prevent reuse.
- Index `(session_id, transition_id)`.

The hidden context is never returned by participant-facing queries.

### 8.9 `assessment_responses`

Owns exact learner submissions.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `assessment_instance_id` | UUID FK, unique, not null |
| `response_text` | text not null |
| `response_format` | text not null |
| `submitted_at` | timestamptz not null |
| `client_action_id` | UUID not null |

Constraints:

- Unique `client_action_id`.
- Append-only trigger.

No normalized label replaces `response_text`.

### 8.10 `llm_calls`

Owns every provider attempt, including retries and failures.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `session_id` | UUID FK, not null |
| `attempt_id` | UUID FK, nullable |
| `assessment_instance_id` | UUID FK, nullable |
| `purpose` | `llm_call_purpose`, not null |
| `status` | `llm_call_status`, not null |
| `retry_group_id` | UUID not null |
| `retry_number` | smallint not null |
| `provider` | text not null |
| `model` | text not null |
| `provider_request_id` | text nullable |
| `generation_parameters` | jsonb not null |
| `compiled_prompt_text` | text nullable |
| `request_payload` | jsonb not null |
| `request_body_text` | text not null |
| `raw_response_text` | text nullable |
| `response_payload` | jsonb nullable |
| `parsed_response` | jsonb nullable |
| `error_class` | text nullable |
| `error_message` | text nullable |
| `input_tokens` | integer nullable |
| `output_tokens` | integer nullable |
| `total_tokens` | integer nullable |
| `latency_ms` | integer nullable |
| `started_at` | timestamptz not null |
| `completed_at` | timestamptz nullable |

Constraints:

- Unique `(retry_group_id, retry_number)`.
- Index `(session_id, started_at)`.
- Index `(attempt_id, purpose)`.
- Check that token counts and latency are non-negative.

The lifecycle is:

```text
STARTED
    ↓
RECEIVED
    ↓
terminal status
```

`RECEIVED` means the raw provider response and available provider metadata have been persisted, but the output has not yet been accepted into domain state. A call may also move from `STARTED` directly to a terminal technical-failure status when no response is received. After terminal status the row is immutable.

### 8.11 `judgments`

Owns the Judge’s accepted structured interpretation of one learner response.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `assessment_response_id` | UUID FK, unique, not null |
| `llm_call_id` | UUID FK → `llm_calls.id`, unique, not null |
| `rubric_id` | text not null |
| `gradable` | boolean not null |
| `correctness` | `correctness_status`, not null |
| `observed_solo_state_id` | text nullable |
| `kc_evidence` | jsonb not null |
| `relation_evidence` | jsonb not null |
| `misconception_ids` | text[] not null |
| `evidence_summary` | jsonb not null |
| `confidence` | numeric nullable, check 0–1 |
| `ambiguity` | jsonb nullable |
| `created_at` | timestamptz not null |

Judgments are append-only and do not directly advance sessions.

### 8.12 `rubric_evaluations`

Owns the deterministic backend pass/fail decision.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `judgment_id` | UUID FK → `judgments.id`, unique, not null |
| `attempt_id` | UUID FK → `attempts.id`, unique, not null |
| `transition_id` | text not null |
| `rubric_id` | text not null |
| `rule_snapshot` | jsonb not null |
| `input_evidence_snapshot` | jsonb not null |
| `passed` | boolean not null |
| `decision_reasons` | jsonb not null |
| `formal_state_before_id` | text not null |
| `formal_state_after_id` | text not null |
| `created_at` | timestamptz not null |

This table makes the Judge/backend authority boundary explicit.

### 8.13 `protocol_events`

Append-only session timeline.

| Column | Type and constraints |
|---|---|
| `id` | bigint generated always as identity, PK |
| `session_id` | UUID FK, not null |
| `sequence_no` | bigint not null |
| `event_type` | text not null |
| `event_version` | smallint not null |
| `attempt_id` | UUID nullable |
| `actor` | text not null |
| `correlation_id` | UUID not null |
| `payload` | jsonb not null |
| `occurred_at` | timestamptz not null |

Constraints:

- Unique `(session_id, sequence_no)`.
- Index `(session_id, occurred_at)`.
- Index `(event_type, occurred_at)`.
- Append-only trigger.

Selection events store candidates, exclusions, selected ID, strategy, and selection metadata.

### 8.14 `idempotency_records`

Prevents duplicate logical actions from retries or double clicks.

| Column | Type and constraints |
|---|---|
| `id` | UUID PK |
| `session_id` | UUID FK, not null |
| `action_type` | text not null |
| `idempotency_key` | text not null |
| `request_hash` | char(64) not null |
| `result_object_type` | text nullable |
| `result_object_id` | UUID nullable |
| `response_snapshot` | jsonb nullable |
| `created_at` | timestamptz not null |
| `expires_at` | timestamptz nullable |

Constraint: unique `(session_id, action_type, idempotency_key)`.

Reusing a key with a different request hash is an error.

### 8.15 Relational data, JSONB, and snapshots

Use normal columns for:

- primary and foreign keys;
- lifecycle status;
- study/session/attempt identity;
- transition/pedagogy/form/rubric IDs;
- pass/fail;
- timestamps;
- uniqueness and idempotency;
- frequently filtered fields.

Use JSONB for:

- immutable compiled study snapshots;
- provider request/response structures;
- Judge evidence whose final Stage-2 schema is not yet frozen;
- deterministic decision explanations;
- event payloads;
- history summaries and instructional traces.

Use text for exact prompts, messages, learner answers, and exact serialized provider bodies. JSONB alone is not sufficient when exact textual reproduction matters.

---

## 9. Entity relationships

```text
StudyVersion
    1
    ├───────────< Session
    │                1
    │                ├───────────< Attempt
    │                │                1
    │                │                ├───────────< Message
    │                │                │
    │                │                ├──────────── AssessmentInstance
    │                │                │                  1
    │                │                │                  └── AssessmentResponse
    │                │                │                           1
    │                │                │                           └── Judgment
    │                │                │                                  1
    │                │                │                                  └── RubricEvaluation
    │                │                │
    │                │                └──────────── LearnerHistorySnapshot
    │                │
    │                ├───────────< LLMCall
    │                ├───────────< ProtocolEvent
    │                └───────────< IdempotencyRecord
    │
    └──────────── ActiveStudyVersion pointer
```

Cardinalities and ownership:

- One immutable StudyVersion contains one authored-content identity and one exact compiled runtime snapshot identity.
- One StudyVersion owns zero or more Sessions.
- One Session owns attempts and its complete audit timeline.
- One Attempt has exactly one pedagogy and at most one assessment.
- An assessment has at most one accepted learner response.
- A response has at most one accepted Judgment.
- A Judgment has exactly one deterministic RubricEvaluation when processing completes.
- Tutor and Judge retries create multiple LLMCall rows, but only the accepted call is linked to the corresponding message or Judgment.
- Protocol events describe changes; they do not replace the current session record.

---

## 10. Current state vs audit/event history

### Current mutable state

`Session` stores the minimum current state needed to resume efficiently:

- status and phase;
- formal SOLO state;
- current transition;
- current attempt;
- attempt number;
- terminal reason;
- concurrency version.

`Attempt` stores current attempt status, assigned pedagogy, and eventual outcome.

`AssessmentInstance` stores current assessment status.

These records answer “what may the participant do now?” without replaying the event log.

### Immutable history

The system additionally appends events for:

- study binding;
- transition start;
- pedagogy candidate pool and selection;
- intervention start/completion;
- Tutor turns;
- assessment candidates and selection;
- assessment submission;
- Judge start/completion;
- deterministic pass/fail;
- formal state change;
- next-attempt routing;
- unresolved or completed termination;
- technical failures and recoveries.

Each state-changing transaction:

1. Locks the Session row.
2. Verifies expected phase and `lock_version`.
3. Checks or creates the idempotency record.
4. Mutates current Session/Attempt state.
5. Inserts the immutable evidence record.
6. Appends the corresponding ProtocolEvent.
7. Increments `lock_version` and event sequence.
8. Commits atomically.

The design is **snapshot plus audit log**, not event sourcing. Current records are authoritative for execution; events and immutable evidence support reconstruction and research audit.

This allows later reconstruction of:

- selected pedagogy and candidate pool;
- selected assessment and excluded forms;
- pass/fail and its exact rule inputs;
- state before and after progression;
- unresolved or completed status;
- technical interruption versus learner failure.

---

## 11. Data support for later AI stages

Stage 1 reserves the following storage and interfaces without defining the full AI contracts:

| Later requirement | Stage-1 support |
|---|---|
| Exact Tutor prompt | `llm_calls.compiled_prompt_text`, request payload/body |
| Exact Judge prompt | Same storage, with Judge purpose and assessment link |
| Raw model response | `raw_response_text` and provider payload |
| Parsed model response | `parsed_response` JSONB |
| Learner history summaries | `learner_history_snapshots` |
| Judge evidence | Normalized core fields plus structured evidence JSONB |
| Deterministic pass/fail | Separate `rubric_evaluations` |
| Tutor instructional trace | Message trace plus exposed material/KC/relation IDs |
| Provider/model metadata | `provider`, `model`, generation parameters |
| Retry lineage | `retry_group_id`, `retry_number`, statuses/errors |
| Token and latency metadata | Dedicated numeric columns |
| Raw learner evidence | Messages and assessment responses as exact text |
| Prompt provenance | Session’s frozen StudyVersion, its stored snapshot hash, and exact compiled request |
| Application provenance | `application_build_id` and sanitized runtime snapshot |

Minimal future-facing interfaces in `runtime/ports.py` may define concepts such as `TutorClient`, `JudgeClient`, and `LLMProvider`, but Stage 1 must not implement prompt composition, provider behavior, retries, or AI output schemas.

Secrets are never copied into runtime snapshots or LLM call records.

---

## 12. Migration/startup design

### 12.1 Alembic organization

- One linear migration history for the POC.
- Exactly one Alembic head.
- Each migration has a focused purpose and reversible downgrade where PostgreSQL permits it safely.
- Native enum creation/change is explicit.
- Indexes, triggers, checks, and constraints are reviewed in generated SQL.
- Autogenerated migrations are starting material, not accepted without review.
- Database integration tests run against PostgreSQL, not SQLite.

Recommended initial sequence:

1. Study version with embedded compiled snapshot, and activation table.
2. Session and attempt lifecycle.
3. Messages, assessments, and responses.
4. LLM calls, judgments, and rubric evaluations.
5. Events, idempotency, and immutability triggers.

### 12.2 Application bootstrap

The local Compose application performs:

```text
connect to PostgreSQL
    ↓
acquire PostgreSQL advisory bootstrap lock
    ↓
inspect Alembic revision
    ↓
upgrade to the single known head if behind
    ↓
abort if revision is ahead, divergent, or migration fails
    ↓
load and validate configured study directory
    ↓
canonicalize and hash frozen authored content
    ↓
compile snapshot and calculate snapshot hash
    ↓
insert/reuse immutable StudyVersion containing both identities and snapshot
    ↓
atomically activate the StudyVersion
    ↓
build StudyCatalog
    ↓
start FastAPI and report readiness
```

Automatic migration is acceptable here because the POC has one local application process and one database. The advisory lock prevents concurrent bootstrap migration.

The web application does not become ready until migration and study validation succeed.

### 12.3 Invalid or changed study behavior

- Invalid YAML or validation failure: startup exits nonzero; no partial activation.
- Same content hash, compiler contract, and snapshot schema: reuse the existing StudyVersion.
- Changed semantics with unchanged content version: fail with version collision.
- Changed semantics with incremented version: insert and activate a new StudyVersion containing its compiled snapshot.
- Same content under a new compiler/snapshot format: create another immutable StudyVersion record with the same content hash and a different compiler/snapshot identity.
- Existing sessions: continue using their original StudyVersion and its stored compiled snapshot.
- New sessions: bind to the active StudyVersion.
- Study files changed while running: no effect until restart or explicit activation.
- Missing compiled-snapshot reader for an existing nonterminal session: startup fails rather than silently recompile it with newer semantics.

The source Markdown's descriptive status does not participate in activation. Missing configuration required by the runtime, such as a mandatory hard budget, remains an ordinary study-validation error.

---

## 13. Stage-1 test design

### Operational parsing

- Parse every declared file in a valid fixture.
- Reject missing declared files.
- Reject undeclared path escapes and external symlinks.
- Reject duplicate YAML keys, custom tags, aliases, and malformed syntax.
- Verify multiline prose and code survive parsing.

### Pydantic validation

- Missing required IDs.
- Invalid ID patterns.
- Unknown fields.
- Wrong types under strict validation.
- Empty required prose.
- Invalid protocol and success-rule enum values.
- Missing or non-positive intervention budgets when hard budgets are required by the protocol/runtime contract.

### Duplicate detection

- Duplicate ID in one file.
- Duplicate ID across component files.
- Same ID used for different entity types.
- Duplicate intervention transition/pedagogy pair.
- Duplicate assessment form ID.

### Broken references

- Unknown transition or pedagogy.
- Unknown KC, relation, misconception, state, form, rubric, or evidence ID.
- Reference with the wrong target entity type.
- Judge form requirement referencing another transition’s form.

### Intervention matrix

- Missing one of the 12 pairs.
- Duplicate pair.
- Cell for an unconfigured pedagogy.
- Cell target knowledge inconsistent with its transition.

### Assessment capacity

- Three active forms when four are required.
- Four total but only three active.
- Protocol maximum attempts exceeding pedagogy count.
- Reserve requirement changing the minimum.
- Duplicate form exposure prevented by the database constraint.

### Knowledge boundaries

- Future KC targeted early.
- Out-of-scope frontier item required.
- Assessment requiring a later transition’s KC.
- Intervention material tag matching a reserved assessment tag.

### Protocol topology

- Skipped SOLO state.
- Transition in the wrong order.
- Repeated transition.
- Wrong initial state.
- Renewed cycle enabled.
- More than three attempts.
- Pedagogy-dependent assessment configuration.

### Successful compilation

- Complete Fibonacci-shaped fixture produces one `CompiledStudy`.
- Four Knowledge Slices exist.
- Twelve cell indexes resolve.
- Four assessment families and four rubrics resolve.
- Each transition plan contains exactly three cells.
- All compiled collections reject mutation.

### Deterministic authored-content and snapshot hashing

- Repeated authored canonicalization produces the same content hash.
- YAML key reordering does not change the content hash.
- Comments and formatting do not change the content hash.
- CRLF versus LF does not change the content hash.
- Equivalent Unicode normalization produces the same content hash.
- List reordering where order is meaningful changes the content hash.
- Any semantic prose, reference, rule, or protocol change changes the content hash.
- Compiler-contract changes do not change the authored content hash.
- Repeated compilation with the same compiler contract produces the same snapshot hash.
- Compiler-contract or snapshot-schema changes change the snapshot hash while retaining the parent content hash.
- Every snapshot hash commits to its parent content hash.

### Study freezing

- Creating a Session stores one StudyVersion ID.
- Activating another StudyVersion does not update the old Session.
- Reloading the old Session uses the snapshot stored in its StudyVersion.
- Attempting to update/delete a StudyVersion fails.
- Same content version with a different hash is rejected.
- Formatting-only re-import reuses the StudyVersion.
- Recompiling unchanged content under a new compiler creates a new StudyVersion record with the same content hash and a different snapshot hash.

### Database integrity

Using real PostgreSQL:

- Foreign keys reject orphan attempts, assessments, and judgments.
- Unique pedagogy-per-transition constraint works.
- Attempt sequence uniqueness works.
- Only one assessment per attempt.
- Only one response per assessment.
- Only one accepted Judgment and RubricEvaluation.
- Session/form uniqueness prevents assessment reuse.
- Partial unique index prevents two active attempts.
- Append-only triggers reject mutation of evidence/events.
- StudyVersion FKs use `RESTRICT`.
- LLMCall permits `STARTED → RECEIVED → terminal` and direct `STARTED → terminal technical failure`.
- Invalid LLMCall lifecycle transitions are rejected.

### Event persistence and concurrency

- State mutation and event append commit together.
- A failed transaction leaves neither change.
- Event sequence is monotonic per session.
- Idempotent replay returns the original result.
- Same key with different request data is rejected.
- Concurrent state mutations allow only one valid winner.
- Candidate and selection data are reconstructable from events.

Stage 1 does not require full Tutor, Judge, UI, or protocol end-to-end tests.

---

## 14. Implementation decisions made

| Decision | Rationale | Alternatives considered | Consequence |
|---|---|---|---|
| YAML 1.2 for operational studies | Best balance of structured validation and reviewable multiline instructional prose | JSON; runtime Markdown parsing | Adds a YAML dependency and requires strict feature restrictions |
| Explicit manifest-listed files | Creates a closed, auditable package and prevents accidental glob discovery | One giant file; recursive discovery | Adding a file requires updating `study.yaml` |
| One atomic study content version | A session must experience one coherent cross-pack definition | Independent pack versions | Any effective component change creates a new study version |
| Stable typed string IDs | Preserves the supplied K/R/M/C/P identifiers and gives readable errors | UUIDs in authored files; positional references | Authors must manage ID stability and uniqueness |
| Strict Pydantic authored models | Typos and silent schema drift are dangerous to experiments | Permissive dictionaries | Schema evolution requires explicit model/version changes |
| Separate authored and compiled models | Authored files remain traceable while runtime gets resolved references | One model used for both | Adds a deliberate compilation layer |
| Materialized Knowledge Slices | Prevents Tutor, assessment, and Judge paths deriving inconsistent slices | Derive on every use | Snapshot contains a small amount of deliberate duplication |
| Separate authored content hash and compiled snapshot hash | Distinguishes what the frozen YAML says from how a particular compiler represents it at runtime | One definition hash containing compiler version | Compiler changes can create new snapshots without changing authored study identity |
| Canonical authored JSON plus SHA-256 | Makes content identity independent of YAML formatting and compiler implementation | Hash raw file bytes | Formatting changes do not create a new authored study version |
| Snapshot hash commits to content hash and compiler contract | Makes the exact runtime representation independently identifiable | Treat compiled JSON as an unversioned cache | Sessions can remain bound to the precise compiler-specific snapshot they started with |
| Store canonical definition, source bundle, identities, and compiled snapshot in one immutable StudyVersion | Keeps the Session binding simple while retaining distinct content and runtime identities | Separate persistent snapshot entity; store only hashes | Recompilation under a new compiler creates another immutable StudyVersion record with the same content hash |
| Immutable StudyVersion plus mutable activation pointer | Separates existing-session stability from new-session activation | Mutable study row; separate compiled-snapshot entity | New activation or recompilation cannot alter prior sessions |
| Reject same content version with changed semantics | Prevents a label such as `0.1` referring to two experiments | Automatically overwrite or suffix | Authors must deliberately increment versions |
| Relational core plus targeted JSONB | Preserves constraints and queryability without over-normalizing evolving evidence | All relational; all JSONB | JSONB schemas still require application validation |
| Separate Judgment from RubricEvaluation | Maintains Judge-evidence/backend-decision boundary | One combined result row | One additional one-to-one table |
| Snapshot plus audit log | Fast current-state access and reconstructable history without full event-sourcing complexity | Event sourcing; mutable records only | Mutations and event inserts must share a transaction |
| Native enums only for stable infrastructure states | Provides database validation without encoding study semantics in DDL | Text checks everywhere; enums for study IDs | Adding lifecycle values requires migrations |
| Direct SQLAlchemy query modules | POC has one database and does not need repository indirection | Generic repository/unit interfaces | Persistence remains concrete and easy to trace |
| Session row lock plus idempotency record | Prevents duplicate transitions and submissions locally | Distributed locks; optimistic locking alone | State-changing transactions must follow one service pattern |
| No hot study reload | Keeps activation explicit and avoids sessions seeing filesystem races | File watcher | Study edits require restart or explicit activation |
| App bootstrap applies migrations under advisory lock | Enables a fresh local Compose environment with one application instance | Manual migration service; migrations inside request handling | Startup aborts if migration cannot complete |

---

## 15. Ambiguities / questions requiring approval

1. **Markdown-to-YAML approval workflow**

   Recommendation: operational YAML should be produced through a one-time reviewed transcription, with a generated cross-reference report comparing IDs, counts, and source hashes. Once frozen, that YAML package is the executable source of truth for its version. Runtime never parses the long Markdown documents, and later Markdown edits do not mutate the frozen version.

2. **Intervention budgets**

   Exact turn/time limits are absent. Recommendation: select explicit positive values in operational study configuration before freezing that YAML version; do not infer them from Markdown status or invent application defaults.

3. **Baseline/pre-transition assessment**

   This remains explicitly undecided. Recommendation: omit it from POC protocol v0.1. If introduced, increase assessment inventory rather than consuming the existing reserve implicitly.

4. **Technical failure and attempt consumption**

   Recommendation for later runtime design: provider/network/parse failures should not count as learner failure or consume a pedagogy attempt. The same Attempt should enter `TECHNICAL_HOLD` and resume under an explicit retry policy.

5. **Judge correctness vocabulary**

   The documents require correctness separate from structure but do not freeze exact machine labels. Recommendation: approve a small closed vocabulary—such as `correct`, `minor_error`, `materially_incorrect`, `not_gradable`—during Stage 2.

6. **Declarative rubric transcription**

   The proposed `SuccessRule` can encode the current C1–C4 rules without executable code, but the exact transcription must be approved by the study author. Especially important are task-specific requirements and what constitutes a “material” misconception.

7. **Pedagogy fidelity validation**

   Structural schema checks cannot establish that prose truly preserves a pedagogy. Recommendation: generate a validation report for human review rather than introducing an LLM-based automatic validator in Stage 1.

8. **Assessment equivalence**

   Four structurally valid forms are not automatically psychometrically equivalent. Recommendation: treat equivalence metadata as author claims requiring pilot review, not as machine-proven properties.

9. **Source provenance scope**

    Recommendation: store exact frozen operational YAML and Markdown provenance separately. The authored content hash is computed from operational semantics only; Markdown provenance changes neither that hash nor runtime behavior for an existing version.

10. **Compiled snapshot compatibility**

    Recommendation: retain readers for every compiled snapshot version referenced by a nonterminal Session. A deployment that cannot read such a snapshot should fail startup instead of recompiling old studies with new semantics.

11. **Participant identifier policy**

    The HLD permits a participant code or opaque token but does not freeze it. Recommendation: Stage 1 stores only an opaque optional `participant_code`; authentication and researcher-facing bootstrap remain for a later stage.
