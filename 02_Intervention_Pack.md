# 02 — Intervention Pack

**Version:** content draft v0.1  
**Dependency:** `01_Knowledge_Pack.md` is the semantic source of truth.

---

# 1. Purpose

This pack defines how each pedagogical family attempts to produce each SOLO transition.

It contains:

1. three pedagogy-family contracts;
2. twelve transition × pedagogy intervention cells.

The family definition fixes the treatment mechanism.

The cell defines how that mechanism is instantiated for the current transition.

The LLM may adapt surface wording and local examples, but must remain inside both layers.

---

# 2. Shared intervention envelope

Every intervention, regardless of pedagogy, must satisfy the following.

## Same target

All three pedagogies operating on a given transition target the same Knowledge Slice.

## Same frontier

All interventions remain inside recursive Fibonacci + memoization.

## No assessment leakage

The Tutor must not use a reserved assessment form verbatim or reveal its hidden scoring context.

## No pedagogy switching

One pedagogy family remains fixed for the entire attempt.

## Independent outcome

The intervention itself never declares that the learner has passed.

Completion means only that the teaching attempt has ended.

A fresh assessment follows.

## Runtime history

A later intervention on the same transition receives structured history describing previous exposures/evidence.

History may alter emphasis and surface choice.

History may not authorize a change of pedagogy family.

---

# 3. Pedagogy family: Worked-Example Instruction

## Core mechanism

**Model the organization.**

The learner studies an explicitly organized solved case in which the target reasoning is visible.

## Tutor role

The Tutor may:

- present a complete solved example;
- make reasoning steps explicit;
- explain why each step is valid;
- make the target relationship visible;
- ask short rationale/engagement questions after or around modeled reasoning;
- choose a new instructional instance if prior history shows that an earlier instance has already been exposed.

## Tutor must not

- turn the main mechanism into a long sequence of discovery questions;
- withhold the key organization in order to make the learner infer it independently;
- use a contrast between two cases as the primary mechanism.

## Treatment-fidelity test

If the learner could receive the whole intervention without seeing an organized model of the target reasoning, the cell is probably not functioning as Worked-Example Instruction.

---

# 4. Pedagogy family: Guided Questioning

## Core mechanism

**Guide the learner to construct the organization.**

The Tutor uses bounded, sequenced questions to elicit the target relationship from the learner.

## Tutor role

The Tutor may:

- ask targeted questions;
- ask for prediction;
- ask for justification;
- narrow a question;
- refer to the learner's immediately preceding answer;
- expose inconsistency through another question;
- provide minimal factual clarification when required to keep the questioning process viable.

## Tutor must not

- present the complete target reasoning before the learner has constructed it;
- replace questioning with a worked solution because the learner struggles;
- use a pairwise comparison task as the primary teaching mechanism;
- silently switch to Worked Example.

## Treatment-fidelity test

The learner should be doing the relation-building cognitive work.

The Tutor controls the path, but does not simply hand over the completed structure.

---

# 5. Pedagogy family: Contrasting-Case Instruction

## Core mechanism

**Infer the organization through comparison.**

The Tutor presents controlled cases designed so that comparison reveals the target structural feature.

## Tutor role

The Tutor may:

- present two or more aligned cases;
- ask what is shared;
- ask what differs;
- ask which difference matters;
- ask what rule/mechanism can be inferred;
- stabilize irrelevant features while varying the diagnostic feature.

## Tutor must not

- merely label one case correct and explain the target without requiring comparison;
- vary many unrelated difficulty dimensions at once;
- collapse into Worked Example;
- collapse into a generic Socratic sequence with no meaningful contrast.

## Treatment-fidelity test

The learner's understanding should be driven by noticing/inferencing from a controlled contrast.

---

# 6. C1 — P → U interventions

## C1 target

Establish one coherent relationship:

> the Fibonacci recurrence depends on the two preceding Fibonacci values and can be represented recursively with base cases.

Target references:

- K1
- K2
- K3
- R1

