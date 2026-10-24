# AI Harness Study-Pack Specification

**Status:** Working design specification for the proof-of-concept harness  
**Primary POC domain:** Python Programming  
**Primary POC topic:** Recursive Fibonacci with Memoization  
**Purpose:** Define the conceptual contracts, ownership boundaries, dependencies, runtime behavior, and implementation constraints of the AI-mediated learning harness before concrete pack authoring or backend implementation.

---

# 1. Purpose of this specification

This document defines the **study-definition architecture** for a local, containerized AI learning/experiment harness.

It is intentionally **implementation-independent** at the content-contract level. It does not prescribe exact Pydantic models, SQL tables, YAML schemas, API routes, or prompt strings. Those are implementation details that may evolve.

Instead, this document specifies:

- what the harness is responsible for;
- what a study definition is responsible for;
- the four core content/research packs;
- the role of the protocol configuration;
- how the packs depend on one another;
- what information may and may not cross component boundaries;
- how Tutor and Judge prompts are assembled;
- how prior learner history is used;
- how assessments remain independent from pedagogy;
- how the Judge remains blind to intervention history;
- how progression through SOLO is controlled;
- what must be logged for reproducibility;
- and what is explicitly **out of scope** for the current POC.

The intended result is a stable conceptual contract that can sit above both:

1. the concrete study content, and
2. the backend implementation.

The harness should be reusable across future domains/topics, but the current proof of concept deliberately uses only one domain and one topic.

---

# 2. Normative language

The following terms are used deliberately:

- **MUST** — required for a conforming implementation or study definition.
- **MUST NOT** — explicitly prohibited.
- **SHOULD** — strongly recommended; deviations require a reason.
- **SHOULD NOT** — generally prohibited unless there is a documented reason.
- **MAY** — optional and implementation-dependent.

These terms apply to design boundaries, not to exact serialization or code structure.

---

# 3. Core product definition

The system is best understood as:

> **A containerized AI-mediated learning experiment runtime that executes a versioned study definition against a persistent local learner/session state.**

The harness is not itself “the Fibonacci tutor.”

The harness owns the mechanics of execution:

- session lifecycle;
- state progression;
- treatment selection;
- prompt compilation;
- Tutor LLM calls;
- assessment selection;
- Judge LLM calls;
- deterministic progression logic;
- persistence;
- logging;
- and reproducibility.

The study definition owns the meaning of the experiment:

- what is being learned;
- what the learner states mean;
- what each transition means;
- what each pedagogy is;
- how each pedagogy acts at each transition;
- how a transition is assessed;
- and how learner evidence is judged.

The current POC instantiates that generic machinery using:

- **Domain:** Python Programming
- **Topic:** Recursive Fibonacci with Memoization
- **SOLO states:** Prestructural, Unistructural, Multistructural, Relational, Extended Abstract
- **Transitions:** C1 P→U, C2 U→M, C3 M→R, C4 R→EA
- **Pedagogies:** Worked-Example Instruction, Guided Questioning, Contrasting-Case Instruction
- **Maximum pedagogy attempts per transition:** 3
- **Renewed pedagogy cycles:** disabled for the POC
- **Assessment forms per transition:** 4
- **Storage:** local PostgreSQL
- **LLM roles:** Tutor and Judge

---

# 4. POC scope and research boundary

The POC intentionally reduces the scientific design to **one domain and one topic**.

That means it is primarily validating whether the **apparatus works**:

- can a study definition be loaded and validated?
- can the harness execute transition-specific pedagogies?
- can it preserve treatment identity?
- can it administer fresh independent assessments?
- can a Judge classify responses against explicit structural criteria?
- can prior learner history inform later interventions without contaminating the Judge?
- can all relevant events and raw evidence be stored and replayed?

The POC is **not** intended to resolve the full causal-comparison problem that motivated the later three-topic experimental design.

Because the same learner receives multiple interventions on the same topic, later attempts are path-dependent: the learner has already been exposed to earlier instruction. The harness MUST therefore record this history and use it responsibly, but POC data MUST NOT be represented as equivalent to the final matched-topic causal experiment.

---

# 5. High-level architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                         Browser UI                            │
│                                                               │
│  learner interaction                                         │
│  tutor conversation                                          │
│  assessment submission                                       │
│  simple session/result state                                 │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                         AI HARNESS                            │
│                                                               │
│  Pack Loader / Validator                                      │
│  Protocol Engine                                              │
│  Prompt Compiler                                              │
│  Intervention Runtime                                         │
│  Assessment Runtime                                           │
│  Judge Runtime                                                │
│  Learner History Builder                                      │
│  Persistence / Logging                                        │
└───────────────┬───────────────────────────────┬───────────────┘
                │                               │
                ▼                               ▼
        ┌───────────────┐               ┌───────────────┐
        │  PostgreSQL   │               │ LLM Provider  │
        │    local      │               │ Tutor / Judge │
        └───────────────┘               └───────────────┘
                ▲
                │
                │ study definition loaded at startup
                │
┌───────────────┴───────────────────────────────────────────────┐
│                       STUDY DEFINITION                        │
│                                                               │
│  Knowledge Pack                                               │
│  Intervention Pack                                            │
│  Assessment Pack                                              │
│  Judge/Rubric Pack                                            │
│  Protocol Configuration                                       │
└───────────────────────────────────────────────────────────────┘
```

---

# 6. Study-definition components

The study definition contains four substantive content/research packs plus one lightweight protocol configuration.

```text
STUDY DEFINITION
│
├── 1. Knowledge Pack
│      "What must be understood?"
│
├── 2. Intervention Pack
│      "How does this pedagogy try to produce that understanding?"
│
├── 3. Assessment Pack
│      "What fresh independent task exposes whether it happened?"
│
├── 4. Judge / Rubric Pack
│      "What observable evidence means the transition occurred?"
│
└── 5. Protocol Configuration
       "What does the harness do next?"
