# AI Harness — High-Level Design

**Status:** Architecture baseline for implementation-design review  
**Project:** SOLO-Transition Pedagogy POC  
**Primary study:** Python — Recursive Fibonacci with Memoization  
**Purpose:** Freeze the architecture, component responsibilities, runtime flow, information boundaries, persistence requirements, and non-negotiable experimental invariants before Codex proposes concrete schemas and code.

---

## 1. Position of this document

This HLD sits between the research definition and the concrete implementation design:

```text
Study-Pack Specification
        ↓
Fibonacci POC Study Definition
        ↓
THIS HLD
        ↓
Codex Technical Implementation Proposal
        ↓
Human Review
        ↓
Implementation
```

The study documents define **what the experiment means**. This HLD defines **how the major runtime system is organized**. The later implementation proposal may choose exact tables, classes, routes, serialization formats, and helper abstractions, but it must preserve the boundaries defined here.

This HLD deliberately does **not** prescribe exact SQL schemas, Pydantic classes, FastAPI routes, YAML structures, migration files, transaction code, dependency-injection patterns, or frontend partials.

---

## 2. System objective

The harness is a **local-first, containerized runtime for controlled AI-mediated learning experiments**.

It must allow a researcher to:

- load a versioned study definition;
- start participant sessions;
- deliver an assigned LLM-mediated pedagogical intervention;
- administer a fresh independent assessment after each intervention;
- judge the learner response using a separate Judge role;
- apply deterministic progression rules;
- preserve raw evidence and exact model interactions;
- reconstruct the session later for audit/reanalysis.

The first POC uses:

```text
Domain: Python Programming
Topic: Recursive Fibonacci with Memoization
States: P → U → M → R → EA
Transitions: C1, C2, C3, C4
Pedagogies: Worked Example, Guided Questioning, Contrasting Cases
```

The core harness should avoid hard-coding Fibonacci-specific semantics.

---

## 3. Core architectural rule

> **The study definition owns experimental meaning. The harness owns execution.**

The study definition owns:

- topic/frontier;
- KCs, relations, misconceptions;
- SOLO states/transitions;
- pedagogy-family definitions;
- transition × pedagogy intervention content;
- assessment families/forms;
- Judge/rubric content;
- protocol settings.

The harness owns:

- loading/validating the study;
- freezing a study version;
- session lifecycle;
- state progression;
- randomization;
- prompt compilation;
- Tutor/Judge calls;
- assessment selection;
- history construction;
- deterministic pass/fail application;
- persistence/audit;
- browser-facing state.

The harness must not silently reinterpret study semantics.

---

## 4. Deployment model

The POC should be a single Docker Compose ecosystem per machine:

```text
docker compose
│
├── app
└── postgres
```

The `app` service contains the HTTP server, study loader, protocol engine, prompt compiler, Tutor runtime, assessment runtime, Judge runtime, LLM adapter, templates/static files, and persistence logic.

The `postgres` service stores durable runtime/audit data.

The study definition is mounted read-only into the app container.

The POC should not require Redis, Celery, Kafka, Nginx, object storage, a separate frontend service, or a separate worker unless a later requirement clearly justifies one.

---

## 5. Configuration boundaries

Three classes of configuration must remain distinct.

### Infrastructure/environment

Examples:

```text
DATABASE_URL
LLM_API_KEY
LLM_BASE_URL
TUTOR_MODEL
JUDGE_MODEL
LOG_LEVEL
PORT
```

These may vary by machine without changing the study.

### Study definition

```text
Knowledge Pack
Intervention Pack
Assessment Pack
Judge/Rubric Pack
Protocol configuration
```

Changing these changes the experiment and must be versioned.

### Runtime state

```text
current transition
current attempt
used pedagogies
seen assessments
current phase
current intervention stage
prior attempt history
latest judgment
```

This belongs in persistent backend state, never only in browser memory.

---

## 6. Authority hierarchy

```text
Semantic authority        → Knowledge Pack
Pedagogy authority        → Intervention Pack
Assessment authority      → Assessment Pack
Judgment authority        → Judge/Rubric Pack
Control-flow authority    → Protocol Engine
Runtime-state authority   → Backend + Database
Surface text authority    → LLM within constraints
Display authority         → Frontend only
```

