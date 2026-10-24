# 03 — Assessment Pack

**Version:** content draft v0.1  
**Dependency:** Knowledge Pack defines the construct.  
**Runtime rule:** Assessment selection is independent of the pedagogy just used.

---

# 1. Purpose

This pack defines fresh, transition-specific assessment families.

Each transition has four forms in the POC.

A form tests whether the learner can independently demonstrate the target structure.

The assessment must not merely rehearse the instructional instance.

---

# 2. Global assessment rules

## Pedagogy independence

The selector must not choose a form because the learner received Worked Example, Guided Questioning, or Contrasting Cases.

## Freshness

Within one session, an assessment form should not be reused.

## Equivalence

Forms within a transition family should be comparable in conceptual demand.

## Non-leakage

Reserved assessment material should not be used verbatim during intervention.

## Independent response

During assessment:

- no tutoring;
- no hints;
- no intervention continuation;
- no corrective feedback before submission.

---

# 3. C1 Assessment Family — P → U

## Construct

Can the learner demonstrate one usable central structure connecting:

- Fibonacci base cases;
- the two-predecessor recurrence;
- recursive computation?

## Required evidence

A successful C1 response should show the core idea that for non-base inputs, `fib(n)` depends on `fib(n-1)` and `fib(n-2)`, with base cases terminating the recursion.

## Equivalence envelope

All forms should:

- require only basic Python reading/writing;
- avoid memoization;
- avoid repeated-subproblem analysis;
- require a short explanation or simple completion;
- assess the same recurrence-to-recursion relationship.

---

## C1-A1 — Complete the recursive relationship

A student has started this function:

```python
def fib(n):
    if n <= 1:
        return n

    # one line is missing here
```

**Question**

Write or describe what the missing return step must do for the function to follow the Fibonacci definition. Explain why two smaller Fibonacci values are needed.

### Hidden scoring context

Expected:

- uses `fib(n-1)` and `fib(n-2)`;
- combines by addition;
- explanation reflects the two-predecessor recurrence;
- base case is recognized as termination if discussed.

Material tag: `c1_code_completion_alpha`

---

## C1-A2 — Explain a concrete value recursively

**Question**

Without listing the whole Fibonacci sequence from memory, explain how a recursive function could compute `fib(5)`. Your answer should describe:

1. which smaller Fibonacci values `fib(5)` depends on; and
2. what happens when the input reaches 0 or 1.

### Hidden scoring context

Expected:

- `fib(5)` depends on `fib(4)` + `fib(3)`;
- recursive continuation follows same relation;
- `fib(0)`/`fib(1)` terminate with known values.

Material tag: `c1_explanation_beta`

---

## C1-A3 — Choose the structurally correct recursive rule

Consider these two candidate recursive return rules for `n > 1`.

**Rule A**

```python
return fib(n - 1)
```

**Rule B**

```python
return fib(n - 1) + fib(n - 2)
```

**Question**

Which rule represents Fibonacci recursion, and why? Include the role of the base cases in your explanation.

### Hidden scoring context

Expected:

- chooses B;
- identifies two-predecessor Fibonacci relation;
- base cases prevent infinite recursion/provide known terminal values.

Material tag: `c1_rule_choice_gamma`

---

## C1-A4 — Trace one dependency step

Suppose a recursive Fibonacci function is asked to compute `fib(6)`.

**Question**

Before either smaller call is fully evaluated, which two Fibonacci subproblems must the function request to follow the standard Fibonacci recurrence? Explain how this same rule continues until the base cases are reached.

### Hidden scoring context

Expected:

- `fib(5)` and `fib(4)`;
- same two-predecessor relation recursively;
- eventually reaches 0/1.

Material tag: `c1_dependency_delta`

---

# 4. C2 Assessment Family — U → M

## Construct

Can the learner demonstrate several relevant components concerning:

- recursive dependency;
- repeated subproblems;
- repeated computation;
- storing a solved result;
- lookup/reuse;
- shared cache state?

Full causal integration is not required for C2 success.

## Equivalence envelope

Each form should elicit multiple distinct relevant observations.

The form should not require a polished C3 causal explanation.

---

## C2-A1 — Identify repeated subproblems and stored information

Consider this partial call structure:

```text
fib(6)
├── fib(5)
│   ├── fib(4)
│   └── fib(3)
└── fib(4)
```

**Question**

Identify one Fibonacci subproblem that appears more than once in the structure. If the program does not remember previous results, what happens when that subproblem is encountered again? What information could be stored after the first completed calculation?

### Hidden scoring context