Future memoization content must not be required.

---

## C1 × Worked Example

### Instructional objective

Model how the mathematical Fibonacci definition maps directly to a recursive Python function.

### Recommended instructional instance

Use a small value such as `fib(4)` or `fib(5)` that is not reserved for the selected assessment.

### Modeled content

The Tutor should explicitly model:

1. `fib(0)=0` and `fib(1)=1` as terminating cases.
2. For `n >= 2`, `fib(n)=fib(n-1)+fib(n-2)`.
3. Therefore a recursive function for `fib(n)` requests the two smaller Fibonacci values.
4. The returned result is their sum.

Illustrative solved program:

```python
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
```

Illustrative walkthrough:

```text
fib(4)
= fib(3) + fib(2)

fib(3)
= fib(2) + fib(1)

Eventually recursive calls reach fib(1) or fib(0),
where the function can return a known value rather than recurse again.
```

### Must make visible

- two-predecessor dependence;
- mapping between recurrence and recursive calls;
- role of base cases in termination.

### Must not introduce as instructional target

- repeated-subproblem inefficiency;
- caching;
- memoization;
- tabulation.

### Completion condition

The solved relationship has been modeled clearly and the learner has had an opportunity to restate or answer a short rationale question about why the function has two recursive calls and base cases.

---

## C1 × Guided Questioning

### Instructional objective

Guide the learner to construct the recurrence-to-recursion relationship.

### Required questioning progression

The Tutor should guide approximately through these functions:

1. **Sequence dependency**
   - Ask how a later Fibonacci value is obtained from earlier ones.
   - Use a concrete example if needed, such as `0, 1, 1, 2, 3, 5`.

2. **Two predecessors**
   - Elicit that `fib(n)` depends on both `fib(n-1)` and `fib(n-2)`.

3. **Recursive representation**
   - Ask what a function computing `fib(n)` could request from itself.

4. **Termination**
   - Ask what should happen at `n=0` and `n=1`, and why recursion cannot continue indefinitely.

5. **Synthesis**
   - Ask the learner to state the basic recursive rule in words or simple pseudocode.

### Illustrative moves

- “To get 5 from the Fibonacci sequence, which earlier values were combined?”
- “If a function is asked for `fib(n)`, which two smaller Fibonacci inputs does it need?”
- “What should happen when the input reaches 0 or 1?”

### Recovery rule

If the learner proposes only `fib(n-1)`, ask for a concrete sequence check rather than immediately giving the formula.

### Prohibition

Do not shift into memoization or repeated-work discussion.

### Completion condition

The learner has constructed the central recurrence/recursive relationship or the intervention budget is exhausted.

---

## C1 × Contrasting Cases

### Instructional objective

Have the learner infer the essential two-predecessor recursive structure by comparing two closely matched candidate definitions.

### Controlled cases

Case A:

```python
def fib_a(n):
    if n <= 1:
        return n
    return fib_a(n - 1)
```

Case B:

```python
def fib_b(n):
    if n <= 1:
        return n
    return fib_b(n - 1) + fib_b(n - 2)
```

### Invariants across cases

- same function purpose;
- same parameter;
- same base-case structure;
- both are recursive.

### Diagnostic difference

- Case A uses only one preceding Fibonacci input.
- Case B uses both required preceding inputs.

### Comparison sequence

The Tutor should ask the learner to:

1. identify what the functions have in common;
2. identify the key difference in the recursive return line;
3. test the two definitions against a small Fibonacci value;
4. infer which structure matches the Fibonacci sequence and why.

### Intended inference

The two-predecessor recurrence is the central structure required for recursive Fibonacci.

### Prohibition

Do not introduce caching or efficiency as the comparison dimension.

---

# 7. C2 — U → M interventions

## C2 target

Build several relevant components:

- recursive dependency structure;
- repeated subproblems;
- repeated computation;
- result storage;
- lookup/reuse;
- shared cache state.

Target references:

- K4–K9
- R2–R5 as component relations may be encountered, but full causal integration is not yet required.

The desired state is **multiple relevant pieces**, not yet necessarily a fully integrated C3 explanation.

---

## C2 × Worked Example

### Instructional objective

Model several distinct components that become relevant once the learner already understands basic recursive Fibonacci.

### Part A — show dependency/repetition

Use a small naive recursive call tree, for example:

```text
fib(5)
├── fib(4)
│   ├── fib(3)
│   └── fib(2)
└── fib(3)
```

Explicitly identify:

- a recursive dependency;
- a repeated subproblem such as `fib(3)`;
- the fact that naive recursion computes it again when no result was retained.

### Part B — show storage as a separate mechanism

Introduce a small cache table conceptually:

```text
input   stored result
  2          1
  3          2
```

Explain:

- a solved value can be stored with its input;
- the function can later check whether an input already has a stored result;
- a stored result can be reused.

### Part C — show shared state

Explain that recursive calls must be using the same relevant cache if one branch is to benefit from work done in another branch.

### C2 boundary

The Tutor may name and demonstrate the pieces, but should not make the full C3 causal chain the central instructional object.

The learner is being equipped with multiple relevant components.

### Completion condition

All target components have been modeled as identifiable pieces and the learner can recognize at least several of them.

---

## C2 × Guided Questioning

### Instructional objective

Elicit several relevant observations/components without requiring the learner to produce the full integrated memoization mechanism.

### Required progression

1. **Dependency**
   - “What smaller calls are needed while computing `fib(5)`?”

2. **Repetition**
   - Show/construct a small call tree.
   - “Which smaller input appears in more than one branch?”

3. **Repeated computation**
   - “If the program remembers nothing, what happens when that same input appears again?”

4. **Storage**
   - “What information from the first completed calculation could be kept?”

5. **Input/result association**
   - “How would the program know that the stored value belongs to `fib(3)` rather than `fib(4)`?”

6. **Lookup/reuse**
   - “Before calculating the same input again, what could the function check?”

7. **Shared cache**
   - “If every recursive call created a completely separate empty store, could one branch reuse a result found by another?”

### C2 boundary

Do not require a polished explanation of the entire causal chain.

It is acceptable at C2 for the learner to express the pieces separately.

### Completion condition

The learner has demonstrated or engaged with several relevant components, or the budget is exhausted.

---

## C2 × Contrasting Cases

### Instructional objective

Use controlled comparisons to help the learner identify multiple relevant components of repeated work and result reuse.

### Contrast 1 — repeated vs non-repeated positions

Present a small recursive dependency diagram containing repeated `fib(k)` nodes.

Ask:

- which labels repeat;
- which are unique in the shown portion;
- what the repeated label means.

### Contrast 2 — no stored result vs stored result available

Present two execution snapshots for the same requested subproblem.

Case A:

```text
Request: fib(3)
Stored entries: none
```

Case B:

```text
Request: fib(3)
Stored entries: {3: 2}
```

Ask:

- what information differs;
- what action becomes possible in B that is not possible in A.

### Contrast 3 — shared vs separate cache

Case A:

```text
all recursive calls receive the same memo mapping
```

Case B:

```text
each recursive call starts with a new empty memo mapping
```

Ask what opportunity for reuse differs.

### Intended C2 result

The learner accumulates multiple relevant distinctions:

- repeated subproblem;
- recomputation;
- stored result;
- lookup/reuse;
- shared state.

### Boundary

Do not require a generalized, integrated efficiency explanation yet.

---

# 8. C3 — M → R interventions

## C3 target

Integrate the existing pieces into one causal mechanism.

Target references:

- K10
- K11
- R2–R9

Critical invariant:

> memoization changes reuse/evaluation behavior, not the Fibonacci recurrence.

---

## C3 × Worked Example

### Instructional objective

Use a complete solved execution example to model the causal relationship:

```text
repeated subproblems
→ repeated computation
→ storage
→ lookup/reuse
→ avoided recursive recomputation
```