The frontend is never the experiment state authority. The Tutor never directly advances the learner. The Judge never selects pedagogy. The LLM never owns protocol progression.

---

## 7. Major logical subsystems

The harness should contain the following logical responsibilities:

```text
Study Loader / Compiler
Cross-Pack Validator
Study Version Manager
Session Service
Protocol Engine
Prompt Compiler
Tutor Runtime
History Builder
Assessment Selector / Runtime
Judge Runtime
Deterministic Rubric Evaluator
LLM Adapter
Persistence / Audit Layer
Web UI / HTTP Interface
```

These names are logical contracts, not mandatory Python module names. Codex may combine/split implementation units if the boundaries remain intact.

---

## 8. Study Loader / Compiler

### Input

A study-definition directory.

### Output

A validated canonical runtime representation, referred to in this document as `CompiledStudy`.

The exact class/schema is left to implementation design.

### Responsibilities

The loader must:

- discover study components;
- parse them;
- validate local structure;
- resolve cross-references;
- validate completeness;
- reject invalid IDs/references;
- produce a canonical representation;
- calculate a stable study hash/version identity;
- expose the compiled definition to runtime services.

It must not choose pedagogy, call an LLM, mutate participant state, invent missing content, or silently repair invalid study definitions.

---

## 9. Cross-Pack Validator

Before any participant session runs, validation should confirm at least:

```text
all referenced transitions exist
all referenced pedagogies exist
all expected 4 × 3 intervention cells exist
all KC/relation/misconception references resolve
all assessment families reference valid transitions
all Judge rubrics reference valid transitions
assessment capacity supports protocol max attempts
protocol transition order is legal
study IDs are internally unique
forbidden/out-of-scope knowledge is not accidentally required
```

The system should prefer a clear startup/activation failure over runtime improvisation.

---

## 10. Study Version Manager

A session must run against an immutable study definition.

Once a session begins, editing files on disk must not change what that participant receives.

The implementation may freeze the study using a compiled snapshot, canonical serialized copy, hash-addressed version record, or another reliable method. The invariant matters more than the exact storage pattern.

Every session must be traceable to:

```text
study identity
study version
study hash
effective compiled content
```

---

## 11. Session Service

The Session Service owns participant-session lifecycle.

It must support:

- creating a session;
- binding it to a frozen study version;
- determining current phase/state;
- exposing the next permitted participant action;
- resuming after refresh/reconnect;
- clean completion or unresolved termination.

It delegates progression to Protocol Engine, teaching to Tutor Runtime, assessment to Assessment Runtime, and judging to Judge Runtime.

---

## 12. Protocol Engine

The Protocol Engine answers:

> **Given current persistent experiment state and the latest completed outcome, what happens next?**

It owns:

- formal SOLO state;
- current transition;
- pedagogy selection;
- without-replacement enforcement;
- attempt count;
- success advancement;
- failure routing;
- exhaustion behavior;
- terminal session state.

It does not own topic semantics, pedagogy content, assessment questions, Judge evidence interpretation, or provider logic.

---

## 13. POC protocol behavior

At each transition:

```text
select unused pedagogy randomly
        ↓
deliver intervention
        ↓
fresh independent assessment
        ↓
Judge
        ↓
deterministic rubric outcome
```

On success:

```text
advance exactly one formal SOLO transition
```

On failure with an unused pedagogy:

```text
remain at same transition
record history
select another unused pedagogy
```

After all three pedagogies fail:

```text
mark transition unresolved
stop progression
```

There is no renewed pedagogy cycle in the POC.

---

## 14. Runtime state machine

The implementation should enforce a state machine conceptually equivalent to:

```text
SESSION_CREATED
      ↓
TRANSITION_READY
      ↓
PEDAGOGY_ASSIGNED
      ↓
INTERVENTION_ACTIVE
      ↓
INTERVENTION_COMPLETE
      ↓
ASSESSMENT_ACTIVE
      ↓
ASSESSMENT_SUBMITTED
      ↓
JUDGING
      ↓
JUDGED
      ↓
TRANSITION_OUTCOME
   ┌──┴──────────────┐
   │                 │
 SUCCESS           FAILURE
   │                 │
   ▼                 ▼
NEXT TRANSITION   UNUSED PEDAGOGY?
                  ┌────┴────┐
                 YES        NO
                  │          │
                  ▼          ▼
             NEXT ATTEMPT  UNRESOLVED
```

