# 01 — Topic / Knowledge Pack

**Pack identity:** `python_fibonacci_memoization`  
**Version:** content draft v0.1

---

# 1. Purpose

This pack is the semantic source of truth for the POC.

It answers:

> What exactly is being learned, how is that knowledge structured, and what does P → U → M → R → EA mean for recursive Fibonacci with memoization?

Every intervention, assessment, and rubric must reference this pack rather than independently redefine the topic.

---

# 2. Topic

## Domain

Python Programming

## Topic

Recursive Fibonacci with Memoization

## Topic statement

The learner develops an increasingly structured understanding of how the Fibonacci recurrence can be expressed recursively in Python, why naive recursive evaluation repeats subproblems, and how memoization stores and reuses solved results without changing the Fibonacci recurrence.

---

# 3. Prerequisite assumptions

The learner is assumed to be able to:

- read a basic Python function definition;
- understand a function parameter;
- understand `return`;
- understand a simple `if` conditional;
- read integer literals and basic addition;
- understand that calling a function evaluates that function for a supplied input.

The study does not attempt to teach those prerequisites.

A learner who cannot interpret basic Python syntax should not automatically be treated as conceptually Prestructural in the target topic; prerequisite failure is a different issue.

---

# 4. Bounded conceptual frontier

## 4.1 In scope

The POC may teach and assess:

- Fibonacci base cases;
- the Fibonacci recurrence;
- expression of the recurrence as recursive Python computation;
- recursive dependency structure;
- repeated subproblems in naive recursive Fibonacci;
- repeated computation caused by unresolved repeated subproblems;
- storing a solved result associated with its Fibonacci input;
- checking whether a result has already been stored;
- reusing a stored result;
- shared cache state within one top-level recursive computation;
- memoized recursive Fibonacci;
- why memoization reduces redundant recursive work;
- reasoning about cache contents and cache reuse;
- recognizing whether unfamiliar recursive Fibonacci code genuinely implements memoization;
- comparing alternative but equivalent memoization organizations;
- deriving implementation requirements from the underlying memoization mechanism.

## 4.2 Out of scope

The POC does not require or intentionally teach:

- iterative Fibonacci;
- bottom-up dynamic programming;
- tabulation;
- rolling-variable / space-optimized Fibonacci;
- general dynamic-programming problem solving;
- knapsack;
- longest common subsequence;
- graph algorithms;
- formal recurrence-solving mathematics;
- asymptotic-analysis notation as a success requirement;
- Python decorators such as `functools.lru_cache`;
- persistence of caches across unrelated program runs;
- concurrency/thread-safety;
- distributed caching.

Out-of-scope material must not be introduced merely because an LLM considers it educationally useful.

---

# 5. Knowledge components

The identifiers below are stable semantic references for the other packs.

## K1 — Fibonacci base cases

`fib(0) = 0` and `fib(1) = 1` provide the terminating values for the recursive definition used in this POC.

## K2 — Fibonacci recurrence

For `n >= 2`:

`fib(n) = fib(n - 1) + fib(n - 2)`.

## K3 — Recursive Python representation

A Python function can express K2 by recursively requesting `fib(n - 1)` and `fib(n - 2)` and using K1 to terminate recursion.

## K4 — Recursive dependency structure

Computing a larger Fibonacci value creates dependent computations for smaller Fibonacci inputs.

## K5 — Repeated subproblems

During naive recursive evaluation, the same smaller input such as `fib(3)` can be requested from more than one branch of the computation.

## K6 — Repeated computation

If earlier solved results are not retained, a repeated request for the same subproblem causes that subproblem's recursive computation to be performed again.

## K7 — Cache mapping

A computed Fibonacci result can be retained in a mapping from the subproblem input to its result, conceptually:

`n → fib(n)`.

The concrete Python representation may vary, but the input/result association is essential.

## K8 — Cache lookup and reuse

When a Fibonacci input is requested again, the function can check whether a result for that input is already available and return/reuse it instead of recursively solving the same subproblem again.

## K9 — Shared cache state

