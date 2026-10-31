# Independent model semantic review — v0.4

Use a distinct review call/context where feasible; the reviewer sees: specific reusable contract, exact verified generated case, oracle-derived facts, proposed learner-facing question and all four options. It does **not** receive a passed/failed learner result. Review is fallible and not formal proof.

```text
Independently compare the learner-facing item against the scientific assessment
contract and the mathematical oracle facts for THIS instance.
Determine: (1) does the stem ask the intended task, at an appropriate SOLO demand?
(2) Does each option state its assigned proposition accurately under all stated
assumptions? (3) Is exactly one option scientifically defensible and is it the
oracle-bound semantic answer? (4) Do incorrect options reflect the intended
misconceptions and remain false? (5) Does any wording ambiguity or numerical
claim require expert review? (6) Is any answer cued elsewhere in the form?

Return per-proposition assessment, evidence of any semantic mismatch, and
ACCEPT / REVISE / REVIEW_REQUIRED. Do not certify solely from matching IDs,
JSON validity, textual similarity, or identical wording. If uncertain, hold.
```

Backend can verify format, IDs, one-to-one semantic mapping and computed numeric outcomes; it must not pretend a regex proves meaning. It must block deployment of an item when substantive meaning is unverified. Corpus-level human audit still required prior to real participants.