Codex may choose different state names. What matters is that invalid transitions are prevented.

---

## 15. Randomization and auditability

Randomization is part of the experiment and must be auditable.

For pedagogy selection the system must be able to reconstruct:

- candidate pedagogies;
- already-used pedagogies;
- selected pedagogy.

For assessment selection:

- eligible forms;
- already-seen forms;
- selected form.

The exact random-number implementation is left to Codex, but the decision must be persistently auditable. No pedagogy repeats within one transition in the POC.

---

## 16. Prompt Compiler

Prompt construction is a first-class subsystem. Prompts should not be assembled ad hoc inside route handlers.

Conceptually every prompt has four layers:

```text
0. Harness / execution contract
1. General role or pedagogy family
2. Specific experiment unit
3. Runtime context
```

The exact template system is an implementation detail.

---

## 17. Tutor prompt composition

Conceptually:

```text
Harness Tutor Contract
        +
Pedagogy Family Contract
        +
Current Intervention Cell
        +
Resolved Knowledge Slice
        +
Prior-Attempt Structured History
        +
Current Attempt Dialogue/Stage
        +
Runtime Budgets
```

The Tutor may receive:

- assigned pedagogy;
- current transition;
- relevant knowledge definitions;
- cell procedure;
- prior instructional exposure;
- prior learner evidence/misconceptions;
- current dialogue;
- remaining intervention budget.

The Tutor must not receive:

- future assessment content;
- hidden answer key;
- future pedagogy assignment;
- permission to switch family;
- protocol authority.

---

## 18. Tutor Runtime

The Tutor Runtime executes one assigned intervention attempt while preserving treatment fidelity.

Responsibilities:

- initialize intervention context;
- compile Tutor prompts;
- call Tutor LLM;
- validate machine-readable output;
- maintain current dialogue;
- enforce hard budgets;
- record intervention stage/material exposure where available;
- determine whether the intervention continues or ends;
- return control to the protocol/assessment flow when complete.

The Tutor Runtime must never directly declare transition success or mutate formal learner state.

---

## 19. Tutor output contract — high level

The exact schema is left to Codex, but Tutor output should make at least these concepts machine-readable:

```text
learner-facing message
current intervention stage
continue vs intervention_complete
optional instructional trace
```

Malformed Tutor output is a technical problem, not learner failure.

---

## 20. History Builder

Later attempts on the same transition must know what the learner has already experienced.

The History Builder creates a compact structured prior-attempt summary using:

### Deterministic facts

- prior pedagogy;
- material/example IDs;
- turn count;
- stages covered;
- timestamps.

### Tutor observations

- concepts exposed;
- relations exposed;
- possible misconceptions;
- learner statements/evidence.

### Judge evidence

- demonstrated KCs/relations;
- partial evidence;
- absent evidence;
- misconceptions;
- prior assessment outcome.

The precise schema is an implementation choice.

---

## 21. History information boundary

A later Tutor may know:

```text
previous pedagogies
concepts already exposed
materials already used
learner evidence
misconceptions
previous transition failure
```

It should not receive:

```text
future assessment
hidden answer key
Judge chain-of-thought
future treatment assignment
```

Raw old transcripts remain persisted for audit, but the next prompt should normally receive a structured summary rather than all prior transcripts wholesale.

History may personalize the assigned pedagogy; it may not change the assigned pedagogy.

---

## 22. Assessment Selector / Runtime

Assessment is transition-specific and pedagogy-independent.

Selection inputs should include only things such as:

```text
current transition
active/eligible forms
seen assessment IDs
study version
```

Selection must not use:

```text
pedagogy just used
Tutor recommendation
learner preference
```

For the POC:

```text
eligible = forms in transition family - forms already seen
```

Select randomly among eligible forms.

---

## 23. Assessment phase behavior

When intervention completes:

1. select a fresh assessment;
2. persist the assessment instance;
3. render it to the learner;
4. disable Tutor continuation;
5. accept learner submission;
6. persist the raw response exactly;
7. close the assessment;
8. invoke Judge.

