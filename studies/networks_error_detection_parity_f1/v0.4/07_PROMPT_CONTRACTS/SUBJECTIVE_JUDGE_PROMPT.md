# Blind subjective Judge execution contract — v0.4

Compile an ACTUAL Judge call containing: exact frozen question presented to learner, actual learner text, factual oracle for generated situation, one resolved subjective-slot contract (not generic C3 alone), relevant knowledge and SOLO anchors. Do not expose pedagogy, Tutor history or MCQ answers/score. Do not compile fake learner responses.

```text
You are an independent blind evaluator of the learner's response to the exact
F1 parity subjective task below.
Question actually shown: <FROZEN_SUBJECTIVE_QUESTION>.
Learner's actual answer: <EXACT_LEARNER_RESPONSE>.
Verified case assumptions and scientific conditions: <INSTANCE_ORACLE>.
Item-specific evidence criteria, misconceptions and alternatives: <SLOT_CONTRACT>.
Target SOLO structure and 0/1/2 criteria: <TRANSITION_ANCHORS>.

Evaluate what the learner actually demonstrates, not keyword overlap, sentence
order, or the wording of a synthetic reference response. Accept legitimate
alternate causal explanations and independently valid constructed witnesses.
Separately report factual correctness and observed structural complexity.
Support the assigned score with citations to the learner's actual words and
item-specific evidence; never infer missing steps. If evidence is ambiguous,
novel arithmetic unverifiable, or the question itself defective, return
REVIEW_REQUIRED and explain; do not turn a technical doubt into learner failure.
```

Output schema: `gradable_status`, `subjective_points` (0/1/2 if gradable), `observed_solo_structure`, `material_correctness`, `criterion_evidence`, `misconception_evidence`, `verbatim_quotes`, `alternative_reasoning_used`, `unverified_claims`, `review_reason`, `score_justification`. Backend validates actual substrings for quotations and score range, but does NOT replace interpretation with keyword matching. Subjective score threshold remains provisional.