```

The first four are intellectual/content components of the study.

The protocol is wiring/configuration for the runtime. It should remain much smaller.

---

# 7. Global dependency principle

The Knowledge Pack is the semantic source of truth.

Other packs reference concepts defined there; they do not independently redefine them.

```text
                         KNOWLEDGE PACK
                         source of truth
                               │
               ┌───────────────┼──────────────────┐
               │               │                  │
               ▼               ▼                  ▼
        INTERVENTION       ASSESSMENT           JUDGE
            PACK               PACK              PACK
               │               │                  │
               │               └────────┐         │
               │                        │         │
               ▼                        ▼         ▼
          Tutor runtime             learner    Judge runtime

                         PROTOCOL CONFIG
                               │
                               ▼
                        runtime sequencing
```

The fundamental traceability chain is:

```text
Domain / Topic Knowledge
        ↓
SOLO State / Transition Meaning
        ↓
Pedagogy-Specific Intervention
        ↓
Independent Assessment
        ↓
Observable Evidence
        ↓
Judgment
        ↓
Protocol Outcome
```

---

# 8. Knowledge Pack

## 8.1 Purpose

The Knowledge Pack defines the learning world.

It answers:

> **What exactly is being learned, how is that knowledge structured, and what does P→U→M→R→EA mean for this topic?**

It is the semantic authority for every downstream pack.

---

## 8.2 The Knowledge Pack MUST contain

### A. Topic identity

The pack identifies:

- domain;
- topic;
- topic version;
- short topic description.

For the current POC:

```text
Domain:
Python Programming

Topic:
Recursive Fibonacci with Memoization
```

---

### B. Prerequisite assumptions

The Knowledge Pack MUST state what the learner is expected to know before entering the experimental frontier.

For the POC, this may include:

- basic Python function syntax;
- parameters;
- return values;
- conditionals;
- ordinary integer arithmetic.

Prerequisites are not themselves the experimental target.

A learner failing prerequisites should not be misclassified as structurally Prestructural within the target topic when the actual problem is inability to read Python syntax.

---

### C. Conceptual frontier

The pack MUST define the bounded learning frontier.

For the POC, the in-scope frontier includes concepts such as:

- Fibonacci base cases;
- Fibonacci recurrence;
- recursive function execution;
- recursive dependencies;
- repeated subproblems;
- repeated computation;
- storing solved results;
- cache lookup;
- cache reuse;
- memoized recursive execution;
- why memoization avoids redundant recomputation;
- reasoning about equivalent memoization structures.

The frontier also MUST state what is outside the current topic.

For the POC, excluded material includes:

- tabulation;
- bottom-up dynamic programming;
- space-optimized Fibonacci;
- knapsack;
- longest common subsequence;
- a general dynamic-programming curriculum;
- specialist shortcuts such as built-in caching decorators unless explicitly introduced later.

This boundary is instructional as well as conceptual.

An intervention MUST NOT introduce excluded content merely because the LLM believes it is pedagogically useful.

---

### D. Knowledge components

The Knowledge Pack MUST define stable knowledge-component identities.

A knowledge component is a meaningful concept or proposition that may be:

- assumed;
- targeted;
- demonstrated;
- partially demonstrated;
- absent;
- or contradicted by a misconception.

For the POC, representative KCs include:

- Fibonacci base cases;
- Fibonacci recurrence;
- recursive representation;
- recursive dependency structure;
- repeated subproblems;
- repeated computation;
- cache/storage;
- cache reuse;
- memoized recursion mechanism;
- efficiency mechanism;
- abstraction across equivalent memoization implementations.

Exact identifiers are an implementation detail, but stable referential identities are required.

Other packs MUST reference these concepts rather than duplicating their definitions.

---

### E. Knowledge relations

The Knowledge Pack MUST represent important relationships between knowledge components.

This is essential because SOLO is not merely a count of correct facts.

Example conceptual structure:

```text
Fibonacci base cases ─────┐
                          ├──► recursive implementation
Fibonacci recurrence ─────┘             │
                                        ▼
                              dependency structure
                                        │
                                        ▼
                              repeated subproblems
                                        │
                                        ▼
                              repeated computation
                                        │
                                        ▼
                               cache + reuse
                                        │
                                        ▼
                               memoized recursion
                                        │
                                        ▼
                           reduced redundant computation
                                        │
                                        ▼
                                abstraction / transfer
```

A learner may possess several pieces without integrating them.

That difference is central to the Multistructural → Relational transition.

---

### F. Misconceptions and partial models

The Knowledge Pack MUST define meaningful incorrect or partial models when known.

Examples include:

- believing Fibonacci recursion requires only one prior value;
- believing base cases are what make the recursive algorithm efficient;
- believing repeated `fib(k)` calls represent different subproblems;
- believing memoization changes the Fibonacci recurrence;
- believing memoization stores calls rather than computed results;
- believing the presence of a dictionary alone means the function is memoized.

Misconceptions MUST be defined once in the Knowledge Pack and referenced elsewhere.

The Intervention Pack may target them.

The Assessment Pack may expose them.

The Judge Pack may define observable indicators of them.

---

### G. SOLO state definitions for this topic

The Knowledge Pack MUST define all five SOLO states specifically for the topic.

#### Prestructural

No usable conceptual model of the target frontier is demonstrated.

Relevant ideas may be missing, irrelevant, or materially misconceived.

#### Unistructural

One central relevant structure is usable.

For the Fibonacci POC, this is expected to center on the recurrence and its recursive representation.

#### Multistructural

Multiple relevant components are present, but they remain largely separate.

The learner may recognize:

- recursion;
- repeated calls;
- repeated computation;
- storage;
- reuse;

without yet integrating them into one causal memoization mechanism.

#### Relational

The learner integrates the components into a coherent model.

For example:

```text
recursive dependency
    ↓
same subproblem appears repeatedly
    ↓
without storage it is recomputed
    ↓