No teaching/hints should occur during assessment.

---

## 24. Judge prompt composition

Conceptually:

```text
Harness Judge Contract
        +
Transition Rubric
        +
Resolved Knowledge Slice
        +
Selected Assessment Prompt
        +
Hidden Item-Specific Scoring Context
        +
Learner Response
```

The Judge must not receive:

```text
pedagogy identity
Tutor transcript
previous failed attempts
attempt number as evaluative context
future treatment
```

This blindness must be enforced by data flow, not merely by telling the Judge to ignore information it was given.

---

## 25. Judge Runtime

Responsibilities:

- compile blinded Judge prompt;
- call Judge LLM;
- validate structured output;
- persist raw output;
- persist parsed evidence;
- expose evidence to deterministic rubric evaluation.

The Judge may return:

- correctness;
- KC evidence;
- relation evidence;
- misconceptions;
- observed SOLO state;
- uncertainty/confidence.

It must not directly advance the protocol.

---

## 26. Deterministic Rubric Evaluator

The backend converts Judge evidence into transition outcome.

```text
Judge evidence
      +
transition rubric
      ↓
deterministic rule
      ↓
PASS / FAIL
```

This avoids inconsistent LLM-only decisions such as `observed_solo=U` but `transition_achieved=true` for C2.

The exact rule representation may be proposed by Codex, but the final protocol outcome must be deterministic given the persisted evidence/rubric inputs.

---

## 27. Above-target responses

Observed learner structure and formal protocol state are distinct.

Example:

```text
current transition = C2 U→M
Judge observes = R
```

Persist `observed_solo = R`, but formal progression advances only:

```text
U → M
```

C3 remains independently tested.

---

## 28. LLM Adapter

The application should use a provider abstraction for Tutor/Judge calls.

Responsibilities:

- send requests;
- support role-specific model config;
- support structured output where available;
- capture raw response;
- surface parsed response;
- expose provider errors;
- expose token/latency metadata where available;
- support retry/repair policy.

The adapter must not know SOLO progression, pedagogy selection, assessment selection, or study semantics.

The current provider may be OpenAI-compatible/AICredits, but the harness should not require provider-specific logic throughout the application.

---

## 29. Technical failure vs learner failure

The harness must distinguish technical errors from legitimate learner outcomes.

Technical examples:

```text
network timeout
rate limit
provider 5xx
empty response
malformed structured output
parse failure after allowed repair
```

Learner-outcome examples:

```text
response lacks target evidence
response is materially incorrect
Judge evidence fails rubric
```

A technical failure must never silently become a pedagogy/learner failure.

Exact retry counts and repair strategy are implementation decisions to review.

---

## 30. Persistence — conceptual entities

The implementation must durably represent at least these concepts:

```text
Study Version
Session
Transition/Attempt
Tutor Interaction / Message
Assessment Instance
Learner Assessment Response
Judgment
LLM Call
Protocol Event
```

Codex may use fewer or more physical tables.

---

## 31. Persistence invariants

The implementation must preserve:

```text
Every session belongs to one frozen study version.
Every attempt belongs to one session and one transition.
Every attempt has exactly one assigned pedagogy.
Intervention completion is distinct from transition success.
Assessment instance is traceable to its source form.
Learner response is preserved exactly.
Judgment is traceable to exact response/assessment.
Every LLM call is traceable to exact compiled input and raw output.
Protocol decisions are auditable.
Study version cannot silently change mid-session.
```

---

## 32. Protocol/audit event history

An append-oriented protocol event stream is strongly recommended.

Example event concepts:

```text
SESSION_CREATED
STUDY_BOUND
TRANSITION_STARTED
PEDAGOGY_SELECTED
INTERVENTION_STARTED
TUTOR_TURN_COMPLETED
INTERVENTION_COMPLETED
ASSESSMENT_SELECTED
ASSESSMENT_SUBMITTED
JUDGE_STARTED
JUDGMENT_COMPLETED
TRANSITION_PASSED
TRANSITION_FAILED
NEXT_ATTEMPT_STARTED
SESSION_UNRESOLVED
SESSION_COMPLETED
TECHNICAL_FAILURE
```

