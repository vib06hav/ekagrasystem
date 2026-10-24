# Stage 2 — Runtime & AI Execution Design

**System:** SOLO-Transition AI Learning Harness  
**Initial study:** Recursive Fibonacci with Memoization  
**Status:** Proposed technical design for human review  
**Scope:** Protocol execution, interventions, prompts, Tutor/Judge contracts, assessments, history, LLM integration, deterministic evaluation, failure recovery, transactions, and runtime tests. No implementation is included.

---

## 1. Understanding of the approved Stage-1 foundation

Stage 2 builds on these approved Stage-1 decisions:

- The application is a FastAPI/PostgreSQL modular monolith.
- Operational YAML is the executable source of truth after review and freezing.
- Markdown is provenance and research/design authority, not a runtime input.
- `StudyVersion.content_hash` identifies authored operational content.
- `StudyVersion.compiler_contract_version` and `StudyVersion.snapshot_hash` separately identify the compiler/runtime interpretation and compiled representation.
- Every Session is permanently bound only to its immutable StudyVersion through `study_version_id`.
- Runtime services access one immutable `CompiledStudy`.
- PostgreSQL owns current runtime state.
- Protocol events and raw evidence provide audit history.
- Session, Attempt, Message, AssessmentInstance, AssessmentResponse, LLMCall, Judgment, RubricEvaluation, and LearnerHistorySnapshot persistence already exists.
- LLM calls, learner evidence, prompts, provider metadata, and parsed outputs are persistable.
- Session mutations use row locking, idempotency records, and same-transaction event appends.

Stage 2 does not change the study or persistence architecture.

### Approved LLMCall lifecycle

Stage 1 defines the nonterminal `RECEIVED` status for the interval after a raw provider response is persisted and before it is accepted into domain state:

```text
STARTED
   ↓
RECEIVED
   ├──→ SUCCEEDED
   ├──→ INVALID_OUTPUT
   └──→ FAILED
```

No new table or column is required. `RECEIVED` means the raw provider response has been committed but has not yet been accepted into domain state.

Consequences:

- Raw responses can be recovered and revalidated after restart.
- A crash after receipt does not require another provider call.
- Stage-1 immutability still applies after a terminal LLMCall status.

---

## 2. Stage-2 runtime architecture

### 2.1 Components

| Component | Responsibility |
|---|---|
| `SessionRuntime` | Application-level orchestrator and transaction owner for participant actions |
| `ProtocolEngine` | Pure determination of valid next protocol action |
| `PedagogySelector` | Candidate calculation and auditable random selection |
| `InterventionRuntime` | Attempt initialization, budgets, instructional progress trace, and assessment handoff |
| `TutorRuntime` | Tutor prompt execution and validated Tutor-result processing |
| `PromptCompiler` | Provider-neutral Tutor and Judge prompt construction |
| `HistoryBuilder` | Deterministic construction of prior-attempt summaries |
| `AssessmentSelector` | Transition-specific, pedagogy-blind unseen-form selection |
| `AssessmentRuntime` | Assessment activation, submission, and Judge handoff |
| `JudgeRuntime` | Blinded Judge prompt execution and Judgment creation |
| `RubricEvaluator` | Pure deterministic pass/fail calculation |
| `RandomSelector` | Standard trustworthy random choice with an injectable test source |
| `StructuredOutputProcessor` | Extraction, parsing, schema validation, semantic validation, and repair planning |
| `LLMClient` | Provider-neutral execution interface |
| `OpenAICompatibleClient` | HTTP/provider implementation behind `LLMClient` |
| `StudyCatalog` | Loads the compiled snapshot stored in the session-bound StudyVersion |
| Persistence/query modules | Focused SQLAlchemy reads and writes |
| `ProtocolEventWriter` | Appends versioned audit events inside caller-owned transactions |

These are modules/classes inside one application, not independently deployed services.

### 2.2 Component diagram

```text
Participant command
        │
        ▼
┌─────────────────────┐
│   SessionRuntime    │
│ transaction owner   │
└──────┬──────────────┘
       │
       ├───────────────► StudyCatalog ─────► frozen CompiledStudy
       │
       ├───────────────► ProtocolEngine
       │                       │
       │                       ├──► PedagogySelector
       │                       └──► RandomSelector
       │
       ├───────────────► InterventionRuntime
       │                       │
       │                       ├──► HistoryBuilder
       │                       └──► TutorRuntime
       │                                │
       │                                ├──► TutorPromptCompiler
       │                                ├──► StructuredOutputProcessor
       │                                └──► LLMClient
       │
       ├───────────────► AssessmentRuntime
       │                       │
       │                       ├──► AssessmentSelector
       │                       └──► RandomSelector
       │
       └───────────────► JudgeRuntime
                               │
                               ├──► JudgePromptCompiler
                               ├──► StructuredOutputProcessor
                               ├──► LLMClient
                               └──► RubricEvaluator
                                           │
                                           ▼
                                    ProtocolEngine
                                           │
                                           ▼
                                  next attempt / state /
                                  unresolved / completed

All state changes
        │
        ▼
PostgreSQL + ProtocolEventWriter
```

### 2.3 Allowed dependencies

- `SessionRuntime` may call every runtime application component.
- `ProtocolEngine` may use CompiledStudy protocol data and pure selectors.
- `InterventionRuntime` may use the compiled cell, Knowledge Slice, history, messages, and budget state.
- `TutorRuntime` may use only Tutor-specific prompt input and the generic LLM client.
- `AssessmentSelector` may use transition, family, active forms, seen form IDs, and the configured random selector.
- `JudgeRuntime` may use only the selected assessment, learner response, Knowledge Slice, Judge contract, and rubric.
- `RubricEvaluator` may use only validated Judge evidence, the compiled rubric, the selected form ID, and formal state.
- The LLM adapter may know provider configuration, messages, schemas, and request metadata.

### 2.4 Prohibited dependencies

- Protocol code must not call an LLM.
- Tutor code must not mutate formal SOLO state.
- Tutor code must not select an assessment or pedagogy.
- Assessment selection must not receive an Attempt, pedagogy ID, Tutor output, or Tutor transcript.
- Judge prompt construction must not receive an Attempt, pedagogy ID, Tutor message, prior history, or previous outcome.
- Judge code must not directly advance the Session.
- The LLM adapter must not know about SOLO, KCs, transitions, assessment selection, or protocol routing.
- Tutor and Judge must not share conversational state.
- Runtime services must not read operational YAML during participant execution.
- Provider-specific message formatting must not enter CompiledStudy or study semantics.

---

## 3. Protocol Engine

### 3.1 State model

Recommended Session phases:

```text
TRANSITION_READY
INTERVENTION_ACTIVE
ASSESSMENT_ACTIVE
JUDGING
TERMINAL
```

Recommended Attempt statuses:

```text
ASSIGNED
INTERVENTION_ACTIVE
INTERVENTION_COMPLETE
ASSESSMENT_ACTIVE
ASSESSMENT_SUBMITTED
JUDGING
PASSED
FAILED
TECHNICAL_HOLD
```

A technical hold is recorded on the Attempt while the Session retains the underlying phase. For example, a failed Judge call leaves:

```text
Session.phase = JUDGING
Attempt.status = TECHNICAL_HOLD
```

This preserves the correct recovery target.

### 3.2 Initial attempt creation

When a Session is created:

1. Load its bound CompiledStudy.
2. Verify formal state equals the protocol initial state `P`.
3. Resolve the first transition `C1`.
4. Calculate unused pedagogy candidates.
5. Select one through `RandomSelector`.
6. Create Attempt 1 with:
   - `transition_id=C1`;
   - selected pedagogy;
   - `formal_state_before_id=P`;
   - status `ASSIGNED`.
7. Set Session:
   - `current_transition_id=C1`;
   - `current_attempt_id=<new attempt>`;
   - `current_attempt_number=1`;
   - `phase=INTERVENTION_ACTIVE`.
8. Append selection and attempt-created events.
9. Commit.
10. The opening Tutor turn may then be initiated outside that transaction.

A pedagogy counts as used when its Attempt row is committed, not only after intervention completion. A technical retry never creates another Attempt.

### 3.3 Candidate calculation

For transition `T`:

```text
configured =
    protocol.pedagogy_ids

used =
    pedagogy_id from every existing Attempt
    for Session + transition T

candidates =
    configured - used
```

The resulting candidates retain no preference or adaptive ranking.

An empty candidate pool is legal only after the maximum allowed attempts have been exhausted.

### 3.4 Applying a completed rubric evaluation

The protocol receives:

```text
Session current state
Attempt
CompiledTransitionPlan
RubricEvaluation
```

It does not reinterpret Judge evidence.

Pseudocode:

```text
apply_outcome(session, attempt, evaluation):

    require session.current_attempt_id == attempt.id
    require session.phase == JUDGING
    require attempt has no prior RubricEvaluation

    if evaluation.passed:
        attempt.status = PASSED
        attempt.passed = true
        attempt.formal_state_after = transition.target_state

        session.formal_state = transition.target_state

        if transition is final transition:
            session.status = COMPLETED
            session.phase = TERMINAL
            session.current_transition_id = null
            session.current_attempt_id = null
            session.terminal_reason = COMPLETED_EA
        else:
            next_transition = protocol.next_transition(transition)
            create_first_attempt(next_transition)

    else:
        attempt.status = FAILED
        attempt.passed = false
        attempt.formal_state_after = session.formal_state

        unused = unused_pedagogies(session, transition)

        if unused is not empty:
            create_next_attempt_same_transition(unused)
        else:
            session.status = UNRESOLVED
            session.phase = TERMINAL
            session.current_attempt_id = null
            session.terminal_reason = UNRESOLVED_<transition_id>
```