solved result is cached
    ↓
later calls reuse it
    ↓
same recurrence, less redundant computation
```

#### Extended Abstract

The learner reasons from the mechanism rather than merely recalling the canonical implementation.

Within the bounded Fibonacci topic, this can include:

- evaluating unfamiliar memoized implementations;
- predicting cache behavior;
- identifying whether a novel implementation genuinely memoizes;
- deriving an equivalent caching arrangement;
- explaining what remains invariant across alternative implementations.

EA MUST NOT be defined merely as “a harder Fibonacci question.”

---

### H. Transition definitions

The pack MUST define the four transitions:

```text
C1: P  → U
C2: U  → M
C3: M  → R
C4: R  → EA
```

Each transition MUST define:

- starting structural state;
- target structural state;
- assumed established knowledge;
- target knowledge;
- target relations;
- relevant misconceptions;
- the structural change being attempted;
- and future knowledge that is not yet required.

This transition definition is what downstream components consume.

---

## 8.3 Knowledge Slice

At runtime, the harness SHOULD resolve each transition into a canonical **Knowledge Slice**.

A Knowledge Slice is not a separate authored pack. It is a runtime view of the Knowledge Pack for one transition.

Conceptually:

```text
C3 KNOWLEDGE SLICE
────────────────────────────────────────

Topic:
Recursive Fibonacci with Memoization

Starting state:
Multistructural

Target state:
Relational

Assumed knowledge:
concepts already expected to be available

Target knowledge:
concepts that must now become part of the learner's model

Target relations:
relationships that must become integrated

Relevant misconceptions:
known incorrect structures relevant to this transition

Not-yet-required knowledge:
future concepts that should not be forced into the intervention

Structural change:
multiple relevant pieces
        ↓
integrated causal memoization model
```

The Intervention Pack, Assessment Pack and Judge Pack all consume this slice differently.

---

## 8.4 Knowledge Pack ownership boundary

The Knowledge Pack OWNS:

- topic identity;
- prerequisites;
- in-scope frontier;
- excluded content;
- knowledge components;
- knowledge relations;
- misconceptions;
- topic-specific meaning of P/U/M/R/EA;
- topic-specific meaning of C1/C2/C3/C4.

The Knowledge Pack MUST NOT own:

- how Worked Example teaches;
- how Guided Questioning teaches;
- how Contrasting Cases teaches;
- learner-facing assessment questions;
- judging procedure;
- pedagogy selection;
- randomization;
- attempt sequencing;
- LLM provider configuration.

---

# 9. Intervention Pack

## 9.1 Purpose

The Intervention Pack defines:

> **How a specific pedagogy attempts to produce a specific transition in this specific topic.**

It is strongly dependent on the Knowledge Pack.

It MUST NOT invent its own independent interpretation of the transition target.

---

## 9.2 Two-level structure

The Intervention Pack has two conceptually different layers:

```text
PEDAGOGY FAMILY DEFINITIONS
        +
TRANSITION × PEDAGOGY CELLS
```

For three pedagogies and four transitions:

```text
                     Worked       Guided       Contrast
C1 P→U                 X             X             X
C2 U→M                 X             X             X
C3 M→R                 X             X             X
C4 R→EA                X             X             X
```

There are therefore **12 intervention cells**.

---

## 9.3 Pedagogy family definitions

The family definition specifies the invariant treatment mechanism.

### Worked-Example Instruction

Core mechanism:

> learner studies already-organized reasoning instantiated in a solved case.

The family may permit:

- modeled reasoning;
- solved examples;
- explanation of why steps work;
- bounded rationale prompts.

It must not silently become Guided Questioning or Contrasting Cases.

---

### Guided Questioning

Core mechanism:

> learner constructs the missing structure through sequenced elicitation.

The family may permit:

- targeted questions;
- requests for prediction;
- requests for justification;
- narrowing questions;
- questions that expose inconsistency;
- adaptation to the learner's preceding response.

It MUST NOT:

- simply present the complete target explanation;
- convert into a worked example when the learner struggles;
- switch to contrasting-case teaching.

---

### Contrasting-Case Instruction

Core mechanism:

> learner infers the target relationship by comparing carefully controlled cases that differ on a structurally diagnostic dimension.

The family may permit:

- presentation of aligned cases;
- requests for similarity/difference;
- prompts to infer the underlying rule.

Contrasts SHOULD vary the diagnostic feature while holding irrelevant features as constant as feasible.

---

## 9.4 Cell-specific intervention definition

Each of the 12 cells is the actual domain/topic/transition-specific intervention specification.

For example:

```text
Topic:
Recursive Fibonacci with Memoization

Transition:
C3 Multistructural → Relational