Expected components:

- identifies `fib(4)` as repeated;
- repeated request can cause recomputation;
- can store mapping such as `4 → 3`.

Material tag: `c2_tree_alpha`

---

## C2-A2 — Read an execution log

A naive recursive Fibonacci program produces part of this execution log:

```text
start fib(4)
start fib(3)
start fib(2)
...
finish fib(3) = 2
...
start fib(3)
...
```

**Question**

What relevant pattern do you notice in the log? Name at least two pieces of information a memoized version would need in order to reuse work from the first `fib(3)` calculation.

### Hidden scoring context

Expected several of:

- same `fib(3)` requested again;
- first result is 2;
- mapping from input 3 to result 2;
- later lookup/check;
- shared/accessibly retained storage.

Material tag: `c2_trace_beta`

---

## C2-A3 — Separate useful cache components

Suppose a learner says:

> “To memoize Fibonacci, I only need to create an empty dictionary.”

**Question**

What additional actions or properties are needed before that dictionary can actually help with repeated Fibonacci subproblems? Give at least three relevant components.

### Hidden scoring context

Any three or more relevant components such as:

- store computed result by input;
- check whether input is already present;
- return/reuse stored result;
- share the relevant cache across recursive calls;
- repeated subproblem exists.

Do not require full causal integration.

Material tag: `c2_components_gamma`

---

## C2-A4 — Shared versus separate cache state

Consider two designs.

**Design A**

Every recursive call receives the same `memo` mapping.

**Design B**

Every recursive call starts by creating a new empty `memo` mapping for itself.

**Question**

List the important differences this creates for stored Fibonacci results. In your answer, mention repeated subproblems, availability of earlier results, and possible reuse.

### Hidden scoring context

Expected multiple relevant pieces:

- repeated subproblems can occur in either;
- A allows previous results to remain available across branches;
- B loses that sharing;
- A can support reuse.

Full C3 chain is welcome but not required.

Material tag: `c2_scope_delta`

---

# 5. C3 Assessment Family — M → R

## Construct

Can the learner independently integrate:

```text
repeated subproblem
→ repeated computation
→ storage
→ lookup/reuse
→ avoided recursive recomputation
```

while recognizing that the Fibonacci recurrence itself is unchanged?

## Equivalence envelope

All forms must require causal integration rather than keyword listing.

They should not require tabulation, another algorithmic domain, or formal complexity notation.

---

## C3-A1 — Explain the memoized execution mechanism

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

**Question**

During the calculation of `fib(6)`, some smaller Fibonacci values are requested more than once. Explain what happens the first time one of those repeated values is calculated and what happens when the same value is requested later. Use this to explain why the function performs less repeated recursive work than the ordinary recursive version. Also state whether memoization changes the Fibonacci recurrence itself.

### Hidden scoring context

Expected integrated chain:

- repeated subproblem;
- first computation;
- stored mapping;
- later lookup;
- reuse;
- avoided recursive expansion;
- recurrence unchanged.

Material tag: `c3_code_alpha`

---

## C3-A2 — Evaluate two explanations

Student A says:

> “Memoization makes recursive Fibonacci faster because it changes the Fibonacci formula so fewer previous numbers are needed.”

Student B says:

> “The Fibonacci formula stays the same. After a smaller Fibonacci problem has been solved, its result can be stored. If the same subproblem is requested again, that result can be reused rather than recursively calculated again.”

**Question**

Which explanation better describes memoized recursive Fibonacci? Explain why, making clear how repeated subproblems, stored results, and later recursive calls are connected.

### Hidden scoring context

Expected:

- B;
- causal integration;
- explicitly rejects recurrence-changing misconception.

Material tag: `c3_explanations_beta`

---

## C3-A3 — Compare second-request behavior

During one evaluation, `fib(4)` has already been calculated and returned 3.

Later in the same overall recursive computation, another branch requests `fib(4)`.

**Question**

Compare what happens at this second request in:

1. ordinary recursive Fibonacci with no retained results; and
2. recursive Fibonacci using a shared memoization cache.

Explain how the difference arises and why it reduces repeated work. State what remains unchanged about the Fibonacci rule.

### Hidden scoring context

Expected:

- naive version recursively recomputes;
- memoized version checks and reuses stored 3;
- avoids recursive expansion;
- recurrence unchanged.

Material tag: `c3_second_request_gamma`

---

## C3-A4 — Complete the mechanism conceptually

```python
def fib(n, cache):
    if n <= 1:
        return n

    # cache-related operation(s) omitted here

    result = fib(n - 1, cache) + fib(n - 2, cache)

    # cache-related operation(s) omitted here

    return result
```