All changes and events occur in one transaction.

### 3.5 Next-attempt creation

When another Attempt is required:

- A new pedagogy is selected without replacement.
- The Attempt sequence is previous sequence + 1.
- `formal_state_before_id` remains the current formal state.
- A deterministic PriorAttemptHistory snapshot is created for the new Attempt.
- Session points to the new Attempt.
- Session phase becomes `INTERVENTION_ACTIVE`.
- The new Attempt starts as `ASSIGNED`.

For the first Attempt of a new transition, same-transition history is empty.

### 3.6 Formal versus observed SOLO state

The Judgment may report an observed state above or below the transition target.

Example:

```text
formal state before: U
transition: C2 U→M
observed state: R
evaluation: PASS
formal state after: M
```

The observed state is evidence. It never causes the protocol to skip C3.

On failure:

```text
formal state after = formal state before
```

No state is inferred from Tutor conversation.

---

## 4. Randomization

### 4.1 Decision

Use a standard trustworthy random selector. The production implementation uses `secrets.SystemRandom().choice()` over the eligible candidate list.

The selector is dependency-injected so tests may use a standard seeded `random.Random` instance or a fixed fake selector. A simple optional Session seed may be stored in `runtime_config_snapshot` when a deterministic test/pilot mode is deliberately enabled. Production audit does not depend on replaying the draw: the committed selected action is the authoritative experimental fact.

### 4.2 Selection algorithm

For either pedagogy or assessment selection:

1. Calculate the eligible candidate IDs.
2. Preserve a stable sorted copy for audit output.
3. Call the configured standard random selector once.
4. Verify the returned ID belongs to the eligible candidates.
5. Persist the complete selection record in the same transaction as the resulting Attempt or AssessmentInstance.

No custom HMAC, digest, rejection-sampling, or application-specific RNG protocol is used.

### 4.3 Pedagogy selection audit

Persist in the selection event:

```text
configured pedagogy IDs
already-used pedagogy IDs
eligible candidate IDs
selected pedagogy ID
selection method
selection timestamp
optional configured Session seed identifier/value when deterministic mode is used
```

The Attempt row remains the authoritative selected action. The event explains which alternatives were eligible and excluded when the selection occurred.

### 4.4 Assessment selection

Eligible forms are:

```text
active forms in assessment family for current transition
    minus
every form with an AssessmentInstance in this Session
```

Once an AssessmentInstance is committed, its form is treated as seen even if a later technical failure occurs.

The selector input is a narrow DTO:

```text
AssessmentSelectionInput
    session_id
    transition_id
    active_form_ids
    seen_form_ids
```

It contains no pedagogy field and cannot accept an Attempt object. This enforces pedagogy blindness structurally.

The selection event records:

- active forms;
- seen forms;
- eligible candidates;
- selected form.
- selection method and timestamp.

No adaptive treatment assignment or learner-dependent weighting is permitted.

---

## 5. Intervention Runtime

### 5.1 Starting an Attempt

Given an `ASSIGNED` Attempt, the runtime resolves from CompiledStudy:

- `CompiledTransitionPlan`;
- `CompiledInterventionCell` for transition/pedagogy;
- `PedagogyFamily`;
- `KnowledgeSlice`;
- authored intervention procedure guidance;
- cell budget;
- PriorAttemptHistory snapshot, if any.

It verifies:

- Attempt transition matches the Session;
- selected cell matches the immutable pedagogy ID;
- Session is in `INTERVENTION_ACTIVE`;
- no AssessmentInstance exists;
- no other nonterminal Tutor LLM call exists.

It then records `intervention_started_at` and changes Attempt status to `INTERVENTION_ACTIVE`.

### 5.2 Opening Tutor turn

Every Attempt begins with a generated Tutor opening turn. The prompt contains no invented learner message; instead it includes a harness control instruction:

```text
Begin the assigned intervention using the authored procedure guidance.
```

The opening counts as one Tutor turn for budget purposes.

### 5.3 Current-attempt dialogue

Messages are loaded in `sequence_no` order. Only Messages belonging to the current Attempt enter the Tutor dialogue.

The dialogue includes:

- accepted learner messages;
- accepted learner-facing Tutor messages.

It excludes:

- raw invalid Tutor outputs;
- repair prompts;
- provider errors;
- assessment responses;
- prior-attempt raw transcripts.

Invalid outputs remain in LLMCall records only.

### 5.4 Stage tracking

Procedure stages are authored guidance and runtime trace/progress information. They do not form a secondary harness state machine unless the operational study definition explicitly requires strict sequencing.

The Tutor may report the current or most relevant authored stage. If it reports a stage ID, that ID must belong to the assigned intervention cell. Unknown or cross-cell stage IDs are schema-semantic errors. Earlier, later, repeated, or omitted stage references are not errors merely because they do not form a strict progression.

Instructional progress survives refresh because every accepted Tutor message stores its structured trace. The latest trace may be supplied as context on the next turn, but it does not independently control protocol state.

### 5.5 Turn allowance

A Tutor call is allowed only if:

- Session phase is `INTERVENTION_ACTIVE`;
- current Attempt matches the Session;
- Attempt is `ASSIGNED` or `INTERVENTION_ACTIVE`;
- no assessment exists;
- no Tutor call is currently pending;
- Tutor-turn budget remains;
- configured elapsed budget, if any, has not expired;
- intervention has not been completed.

Tutor-turn count is the number of accepted Tutor messages, including the opening.

### 5.6 Completion authority

The Tutor may return `COMPLETE` when the assigned intervention has reached an appropriate instructional stopping point. The harness, not the Tutor, remains responsible for the resulting state transition.

The harness accepts `COMPLETE` when the output is otherwise valid and all ordinary intervention constraints are satisfied. It does not require every authored stage to have been individually completed unless the study definition explicitly declares a strict stage-sequence requirement.

The harness completes an intervention when either:

1. A valid Tutor `COMPLETE` disposition is accepted; or
2. A hard budget is exhausted.

Completion reasons are controlled values:

```text
TUTOR_COMPLETE
TURN_BUDGET_EXHAUSTED
ELAPSED_BUDGET_EXHAUSTED
```

Completion does not mean transition success.

### 5.7 Budget enforcement

Before reserving a call:

- If no turn remains, complete the intervention without another LLM call.
- If the elapsed deadline has passed, complete without accepting another learner message.

After a call:

- The Tutor response is preserved.
- If that response consumes the final turn or crosses an elapsed deadline, the harness marks the intervention complete regardless of `CONTINUE`.
- The Tutor is not asked to override or reinterpret a hard limit.

Technical-hold duration is excluded from an elapsed budget.

### 5.8 Assessment handoff

Intervention completion and assessment selection occur atomically:

1. Mark Attempt intervention complete.
2. Persist completion reason.
3. Calculate eligible forms through `AssessmentSelector`.
4. Select one using the configured standard random selector.
5. Insert the frozen AssessmentInstance.
6. Set Attempt status to `ASSESSMENT_ACTIVE`.
7. Set Session phase to `ASSESSMENT_ACTIVE`.
8. Append completion and selection events.
9. Commit.

After this transaction, no Tutor call or learner Tutor message is permitted.

---

## 6. Prompt Compiler

### 6.1 Provider-neutral prompt representation

The compiler emits a `PromptEnvelope`:

```text
PromptEnvelope
    schema_version
    prompt_contract_version
    logical_role                 TUTOR | JUDGE
    operation_id
    study_version_id
    content_hash
    compiler_contract_version
    snapshot_hash
    ordered_messages
    response_schema_name
    response_schema_version
    response_json_schema
    audit_context
    canonical_prompt_text
    prompt_hash
```

A `CanonicalMessage` contains:

```text
role: SYSTEM | USER | ASSISTANT
content: string
```

`audit_context` is persisted but is never serialized to the provider unless explicitly included in the ordered messages.

The prompt hash is over the canonical provider-neutral messages and response schema. It is distinct from the study and compiled-snapshot hashes.

### 6.2 Tutor compiler interface

Input:

```text
TutorPromptInput
    Tutor harness contract
    PedagogyFamily
    CompiledInterventionCell
    KnowledgeSlice
    PriorAttemptHistory
    authored procedure guidance
    latest reported progress stage, if any
    ordered current-attempt dialogue
    remaining turn budget
    remaining elapsed budget
```

Output: `PromptEnvelope[TutorTurnOutput]`.

### 6.3 Tutor section order and precedence

The Tutor system message uses this order:

```text
0. HARNESS TUTOR CONTRACT
1. ASSIGNED PEDAGOGY FAMILY
2. KNOWLEDGE SLICE
3. INTERVENTION CELL
4. PROCEDURE GUIDANCE AND CURRENT PROGRESS
5. PRIOR-ATTEMPT STRUCTURED HISTORY
6. CURRENT BUDGET AND RUNTIME CONSTRAINTS
7. REQUIRED OUTPUT SCHEMA
```

Then the current Attempt dialogue is appended as normal `USER` and `ASSISTANT` messages.

Precedence is explicit:

```text
Harness safety/execution contract
    >
Knowledge semantic truth
    >
Pedagogy-family mechanism
    >
Transition-specific cell
    >
Runtime history and dialogue
```

A conflict that should have been caught at study compilation is treated as a system error, not resolved by the LLM.

### 6.4 Representative Tutor structure

```text
SYSTEM

[HARNESS_TUTOR_CONTRACT]
You are the Tutor for one assigned intervention attempt.
Remain in the assigned pedagogy.
Do not select assessments, judge transition success, or change formal state.
Return only the required structured output.

[PEDAGOGY_FAMILY id="P2"]
Core mechanism: ...
Permissions: ...
Prohibitions: ...

[KNOWLEDGE_SLICE transition="C3"]
Starting state: M
Target state: R
Assumed knowledge: ...
Target knowledge: ...
Target relations: ...
Relevant misconceptions: ...
Not-yet-required knowledge: ...

[INTERVENTION_CELL id="C3-P2"]
Instructional intent: ...
Missing structure: ...
Required procedure: ...

[PROCEDURE_GUIDANCE]
Authored stages: ...
Latest reported progress stage: C3-P2-S2

[PRIOR_ATTEMPT_HISTORY]
<canonical JSON data, or "none">

[RUNTIME]
Tutor turns remaining after this call: 4
Elapsed budget remaining: 620 seconds
Latest instructional trace summary: ...

[OUTPUT_CONTRACT]
TutorTurnOutput schema version 1.0
```

Dialogue messages follow. For the opening call, the final user message is a fixed harness control message rather than a fabricated learner statement.

### 6.5 Judge compiler interface

Input:

```text
JudgePromptInput
    Judge harness contract
    CompiledJudgeRubric
    KnowledgeSlice
    AssessmentPromptSnapshot
    HiddenScoringContextSnapshot
    LearnerResponseText
```

No other input type is accepted.

Output: `PromptEnvelope[JudgeObservation]`.

### 6.6 Judge section order

```text
0. HARNESS JUDGE CONTRACT
1. TRANSITION RUBRIC
2. KNOWLEDGE SLICE
3. SELECTED ASSESSMENT
4. HIDDEN ITEM-SPECIFIC CONTEXT
5. LEARNER RESPONSE
6. REQUIRED OUTPUT SCHEMA
```

Representative form:

```text
SYSTEM

[HARNESS_JUDGE_CONTRACT]
Evaluate demonstrated evidence only.
Do not teach, infer treatment history, or direct protocol behavior.
Return only JudgeObservation schema version 1.0.

[TRANSITION_RUBRIC id="JR-C3"]
Target state: R
Evidence criteria: ...
Blocking misconceptions: ...

[KNOWLEDGE_SLICE transition="C3"]
...

[ASSESSMENT]
Prompt:
...

[HIDDEN_ITEM_CONTEXT]
...

[OUTPUT_CONTRACT]
JudgeObservation schema version 1.0

USER

[LEARNER_RESPONSE]
...
```

### 6.7 Natural-language serialization

Authored prose is inserted verbatim after newline normalization.

Each block is:

- explicitly named;
- ID-labelled where applicable;
- bounded by deterministic section markers;
- serialized in a fixed order.

Learner content is clearly marked as untrusted response data. It is never interpolated into system instructions.

### 6.8 Persistence

Before sending, persist:

- canonical prompt text;
- canonical messages;
- response schema;
- prompt contract version;
- prompt hash;
- exact provider request body produced by the adapter;
- generation parameters.

The provider adapter may translate canonical messages into provider-specific fields, but may not alter their semantic order or content silently.

---

## 7. Tutor structured contract

### 7.1 Pydantic-style schema

```text
TutorDisposition =
    CONTINUE
    COMPLETE

StageStatus =
    IN_PROGRESS
    COMPLETED

LearnerEvidenceStatus =
    DEMONSTRATED_IN_DIALOGUE
    PARTIAL_IN_DIALOGUE
    UNCLEAR

TutorMisconceptionStatus =
    EXPRESSED
    SUSPECTED

TutorLearnerObservation:
    target_type: KC | RELATION
    target_id: EntityId
    status: LearnerEvidenceStatus
    summary: str, 1..500 characters

TutorMisconceptionObservation:
    misconception_id: MisconceptionId
    status: TutorMisconceptionStatus
    summary: str, 1..500 characters

TutorInstructionalTrace:
    stage_id: EntityId | null
    stage_status: StageStatus
    exposed_kc_ids: tuple[KnowledgeComponentId, ...]
    exposed_relation_ids: tuple[RelationId, ...]
    used_material_ids: tuple[str, ...]
    learner_observations: tuple[TutorLearnerObservation, ...]
    misconception_observations: tuple[TutorMisconceptionObservation, ...]
    concise_summary: str, 1..1000 characters

TutorTurnOutput:
    schema_version: Literal["1.0"]
    learner_message: str, 1..8000 characters
    disposition: TutorDisposition
    trace: TutorInstructionalTrace
```

All models use strict validation and `extra="forbid"`.

### 7.2 Semantic validation

Beyond Pydantic shape:

- If present, `stage_id` must belong to the assigned intervention cell.
- Exposed KCs and relations must belong to the cell/Knowledge Slice.
- Misconception IDs must belong to the cell’s relevant misconceptions.
- Material IDs must be allowed by the cell.
- Reserved assessment material tags are forbidden.
- IDs must be unique within each list.
- `COMPLETE` is accepted without inventing an all-stages-complete rule; any explicit strict stage constraint authored by the study is still enforced.
- The output must not contain protocol fields such as `passed`, `next_pedagogy`, or `formal_state`.

### 7.3 Authority limits

Tutor observations are provisional interaction evidence. They may support later personalization but cannot:

- establish transition success;
- override Judge evidence;
- advance formal state;
- select treatment;
- select assessment;
- modify the Knowledge Slice.

### 7.4 Visibility and persistence

Learner-visible:

- `learner_message` only.

Persisted internally:

- entire parsed `TutorTurnOutput`;
- instructional trace on the Tutor Message;
- raw provider response;
- validation result;
- LLMCall metadata.

No hidden chain-of-thought, reasoning trace, private scratchpad, or token-by-token explanation is requested.

---

## 8. Tutor turn lifecycle

### 8.1 Opening turn

```text
ensure Attempt is ASSIGNED
    ↓ transaction
mark intervention started
compile Tutor opening prompt
prepare provider request
insert STARTED LLMCall
commit
    ↓ no transaction
send provider request
    ↓ transaction
persist raw response as RECEIVED
commit
    ↓
validate / repair if necessary
    ↓ transaction
persist accepted Tutor Message + trace
persist instructional trace and update budget-derived state
possibly complete intervention/select assessment
mark LLMCall SUCCEEDED
append events
commit
```

### 8.2 Learner reply turn

```text
learner command with idempotency key
    ↓ transaction
lock Session
validate INTERVENTION_ACTIVE
reject if pending call or budget exhausted
persist learner Message
load frozen study/current dialogue/history
compile Tutor prompt
prepare exact provider request
insert STARTED LLMCall
store idempotency reservation
commit
    ↓ no transaction
provider call
    ↓ transaction
persist raw response as RECEIVED
commit
    ↓
validate / repair
    ↓ transaction
persist Tutor Message and trace
update progress
complete intervention if required
complete idempotency record
append events
commit
```

### 8.3 Data reread each turn

From PostgreSQL:

- Session and current Attempt;
- Session-bound compiled snapshot identity;
- ordered current Attempt Messages;
- latest nonterminal LLMCall;
- LearnerHistorySnapshot;
- existing AssessmentInstance;
- idempotency record;
- relevant timestamps.

From CompiledStudy cache:

- protocol;
- transition plan;
- Knowledge Slice;
- pedagogy family;
- intervention cell;
- procedure and budget.

The CompiledStudy cache is keyed by immutable `study_version_id`; the cached object is verified against the `snapshot_hash` stored in that StudyVersion. Current state is never trusted solely from process memory.

### 8.4 Tutor completion result

If Tutor returns a valid `COMPLETE` disposition:

- Persist the Tutor message and instructional trace.
- Finalize the intervention without requiring an invented strict stage progression.
- Select and snapshot the assessment in the same transaction.
- Change the Session to `ASSESSMENT_ACTIVE`.

The output remains invalid if it changes the assigned pedagogy, references a stage outside the assigned cell, uses prohibited content/material, or violates another explicit study constraint.

### 8.5 Budget exhaustion

If exhausted before a new call:

- Do not persist the submitted text as a Tutor dialogue message.
- Complete the intervention.
- Select the assessment.
- Return the authoritative assessment-ready state.

If exhausted because an accepted Tutor response consumes the last turn:

- Persist that response.
- Ignore its `CONTINUE` disposition for control-flow purposes.
- Complete with `TURN_BUDGET_EXHAUSTED`.
- Move atomically to assessment.

---

## 9. Prior-Attempt History

### 9.1 Schema