Pedagogy:
Guided Questioning
```

The cell MUST reference the Knowledge Pack for:

- assumed knowledge;
- target KCs;
- target relations;
- relevant misconceptions.

The cell MUST NOT redefine those concepts independently.

---

## 9.5 Each intervention cell SHOULD contain

### Identity

- transition reference;
- pedagogy-family reference.

### Knowledge references

- assumed knowledge;
- target knowledge;
- target relations;
- relevant misconceptions;
- future/out-of-scope knowledge.

### Instructional intent

- what conceptual gap is being addressed;
- what structural change is desired;
- what the learner is expected to construct or understand.

### Missing structure

The cell SHOULD explicitly describe what is missing between the assumed state and the target state.

This is especially useful for the LLM.

### Material requirements

The cell MAY define:

- appropriate representations;
- code fragments;
- call trees;
- case structures;
- example characteristics;
- constraints on numerical instances;
- content that must not be used.

### Delivery procedure

The cell SHOULD define a sequence of **instructional functions**, not necessarily a fixed learner-facing script.

For example, C3 Guided Questioning might require functions such as:

1. establish recognition of repeated subproblems;
2. establish that naive recursion recomputes them;
3. establish that results can be stored;
4. establish what happens on a repeated request;
5. integrate storage and reuse into memoization;
6. establish that the recurrence itself has not changed.

The LLM retains freedom over surface wording.

### Cell-specific permissions and prohibitions

The cell may be stricter than the family definition.

It MUST NOT weaken the family definition.

### Illustrative moves

The cell MAY include example questions or examples, but these MUST be explicitly marked as illustrative rather than mandatory scripts unless the study intentionally requires fixed wording.

### Completion condition

The cell MUST state when the **intervention** ends.

Intervention completion MUST NOT be interpreted as transition success.

Only the independent assessment and judging process can establish transition success.

### Instructional budget

The cell MAY define a turn/content/time budget.

The harness MUST enforce hard limits even if the LLM requests to continue.

---

## 9.6 Precedence rules

The following precedence MUST hold.

### Content truth

```text
Knowledge Pack > Intervention Cell
```

The cell cannot contradict the Knowledge Pack.

### Pedagogical mechanism

```text
Pedagogy Family > Intervention Cell
```

A Guided Questioning cell cannot authorize direct worked-solution behavior that violates the family.

### Transition-specific instructional path

```text
Intervention Cell > Generic Pedagogy Family
```

The family says how teaching works in general.

The cell says exactly what this pedagogy must accomplish for this transition.

### Surface realization

```text
Runtime LLM freedom
```

The LLM may adapt wording and local examples within the supplied boundaries.

---

# 10. Learner history and later interventions

## 10.1 Why history is required

A later intervention on the same transition does not encounter an untouched learner.

The learner may already have:

- seen particular material;
- discussed particular concepts;
- partially learned some KCs;
- formed or corrected misconceptions;
- failed an independent assessment;
- received one or two other pedagogies.

Therefore, each later Tutor intervention MUST receive a structured summary of prior exposure relevant to the current transition.

---

## 10.2 Three history layers

### Current-attempt conversation

The Tutor needs the full interaction within the current intervention so it can conduct a coherent multi-turn exchange.

### Prior-attempt structured history

Later interventions SHOULD receive a compact structured summary including:

- pedagogy previously received;
- concepts exposed;
- relations exposed;
- instructional artifacts already used;
- learner evidence demonstrated;
- learner evidence partial;
- learner evidence absent;
- misconceptions observed;
- prior transition-assessment outcome.

### Raw history

All full transcripts, raw responses and raw model outputs MUST remain stored.

They do not need to be pasted wholesale into every later prompt.

---

## 10.3 History boundary

History MAY personalize the assigned pedagogy.

History MUST NOT change the assigned pedagogy.

For example:

```text
Prior history says:
learner already understands repeated calls

        ↓

New Worked-Example intervention may:
focus its example on cache reuse

        ↓

But it MUST remain:
Worked-Example Instruction
```

The Tutor cannot switch to Guided Questioning because it thinks that would work better.

---

## 10.4 Assessment leakage boundary

Later Tutor prompts MUST NOT receive:

- exact previous assessment items unless required for audit outside the Tutor;
- answer keys;
- future assessment items;
- hidden Judge scoring context;
- Judge chain-of-thought or hidden reasoning.

The Tutor may receive summarized learner evidence derived from previous judgments.

---

# 11. Assessment Pack

## 11.1 Purpose

The Assessment Pack defines:

> **How the system independently tests whether a target SOLO transition has occurred.**

Assessment is transition-dependent but pedagogy-independent.

---

## 11.2 Central independence rule

At runtime, assessment selection MUST NOT depend on which pedagogy was just used.

This is a core experimental boundary.

Bad pattern:

```text
Worked Example
    ↓
worked-example-shaped test

Guided Questioning
    ↓
questioning-shaped test

Contrasting Cases
    ↓
comparison-shaped test
```

Desired pattern:

```text
Worked ───────┐
Guided ───────┼──► SAME TRANSITION TARGET ───► fresh equivalent assessment
Contrast ─────┘
```

The question is:

> Did the learner independently demonstrate the target structure?

not:

> Did the learner perform well on a test that resembles the pedagogy they just received?

---

## 11.3 Assessment family

The pack SHOULD define one assessment family per transition:

```text
C1 Assessment Family
C2 Assessment Family
C3 Assessment Family
C4 Assessment Family
```

Each family defines:

- transition reference;
- target knowledge;
- target relations;
- what must be observable;
- equivalence constraints;
- representation constraints;
- difficulty envelope;
- non-leakage constraints;
- the set of fresh forms.

---

## 11.4 Assessment forms

Each family contains multiple concrete learner-facing forms.

For the POC:

> **4 forms per transition**

The current protocol allows at most three post-intervention assessments on a transition, so four forms provide one reserve.

Assessment forms SHOULD vary in surface realization while remaining structurally equivalent.

They MUST NOT merely duplicate the instructional example with a renamed variable or adjacent Fibonacci input if that makes recall sufficient.

---

## 11.5 Equivalence envelope

Forms within the same family SHOULD be comparable on factors such as:

- conceptual demand;
- required SOLO structure;
- Python-reading burden;
- prerequisite burden;
- expected response complexity;
- representational complexity;
- amount of information supplied;
- requirement for explanation versus code;
- exposure of misconceptions.

The family MUST define what may vary and what must remain stable.

---

## 11.6 Pedagogy independence vs intervention awareness

The runtime selector MUST be blind to pedagogy.

However, assessment authoring and validation SHOULD be aware of intervention materials for **non-leakage auditing**.

The relationship is:

```text
Knowledge Pack ─────► Assessment Pack
      strong semantic dependency

Intervention Pack ──► Assessment QA
      leakage audit only

Pedagogy used at runtime ──X──► assessment selection
      forbidden dependency