For reuse to occur across recursive branches within a top-level computation, the recursive calls must have access to the same relevant cache state. Reinitializing an empty cache independently for every recursive call defeats cross-call reuse.

## K10 — Integrated memoized-recursion mechanism

Memoized recursive Fibonacci combines:

- the same Fibonacci recurrence;
- recursive decomposition;
- result storage;
- lookup before repeated recursive expansion;
- and reuse of already solved subproblems.

Memoization changes execution/reuse behavior; it does not redefine Fibonacci.

## K11 — Efficiency mechanism

The reduction in redundant work arises because already solved cacheable Fibonacci subproblems do not need to be recursively solved again when requested later within the same shared-cache computation.

The POC does not require formal Big-O notation to demonstrate this component.

## K12 — Memoization invariants across implementations

Different recursive Fibonacci implementations can organize syntax differently while implementing the same memoization mechanism if they preserve essential invariants:

- subproblems are identified consistently;
- previously stored results can be consulted before redundant recursive expansion;
- newly solved results are stored correctly;
- recursive calls participate in the relevant shared cache;
- the Fibonacci recurrence remains correct.

## K13 — Cache-state reasoning

Given an input and a stated initial cache, the learner can reason about which Fibonacci results are already reusable, which values must still be computed, and how the cache changes as the recursive computation proceeds.

## K14 — Derivation/evaluation from mechanism

The learner can use the memoization invariants to derive, diagnose, or evaluate an unfamiliar recursive Fibonacci implementation rather than relying on memorized canonical code.

---

# 6. Knowledge relations

## R1 — Base cases + recurrence enable recursive Fibonacci

K1 and K2 jointly support K3.

A recursive implementation needs both the recurrence and a terminating base condition.

## R2 — Recursive dependency can produce repeated subproblems

K4 can generate K5 because branching recursive dependencies can reach the same smaller Fibonacci input from different branches.

## R3 — Repeated subproblems cause repeated computation when results are not retained

K5 combined with absence of retained results produces K6.

## R4 — Solved results can be associated with their subproblem

K7 provides the storage relation required for later reuse.

## R5 — Lookup + shared cache enable reuse

K8 and K9 jointly explain how a later request can reuse a previously solved result.

## R6 — Storage and reuse integrate with recursion to form memoization

K7, K8, K9 and the recursive recurrence integrate into K10.

## R7 — Memoization reduces redundant recursive work

K10 explains K11: because already solved subproblems can be reused, repeated recursive evaluation of those subproblems can be avoided.

## R8 — The recurrence is invariant under memoization

K2 remains true in both naive recursive Fibonacci and memoized recursive Fibonacci.

Memoization changes evaluation strategy, not the mathematical Fibonacci relationship.

## R9 — Cache scope affects effectiveness

K9 is necessary for practical reuse across recursive branches. If a fresh empty cache is created independently inside every recursive call, stored results are not shared in the needed way.

## R10 — Multiple code organizations can realize the same mechanism

K12 abstracts over specific syntax: equivalent implementations may differ in ordering or representation while preserving the essential mechanism.

## R11 — Cache state can be predicted from mechanism

K13 follows from understanding storage, lookup, reuse, and cache scope.

## R12 — Mechanism supports derivation and diagnosis

K12 and K13 support K14: the learner can reason about unfamiliar code and determine whether it really memoizes.

---

# 7. Misconceptions / partial models

## M1 — One-predecessor Fibonacci

The learner believes recursive Fibonacci needs only one previous Fibonacci value.

**Conflicts with:** K2.

## M2 — Base cases create the efficiency improvement

The learner attributes the reduction in repeated work to the base cases rather than reuse of solved subproblems.

**Conflicts with:** K5, K6, K11.

## M3 — Repeated occurrences are different problems

The learner believes two requests for the same `fib(k)` are fundamentally different subproblems and therefore cannot reuse the same result.

**Conflicts with:** K5, K7, K8.

## M4 — Memoization changes the Fibonacci recurrence

The learner claims memoization changes the mathematical definition of Fibonacci.