```text
HistoryEvidenceSource =
    TUTOR_DIALOGUE
    JUDGE_ASSESSMENT

HistoryEvidenceStatus =
    DEMONSTRATED
    PARTIAL
    NOT_DEMONSTRATED
    UNCLEAR

HistoryMisconceptionStatus =
    DETECTED
    POSSIBLE
    SUSPECTED_IN_DIALOGUE

PriorExposure:
    reported_stage_ids: tuple[EntityId, ...]
    material_ids: tuple[str, ...]
    exposed_kc_ids: tuple[KnowledgeComponentId, ...]
    exposed_relation_ids: tuple[RelationId, ...]

PriorEvidence:
    source: HistoryEvidenceSource
    target_type: KC | RELATION | RUBRIC_CRITERION
    target_id: EntityId
    status: HistoryEvidenceStatus
    summary: str

PriorMisconception:
    misconception_id: MisconceptionId
    status: HistoryMisconceptionStatus
    source: HistoryEvidenceSource
    summary: str

PriorAssessmentOutcome:
    gradable: bool
    correctness: CorrectnessStatus
    observed_solo_state_id: SoloStateId | null
    transition_passed: bool
    evidence_summary: str

PriorAttemptEntry:
    source_attempt_id: UUID
    sequence_in_transition: int
    pedagogy_id: PedagogyId
    intervention_completion_reason: str
    exposure: PriorExposure
    learner_evidence: tuple[PriorEvidence, ...]
    misconceptions: tuple[PriorMisconception, ...]
    assessment_outcome: PriorAssessmentOutcome

PriorAttemptHistory:
    schema_version: Literal["1.0"]
    transition_id: TransitionId
    target_attempt_id: UUID
    attempts: tuple[PriorAttemptEntry, ...]
```

### 9.2 Field sources

| Field | Source |
|---|---|
| Pedagogy and attempt sequence | Attempt |
| Completion reason | Attempt |
| Stages/materials/KCs/relations exposed | Accepted Tutor traces |
| Tutor learner observations | Accepted Tutor traces |
| Gradability/correctness/observed state | Judgment |
| Criterion and semantic evidence | Judgment |
| Misconceptions | Tutor traces and Judgment, with provenance retained |
| Pass/fail | RubricEvaluation |

### 9.3 Generation

History is generated deterministically when a failed Attempt causes creation of the next Attempt on the same transition.

The builder:

1. Reads all completed prior Attempts on that Session/transition.
2. Aggregates accepted structured traces and judgments.
3. Preserves source/provenance.
4. Uses stable ordering by Attempt sequence and entity ID.
5. Creates one immutable LearnerHistorySnapshot targeting the new Attempt.

No history is carried from C1 into the first C2 Attempt. The current formal state and C2 Knowledge Slice represent established prior-transition assumptions.

### 9.4 No LLM summarizer

The POC does not need a separate history-summarization LLM.

Reasons:

- Required information is already structured.
- Deterministic aggregation is reproducible.
- It avoids another model dependency and another leakage boundary.
- It prevents free-form summarization from inventing learner evidence.

Concise summaries supplied by accepted Tutor/Judge contracts may be included, but the aggregation itself is deterministic.

### 9.5 Excluded information

The Tutor-facing history contains no:

- assessment form ID;
- assessment prompt;
- hidden scoring context;
- answer key;
- raw assessment response;
- learner-response excerpt from the assessment;
- Judge hidden reasoning;
- future assessment;
- future pedagogy;
- provider/model metadata.

Raw transcripts and responses remain in their Stage-1 tables for audit and are not copied wholesale into Tutor prompts.

---

## 10. Assessment Runtime

### 10.1 Selection boundary

The AssessmentRuntime constructs `AssessmentSelectionInput` from:

- Session ID;
- snapshot hash;
- current transition ID;
- compiled assessment family;
- active form IDs;
- form IDs already instantiated in the Session;
- assessment ordinal.

It deliberately does not load or pass pedagogy identity to `AssessmentSelector`.

The enclosing persistence transaction may know the Attempt ID for ownership, but the selector and its input model cannot represent pedagogy.

### 10.2 Activation transaction

On intervention completion:

1. Lock Session.
2. Verify Session and Attempt still permit completion.
3. Mark intervention complete.
4. Calculate seen form IDs.
5. Resolve the transition’s assessment family.
6. Calculate active unseen candidates.
7. Fail with a protocol-invariant error if none exist.
8. Select one with the configured standard random selector.
9. Insert AssessmentInstance with:
   - candidate list;
   - selection audit: eligible and excluded candidates, selected ID, method, timestamp, and optional test seed;
   - prompt snapshot;
   - hidden scoring context snapshot;
   - family/form/transition IDs.
10. Change Attempt to `ASSESSMENT_ACTIVE`.
11. Change Session to `ASSESSMENT_ACTIVE`.
12. Append events.
13. Commit.

The prompt and hidden scoring context are copied from CompiledStudy at selection time. Later runtime code uses these snapshots for this assessment.

### 10.3 Submission

The participant may submit exactly once.

The submission command:

- requires an idempotency key;
- requires Session phase `ASSESSMENT_ACTIVE`;
- requires AssessmentInstance status active;
- rejects an already submitted instance unless the idempotency key matches the original command;
- persists the exact response;
- changes the assessment to submitted;
- changes Attempt status to `JUDGING`;
- changes Session phase to `JUDGING`;
- prepares and reserves the Judge LLMCall;
- commits before the provider call.

An empty response may be rejected as invalid input if the assessment contract requires nonempty text. It is not silently converted into a protocol outcome.

### 10.4 Tutor prohibition

After AssessmentInstance activation:

- Tutor message submission fails phase validation.
- Tutor call reservation fails.
- No Tutor prompt can be compiled for that Attempt.
- Existing Tutor dialogue remains read-only.
- No hints or corrective content are generated.

### 10.5 Judge triggering

Judge processing begins from the committed AssessmentResponse. It is safe to resume because the raw learner response exists before any provider request occurs.

---

## 11. Judge structured contract

### 11.1 Controlled vocabularies

```text
CorrectnessStatus =
    CORRECT
    MINOR_ERROR
    MATERIALLY_INCORRECT
    NOT_GRADABLE

EvidenceStatus =
    DEMONSTRATED
    PARTIAL
    NOT_DEMONSTRATED
    CONTRADICTED
    NOT_EVALUABLE

MisconceptionStatus =
    NOT_DETECTED
    POSSIBLE
    DETECTED

NotGradableReason =
    EMPTY_OR_NO_MEANINGFUL_RESPONSE
    OFF_TOPIC
    UNINTERPRETABLE
    INSUFFICIENT_TO_EVALUATE
```

`MINOR_ERROR` means the response remains materially sound for the target construct. A substantive contradiction must be `MATERIALLY_INCORRECT`.

### 11.2 Evidence citation

```text
EvidenceCitation:
    excerpt: str, 1..300 characters
```

Each excerpt must be verifiably present in the submitted learner response after newline normalization. The Judge is not asked for hidden reasoning.

### 11.3 Evidence objects

```text
KnowledgeComponentEvidence:
    kc_id: KnowledgeComponentId
    status: EvidenceStatus
    citations: tuple[EvidenceCitation, ...]
    concise_summary: str, max 500

RelationEvidence:
    relation_id: RelationId
    status: EvidenceStatus
    citations: tuple[EvidenceCitation, ...]
    concise_summary: str, max 500

CriterionEvidence:
    criterion_id: EvidenceCriterionId
    status: EvidenceStatus
    citations: tuple[EvidenceCitation, ...]
    concise_summary: str, max 500

MisconceptionEvidence:
    misconception_id: MisconceptionId
    status: MisconceptionStatus
    citations: tuple[EvidenceCitation, ...]
    concise_summary: str, max 500
```

### 11.4 Complete Judge schema

```text
JudgeObservation:
    schema_version: Literal["1.0"]

    gradable: bool
    not_gradable_reason: NotGradableReason | null

    correctness: CorrectnessStatus
    observed_solo_state_id: SoloStateId | null

    kc_evidence:
        tuple[KnowledgeComponentEvidence, ...]

    relation_evidence:
        tuple[RelationEvidence, ...]

    criterion_evidence:
        tuple[CriterionEvidence, ...]

    misconception_evidence:
        tuple[MisconceptionEvidence, ...]

    confidence:
        Decimal in [0, 1] | null

    ambiguity_summary:
        str, max 1000 | null

    overall_evidence_summary:
        str, 1..1500
```

### 11.5 Completeness validation

For a gradable response:

- `not_gradable_reason` must be null.
- Correctness cannot be `NOT_GRADABLE`.
- Observed state must be one of the study’s states.
- Every rubric evidence criterion must appear exactly once.
- Every blocking misconception must appear exactly once, including `NOT_DETECTED`.
- Required KC and relation IDs must have corresponding evidence entries.
- All IDs must belong to the Judge prompt context.
- Citations must match the learner response.
- Duplicate IDs are rejected.

For a non-gradable response:

- `correctness=NOT_GRADABLE`.
- `observed_solo_state_id=null`.
- `not_gradable_reason` is required.
- Criterion statuses must be `NOT_EVALUABLE` or `NOT_DEMONSTRATED`.
- The response still receives a concise evidence summary.

### 11.6 Authority boundary

The Judge schema contains no fields for:

- `transition_passed`;
- formal state after;
- next pedagogy;
- retry/stop;
- reward;
- protocol action.

Unknown fields are rejected.

Confidence is logged but does not affect the POC’s deterministic pass/fail rule.

---

## 12. Judge blindness / information boundaries

### 12.1 Narrow input construction

`JudgeRuntime` accepts an AssessmentResponse ID, not an Attempt object.

Its query path loads:

- AssessmentResponse;
- AssessmentInstance snapshots;
- Session’s StudyVersion ID and its stored snapshot hash;
- transition ID.

It does not load:

- Attempt pedagogy;
- Messages;
- LearnerHistorySnapshot;
- previous AssessmentInstances;
- previous Judgments.

The assessment’s Attempt ID remains a persistence relationship but is omitted from `JudgePromptInput`.

### 12.2 Typed prompt boundary

The only accepted compiler input is:

```text
JudgePromptInput
    judge_contract
    knowledge_slice
    rubric
    assessment_prompt
    hidden_scoring_context
    learner_response
```

Because the type has no treatment/history fields, those values cannot accidentally be serialized through normal prompt compilation.

### 12.3 Audit metadata separation

Internal audit data such as:

- Session ID;
- AssessmentInstance ID;
- LLMCall ID;
- snapshot hash;

may be attached to `PromptEnvelope.audit_context`.

The provider serializer has an allowlist and does not include audit context in provider messages.

### 12.4 Forbidden flows

```text
Attempt.pedagogy_id ─────────X──► JudgePromptInput
Tutor Messages ──────────────X──► JudgeRuntime
PriorAttemptHistory ─────────X──► JudgeRuntime
previous outcomes ───────────X──► JudgePromptCompiler
attempt ordinal ─────────────X──► provider request
```

Judge blindness is therefore enforced by query design, DTO shape, provider serialization, and tests—not by asking the Judge to ignore supplied data.

---

## 13. Deterministic Rubric Evaluator

### 13.1 Interface

The evaluator is pure:

```text
evaluate(
    formal_state_before,
    transition,
    assessment_form_id,
    compiled_rubric,
    judge_observation
) -> RubricEvaluationResult
```

It performs no database access and no LLM call.

### 13.2 Output

```text
RubricEvaluationResult:
    passed: bool
    reason_codes: tuple[RubricReasonCode, ...]
    reason_details: tuple[str, ...]
    satisfied_evidence_ids: tuple[EvidenceCriterionId, ...]
    unsatisfied_evidence_ids: tuple[EvidenceCriterionId, ...]
    blocking_misconception_ids: tuple[MisconceptionId, ...]
    formal_state_before_id: SoloStateId
    formal_state_after_id: SoloStateId
```

Representative reason codes:

```text
PASS_ALL_REQUIREMENTS
NOT_GRADABLE
CORRECTNESS_GATE_FAILED
OBSERVED_STATE_BELOW_TARGET
REQUIRED_EVIDENCE_MISSING
MINIMUM_EVIDENCE_NOT_MET
EVIDENCE_GROUP_NOT_MET
ITEM_REQUIREMENT_NOT_MET
BLOCKING_MISCONCEPTION_DETECTED
```

### 13.3 Evaluation order

1. Verify transition source state equals formal state before.
2. If not gradable, fail.
3. Apply correctness requirement.
4. Compare observed state rank with target rank.
5. Evaluate `evidence_all_of`.
6. Evaluate each `evidence_any_of_group`.
7. Evaluate `minimum_evidence_count`.
8. Apply assessment-form-specific evidence requirements.
9. Detect blocking misconceptions.
10. Produce pass/fail and complete reason set.
11. If passed, set formal state after to the transition target only.
12. If failed, retain formal state before.

A criterion counts as satisfied only when status is `DEMONSTRATED`. `PARTIAL` is preserved but does not satisfy a required criterion unless a future authored rule explicitly permits it.

A blocking misconception blocks only when status is `DETECTED`. `POSSIBLE` is logged but does not deterministically fail the transition.

### 13.4 Correctness gate

For Stage-1 `materially_sound`:

```text
accepted:
    CORRECT
    MINOR_ERROR

rejected:
    MATERIALLY_INCORRECT
    NOT_GRADABLE
```

A required criterion marked `CONTRADICTED` also remains unsatisfied even if the overall correctness label is permissive.

### 13.5 C1–C4 representation

C1:

```text
gradable required
materially sound required
observed state >= U
all_of: C1-E1, C1-E2
form-specific requirements, including C1-E3 where applicable
blocking: M1
```

C2:

```text
gradable required
materially sound required
observed state >= M
minimum demonstrated criteria: 3
any_of group: C2-E1 or C2-E2
any_of group: C2-E3 or C2-E4
form-specific required criterion, such as C2-E5 where probed
blocking: M3, M5, M6, and M8 where relevant
```

C3:

```text
gradable required
materially sound required
observed state >= R
all_of: C3-E1, C3-E2, C3-E3, C3-E4
form-specific: C3-E5 and/or C3-E6
blocking: M3–M9 as authored
```

C4:

```text
gradable required
materially sound required
observed state >= EA
any_of abstraction group: C4-E1 or C4-E2
any_of transfer group: C4-E3, C4-E4, C4-E5, or C4-E6
form-specific requirements
blocking: M6, M7, M8, M10, and recurrence errors
```

The exact criterion mappings remain authored rubric content. The evaluator implements only the generic declarative operators.

### 13.6 Above-target handling

If observed rank exceeds target rank and every other requirement passes:

```text
evaluation = PASS
formal_state_after = transition.target_state
```

No protocol state is skipped.

### 13.7 Not-gradable handling

A valid Judge observation of `not gradable` due to the learner’s submitted response fails the rubric because gradability is required.

It is a learner/experimental outcome, not a technical failure.

A Judge refusal, malformed output, or inability to produce the schema is instead a technical failure and never becomes `not gradable` automatically.

---

## 14. LLM Adapter

### 14.1 Internal request

```text
LLMRole =
    TUTOR
    JUDGE

StructuredOutputMode =
    PROVIDER_NATIVE_JSON_SCHEMA
    JSON_TEXT_FALLBACK

LLMRequest:
    logical_role: LLMRole
    operation_id: UUID
    retry_group_id: UUID
    retry_number: int
    provider: str
    base_url_key: str
    model: str
    messages: tuple[CanonicalMessage, ...]
    response_schema_name: str
    response_schema_version: str
    response_json_schema: dict
    structured_output_mode: StructuredOutputMode
    generation_parameters: dict
    timeout_seconds: Decimal
    provider_idempotency_key: str | null
    audit_context: dict
```

`base_url_key` identifies configured infrastructure; secrets and raw credentials are not part of the request model or persistence.

### 14.2 Prepared request

The adapter separates preparation from network execution:

```text
prepare(request) -> PreparedLLMRequest
send(prepared) -> RawLLMResponse
```

`PreparedLLMRequest` contains the exact headers-with-secrets-redacted and exact body that will be persisted before sending.

### 14.3 Response

```text
RawLLMResponse:
    provider_request_id: str | null
    status_code: int
    raw_response_text: str
    response_payload: dict | null
    structured_candidate: object | string | null
    finish_reason: str | null
    refusal: bool
    usage:
        input_tokens
        output_tokens
        total_tokens
    latency_ms: int
```

The adapter does not construct TutorTurnOutput or JudgeObservation. It only returns provider-level results.

### 14.4 Configuration

Environment/runtime configuration supplies:

- provider type; for this POC, `AICredits.in`;
- AICredits base URL and API credential reference;
- Tutor model;
- Judge model;
- role-specific generation parameters;
- timeouts;
- structured-output capability flags.

Effective non-secret values are copied into the Session runtime configuration snapshot and every LLMCall.

`OpenAICompatibleClient` is the selected AICredits adapter path when the configured AICredits endpoint is OpenAI-compatible. Any small provider-specific request/response variation is isolated in that adapter; it must not enter protocol, Tutor, Judge, or study-pack code.

Provider network I/O is asynchronous so one Uvicorn process can serve state reads and polling while an AICredits request is in flight. The logical participant command remains synchronous from the browser's perspective, and no database transaction spans the awaited network call.

### 14.5 Provider-native structured output

Use provider-native JSON Schema response formatting when supported.

Fallback:

- include the same schema contract in the prompt;
- request one JSON object;
- extract and validate locally.

Provider claims of schema compliance do not replace Pydantic and semantic validation.

### 14.6 Error classification

Adapter-level exceptions:

```text
AUTHENTICATION_ERROR          non-retryable automatically
CONFIGURATION_ERROR           non-retryable automatically
BAD_REQUEST                   normally non-retryable
RATE_LIMIT                    retryable
CONNECTION_ERROR              retryable
TIMEOUT                       retryable
PROVIDER_5XX                  retryable
PROVIDER_REFUSAL              output-repair eligible once
EMPTY_RESPONSE                output-repair eligible once
```

The adapter does not classify any provider error as learner failure.

---

## 15. Structured-output validation and repair

### 15.1 Validation sequence

```text
HTTP/provider success
    ↓
persist raw response as RECEIVED
    ↓
extract provider structured candidate
    ↓
parse JSON if necessary
    ↓
Pydantic strict schema validation
    ↓
role-specific semantic validation
    ↓
accept or plan repair
```

Role-specific semantic validation includes allowed IDs, stage constraints, evidence completeness, and citation grounding.

### 15.2 Outcomes

| Condition | Action |
|---|---|
| Valid structured output | Finalize domain result |
| Malformed JSON | Persist invalid result; attempt repair |
| Valid JSON, wrong shape | Persist validation errors; attempt repair |
| Pydantic-valid but semantic violation | Persist semantic errors; attempt repair |
| Empty response | Treat as invalid output; attempt repair |
| Provider refusal | Persist refusal; attempt one repair |
| Retryable provider error | One transport retry |
| Non-retryable provider/configuration error | Technical hold |
| Repeated invalid/refused output | Technical hold |