while preserving the recurrence.

### Naive recursive model

```python
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
```

Illustrative reasoning:

```text
When fib(5) is computed, fib(3) can be reached while solving fib(4)
and then requested again from another branch.

The second fib(3) request is the same mathematical subproblem.

Because the naive implementation retained no result for fib(3),
that second request triggers the recursive work for fib(3) again.
```

### Memoized recursive model

```python
def fib(n, memo=None):
    if memo is None:
        memo = {}

    if n in memo:
        return memo[n]

    if n <= 1:
        return n

    memo[n] = fib(n - 1, memo) + fib(n - 2, memo)
    return memo[n]
```

Model:

1. first request for a non-cached subproblem recursively solves it;
2. its result is stored under the input;
3. a later request checks the shared cache;
4. if the result exists, it is returned;
5. the recursive expansion for that subproblem is avoided;
6. the Fibonacci recurrence remains unchanged.

### Required synthesis

The Tutor must explicitly model the whole causal chain.

### Prohibitions

- no tabulation;
- no claim that recurrence changes;
- no assessment item verbatim.

### Completion condition

The integrated mechanism has been modeled and the learner has engaged with or restated it.

---

## C3 × Guided Questioning

### Instructional objective

Guide the learner to construct the integrated causal mechanism themselves.

### Required progression

#### Stage 1 — establish repetition

Use a small recursive dependency structure and ask which `fib(k)` is reached more than once.

#### Stage 2 — establish recomputation

Ask what naive recursion does on the later request if no prior result is retained.

#### Stage 3 — establish storage

Ask what result from the first computation could be retained and how it is associated with the input.

#### Stage 4 — establish reuse

Ask what the function should check on the later request and what it can return if the result exists.

#### Stage 5 — integrate

Ask the learner to connect:

```text
repeated request
→ otherwise recomputed
→ stored result
→ later lookup
→ reuse
→ avoided recursive work
```

#### Stage 6 — preserve recurrence

Ask whether memoization changes:

`fib(n) = fib(n-1) + fib(n-2)`

or instead changes how already solved recursive subproblems are handled.

### Recovery rule

If the learner produces M4 (“memoization changes the recurrence”), continue questioning from the recurrence itself rather than dumping the final answer.

### Prohibition

Do not convert to direct worked explanation.

---

## C3 × Contrasting Cases

### Instructional objective

Have the learner infer the integrated memoization mechanism by comparing two recursive implementations with the same recurrence but different result-retention behavior.

### Case A

```python
def fib_a(n):
    if n <= 1:
        return n
    return fib_a(n - 1) + fib_a(n - 2)
```

### Case B

```python
def fib_b(n, memo=None):
    if memo is None:
        memo = {}

    if n in memo:
        return memo[n]

    if n <= 1:
        return n

    memo[n] = fib_b(n - 1, memo) + fib_b(n - 2, memo)
    return memo[n]
```

### Invariants

- same Fibonacci task;
- same base cases;
- same recurrence;
- same recursive decomposition.

### Diagnostic difference

B stores and reuses solved subproblem results.

### Required comparison sequence

Ask:

1. what mathematical rule is shared;
2. what happens in both on the first uncached request;
3. what happens when the same subproblem is requested later;
4. which specific difference causes the changed behavior;
5. why this avoids repeated work without changing Fibonacci.

### Intended inference

The learner constructs the integrated causal mechanism through comparison.

---

# 9. C4 — R → EA interventions

## C4 target

Abstract the memoization mechanism beyond one canonical code form.

Target references:

- K12
- K13
- K14
- R9–R12

The learner should reason from invariants.

---

## C4 × Worked Example

### Instructional objective

Model how to evaluate an unfamiliar recursive Fibonacci implementation by checking memoization invariants rather than matching memorized syntax.

### Worked example: superficially cached but ineffective sharing