**Conflicts with:** K2, K10, R8.

## M5 — Cache stores calls rather than computed results

The learner treats the cache as storing pending function-call objects rather than a usable association between an input and its solved Fibonacci value.

**Conflicts with:** K7.

## M6 — Dictionary presence alone equals memoization

The learner believes any function containing a dictionary is memoized even if the dictionary is never checked for reusable results.

**Conflicts with:** K8, K10, K12.

## M7 — Cache lookup after full recomputation is sufficient

The learner believes it is enough to check the cache only after recursively solving the subproblem again.

**Conflicts with:** K8, K11, K12.

## M8 — Fresh cache per recursive call still provides full memoization

The learner believes every recursive call may initialize an independent empty cache and still achieve reuse across branches.

**Conflicts with:** K9, R9.

## M9 — Memoization means avoiding recursion entirely

The learner believes a memoized recursive solution stops being recursive.

**Conflicts with:** K10.

## M10 — One canonical code shape defines memoization

The learner believes only the memorized dictionary-based code arrangement counts as memoization, even if another implementation preserves the same essential mechanism.

**Conflicts with:** K12, K14.

---

# 8. SOLO state definitions

## P — Prestructural

The learner does not yet demonstrate a usable conceptual relationship connecting the Fibonacci definition to recursive computation.

Possible evidence includes:

- irrelevant statements;
- guessing;
- treating recursion and Fibonacci as unrelated terms;
- materially incorrect dependence such as “`fib(n)` is just `fib(n-1)`”;
- code fragments with no usable recurrence relation.

Prestructural does not mean “knows nothing about Python.” It refers to organization within this bounded conceptual frontier.

---

## U — Unistructural

The learner demonstrates one central usable structure:

> Fibonacci values depend on the two previous Fibonacci values, and this dependence can be represented recursively with terminating base cases.

The learner may correctly understand K1/K2/K3 without yet recognizing the larger repeated-subproblem and memoization structure.

A typical U response can correctly explain or recognize the basic recursive definition but does not yet demonstrate several distinct relevant ideas about redundant recursion and caching.

---

## M — Multistructural

The learner demonstrates several relevant components of recursive Fibonacci and memoization but does not yet reliably integrate them into one causal mechanism.

The learner may correctly recognize several of:

- recursive dependencies;
- repeated subproblems;
- repeated computation;
- storing results;
- cache lookup;
- reuse;
- shared cache.

However, these ideas may appear as a list or loosely connected observations.

Example profile:

> “Recursive Fibonacci repeats calls. A dictionary can store results. You can check the dictionary and reuse values.”

This is relevant and multi-part, but the causal structure may still be incomplete.

---

## R — Relational

The learner integrates the relevant components into a coherent explanation of memoized recursive Fibonacci.

A relational account links:

```text
branching recursive dependencies
        ↓
same subproblem requested repeatedly
        ↓
without retained result it is recomputed
        ↓
first solved result is stored
        ↓
later request checks shared cache
        ↓
stored result is reused
        ↓
redundant recursive evaluation is avoided
```

The learner also understands that the Fibonacci recurrence remains unchanged.

The central distinction from M is organization and integration, not simply additional vocabulary.

---

## EA — Extended Abstract

The learner can reason from the underlying memoization mechanism beyond the canonical example/code shape.

Within this deliberately narrow topic, EA may be evidenced by the ability to:

- identify whether unfamiliar recursive Fibonacci code genuinely implements memoization;
- diagnose why superficially “cached” code fails to reuse results;
- reason correctly about cache scope/lifetime;
- predict cache behavior from an arbitrary valid input and stated initial cache;
- explain why different code organizations implement the same mechanism;
- derive the requirements of a correct memoized recursive implementation from principle rather than recalling one memorized program.

EA is not defined as merely answering a numerically larger or syntactically harder Fibonacci question.

---

# 9. Transition definitions

# C1 — P → U

## Structural change

```text
no usable recursive Fibonacci model
        ↓
one coherent central relationship:
Fibonacci recurrence ↔ recursive computation
```