Exact event names are not mandated. The goal is reconstructability.

---

## 33. Database as runtime source of truth

Persistent backend state, not frontend memory, owns the session.

The system must handle:

- browser refresh;
- reconnect;
- duplicate-click protection;
- request retry;
- process restart recovery where feasible.

The UI should request current server state and render the correct phase.

---

## 34. UI architecture

Recommended POC frontend:

```text
FastAPI + Jinja2 + HTMX + minimal vanilla JS
```

This is a recommendation rather than a research invariant. The important requirement is a thin UI over server-owned experiment state.

Participant phases are roughly:

```text
session bootstrap
intervention chat
assessment
judging/wait
next attempt or next transition
completed / unresolved
```

Instruction and assessment should be visually and behaviorally distinct.

---

## 35. Session bootstrap

The POC does not require RBAC/authentication infrastructure.

A simple local mechanism is sufficient, for example:

- researcher-created session;
- generated participant code;
- opaque session token.

Codex may choose the exact approach.

---

## 36. Idempotency and concurrency

Even locally, the system must avoid duplicate logical actions.

Examples:

- double assessment submission;
- repeated Tutor-turn request;
- refresh while Judge is running;
- duplicate transition advancement.

Codex should explicitly propose an idempotency/transaction strategy.

The architectural requirement is:

> one logical action must not be committed twice.

---

## 37. Prompt/response persistence

Every Tutor/Judge call should preserve enough information to reconstruct it:

- role;
- provider/model;
- relevant generation configuration;
- exact compiled prompt/request;
- raw provider response;
- parsed structured response;
- timestamps;
- retries/errors;
- token usage and latency where available.

---

## 38. Research reproducibility requirement

A completed session record must allow a researcher to answer:

```text
Which study version ran?
Which pedagogy was selected each attempt?
What were the eligible randomization candidates?
What exact prompt did Tutor receive?
What did Tutor say?
What did learner say?
Which assessment was selected?
What did learner submit?
What exact prompt did Judge receive?
What evidence did Judge return?
Which deterministic rule produced pass/fail?
Why did protocol advance/retry/stop?
```

If those cannot be reconstructed, the audit design is insufficient.

---

## 39. Study-definition lifecycle

Recommended lifecycle:

```text
authored study files
      ↓
parse
      ↓
validate
      ↓
cross-reference validation
      ↓
canonical compile
      ↓
hash/version freeze
      ↓
available for new sessions
```

Existing sessions remain bound to the version they started with.

---

## 40. Operational study format

The HLD does not mandate YAML vs JSON.

The operational representation should support:

- stable IDs;
- structured references;
- multiline instructional guidance;
- human review;
- machine validation;
- versioning.

Codex should propose the concrete format. The human-readable study docs remain the conceptual authority during review.

---

## 41. Security and privacy boundary

The POC must:

- keep LLM credentials out of study packs and source control;
- avoid sending irrelevant participant metadata to models;
- preserve Tutor/Judge context separation;
- use opaque participant/session IDs where practical;
- persist only participant information needed by the study.

The POC does not require enterprise RBAC, SSO, multi-tenant isolation, or internet-facing production hardening.

---

## 42. Observability and error classes

Operational logs should distinguish:

### Study-definition errors

Example: unknown `K99` in an intervention.

These block study activation.

### Runtime technical errors

Example: Judge provider timeout.

These do not count as learner failure.

### Protocol invariant errors

Example: assigning the same pedagogy twice within one transition.

These are system errors.

### Legitimate learner outcomes

Example: learner response fails C3 rubric.

These are normal experiment outcomes.

---

## 43. Recovery philosophy

On technical failure:

- preserve already committed evidence;
- do not silently advance protocol;
- do not silently mark treatment failure;
- allow retry/resume according to explicit policy;
- record the failure.

Exact recovery UX and retry count may be chosen in the implementation proposal.

---

## 44. Testability principle

Most experiment behavior must be testable **without a real LLM**.

The architecture should allow fake/stub Tutor and Judge implementations.

With fake components, tests should be able to prove:

- without-replacement pedagogy selection;
- fresh assessment selection;
- pass/fail routing;
- next-transition advancement;
- unresolved stopping;
- history construction;
- persistence;
- reconnect/resume behavior.