```

---

## 11.7 Non-leakage rules

The assessment SHOULD avoid:

- exact instructional examples;
- identical code snippets;
- identical solved cases;
- exact guided-question sequences;
- instructional material that effectively revealed the answer.

The following principle should hold:

> **Conceptual equivalence is required; surface duplication is not.**

---

## 11.8 Assessment selection

The current POC SHOULD select randomly from unseen eligible forms within the target transition family.

The selector SHOULD consider:

- correct transition;
- active/eligible form;
- not previously shown in the session;
- no exact material conflict;
- same assessment family.

The selector MUST NOT use:

- pedagogy identity;
- learner preference;
- Tutor recommendation.

---

# 12. Judge / Rubric Pack

## 12.1 Purpose

The Judge Pack operationalizes the Knowledge Pack into observable evidence rules.

It answers:

> **Given this learner response to this assessment, what knowledge, relationships and structural organization are actually demonstrated?**

---

## 12.2 Judge structure

The Judge Pack consists conceptually of:

```text
1 generic Judge contract
        +
4 transition-specific rubrics
```

It does not need a 4×3 pedagogy matrix because judging is not pedagogy-specific.

---

## 12.3 Generic Judge contract

The Judge MUST:

- evaluate only demonstrated evidence;
- distinguish correctness from structural organization;
- avoid inferring unstated knowledge;
- avoid rewarding terminology alone;
- ground judgments in the learner response;
- report uncertainty where evidence is ambiguous;
- avoid teaching or correcting the learner;
- produce structured evidence rather than free-form prose only.

The Judge MUST NOT receive:

- pedagogy identity;
- Tutor instructions;
- Tutor conversation;
- previous pedagogy outcomes;
- previous attempt number;
- cycle number;
- next pedagogy;
- reward information;
- future assessment information.

---

## 12.4 Strong dependencies

The Judge depends strongly on:

### Knowledge Pack

For:

- KCs;
- relations;
- misconceptions;
- state definitions;
- transition targets.

### Assessment Pack

For:

- exact assessment prompt;
- item-specific factual context;
- expected observations;
- acceptable variants;
- assessment-family reference.

The Judge has no runtime dependency on the Intervention Pack.

---

## 12.5 Correctness and structure are separate

The Judge MUST evaluate at least two dimensions:

### Correctness

Is the content materially correct relative to the topic frontier?

### Structural SOLO evidence

How are the learner's demonstrated ideas structurally organized?

A response may be structurally sophisticated but factually wrong.

Such a response MUST NOT automatically count as successful learning.

Example:

```text
"Memoization makes Fibonacci faster because it changes the recurrence
so fib(n) only needs fib(n-1)."
```

This may exhibit causal organization, but it materially contradicts the target knowledge.

The system should preserve both observations:

```text
structural organization: relatively integrated
correctness: materially incorrect
transition success: false
```

---

## 12.6 Transition-specific rubrics

Each transition rubric SHOULD define observable evidence for:

- required KCs;
- required relations;
- misconceptions;
- partial evidence;
- blocking misconceptions;
- state-level structural patterns;
- ambiguity cases.

The rubric references the Knowledge Pack rather than redefining it.

---

## 12.7 Judge output

The Judge SHOULD return structured evidence such as:

- gradable / not gradable;
- correctness result;
- KC evidence;
- relation evidence;
- misconceptions detected;
- observed SOLO state;
- confidence or uncertainty;
- short evidence excerpts or summaries.

The exact serialization format is an implementation detail.

---

## 12.8 Transition success is deterministic backend logic

The LLM SHOULD NOT be the sole authority deciding:

> “transition achieved = true”

Instead:

```text
Judge LLM
    ↓
structured evidence
    ↓
Judge rubric
    ↓
backend deterministic rule
    ↓
success / failure
```

This avoids contradictions such as:

```text
observed state = U
transition target = M
transition achieved = true
```

The backend derives success from the judged evidence and the rubric.

---

## 12.9 Above-target answers

If a learner demonstrates a state above the target state, the transition may still count as achieved.

However, the POC SHOULD advance only one formal transition at a time.

Example:

```text
Testing C2: U→M

Judge observes:
R-level response

Result:
C2 succeeds

Formal learner state:
advances to M

Next:
C3 is still tested independently
```

The raw observed state can still be logged.

---

## 12.10 Ambiguity

The Judge MAY express uncertainty.

The POC SHOULD log confidence/ambiguity but SHOULD NOT make a complex confidence-threshold policy part of the first implementation unless deliberately specified later.

---

# 13. Protocol configuration

## 13.1 Status

The protocol is necessary, but it does not need to be treated as a full intellectual content pack.

It is best considered:

> **versioned experiment configuration**

rather than a plugin.

---

## 13.2 Why protocol is not environment configuration

Deployment configuration and experiment configuration are different.

Environment configuration may contain:

- database connection;
- LLM API key;
- provider endpoint;
- Tutor model;
- Judge model;
- logging level.

Protocol configuration contains experimental behavior such as:

- transition sequence;
- pedagogy selection strategy;
- failure behavior;
- maximum attempts;
- assessment selection behavior;
- success progression.

Changing protocol behavior changes the experimental procedure and therefore MUST be versioned with the study definition.

---

## 13.3 Current POC protocol

The current intended POC behavior is:

```text
Initial formal state:
P

Transition order:
C1 → C2 → C3 → C4

At each transition:
randomize the three pedagogies without replacement

Attempt 1:
pedagogy A
    ↓
fresh assessment

if success:
advance one transition

if failure:
pedagogy B
    ↓
fresh assessment

if success:
advance one transition

if failure:
pedagogy C
    ↓
fresh assessment

if success:
advance one transition

if failure:
mark transition unresolved
stop session / stop progression

Renewed pedagogy cycle:
NO for this POC
```

---

## 13.4 Protocol engine boundary

The configuration chooses behavior.

The backend owns executable control flow.

The protocol configuration MUST NOT contain arbitrary executable scripts.

Conceptually:

```text
protocol config
    ↓
generic protocol engine
    ↓