```python
def fib(n):
    memo = {}

    if n in memo:
        return memo[n]

    if n <= 1:
        return n

    memo[n] = fib(n - 1) + fib(n - 2)
    return memo[n]
```

### Modeled analysis

The Tutor should reason explicitly:

1. There is a dictionary, but dictionary presence alone is not enough.
2. Every call to `fib` creates a new empty `memo`.
3. A result stored inside one call is not available to a sibling recursive call.
4. Therefore repeated subproblems cannot reliably reuse previously stored values across the recursive tree.
5. The code is still recursively computing Fibonacci, but it does not realize the intended shared memoization mechanism.

Then model a valid alternative whose cache is shared:

```python
def fib(n, memo):
    if n in memo:
        return memo[n]

    if n <= 1:
        return n

    result = fib(n - 1, memo) + fib(n - 2, memo)
    memo[n] = result
    return result
```

### Abstraction

The Tutor should extract invariants:

```text
valid memoized recursion does not depend on one exact code layout

what matters is:
- consistent subproblem identity;
- shared accessible stored results;
- lookup before redundant recursive expansion;
- correct storage of newly solved values;
- preserved recurrence.
```

### Completion condition

The invariants have been modeled and applied to at least one unfamiliar implementation.

---

## C4 × Guided Questioning

### Instructional objective

Guide the learner to derive memoization invariants from unfamiliar code and use them to diagnose implementation behavior.

### Unfamiliar example

Use a snippet different from reserved assessments, for example one where the cache is passed as a parameter but lookup occurs too late.

Guide through:

1. “Where does the stored state live?”
2. “Do recursive calls see the same state?”
3. “At what point is the cache checked?”
4. “If recursive work happens before the check, what work has already been done?”
5. “What must be true for a repeated `fib(k)` request to avoid recursive expansion?”
6. “Which parts are essential mechanism and which are merely code style?”
7. “Can you state a set of requirements that any correct memoized recursive Fibonacci function should satisfy?”

### Desired learner construction

The learner derives invariants rather than reproducing canonical code.

### Prohibition

Do not give the complete invariant list before the learner has substantially constructed it.

---

## C4 × Contrasting Cases

### Instructional objective

Use contrasting unfamiliar implementations to help the learner infer which features are essential versus incidental.

### Example contrast

Case A:

- cache passed through recursive calls;
- cache checked before recursive expansion;
- result stored after computation.

Case B:

- same recurrence;
- dictionary present;
- a fresh dictionary created inside every recursive call.

Keep other syntax as similar as possible.

### Comparison sequence

Ask:

1. what both cases share;
2. what differs in cache lifetime/scope;
3. whether the same computed result can be available to a later sibling request;
4. which implementation genuinely memoizes;
5. what general rule about cache sharing follows.

### Second contrast dimension

Optionally compare two **both-valid** implementations whose surface organization differs, for example:

- one pre-seeds base cases in the cache;
- one handles base cases directly and only caches non-base results.

Ask what invariant mechanism remains common.

### Intended inference

The learner abstracts away from canonical syntax and identifies the essential mechanism.

---

# 10. Runtime history guidance for all cells

When prior attempts exist on the same transition, the Tutor may receive:

- previous pedagogy identities;
- target KCs already exposed;
- material IDs already used;
- learner evidence;
- misconceptions;
- prior assessment outcome.

The Tutor should:

- avoid exact reuse of prior instructional material where feasible;
- avoid spending the entire intervention reteaching already-demonstrated pieces;
- focus within the assigned cell on unresolved target evidence;
- preserve the pedagogy family.

The Tutor must not receive:

- future assessment forms;
- hidden scoring context;
- answer keys;
- Judge hidden reasoning.

---

# 11. Treatment-fidelity summary

```text
WORKED EXAMPLE
Learner sees the organization modeled.

GUIDED QUESTIONING
Learner constructs the organization through bounded questions.

CONTRASTING CASES
Learner infers the organization through controlled comparison.
```

All three share the same transition target.

Their pedagogical mechanisms intentionally differ.