LLM integration should be a layer, not a prerequisite for testing the protocol engine.

---

## 45. Required testing levels

### Unit

- study validation;
- protocol transitions;
- randomization constraints;
- assessment selection;
- deterministic rubric evaluation;
- history construction;
- prompt compilation.

### Integration

- DB persistence;
- service interactions;
- session resume;
- mocked provider adapter;
- full attempt lifecycle.

### End-to-end

At least one deterministic test should run:

```text
session start
→ C1 attempt
→ intervention complete
→ assessment
→ Judge result
→ progression
→ ...
→ C4
→ completion
```

A separate failure-path test should exhaust all three pedagogies on one transition and end unresolved.

---

## 46. POC acceptance criteria

The harness is structurally ready when all are true:

1. Study definition loads and validates.
2. Invalid cross-pack references block activation.
3. Session binds to frozen study version.
4. Session starts at P/C1.
5. Pedagogy is selected without replacement.
6. Correct intervention cell resolves.
7. Tutor receives correct compiled context.
8. Tutor cannot directly advance learner.
9. Intervention completion triggers a fresh assessment.
10. Assessment selection is blind to pedagogy.
11. Learner assessment response is stored exactly.
12. Judge receives blinded context.
13. Judge structured evidence is stored.
14. Backend deterministic rubric produces pass/fail.
15. Success advances exactly one transition.
16. Failure selects another unused pedagogy.
17. Later Tutor receives structured prior history.
18. Three failures end unresolved.
19. No assessment is silently reused.
20. Refresh/reconnect preserves state.
21. Technical LLM failure is not learner failure.
22. Exact Tutor/Judge requests and responses are recoverable.
23. Entire POC runs through Docker Compose on a fresh machine.

---

## 47. Explicit POC non-goals

Do not expand the implementation to include:

- multiple matched topic tracks;
- Experiment 2 adaptive pedagogy selection;
- reward optimization;
- RL/bandits;
- automated pedagogy ranking;
- cloud multi-tenancy;
- complex admin/RBAC;
- distributed workers;
- analytics dashboards;
- physiology/sensors;
- voice/video tutoring;
- mobile apps;
- arbitrary executable study plugins.

---

## 48. Future extensibility — desirable, not required

The design should avoid obviously blocking later support for:

```text
new topics/domains
multiple parallel topics
renewed cycles
different assessment counts
additional pedagogies
different Tutor/Judge models
different providers
Experiment 2 adaptive selection
```

Do not over-engineer the POC for these.

---

## 49. Critical information-flow boundaries

Allowed flow:

```text
Knowledge ─┬─► Intervention ─► Tutor
           ├─► Assessment ───► Learner response
           └─► Judge rubric ─► Judge

Judge evidence ─► deterministic rubric ─► Protocol
Protocol outcome ─► History Builder ─► next Tutor
```

Forbidden direct flows:

```text
Intervention identity ─X─► Judge
Future assessment ─────X─► Tutor
Tutor completion ──────X─► direct progression
Judge free-form opinion X─► protocol without rubric
Frontend state ────────X─► authoritative state
```

---

## 50. Non-negotiable architectural invariants

### Study semantics

- Knowledge Pack is semantic authority.
- Other packs reference rather than redefine knowledge.
- Assessment is transition-specific.
- Judge rubric is transition-specific.
- Protocol is control-flow configuration.

### Treatment fidelity

- one pedagogy per attempt;
- no family switching mid-attempt;
- assigned pedagogy remains identifiable.

### Assessment independence

- every intervention gets a fresh assessment;
- runtime selection is blind to pedagogy;
- no silent form reuse.

### Judge independence

- Judge blind to pedagogy/history;
- correctness and structure remain separate;
- Judge returns evidence;
- backend determines formal outcome.

### History

- later Tutor gets prior structured history;
- raw transcripts remain stored;
- history cannot alter treatment assignment.

### Protocol

- max three pedagogy attempts;
- without replacement;
- no renewed cycle;
- advance one transition at a time.

### Reproducibility

- frozen study version;
- exact model calls preserved;
- random choices auditable;
- raw learner responses preserved.

### Runtime authority