session state transition
```

---

# 14. Prompt architecture

Prompt composition is a first-class subsystem.

Prompts MUST NOT be assembled ad hoc throughout the application.

Both Tutor and Judge prompts follow the same high-level layered pattern.

```text
LAYER 0
HARNESS / EXECUTION CONTRACT

        ↓

LAYER 1
GENERAL ROLE / FAMILY

        ↓

LAYER 2
SPECIFIC EXPERIMENT UNIT

        ↓

LAYER 3
RUNTIME CONTEXT
```

---

## 14.1 Layer 0 — Harness contract

Owned by the harness.

Examples of responsibilities:

- output format;
- valid identifiers;
- structured-result expectations;
- no invention of hidden fields;
- separation of Tutor and Judge responsibilities;
- basic runtime constraints.

Study authors should not need to redefine this per cell.

---

## 14.2 Tutor prompt

### General layer

Comes from:

- generic Tutor contract;
- pedagogy-family definition.

Answers:

> What kind of teacher are you allowed to be?

### Specific layer

Comes from:

- current Knowledge Slice;
- current intervention cell.

Answers:

> What exactly must this pedagogy do at this transition?

### Runtime layer

Contains:

- current attempt;
- prior-attempt structured history;
- material already exposed;
- learner evidence already seen;
- current intervention conversation;
- remaining turn budget.

Answers:

> What has happened to this learner so far?

---

## 14.3 Judge prompt

### General layer

Comes from:

- generic Judge contract.

### Specific layer

Comes from:

- Knowledge Slice;
- transition rubric;
- selected assessment;
- hidden item-specific scoring context.

### Runtime layer

Contains:

- learner's submitted assessment response.

The Judge runtime context is intentionally much narrower than the Tutor context.

It MUST NOT contain Tutor or pedagogy history.

---

## 14.4 Prompt reproducibility

Even if prompts are compiled dynamically, the harness MUST store the exact final prompt/request sent to each LLM call together with:

- model;
- provider;
- parameters;
- raw response;
- parsed response;
- timestamp;
- latency where available;
- token usage where available.

The authored packs define the stable pieces.

The database records the exact instantiated prompt.

---

# 15. Runtime sequence

The complete POC runtime can be represented as:

```text
START SESSION
    │
    ▼
load frozen study version
    │
    ▼
formal learner state = P
    │
    ▼
resolve next transition from Knowledge Pack
    │
    ▼
Protocol selects unused pedagogy
    │
    ▼
Knowledge Pack resolves transition slice
    │
    ▼
Intervention Pack resolves pedagogy family + cell
    │
    ▼
History Builder resolves prior-attempt context
    │
    ▼
Tutor Prompt Compiler
    │
    ▼
TUTOR LLM
    │
    ▼
multi-turn intervention
    │
    ▼
intervention completes / budget reached
    │
    ▼
Assessment Pack selects random unseen equivalent form
    │
    ▼
learner submits independent response
    │
    ▼
Judge Prompt Compiler
    │
    ▼
JUDGE LLM
    │
    ▼
structured correctness + SOLO evidence
    │
    ▼
deterministic rubric evaluation
    │
    ▼
SUCCESS?
   /      \
 YES      NO
  │        │
  ▼        ▼
advance    unused pedagogy remains?
one state       /        \
              YES        NO
               │          │
               ▼          ▼
          next attempt   unresolved
          with history   STOP
```

---

# 16. Cross-pack validation

The harness MUST validate the study definition before allowing a real session to begin.

At minimum, validation SHOULD check the following.

---

## 16.1 Reference integrity

All referenced entities must exist.

Examples:

- intervention references valid transition;
- intervention references valid pedagogy family;
- intervention references valid KCs;
- assessment references valid transition;
- Judge rubric references valid KCs/relations/misconceptions;
- protocol references valid transitions and pedagogies.

---

## 16.2 Intervention-grid completeness

For the current POC:

```text
4 transitions × 3 pedagogies = 12 cells
```

All 12 MUST exist before the study is considered complete.

---

## 16.3 Knowledge-boundary consistency

An intervention MUST NOT target future or out-of-scope knowledge in contradiction with the Knowledge Pack.

An assessment MUST NOT require knowledge outside its transition target unless explicitly justified.

---

## 16.4 Pedagogy-family fidelity

A cell MUST NOT contradict its pedagogy family.

Example:

- Guided Questioning cannot authorize a full solved explanation merely because the cell author wants one.
- Contrasting Cases must actually involve a diagnostic comparison.
- Worked Example must actually model reasoning rather than collapse into bare answer delivery.

---

## 16.5 Assessment capacity

For the current POC:

```text
maximum intervention attempts per transition = 3
assessment forms per transition = 4
```

Therefore each transition has enough forms for:

- all possible post-intervention assessments;
- one reserve form.

The harness MUST NOT silently reuse an assessment if fresh forms are required.

---

## 16.6 Assessment independence

No assessment form may be declared as “for Worked Example,” “for Guided Questioning,” or “for Contrasting Cases.”

The assessment construct is transition-specific, not pedagogy-specific.

---

## 16.7 Judge blindness

The Judge runtime input MUST NOT contain treatment identity or prior attempt history.

This should be enforced in code, not left to prompt wording alone.

---

# 17. Persistence and reproducibility

The harness should preserve both semantic versioning and runtime evidence.

---

## 17.1 Study version freeze

A session MUST reference a frozen study-definition version.

Editing pack files after a participant begins MUST NOT retroactively change that participant's effective study.

A practical implementation may store:

- a study-definition hash;
- a frozen compiled representation;
- or an immutable study-version record.

The conceptual requirement is reproducibility, not a specific storage technique.

---

## 17.2 What must be logged

At minimum:

### Session

- participant/session identifier;
- study version/hash;
- current formal state;
- current transition;
- start/end timestamps;
- final status.

### Randomization / selection

- candidate pedagogy pool;
- selected pedagogy;
- assessment candidate pool;
- selected assessment.

### Tutor interaction

- exact compiled prompt;
- model/provider;
- Tutor output;
- learner messages;
- intervention stage;
- turn count;
- exposed material identifiers;
- intervention completion reason.

### Assessment

- assessment identifier;
- exact learner-facing prompt;
- learner response;
- timestamps.

### Judge

- exact compiled Judge prompt;
- model/provider;
- raw output;
- parsed evidence;
- correctness result;
- observed SOLO state;
- misconceptions;
- uncertainty/confidence.

### Deterministic progression

- rubric decision;
- success/failure;
- formal state before;
- formal state after;
- reason for unresolved stop if applicable.

---

## 17.3 Raw evidence is authoritative

Derived labels MUST NOT replace raw evidence.

The system must retain:

- learner responses;
- prompts;
- model responses;
- assessment prompts.

This allows later human coding, reclassification, debugging and validation.

---

# 18. Runtime history object

Learner history is a core harness concept, not a study pack.

Conceptually:

```text
TRANSITION HISTORY
│
├── Attempt 1
│     pedagogy
│     concepts exposed
│     relations exposed
│     instructional material used
│     learner evidence
│     misconceptions
│     assessment outcome
│
├── Attempt 2
│     ...
│
└── Attempt 3
      ...