## Assumed at entry

Only prerequisites.

No reliable topic-level understanding is assumed.

## Primary target knowledge

- K1
- K2
- K3

## Primary target relation

- R1

## Relevant misconceptions

- M1

## Not required for C1 success

- repeated-subproblem analysis;
- caching;
- memoization;
- efficiency mechanism;
- cache-state abstraction.

The intervention should not force future-transition knowledge into C1.

---

# C2 — U → M

## Structural change

```text
one central recursive model
        ↓
multiple relevant components concerning
recursive dependency, repeated work, and result reuse
```

## Assumed at entry

- K1
- K2
- K3
- R1

## Primary target knowledge

- K4
- K5
- K6
- K7
- K8
- K9

## Target structural character

The learner should be able to recognize multiple relevant components, even if they are not yet integrated into a complete causal explanation.

## Relevant misconceptions

- M2
- M3
- M5
- M6
- M8

## Not required for C2 success

The learner is not yet required to produce the full integrated causal mechanism of K10/K11.

A learner who does produce that mechanism may be observed above target, but C2 remains the formal transition under test.

---

# C3 — M → R

## Structural change

```text
multiple correct but partly separate pieces
        ↓
one integrated causal memoization mechanism
```

## Assumed at entry

The learner is expected to have access to:

- K1 through K9 at least as separate relevant components.

## Primary target knowledge

- K10
- K11

## Primary target relations

- R2
- R3
- R4
- R5
- R6
- R7
- R8
- R9

## Critical integration

The learner must connect:

```text
repeated subproblem
→ otherwise recomputed
→ solved result stored
→ later lookup/reuse
→ avoided recursive recomputation
```

while preserving the Fibonacci recurrence.

## Relevant misconceptions

- M3
- M4
- M5
- M6
- M7
- M8
- M9

---

# C4 — R → EA

## Structural change

```text
understands one integrated memoized-recursion mechanism
        ↓
reasons from the mechanism across unfamiliar
but equivalent Fibonacci implementations and cache states
```

## Assumed at entry

Integrated K1–K11.

## Primary target knowledge

- K12
- K13
- K14

## Primary target relations

- R9
- R10
- R11
- R12

## Abstraction targets

The learner should be able to:

- distinguish essential memoization invariants from incidental syntax;
- evaluate unfamiliar recursive Fibonacci implementations;
- diagnose broken cache sharing/lookup logic;
- reason about cache contents and reuse;
- derive a correct mechanism from principle.

## Relevant misconceptions

- M6
- M7
- M8
- M10

## Important boundary

C4 transfer remains within the bounded topic of recursive Fibonacci + memoization.

The learner is not required to transfer the mechanism to knapsack, shortest paths, or another algorithmic domain.

---

# 10. Canonical transition slices

## C1 slice

**Expected before:** prerequisites only  
**Target:** K1, K2, K3; R1  
**Structural goal:** one usable recurrence-to-recursion relationship  
**Future knowledge:** K4–K14

## C2 slice

**Expected before:** K1–K3; R1  
**Target:** K4–K9 as multiple relevant components  
**Structural goal:** several relevant pieces present  
**Future integration:** K10–K14

## C3 slice

**Expected before:** K1–K9 available as components  
**Target:** K10, K11 and integration relations R2–R9  
**Structural goal:** coherent causal memoization mechanism  
**Future abstraction:** K12–K14

## C4 slice

**Expected before:** integrated K1–K11  
**Target:** K12–K14; R9–R12  
**Structural goal:** abstraction across unfamiliar implementations/cache states

---

# 11. Ownership boundary

This pack owns:

- what the topic means;
- what is in and out of scope;
- what the KCs mean;
- what the relations mean;
- what the misconceptions mean;
- what P/U/M/R/EA mean;
- what C1/C2/C3/C4 mean.

It does not own:

- how a pedagogy teaches;
- actual assessment questions;
- Judge prompting;
- randomization;
- attempt sequencing;
- LLM provider/model configuration.
