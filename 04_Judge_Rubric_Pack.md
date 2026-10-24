# 04 — Judge / Rubric Pack

**Version:** content draft v0.1  
**Dependencies:** Knowledge Pack + selected Assessment Form  
**Forbidden runtime dependency:** Intervention Pack / pedagogy identity / prior Tutor history

---

# 1. Purpose

The Judge interprets a learner's independent assessment response against explicit correctness and SOLO-structure criteria.

The Judge does not teach.

The Judge does not select pedagogy.

The Judge does not decide the next protocol action.

The Judge returns structured evidence.

The backend applies deterministic transition-success rules.

---

# 2. Generic Judge contract

The Judge must:

- evaluate only the submitted assessment response;
- use the exact assessment task and hidden scoring context supplied;
- use Knowledge Pack definitions as semantic authority;
- distinguish factual correctness from structural organization;
- avoid inferring knowledge not demonstrated;
- avoid rewarding terminology alone;
- identify relevant misconceptions only when supported by the response;
- represent ambiguity when evidence is incomplete;
- provide concise evidence-linked justification.

The Judge must not receive or use:

- pedagogy identity;
- Tutor prompt;
- Tutor transcript;
- previous failed assessments;
- attempt number as a reason to score differently;
- next pedagogy;
- reward information.

---

# 3. Generic output concepts

The exact machine schema is deferred, but the Judge should provide the equivalent of:

- `gradable`
- correctness status
- knowledge-component evidence
- relation evidence
- misconceptions detected
- observed SOLO state
- confidence/ambiguity
- short evidence excerpts or evidence summaries

The LLM should not be the sole source of `transition_achieved`.

---

# 4. Global SOLO interpretation

## P

Response lacks a usable relevant structure or is materially off-topic/misconceived.

## U

One central relevant structure is demonstrated.

## M

Multiple relevant components are demonstrated but remain largely separate.

## R

Relevant components are integrated into a coherent causal/relational explanation.

## EA

The learner abstracts the mechanism and applies it to an unfamiliar/equivalent situation, derives invariants, or reasons beyond the canonical representation.

The Judge must not classify by response length or vocabulary density alone.

---

# 5. Correctness policy

Correctness and structural organization are separate dimensions.

A response can be structurally integrated yet materially incorrect.

Such a response may be recorded as showing integrated structure, but a material contradiction of required target knowledge blocks transition success.

Examples of blocking errors include, when relevant:

- wrong Fibonacci recurrence;
- claim that memoization changes the recurrence;
- claim that a cache hit still requires recursively solving the subproblem first;
- claim that independent fresh caches across recursive calls provide cross-branch reuse.

---

# 6. C1 Rubric — P → U

## Target state

Unistructural

## Core target

One coherent recurrence-to-recursion relationship.

## Required correctness

The response must not materially contradict:

- `fib(n) = fib(n-1) + fib(n-2)` for non-base inputs;
- appropriate terminating base cases in the POC definition.

## Evidence criteria

### C1-E1 — Two-predecessor dependence

Learner demonstrates that a non-base Fibonacci value depends on both preceding Fibonacci values.

### C1-E2 — Recursive representation

Learner connects that dependence to recursive calls or an equivalent recursive description.

### C1-E3 — Termination/base cases

Learner correctly handles or explains `fib(0)`/`fib(1)` as terminating known values when the task requires it.

## State guidance

### P

Examples:

- gives unrelated loop explanation;
- says `fib(n)=fib(n-1)` with no correction;
- cannot identify a relevant recurrence structure.

### U

Demonstrates the central two-predecessor recursive relationship.

The answer may be concise.

### M or above

If the learner additionally discusses repeated subproblems, caching, etc., the Judge may observe above-target structure, but the formal C1 result only concerns whether U is reached.

## Blocking misconceptions

- M1 when it materially defines Fibonacci with one predecessor.

## Deterministic success rule

C1 succeeds when:

- response is gradable;
- required core relation C1-E1 + C1-E2 is demonstrated;
- task-specific base-case requirement is correct;
- no blocking misconception materially contradicts the core relation.

---

# 7. C2 Rubric — U → M

## Target state

Multistructural

## Core target

Multiple relevant components concerning recursive repetition and memoization are demonstrated.

Full causal integration is not required.

## Evidence domains

### C2-E1 — Recursive/repeated subproblem

Learner recognizes that the same smaller `fib(k)` may be requested multiple times.

### C2-E2 — Repeated computation

Learner recognizes that without retained results, the repeated subproblem may be recomputed.

### C2-E3 — Stored result

Learner recognizes that a solved result can be stored in association with its input.

### C2-E4 — Lookup/reuse

Learner recognizes that a later request can check/access and reuse a stored result.

### C2-E5 — Shared cache availability

Learner recognizes, when the item probes it, that recursive calls need access to relevant shared cache state for cross-branch reuse.

## State guidance

### U

One relevant idea only.

Example:

> “A dictionary stores previous values.”

### M

Several relevant components are correctly present, even if listed rather than integrated.

Example:

> “The same Fibonacci call can happen again. Without memory it can be calculated again. A cache can store an answer by input, and a later call can reuse it.”

### R or above

If the response causally integrates the components, the Judge may observe R, but C2 still formally advances only to M.

## Blocking misconceptions

Material versions of:

- M3;
- M5;
- M6;
- M8 when the task explicitly probes shared state.

## Deterministic success rule

C2 succeeds when:

- response is gradable;
- at least three transition-relevant evidence domains are demonstrated;
- those domains include at least one repetition/recomputation concept (E1 or E2);
- and at least one storage/reuse concept (E3 or E4);
- any task-explicit required component is correct;
- no blocking misconception invalidates the demonstrated model.

This rule allows a multi-component M response without demanding full C3 integration.

---

# 8. C3 Rubric — M → R

## Target state

Relational

## Core target

The learner integrates repeated subproblems, recomputation, storage, lookup/reuse, and preserved recurrence into one causal memoization mechanism.

## Evidence criteria

### C3-E1 — Repetition causes redundant computation

The learner causally connects a repeated request for the same subproblem to repeated recursive computation when prior results are not retained.

Not enough:

> “Recursion is slow.”

### C3-E2 — Correct storage semantics

The learner explains that a solved Fibonacci result is retained in association with its input.

Not enough:

> “It has a dictionary.”

### C3-E3 — Lookup/reuse before redundant expansion

The learner explains that a later request can find and return/reuse the stored result rather than recursively solving that same subproblem again.

### C3-E4 — Integrated causal chain

The learner connects E1–E3 rather than listing them independently.

Strong evidence resembles:

```text
same subproblem requested again
→ naive version would recompute
→ prior result is stored
→ later call checks/uses stored result
→ recursive expansion for that subproblem is avoided
```

### C3-E5 — Recurrence preserved

The learner correctly states or clearly implies that memoization does not change the Fibonacci recurrence.

### C3-E6 — Shared cache mechanism where relevant

If the assessment probes cache scope, the learner understands that the reusable result must be accessible to later recursive requests.

## State guidance

### M

Multiple relevant pieces are present but largely listed.

### R

The causal mechanism is integrated and correct.

### EA

The learner additionally abstracts the mechanism to unfamiliar code/invariants beyond the immediate item.

## Blocking misconceptions

- M3 if it denies same-input reusability;
- M4;
- M5 when it destroys correct storage semantics;
- M6 when dictionary presence is treated as sufficient;
- M7;
- M8 when cache sharing is relevant;
- M9 if learner claims memoization removes recursion rather than reusing solved recursive subproblems.

## Deterministic success rule

C3 succeeds when:

- response is gradable;
- correctness is materially sound;
- E1, E2, E3, and E4 are demonstrated;
- E5 is demonstrated when explicitly requested or no contradictory claim is present;
- no blocking misconception invalidates the mechanism.

Observed R or EA satisfies the structural threshold, but formal state advances only to R.

---

# 9. C4 Rubric — R → EA

## Target state

Extended Abstract

## Core target

The learner reasons from memoization invariants in an unfamiliar recursive-Fibonacci situation.

The learner must do more than restate the canonical memoized function.

## Evidence criteria

### C4-E1 — Identifies essential invariants

The learner can identify mechanism-level requirements such as:

- consistent subproblem identity;
- accessible/shared relevant cache state;
- lookup/conditional reuse before redundant expansion;
- correct storage of newly solved results;
- preserved recurrence.

### C4-E2 — Distinguishes invariant from incidental syntax

The learner recognizes that details such as:

- variable names;
- exact `if` phrasing;
- whether base cases are also cached;
- temporary local variable names;

are not themselves the definition of memoization.

### C4-E3 — Applies mechanism to unfamiliar implementation

The learner correctly evaluates code or a design that differs from the canonical memorized pattern.

### C4-E4 — Reasons about cache state

Where the item requires it, the learner predicts what existing entries can be reused and how additional entries arise.

### C4-E5 — Diagnoses broken memoization from principle

The learner can explain *why* a superficially cached implementation fails, e.g. because cache state is recreated or lookup occurs only after redundant work.

### C4-E6 — Derives requirements

The learner can state or construct requirements for a valid memoized recursive Fibonacci design without merely reproducing a memorized program.

## State guidance

### R

Correct integrated explanation of canonical memoized recursion, but little evidence of abstraction to the unfamiliar form.

### EA

Mechanism-level reasoning transfers to the unfamiliar code/state and distinguishes essential from incidental features.

## Blocking misconceptions

- M6;
- M7;
- M8;
- M10;
- any material recurrence error.

## Deterministic success rule

C4 succeeds when:

- response is gradable;
- correctness is materially sound;
- the response demonstrates at least one explicit abstraction/invariance criterion (E1 or E2);
- and at least one transfer/derivation criterion appropriate to the item (E3, E4, E5, or E6);
- the response does not simply repeat canonical code without engaging the unfamiliar situation;
- no blocking misconception invalidates the mechanism.

---

# 10. Item-specific scoring context

The Assessment Pack supplies hidden facts/expectations specific to the selected item.

The Judge combines:

```text
Generic Judge Contract
        +
Transition Rubric
        +
Selected Assessment Prompt
        +
Item-Specific Scoring Context
        +
Learner Response
```

It does not combine:

```text
Tutor transcript
Pedagogy identity
Attempt history
```

---

# 11. Using Judge evidence for later Tutor history

After the judgment is complete, the backend may convert selected structured outputs into later Tutor context, for example:

```text
demonstrated:
K5 repeated subproblems

partial:
K8 reuse

misconception:
M4 recurrence-changing belief

transition outcome:
C3 not achieved
```

This happens **after** judging.

The Judge itself remains blind to the previous intervention.

---

# 12. Uncertainty

The Judge may report:

- ambiguity;
- partial evidence;
- low confidence.

The POC should log such uncertainty.

The initial POC should not introduce an elaborate confidence-threshold policy unless separately specified.

Raw learner responses must always be retained for later human review/reclassification.