```

The exact object/schema is implementation-specific.

Its contract is not.

---

# 19. POC deployment boundary

Each Docker Compose deployment is treated as an independent local ecosystem.

The POC does not require central user management.

Conceptually:

```text
ONE COMPUTER
│
├── application container
├── local PostgreSQL container
├── mounted study definition
└── local persistent data volume
```

A new machine can run the experiment by:

- obtaining the application;
- supplying environment credentials/configuration;
- mounting the desired study definition;
- starting the Compose stack.

---

# 20. Current implementation direction

This section records current technical direction without making it part of the study-pack contract.

Recommended POC stack:

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- PostgreSQL
- psycopg
- Jinja2
- HTMX
- minimal vanilla JavaScript
- Docker Compose
- pytest
- OpenAI-compatible LLM client / HTTP adapter for AICredits

The frontend is intentionally simple.

There is no current need for Next.js, React state management, Redis, Celery, Kafka, object storage, or a separate frontend service.

---

# 21. Frontend boundary

The browser should primarily be a view/controller over server-owned experiment state.

The UI needs only to support:

- entering/starting a participant session;
- Tutor chat interaction;
- clear transition into assessment mode;
- assessment submission;
- simple waiting/loading states;
- simple transition outcome/progression;
- experiment completion or unresolved stop.

The frontend MUST NOT become the source of truth for experiment state.

Refresh/reconnect behavior should recover from the backend/database.

---

# 22. LLM-provider boundary

The Tutor and Judge are logical roles, not necessarily different underlying models.

The POC MAY use the same underlying provider/model for both.

However, they MUST have separate:

- prompt contracts;
- context boundaries;
- outputs;
- logs.

The LLM-provider adapter is infrastructure.

It is not part of the study definition.

The provider should be replaceable without rewriting the study packs.

For a controlled experimental run, model identity and important generation parameters SHOULD be pinned and logged.

---

# 23. Explicit decision boundaries

The following decisions are currently considered part of the design contract.

---

## 23.1 Knowledge is defined once

**MUST:** Knowledge Pack is the semantic authority.

**MUST NOT:** Intervention, Assessment or Judge packs independently redefine KC meaning.

---

## 23.2 Pedagogy is stable within an attempt

**MUST:** Assigned pedagogy remains identifiable throughout the intervention.

**MUST NOT:** Tutor switch pedagogy family because the learner struggles.

---

## 23.3 Cell specification is transition-specific

**MUST:** Every intervention be specific to topic + transition + pedagogy.

**MUST NOT:** Rely on a generic “teach using Socratic questioning” prompt alone.

---

## 23.4 LLM wording is flexible, mechanism is not

**MAY:** Tutor adapt wording, examples and local questioning to learner response.

**MUST:** Remain inside cell and pedagogy constraints.

---

## 23.5 Assessment is independent of pedagogy

**MUST:** Runtime assessment selection depend on target transition, not treatment identity.

**SHOULD:** Intervention materials be audited against assessment materials for leakage.

---

## 23.6 Assessment must be fresh

**MUST:** Do not repeatedly ask the same learner the same assessment form within the session when freshness is required.

---

## 23.7 Judge is blind to pedagogy

**MUST NOT:** Judge receive treatment identity, Tutor conversation or prior failures.

---

## 23.8 Judge interprets; backend decides progression

**MUST:** Judge produce structured evidence.

**MUST:** Backend apply deterministic rubric/protocol logic to decide progression.

---

## 23.9 Correctness and structural complexity are distinct

**MUST:** Preserve both.

**MUST NOT:** Treat coherent but materially false reasoning as successful simply because it is structurally integrated.

---

## 23.10 Later interventions know prior exposure

**MUST:** Later Tutor attempts receive relevant structured history.

**MUST NOT:** Treat the learner as untouched after a failed attempt.

---

## 23.11 Prior history cannot override treatment assignment

**MUST:** History may personalize execution.

**MUST NOT:** History authorize a treatment-family switch.

---

## 23.12 Intervention completion is not learning success

**MUST:** Intervention completion only means the teaching attempt ended.

**MUST:** Independent assessment + judgment determine whether the transition succeeded.

---

## 23.13 POC uses no renewed cycle

After all three pedagogies have been used unsuccessfully at a transition:

```text
transition = unresolved
session/progression = stopped
```

No new shuffled cycle begins in the current POC.

---

## 23.14 Formal progression is one transition at a time

Even if the Judge observes above-target structure:

```text
C2 target = M
observed = R
```

the POC formally advances from U to M and still tests C3.

---

# 24. Fibonacci POC instantiation

The first study definition implements the specification using:

```text
DOMAIN
Python Programming