### 15.3 Retry and repair limits

Per logical Tutor or Judge operation:

- Initial call: one.
- Automatic transport retry: at most one.
- Structured-output repair: at most one.
- Total provider calls: at most three.

Examples:

```text
initial timeout
    → transport retry succeeds
    → no repair
```

```text
initial succeeds with malformed JSON
    → one repair call
```

```text
initial timeout
    → transport retry returns schema-invalid output
    → one repair call
```

Every provider attempt receives a new LLMCall row under the same `retry_group_id`.

### 15.4 Repair request

Repair uses:

- the same logical role;
- the same model;
- the original provider-neutral prompt;
- the invalid raw output;
- a concise machine-generated list of validation errors;
- the same output schema;
- a fixed repair instruction;
- deterministic repair parameters, normally temperature zero where supported.

Judge repair receives only the original blinded Judge context. Tutor repair receives only the original Tutor context. Repair never broadens information access.

The invalid response is never learner-visible.

### 15.5 Persistence per provider attempt

Persist:

- exact prepared request;
- raw provider response, if received;
- response payload;
- provider request ID;
- usage and latency;
- parse errors;
- Pydantic validation errors;
- semantic validation errors;
- retry reason;
- repair relationship through retry group/number;
- terminal status.

### 15.6 Terminal technical failure

Failure becomes a technical hold when:

- retry/repair allowance is exhausted;
- configuration/authentication is invalid;
- the provider repeatedly refuses;
- output remains unusable;
- an internal invariant prevents safe finalization.

No RubricEvaluation is created from invalid Judge output. No learner failure is recorded from invalid Tutor output.

---

## 16. Technical failure / recovery semantics

### 16.1 Learner failure

A learner/experimental failure requires:

- a committed AssessmentResponse;
- a valid accepted Judgment;
- a deterministic RubricEvaluation with `passed=false`.

It consumes the current pedagogy Attempt and may lead to another pedagogy or unresolved termination.

### 16.2 Technical failure

A technical failure includes:

- provider timeout or unavailability;
- rate limit after allowed retry;
- invalid structured output after repair;
- provider refusal after repair;
- internal exception;
- process interruption;
- corrupted or incompatible runtime state.

It does not:

- set `Attempt.passed=false`;
- create a RubricEvaluation;
- select another pedagogy;
- increment Attempt sequence;
- select a replacement assessment;
- advance or terminate the protocol as unresolved.

### 16.3 Tutor failure

On unrecoverable Tutor failure:

```text
Session.phase remains INTERVENTION_ACTIVE
Attempt.status = TECHNICAL_HOLD
assigned pedagogy remains unchanged
latest accepted instructional trace remains unchanged
accepted learner message remains stored
failed LLMCalls remain stored
```

Recovery retries the same logical Tutor operation and does not require the learner to submit the message again.

### 16.4 Judge failure

On unrecoverable Judge failure:

```text
Session.phase remains JUDGING
Attempt.status = TECHNICAL_HOLD
AssessmentInstance remains submitted
AssessmentResponse remains immutable
no Judgment is accepted
no RubricEvaluation exists
```

Recovery reruns Judge processing from the same AssessmentResponse and frozen assessment snapshots.

### 16.5 Simple POC recovery

Provide one idempotent backend operation:

```text
resume_pending_operation(session_id)
```

It:

1. Locks the Session.
2. Inspects the current phase and Attempt.
3. Finds the latest logical operation/retry group.
4. If an LLMCall is `RECEIVED`, resumes validation without contacting the provider.
5. If a `STARTED` call is younger than the stale threshold, returns `IN_PROGRESS`.
6. If it is stale, marks it failed with `PROCESS_INTERRUPTED`.
7. If retry allowance remains, reserves a retry of the same operation.
8. Otherwise retains `TECHNICAL_HOLD` for operator intervention.

No Celery, Redis, worker, or background queue is required.

### 16.6 Stale-call threshold

The threshold is infrastructure configuration:

```text
provider timeout + fixed recovery grace
```

It is snapshotted and logged. It does not change experimental treatment behavior.

### 16.7 Provider success before process death

If raw response reached `RECEIVED`, recovery parses the stored response.

If the process dies after the provider handled the request but before `RECEIVED` commits:

- the application cannot prove or retrieve the response generically;
- the original LLMCall becomes stale;
- a retry may produce another provider call;
- provider idempotency headers are used where supported;
- only one result can be committed into experiment state.

This is an unavoidable boundary for a provider without a retrievable job API.

---

## 17. Transaction and idempotency boundaries

No transaction remains open across a network call.

### 17.1 Attempt and pedagogy assignment

One transaction:

- lock Session;
- verify next action;
- calculate candidates;
- make the random selection and persist its selection record;
- create Attempt;
- create history snapshot if needed;
- update Session;
- append events;
- commit.

### 17.2 Tutor message and call reservation

One transaction:

- lock Session;
- validate phase/idempotency/budget;
- persist learner Message;
- compile prompt from committed state plus that message;
- prepare provider body;
- insert STARTED LLMCall;
- reserve idempotency record;
- append call-start event;
- commit.

Then the provider call occurs without a transaction.

### 17.3 Raw Tutor/Judge receipt

Short transaction:

- locate STARTED LLMCall;
- store raw response and provider metadata;
- set status `RECEIVED`;
- commit.

### 17.4 Tutor finalization

One transaction:

- lock Session;
- verify pending operation still belongs to current Attempt;
- store parsed output;
- mark accepted LLMCall succeeded;
- insert Tutor Message and trace;
- update Attempt progress;
- complete intervention and select assessment if required;
- complete idempotency record;
- append events;
- commit.

### 17.5 Budget-only intervention completion

One transaction:

- lock Session;
- verify budget exhausted;
- complete intervention;
- select and insert assessment;
- update Session/Attempt;
- append events;
- commit.

### 17.6 Assessment submission and Judge reservation

One transaction:

- lock Session;
- validate idempotency and active assessment;
- insert immutable AssessmentResponse;
- mark assessment submitted;
- set Session/Attempt to judging;
- compile blinded Judge prompt;
- prepare provider request;
- insert STARTED Judge LLMCall;
- append events;
- commit.

Provider call follows without a transaction.

### 17.7 Judge finalization and protocol advancement

One transaction:

- lock Session;
- verify current response/call and no prior Judgment;
- insert Judgment;
- run or accept the previously computed pure RubricEvaluation result;
- insert RubricEvaluation;
- mark assessment closed;
- finalize Attempt outcome;
- apply ProtocolEngine decision;
- create next Attempt/history/selection if nonterminal;
- update Session;
- complete idempotency record;
- append judgment, rubric, progression, and selection events;
- commit.

This transaction guarantees that pass/fail and protocol state cannot diverge.

### 17.8 Duplicate Tutor submission

The idempotency key is scoped to:

```text
(session_id, SUBMIT_TUTOR_MESSAGE, key)
```

- Same key and same request hash: return the existing operation/result.
- Same key and different hash: conflict.
- Different key while a Tutor call is pending: reject as `OPERATION_IN_PROGRESS`.

### 17.9 Duplicate assessment submission

The database’s one-response-per-assessment constraint is authoritative.

- Same idempotency key: return original acceptance/result.
- Different key after submission: report already submitted.
- Never create a second Judge operation for the duplicate.

### 17.10 Refresh during processing

A state read returns:

```text
current phase
current Attempt status
pending operation type
LLMCall state
whether a result is available
```

It never initiates another LLM call implicitly. An explicit idempotent resume command is required to recover a stale or held operation.

### 17.11 Incomplete calls after restart

At startup or on resume:

- `RECEIVED`: validate stored raw response.
- fresh `STARTED`: report still in progress until stale threshold.
- stale `STARTED`: mark interrupted, then retry under existing retry group.
- terminal invalid with repair remaining: reserve repair.
- terminal failure with no retry remaining: retain technical hold.

---

## 18. Runtime service interfaces

The signatures below are typed contracts, not production code.

### 18.1 SessionRuntime

Application service and transaction owner.

```text
SessionRuntime.initialize_session(
    session_id: UUID,
    command_id: UUID
) -> SessionActionResult

SessionRuntime.submit_tutor_message(
    session_id: UUID,
    learner_text: str,
    idempotency_key: str
) -> TutorOperationResult

SessionRuntime.submit_assessment_response(
    session_id: UUID,
    response_text: str,
    idempotency_key: str
) -> JudgeOperationResult

SessionRuntime.resume_pending_operation(
    session_id: UUID,
    idempotency_key: str
) -> ResumeResult

SessionRuntime.get_runtime_state(
    session_id: UUID
) -> SessionRuntimeView
```

### 18.2 ProtocolEngine

Pure domain logic.

```text
ProtocolEngine.plan_initial_attempt(
    session_state: SessionState,
    compiled_study: CompiledStudy,
    selected_pedagogy_id: PedagogyId
) -> AttemptPlan

ProtocolEngine.plan_after_evaluation(
    session_state: SessionState,
    completed_attempts: tuple[AttemptState, ...],
    evaluation: RubricEvaluationResult,
    compiled_study: CompiledStudy,
    selected_pedagogy_id: PedagogyId | null
) -> ProtocolPlan
```

`ProtocolPlan` is one of:

```text
CreateAttemptPlan
CompleteSessionPlan
UnresolvedSessionPlan
```

### 18.3 PedagogySelector