**Question**

Describe the cache-related operations needed for this function to genuinely use memoization. Explain where they belong in the recursive process and how they work together to prevent repeated subproblems from being fully recomputed.

### Hidden scoring context

Expected:

- lookup before recursive expansion;
- return cached result on hit;
- store computed result after solving;
- shared cache;
- causal link to avoiding recomputation.

Material tag: `c3_mechanism_delta`

---

# 6. C4 Assessment Family — R → EA

## Construct

Can the learner reason from memoization invariants in an unfamiliar Fibonacci situation rather than matching memorized canonical code?

Required evidence should involve abstraction, diagnosis, derivation, or cache-state prediction.

## Equivalence envelope

Forms must:

- remain within recursive Fibonacci + memoization;
- use unfamiliar or transformed surface structure;
- require mechanism-based reasoning;
- avoid simply asking for the standard memorized memoized-Fibonacci function.

---

## C4-A1 — Diagnose ineffective cache lifetime

```python
def fib(n):
    memo = {}

    if n in memo:
        return memo[n]

    if n <= 1:
        return n

    result = fib(n - 1) + fib(n - 2)
    memo[n] = result
    return result
```

**Question**

This function contains a dictionary and both checks and stores values. Does it nevertheless achieve useful memoization across the recursive computation? Explain your answer from the underlying mechanism, and state what property would need to change for repeated subproblems to reuse earlier results.

### Hidden scoring context

Expected abstraction:

- recognizes fresh `memo` per call;
- dictionary presence/check/store are insufficient without shared lifetime;
- derives need for shared relevant cache;
- recurrence itself is not the issue.

Material tag: `c4_scope_alpha`

---

## C4-A2 — Reason from an initial cache state

Suppose a correct memoized recursive Fibonacci function uses a shared cache and begins a call to `fib(7)` with:

```text
cache = {
    2: 1,
    3: 2,
    4: 3
}
```

**Question**

Without writing the entire execution trace, reason about which of these stored values can be reused and which larger Fibonacci results will still need to be computed before `fib(7)` is returned. Explain how the cache is expected to grow and why.

### Hidden scoring context

Expected:

- 2/3/4 are immediately reusable when requested;
- larger needed values 5, 6, 7 must still be solved (assuming not already cached);
- resulting values can be added;
- reasoning based on cache-state mechanism rather than memorized exact trace.

Material tag: `c4_state_beta`

---

## C4-A3 — Evaluate a different but valid organization

Consider:

```python
def fib(n, memo):
    if n <= 1:
        return n

    if n not in memo:
        left = fib(n - 1, memo)
        right = fib(n - 2, memo)
        memo[n] = left + right

    return memo[n]
```

**Question**

This code is organized differently from the common pattern that begins with `if n in memo: return memo[n]`. Does it still implement the same memoization mechanism for non-base Fibonacci values? Explain which underlying invariants are preserved and identify any relevant boundary or assumption.

### Hidden scoring context

Expected:

- yes for non-base values under a shared `memo`;
- lookup/conditional prevents repeat computation;
- newly solved values stored;
- recursive calls share memo;
- base cases may be handled directly rather than cached;
- recurrence preserved.

Material tag: `c4_equivalent_gamma`

---

## C4-A4 — Derive requirements from principle

A programmer wants to write a memoized recursive Fibonacci function but does not want to copy a memorized implementation.

**Question**

State the essential rules their recursive function must satisfy for memoization to genuinely prevent redundant Fibonacci subproblems from being recursively solved again. Your answer should distinguish essential mechanism from incidental choices such as exact variable names or whether base cases are also stored.

### Hidden scoring context

Expected abstraction:

- correct recurrence/base logic;
- shared/accessible stored state;
- consistent input→result identity;
- lookup before redundant recursive expansion;
- return reuse on hit;
- store newly solved values;
- recognizes syntax/variable names/base-case caching as incidental.

Material tag: `c4_derive_delta`

---

# 7. Selection rule

For a given transition:

```text
eligible forms
    =
active forms in target family
    -
forms already shown in this session
```

The runtime should select randomly among eligible forms.

Pedagogy identity is not a selector input.

---

# 8. POC capacity

Each transition contains four forms.

The protocol permits at most three post-intervention assessments.

Therefore:

```text
available forms       = 4
maximum consumed      = 3
reserve               = 1
```

If a later design adds a pre-transition diagnostic, assessment capacity must be reconsidered rather than silently consuming the reserve.