TOPIC
Recursive Fibonacci with Memoization

FRONTIER
Fibonacci recurrence
recursive execution
overlapping/repeated subproblems
recomputation
cache storage
cache reuse
memoized recursion
mechanism-level reasoning

EXCLUDED
tabulation
bottom-up DP
space optimization
other DP problem families
```

---

## 24.1 SOLO progression

```text
P
No usable model
    │
    │ C1
    ▼
U
One central recursive Fibonacci structure
    │
    │ C2
    ▼
M
Multiple relevant pieces:
recursion, repeated calls, cache, reuse
but not yet fully integrated
    │
    │ C3
    ▼
R
Integrated causal memoization mechanism
    │
    │ C4
    ▼
EA
Reasoning from the memoization principle in
novel/equivalent Fibonacci situations
```

---

## 24.2 Intervention matrix

```text
                         Worked       Guided       Contrast
C1 P→U                     X             X             X
C2 U→M                     X             X             X
C3 M→R                     X             X             X
C4 R→EA                    X             X             X

Total:
12 intervention cells
```

---

## 24.3 Assessment inventory

```text
C1: 4 equivalent fresh forms
C2: 4 equivalent fresh forms
C3: 4 equivalent fresh forms
C4: 4 equivalent fresh forms

Total:
16 assessment forms
```

Maximum forms consumed in the current protocol:

```text
3 per transition
```

One reserve remains per transition.

---

## 24.4 Judge inventory

```text
1 generic Judge contract
+
4 transition-specific rubrics
```

The Judge does not vary by pedagogy.

---

# 25. Deliberate non-goals for the POC

The following are explicitly deferred.

The POC does NOT need:

- multiple domains;
- three matched parallel topics;
- final Experiment-1 causal design;
- renewed pedagogy cycles;
- reward computation;
- pedagogy ranking;
- Experiment-2 adaptive exploitation;
- RL;
- bandits;
- GQ;
- cognitive-load estimation;
- physiological signals;
- pupil dilation;
- HRV;
- webcam sensing;
- voice sensing;
- admin RBAC;
- participant authentication;
- institution management;
- cloud database;
- multi-tenant hosting;
- plugin marketplace;
- dynamic arbitrary Python plugin execution;
- sophisticated analytics dashboards;
- full researcher administration portal;
- Next.js unless later product requirements justify it.

---

# 26. What is still open

The following should remain explicitly unresolved until separately decided.

### Baseline / pre-transition assessment

Whether each transition begins with an additional independent check before intervention is not yet frozen.

If used, the assessment inventory and selection rules must account for it.

### Exact intervention budgets

Turn/time/content limits remain to be finalized.

### Exact learner-history summarization

The harness must provide structured prior-attempt context, but the precise mechanism for producing that summary is still open.

Possible sources include:

- deterministic runtime metadata;
- Judge evidence;
- Tutor-reported exposure metadata;
- a separate summarization step.

### Exact assessment-equivalence criteria

The concept is fixed; concrete calibration criteria require authoring/piloting.

### Exact judge evidence thresholds

The Judge/backend separation is fixed, but detailed transition rules still need to be authored with the Fibonacci rubrics.

### Exact LLM models

Provider abstraction is intended. Specific Tutor and Judge models can be selected later.

### Exact serialization

YAML/JSON is an implementation choice.

The conceptual contracts in this specification are format-independent.

---

# 27. Final dependency map

```text
┌───────────────────────────────────────────────────────────┐
│                    KNOWLEDGE PACK                         │
│                                                           │
│ topic                                                     │
│ prerequisites                                             │
│ frontier                                                  │
│ KCs                                                       │
│ relations                                                 │
│ misconceptions                                            │
│ P / U / M / R / EA                                       │
│ C1 / C2 / C3 / C4                                        │
└──────────────┬───────────────────┬───────────────────┬────┘
               │                   │                   │
               ▼                   ▼                   ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌────────────────────┐
│  INTERVENTION PACK   │ │   ASSESSMENT PACK    │ │     JUDGE PACK     │
│                      │ │                      │ │                    │
│ pedagogy families    │ │ transition families  │ │ generic judge      │
│ 12 cells             │ │ fresh equivalent     │ │ 4 rubrics          │
│ how to teach         │ │ forms                │ │ how to interpret   │
└──────────┬───────────┘ └──────────┬───────────┘ └──────────┬─────────┘
           │                        │                        │
           ▼                        ▼                        ▼
      TUTOR PROMPT               LEARNER                JUDGE PROMPT
           │                   ASSESSMENT                    │
           │                        │                        │
           │                        └──────────────┬─────────┘
           │                                       │
           │                                       ▼
           │                               STRUCTURED EVIDENCE
           │                                       │
           │                                       ▼
           │                               DETERMINISTIC RUBRIC
           │                                       │
           └──────────────┐                        │
                          │                        ▼
                          │                 SUCCESS / FAILURE
                          │                        │
                          ▼                        ▼
                    TRANSITION HISTORY       PROTOCOL ENGINE
                          │                        │
                          └────────────┬───────────┘
                                       │
                                       ▼
                                  NEXT ACTION
```

---

# 28. Final conceptual contract

The entire harness can be reduced to five questions:

```text
KNOWLEDGE PACK
What must be understood?

        ↓

INTERVENTION PACK
How does this assigned pedagogy try to cause that understanding?

        ↓

ASSESSMENT PACK
What fresh independent task reveals whether it happened?

        ↓

JUDGE PACK
What observable evidence does the learner's response demonstrate?

        ↓

PROTOCOL
Given that evidence and outcome, what happens next?
```

With one additional runtime principle:

```text
HISTORY
What has this learner already experienced,
and how may the next assigned pedagogy adapt
without changing treatment identity?
```

That is the conceptual center of the POC harness.

Everything else — APIs, SQL models, frontend components, serialization formats, and provider adapters — exists to execute and preserve this contract.
