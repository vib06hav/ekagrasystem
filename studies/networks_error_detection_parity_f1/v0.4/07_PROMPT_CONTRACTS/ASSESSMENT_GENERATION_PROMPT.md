# Executable assessment-realization contract — v0.4

**Input per MCQ:** one FULLY RESOLVED specific MCQ slot from `assessment_families.yaml`; verified generated scenario and declared assumptions; independent computed true proposition and three misconception-target meanings; complexity constraints. **Never** a v0.3 fixed stem or correct display letter. Model may realize text, NOT independently decide what is correct.

```text
Write a clear F1 parity multiple-choice item for this PRECISE assessment role.
Assessed ability: <SLOT_SCIENTIFIC_PURPOSE_AND_SOLO_EVIDENCE>.
Permitted instance and factual assumptions: <FROZEN_GENERATED_SCENARIO>.
Independently verified truth: <ORACLE_CONCLUSIONS>.
Intended one correct proposition: <TRUE_PROPOSITION_MEANING>.
Three scientifically distinct wrong proposition meanings: <DISTRACTOR_MEANINGS>.
Required conceptual boundaries: <SLOT_EQUIVALENCE_AND_F1_LIMITS>.

Write a NEW natural stem and four alternatives appropriate to this exact instance.
Express the supplied one-true/three-false meanings; do not change their truth,
create an unstated assumption, reveal another answer, or make two defensible options.
Return each proposed option with a stable semantic identity, not an answer letter.
Do NOT propose a correct_index, assert your own oracle, copy an example verbatim,
or use previous participant or Tutor information.
```

**Authoritative post-processing:** Run mathematical oracle on actual instance; run semantic review of visible stem and each option; reject/review uncertainty. Randomize displayed option positions independently, bind the correct option's stable meaning to its new *instance-only* displayed index, privately freeze exact question, choices and key. No literal text equality requirement. A model cannot prove its own option semantics by returning matching IDs. For SUBJECTIVE slot, generate a task that elicits the item-specific target evidence and valid scenario; do not embed expected answer or rubric in question shown to learner.
