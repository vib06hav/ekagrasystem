# 05 — POC Protocol Configuration

**Status:** Lightweight experiment wiring, not a content pack  
**Version:** content draft v0.1

---

# 1. Purpose

This document defines the current POC control flow.

It does not define:

- knowledge;
- pedagogy;
- assessment content;
- Judge criteria;
- LLM provider behavior.

The backend owns executable state-machine logic.

This configuration states which supported behavior the POC uses.

---

# 2. Formal states and transitions

Initial formal state:

```text
P
```

Transition order:

```text
C1 P→U
    ↓
C2 U→M
    ↓
C3 M→R
    ↓
C4 R→EA
```

Formal progression occurs one transition at a time.

If a C2 assessment is judged structurally R, C2 succeeds but the formal state advances to M; C3 remains independently assessed.

---

# 3. Pedagogy set

The available pedagogies are:

```text
P1 Worked-Example Instruction
P2 Guided Questioning
P3 Contrasting-Case Instruction
```

At the start of each transition, the three are randomly ordered/sampled without replacement.

A pedagogy may appear at most once on that transition in the current POC.

---

# 4. Attempt behavior

For one transition:

```text
choose unused pedagogy
        ↓
deliver intervention
        ↓
fresh independent assessment
        ↓
judge response
        ↓
deterministic success decision
```

If success:

```text
advance one formal SOLO transition
reset pedagogy pool for the next transition
reset transition-local assessment exposure
continue
```

If failure and an unused pedagogy remains:

```text
remain at same formal state
record prior-attempt history
select another unused pedagogy
deliver next attempt
```

If all three pedagogies have failed:

```text
mark transition unresolved
stop progression
```

---

# 5. No renewed cycle

The current POC does **not** start a new shuffled cycle after all three pedagogies have been exhausted.

Maximum intervention attempts per transition:

```text
3
```

---

# 6. Assessment behavior

Each transition has four assessment forms.

After every intervention:

- select from the current transition family;
- exclude forms already seen in the session;
- choose randomly among eligible forms;
- do not use pedagogy identity in the selection.

Maximum post-intervention assessments per transition:

```text
3
```

Reserve forms per transition:

```text
1
```

The harness must not silently reuse a form if the eligible pool is empty.

---

# 7. Intervention history

Attempt 1 on a transition receives no prior-attempt history.

Attempt 2 receives a structured summary of Attempt 1.

Attempt 3 receives structured summaries of Attempts 1 and 2.

History may include:

- pedagogy already used;
- content/material already exposed;
- learner evidence;
- misconceptions;
- previous assessment outcome.

History must not include:

- future assessment content;
- hidden answer keys;
- hidden Judge reasoning.

---

# 8. Judge blindness

Judge input must not contain:

- pedagogy just used;
- previous pedagogies;
- Tutor conversation;
- attempt number as evaluative context;
- previous failures;
- next pedagogy.

The selected assessment prompt and hidden item-specific scoring context are allowed and required.

---

# 9. Intervention completion vs transition success

Intervention completion means:

> the instructional attempt has ended because its completion condition or hard budget was reached.

It does not mean:

> the learner achieved the transition.

Only:

```text
fresh assessment
    +
Judge evidence
    +
deterministic rubric rule
```

can produce a successful transition outcome.

---

# 10. POC state machine

```text
START
  │
  ▼
Formal state P
  │
  ▼
C1
  │
  ▼
random unused pedagogy
  │
  ▼
INTERVENTION
  │
  ▼
FRESH ASSESSMENT
  │
  ▼
JUDGE
  │
  ▼
SUCCESS?
 ┌┴───────────────┐
 │                │
YES              NO
 │                │
 ▼                ▼
advance       unused pedagogy?
 │              ┌─┴─────────┐
 │             YES          NO
 │              │            │
 │              ▼            ▼
 │        next attempt    UNRESOLVED
 │        with history       STOP
 │
 ▼
next transition
```

---

# 11. Session completion

A session completes successfully when C4 is successfully achieved.

Possible terminal outcomes:

```text
COMPLETED_EA
UNRESOLVED_C1
UNRESOLVED_C2
UNRESOLVED_C3
UNRESOLVED_C4
ABORTED / TECHNICAL_FAILURE
```

Exact machine labels are implementation details.

---

# 12. Explicitly deferred protocol questions

Not frozen in this POC content draft:

- whether there is an initial pre-transition diagnostic before the first intervention;
- exact turn/time budget for each intervention;
- whether technical LLM failures consume an experimental attempt;
- exact retry policy for malformed model output.

Those belong in the later technical/runtime design and must be decided before a real participant study.