Pure.

```text
PedagogySelector.candidates(
    configured_ids: tuple[PedagogyId, ...],
    used_ids: tuple[PedagogyId, ...]
) -> tuple[PedagogyId, ...]

PedagogySelector.select(
    candidates: tuple[PedagogyId, ...],
    random_selector: RandomSelector
) -> SelectionDecision[PedagogyId]
```

### 18.4 RandomSelector

Uses a standard trustworthy random source in production and permits an injected seeded or fixed source for deterministic tests.

```text
RandomSelector.choose(
    candidate_ids: tuple[str, ...]
) -> SelectionDecision[str]

SelectionDecision:
    eligible_candidate_ids: tuple[str, ...]
    selected_id: str
    selection_method: str
    selected_at: datetime
    optional_session_seed: str | null
```

### 18.5 InterventionRuntime

Application-level preparation and state interpretation; caller owns transactions.

```text
InterventionRuntime.resolve_context(
    session: SessionState,
    attempt: AttemptState,
    compiled_study: CompiledStudy,
    history: PriorAttemptHistory | null
) -> InterventionContext

InterventionRuntime.current_progress(
    cell: CompiledInterventionCell,
    accepted_tutor_traces: tuple[TutorInstructionalTrace, ...]
) -> InterventionProgress

InterventionRuntime.check_turn_allowance(
    context: InterventionContext,
    progress: InterventionProgress,
    now: datetime
) -> TurnAllowance

InterventionRuntime.apply_tutor_output(
    context: InterventionContext,
    progress: InterventionProgress,
    output: TutorTurnOutput,
    now: datetime
) -> InterventionUpdate
```

The progress/allowance functions are pure.

### 18.6 TutorRuntime

Application LLM operation.

```text
TutorRuntime.prepare_opening(
    context: InterventionContext
) -> PreparedLogicalLLMOperation

TutorRuntime.prepare_reply(
    context: InterventionContext,
    dialogue: tuple[Message, ...],
    latest_learner_message: Message
) -> PreparedLogicalLLMOperation

TutorRuntime.validate_output(
    operation: PreparedLogicalLLMOperation,
    raw_response: RawLLMResponse
) -> Validated[TutorTurnOutput] | ValidationFailure
```

### 18.7 PromptCompiler

Pure.

```text
PromptCompiler.compile_tutor(
    input: TutorPromptInput
) -> PromptEnvelope[TutorTurnOutput]

PromptCompiler.compile_judge(
    input: JudgePromptInput
) -> PromptEnvelope[JudgeObservation]
```

### 18.8 HistoryBuilder

Pure.

```text
HistoryBuilder.build(
    transition_id: TransitionId,
    target_attempt_id: UUID,
    prior_attempt_records: tuple[CompletedAttemptRecord, ...]
) -> PriorAttemptHistory
```

### 18.9 AssessmentSelector

Pure and pedagogy-blind.

```text
AssessmentSelector.candidates(
    active_form_ids: tuple[AssessmentFormId, ...],
    seen_form_ids: tuple[AssessmentFormId, ...]
) -> tuple[AssessmentFormId, ...]

AssessmentSelector.select(
    input: AssessmentSelectionInput,
    random_selector: RandomSelector
) -> SelectionDecision[AssessmentFormId]
```

### 18.10 AssessmentRuntime

```text
AssessmentRuntime.plan_activation(
    session_id: UUID,
    transition_id: TransitionId,
    compiled_family: CompiledAssessmentFamily,
    seen_form_ids: tuple[AssessmentFormId, ...],
    selection: SelectionDecision[AssessmentFormId]
) -> AssessmentActivationPlan

AssessmentRuntime.validate_submission(
    assessment: AssessmentState,
    response_text: str
) -> ValidatedAssessmentSubmission
```

Planning/validation are pure once the selection decision is supplied; SessionRuntime persists them.

### 18.11 JudgeRuntime

```text
JudgeRuntime.build_blinded_input(
    response: AssessmentResponseRecord,
    assessment: AssessmentInstanceRecord,
    compiled_study: CompiledStudy
) -> JudgePromptInput

JudgeRuntime.prepare(
    input: JudgePromptInput
) -> PreparedLogicalLLMOperation

JudgeRuntime.validate_output(
    input: JudgePromptInput,
    raw_response: RawLLMResponse
) -> Validated[JudgeObservation] | ValidationFailure
```

### 18.12 RubricEvaluator

Pure.

```text
RubricEvaluator.evaluate(
    formal_state_before_id: SoloStateId,
    transition: CompiledTransition,
    assessment_form_id: AssessmentFormId,
    rubric: CompiledJudgeRubric,
    observation: JudgeObservation
) -> RubricEvaluationResult
```

### 18.13 StructuredOutputProcessor

Pure parsing/validation plus repair planning.

```text
StructuredOutputProcessor.process_tutor(
    raw: RawLLMResponse,
    validation_context: TutorValidationContext
) -> OutputProcessingResult[TutorTurnOutput]

StructuredOutputProcessor.process_judge(
    raw: RawLLMResponse,
    validation_context: JudgeValidationContext
) -> OutputProcessingResult[JudgeObservation]

StructuredOutputProcessor.plan_repair(
    original_operation: PreparedLogicalLLMOperation,
    failure: ValidationFailure,
    retry_state: RetryState
) -> RepairPlan | TechnicalFailure
```

### 18.14 LLMClient

Infrastructure-only.

```text
LLMClient.prepare(
    request: LLMRequest
) -> PreparedLLMRequest

async LLMClient.send(
    prepared: PreparedLLMRequest
) -> RawLLMResponse
```

No database transaction is owned by `LLMClient`. SessionRuntime/application operation handlers own all transaction boundaries.

---

## 19. Stage-2 test design

### 19.1 Protocol

- Session initializes at P/C1.
- Initial Attempt receives one configured pedagogy.
- Used pedagogy is excluded from later same-transition candidates.
- Success advances exactly one transition.
- Above-target observation advances only to the current target.
- Failure creates another Attempt at the same transition.
- Second Attempt receives a different pedagogy.
- Three valid failures produce unresolved termination.
- No fourth Attempt or renewed cycle is created.
- C4 success produces `COMPLETED_EA`.
- Tutor disposition cannot mutate formal state.
- Judge output cannot directly route protocol.

### 19.2 Randomization

- The production selector returns only an eligible candidate.
- An injected fixed or seeded selector provides deterministic test behavior.
- The audit record persists eligible candidates, excluded/used candidates, selected ID, selection method, and timestamp.
- The optional Session seed is recorded when deterministic test mode uses one.
- Pedagogy candidates exclude committed Attempts.
- Assessment candidates exclude all existing AssessmentInstances.
- No pedagogy field exists in AssessmentSelectionInput.
- Selection fails clearly on an empty candidate pool.

### 19.3 Intervention and Tutor

- Correct cell, family, and Knowledge Slice are resolved.
- Attempt pedagogy remains unchanged across turns.
- Opening message uses the assigned cell's authored procedure guidance.
- Opening counts against the turn budget.
- Stage IDs outside the cell are rejected.
- Nonsequential, repeated, or omitted stage reporting is accepted unless the study explicitly requires strict sequencing.
- Reserved assessment material tags are rejected.
- Prior history appears only on later same-transition Attempts.
- Future knowledge and future assessments are absent.
- Tutor cannot return pass/fail or next-pedagogy fields.
- A valid Tutor `COMPLETE` disposition completes the intervention without an invented all-stages-complete requirement.
- Turn exhaustion overrides `CONTINUE`.
- Elapsed exhaustion prevents another call.
- Technical-hold time is excluded from elapsed accounting.
- Tutor cannot continue after assessment activation.

### 19.4 Prompt compilation

- Same typed input produces byte-identical canonical messages and prompt hash.
- Layer order and section headings are stable.
- Knowledge content precedes cell/runtime context.
- Current dialogue preserves message order.
- Prior raw transcripts are absent.
- Provider-specific formatting does not alter CompiledStudy.
- Exact canonical prompt and provider body are persisted.
- Learner content is placed only in data/message sections.

### 19.5 History

- Attempt 2 history contains Attempt 1 only.
- Attempt 3 history contains Attempts 1 and 2 in order.
- Exposure derives from accepted Tutor traces.
- Judgment and rubric fields are correctly represented.
- Tutor and Judge evidence provenance remains distinguishable.
- Assessment prompt, form ID, hidden context, response excerpt, future pedagogy, and future assessment are absent.
- No LLM call is needed to build history.
- First Attempt of a new transition receives no same-transition history.

### 19.6 Assessment

- Intervention completion and assessment activation are atomic.
- Selected form belongs to the correct transition.
- Previously instantiated forms are excluded.
- Assessment prompt and hidden context are snapshotted.
- Exactly one response may be submitted.
- Duplicate same-key submission returns the existing operation.
- Different-key second submission is rejected.
- Tutor operations fail after assessment begins.
- Judge reservation occurs only after response persistence.

### 19.7 Judge blindness

- Judge query does not load Messages or LearnerHistorySnapshot.
- `JudgePromptInput` cannot represent pedagogy.
- Attempt ordinal is absent from provider messages.
- Audit context is not serialized to the provider.
- Snapshot prompt and hidden context are included.
- Learner response is included exactly.
- Test fixtures with treatment data cannot leak through serialization.

### 19.8 Judge contract