- DB/backend owns state;
- UI reflects state;
- LLM never directly mutates protocol.

---

## 51. Implementation freedom granted to Codex

Codex may choose, subject to review:

- SQL table design;
- JSONB vs normalized placement;
- Pydantic structures;
- FastAPI routers;
- service/repository abstractions;
- transaction strategy;
- dependency injection;
- state enum names;
- YAML/JSON operational study format;
- structured Tutor/Judge output schemas;
- prompt-template representation;
- LLM client library;
- retry/repair implementation;
- migration layout;
- frontend route/partial structure;
- test fixtures;
- logging implementation.

These decisions must not change the research or architecture invariants.

---

## 52. Required Codex implementation-design proposal

Before writing production code, Codex should propose:

1. repository layout;
2. service/module boundaries;
3. operational study-file format;
4. validation strategy;
5. `CompiledStudy` representation;
6. persistence model;
7. state-machine representation;
8. transaction/idempotency approach;
9. randomization/audit strategy;
10. Tutor runtime;
11. Assessment runtime;
12. Judge runtime;
13. deterministic rubric implementation;
14. History Builder;
15. Prompt Compiler;
16. LLM Adapter;
17. failure/retry handling;
18. FastAPI/UI request flow;
19. migration approach;
20. Docker setup;
21. test strategy;
22. implementation phases.

For every meaningful decision not mandated by this HLD, the proposal should state:

```text
Decision
Rationale
Alternatives considered
Why suitable for POC
Impact on future extensibility
```

---

## 53. Recommended prompt to Codex

> Read the Study-Pack Specification, the Fibonacci POC Study Definition, and the AI Harness High-Level Design as normative inputs. Do not implement yet. Produce a concrete technical implementation proposal for the harness. You may choose implementation details not fixed by the HLD, but identify those choices explicitly. Preserve every experimental invariant and information-flow boundary. Call out ambiguity, contradiction, or implementation risk rather than silently resolving it. Include repository structure, operational study schemas, persistence design, service boundaries, state machine, prompt compilation, LLM integration, failure handling, Docker deployment, testing strategy, and implementation phases. End with a list of implementation decisions that require human approval before coding.

---

## 54. Suggested implementation order after approval

```text
1. Repository + Docker + DB connectivity
2. Study parsing / validation / compilation
3. Study-version freeze + session persistence
4. Protocol state machine with fake Tutor/Judge
5. Assessment selection + deterministic rubric
6. Prompt Compiler + LLM Adapter
7. Tutor Runtime + History Builder
8. Judge Runtime
9. Server-rendered participant UI
10. Audit/recovery/integration tests
11. Real-provider smoke tests
12. Pilot-ready hardening
```

The exact order may change, but the core protocol should be testable with fake models before real LLM calls become necessary.

---

## 55. Final system view

```text
VERSIONED STUDY DEFINITION
          │
          ▼
STUDY LOADER / VALIDATOR
          │
          ▼
     COMPILED STUDY
          │
   ┌──────┴────────┐
   │               │
   ▼               ▼
PROTOCOL       PROMPT COMPILER
ENGINE             │
   │          ┌────┴────┐
   │          ▼         ▼
   │        TUTOR     JUDGE
   │          │         │
   │          ▼         ▼
   │      LLM ADAPTER  LLM ADAPTER
   │          │         │
   │          ▼         ▼
   │    INTERVENTION  EVIDENCE
   │          │         │
   │          ▼         ▼
   │     ASSESSMENT   RUBRIC
   │          │         │
   └──────────┴────┬────┘
                   ▼
            SESSION STATE / DB
                   │
                   ▼
             PARTICIPANT UI
```

---

## 56. Final architectural contract

The harness can be reduced to seven rules:

```text
1. Study files define meaning; harness defines execution.
2. Backend/database own experimental state.
3. Protocol owns sequencing; LLMs do not.
4. Tutor obeys assigned pedagogy and may use prior learner history.
5. Assessment is fresh and independent of the pedagogy just used.
6. Judge is blinded from treatment history and returns evidence, not protocol control.
7. Everything needed to reconstruct the experiment is persisted.
```

If the concrete implementation proposal preserves these rules and the detailed invariants above, the remaining engineering decisions can be made pragmatically for the POC.