- Valid complete JudgeObservation parses.
- Missing rubric criterion is rejected.
- Unknown KC/relation/misconception ID is rejected.
- Duplicate evidence ID is rejected.
- Citation not found in learner response is rejected.
- Gradable/not-gradable consistency is enforced.
- Correctness and observed structure remain independent.
- Protocol-control fields are rejected.
- Confidence has no effect on rubric result.

### 19.9 Rubric evaluation

For each C1–C4 rubric:

- Required evidence pass.
- Missing evidence fails.
- Partial evidence does not satisfy required evidence.
- Required any-of group behavior.
- Minimum-count behavior.
- Item-specific requirements.
- Correctness gate.
- Detected blocking misconception.
- Possible misconception does not automatically block.
- Observed state below target fails.
- Observed state at target passes when other rules pass.
- Observed state above target passes without state skipping.
- Non-gradable observation fails deterministically.
- Identical inputs always produce identical result and reasons.

### 19.10 LLM and repair

Using fake providers:

- Valid provider-native structured response.
- JSON fallback response.
- Malformed JSON.
- Schema-invalid JSON.
- Pydantic-valid but semantically invalid result.
- Empty response.
- Refusal.
- Timeout.
- Rate limit.
- Provider 5xx.
- Authentication error.
- One transport retry only.
- One structured repair only.
- Total call cap of three.
- Every call attempt persists exact request and available raw response.
- Invalid Tutor output is never learner-visible.
- Invalid Judge output never creates a Judgment or RubricEvaluation.

### 19.11 Technical failure

- Tutor failure retains the same Attempt and pedagogy.
- Judge failure retains the assessment response.
- Technical failure does not set `passed=false`.
- Technical failure does not select another pedagogy.
- Retry continues under the same logical retry group.
- Successful recovery clears technical hold.
- Exhausted recovery remains held without protocol advancement.

### 19.12 Transactions and resume

- No database transaction remains open during fake provider delay.
- Concurrent Tutor submissions create one pending operation.
- Concurrent assessment submissions create one response.
- Refresh during STARTED returns in-progress state.
- RECEIVED output resumes validation without a provider call.
- Stale STARTED call is marked interrupted.
- Retry after stale call cannot commit a duplicate Tutor message or Judgment.
- Process interruption after raw receipt preserves response.
- Process interruption before domain finalization can resume deterministically.
- Judgment, RubricEvaluation, and protocol advancement commit atomically.
- Event append and current-state mutation roll back together.

The main suite uses fake providers. Real-provider tests are optional, explicitly marked integration smoke tests, and excluded from normal CI.

---

## 20. Implementation decisions made

| Decision | Rationale | Alternatives considered | Consequence |
|---|---|---|---|
| One SessionRuntime orchestrates all participant commands | Centralizes phase, transaction, and idempotency enforcement | Routes calling components directly; autonomous workflow engine | Runtime actions follow one authoritative path |
| ProtocolEngine and candidate calculations are pure | Makes protocol behavior easy to test | Stateful protocol object with DB access | Random choice is supplied as an explicit selection decision and persistence remains in SessionRuntime |
| Standard trustworthy random selector with an injectable test source | Keeps assignment simple while supporting controlled tests | Custom HMAC/rejection-sampling protocol | Persist the eligible/excluded candidates, selected ID, method, timestamp, and optional test seed |
| Pedagogy counts as used when Attempt is committed | Prevents technical retries from accidentally reassigning treatment | Count only completed interventions | Abandoned technical Attempts still reserve their pedagogy until recovered |
| Create the next Attempt atomically with the prior outcome | Prevents ambiguous gaps and duplicate selection | Leave Session transition-ready until a later request | Next treatment is assigned immediately, though its Tutor opening may occur later |
| Generate a Tutor opening turn for each Attempt | Worked and contrast interventions may need Tutor-initiated material | Require learner to speak first | Opening counts as instructional exposure and a Tutor turn |
| Intervention stages are authored guidance and progress trace unless explicitly constrained | Avoids inventing a rigid secondary state machine | Require every stage to complete in strict order | Referenced stages must belong to the assigned cell, while valid teaching is not rejected for bookkeeping alone |
| Tutor reports `CONTINUE` or `COMPLETE`; harness owns state transition | Preserves budget and protocol authority without treating stage bookkeeping as approval | Require an all-stages-complete recommendation | Valid `COMPLETE` ends intervention and budget exhaustion can still override `CONTINUE` |
| Provider-neutral ordered message envelope | Preserves prompt semantics across providers | One giant prompt string; provider-native prompt objects everywhere | Adapter must serialize messages consistently |
| Persist both canonical prompt and exact provider body | Supports semantic and wire-level reconstruction | Store one representation only | Modest duplicate storage |
| Provider-native JSON Schema preferred, local validation mandatory | Reduces malformed output without trusting provider enforcement | Prompt-only JSON; provider validation only | Provider capability must be configured |
| One transport retry plus one repair, total cap three | Balances recoverability with bounded latency/cost | No retries; unlimited retries | Some operations enter technical hold after bounded failure |
| Repair uses the same model and original context | Avoids changing model treatment during technical correction | Separate repair model | Repair calls may still vary, but remain fully logged |
| Add nonterminal LLMCall `RECEIVED` status | Preserves raw responses before domain finalization | Direct STARTED-to-terminal transition | Minor Stage-1 lifecycle refinement and possible enum migration |
| Deterministic history aggregation without an LLM | Prevents invented summaries and new leakage paths | Summarization model; paste raw transcripts | History is constrained to available structured trace/evidence |
| Omit prior assessment form and raw response from Tutor history | Minimizes assessment leakage | Include full previous assessment | Tutor receives evidence summaries only |
| Judge input uses a dedicated narrow DTO and query path | Enforces blindness structurally | Load full Attempt and ask compiler to omit fields | Some internal query duplication is intentional |
| Four-value correctness vocabulary | Separates minor error, material error, and non-gradability | Boolean correct/incorrect; unrestricted text | Study authors must align `materially_sound` with these values |
| Only `DETECTED` misconceptions block deterministically | Avoids failing on uncertain model suspicions | Treat `POSSIBLE` as blocking | Possible misconceptions remain available for audit/history |
| Confidence is logged but not thresholded | Matches the POC decision to avoid confidence policy | Confidence-based routing | Low-confidence valid evidence still follows authored rubric |
| Assessment activation is atomic with intervention completion | Prevents Tutor continuation or duplicate form selection in an intermediate state | Separate transactions | Completion transaction performs random selection and persists its audit record |
| Judge finalization, rubric evaluation, and progression are atomic | Prevents evidence/outcome/state divergence | Separate commits | Finalization transaction is broader but contains no network call |
| Technical failure holds the same Attempt | Prevents infrastructure errors consuming pedagogy | Mark failure and create next Attempt | Recovery must explicitly resume the held operation |
| Synchronous participant commands with asynchronous provider I/O and explicit resume, no worker queue | Keeps the local POC simple without blocking one Uvicorn event loop | Celery/Redis; durable job system | Long calls depend on HTTP/process lifetime, mitigated by persisted reservations and resume |

---

## 21. Ambiguities / questions requiring approval

1. **Exact intervention budgets**

   The study documents do not choose final turn/time values. Recommendation: make `max_tutor_turns` mandatory in operational study configuration. Make elapsed time optional unless the research design deliberately requires it.

2. **Opening-turn budget accounting**

   This design counts the Tutor’s generated opening as a Tutor turn because it is instructional exposure. Approval is needed because excluding it would change treatment dose.

3. **Elapsed-time meaning**

   If an elapsed budget is used, clarify whether learner reading/typing time counts. Recommendation: use wall-clock elapsed time minus recorded technical-hold intervals, with a generous limit; rely primarily on Tutor-turn count for treatment consistency.

4. **Not-gradable learner responses**

   Recommendation: a valid Judge classification of a learner response as not gradable fails the rubric and consumes the Attempt, because every current rubric requires gradability. Provider refusal or Judge-output failure remains technical instead.

5. **Exact Tutor/Judge models and parameters**

   Model identities, temperatures, token limits, and timeouts remain unset. Recommendation: pin them per logical role in runtime configuration, snapshot effective non-secret settings on the Session, and log them on every LLMCall.

6. **Repair temperature**

   Recommendation: use temperature zero for technical repair when supported, even if the original Tutor call uses a higher value. This affects only schema recovery and is always logged.

7. **Provider idempotency support**

   OpenAI-compatible providers differ in support for idempotency keys and request retrieval. The generic runtime cannot guarantee provider-side deduplication. Recommendation: send a stable key when supported and rely on database idempotency for experiment state.

8. **Evidence citation strictness**

   Recommendation: require Judge excerpts to be exact substrings of the normalized learner response. If multilingual or formatting behavior makes this too brittle, replace excerpts with character ranges rather than allowing unverifiable paraphrases.

9. **Assessment submission emptiness**

    Recommendation: reject a completely empty submission at request validation and keep the assessment active. Whitespace/gibberish that is technically nonempty should be judged and may validly become not gradable.

10. **Automatic versus operator recovery**

    Recommendation: allow one automatic bounded retry/repair within the original command. After technical hold, require an explicit idempotent resume action rather than repeatedly calling the provider during ordinary state reads.

11. **Cross-transition history**

    This design supplies prior-attempt history only within the current transition, matching the source specification. If future studies require cross-transition personalization, that is a study/runtime contract expansion and should not be inferred for the POC.
