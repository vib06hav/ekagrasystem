# No model-generated IDs: proposal for safe LLM interfaces

**Underlying rule:** The backend selects `C1-A1-Q1` or another scientific contract and retains its identity, assigned scenario and oracle outcome. The model is never asked to return the internal ID, original item text or an arbitrary label as proof it complied.

## Assessment MCQ writer

For a single MCQ call, the backend compiles: (1) the slot's scientific purpose and SOLO demand, (2) a verified but fresh scenario with task-appropriate public facts, (3) independently derived true proposition and three *false misconception meanings*, and (4) boundaries. The writer returns **only**:

```json
{
  "stem": "Natural-language question about this generated scenario",
  "correct_option": "A natural rendering of the verified true meaning",
  "distractors": [
    "A natural rendering of the first false meaning",
    "A natural rendering of the second false meaning",
    "A natural rendering of the third false meaning"
  ]
}
```

The keys are uniform **schema field names**, not arbitrary values or item-specific IDs. The model may paraphrase freely. Position of `correct_option` is not a learner-visible position; after semantic review, the backend shuffles the four option strings and freezes its privately known correct position. The JSON keys do **not** establish semantic truth. If meaning changes, review rejects the item. At no point does the model choose `correct_index` or need to echo `slot_id`.

The writer must not be shown the Tutor conversation or assigned pedagogy. It may be told verified mathematics privately, but the backend must not copy that private context verbatim into the learner's stem.

## Independent semantic reviewer

Reviewer receives the **realized** stem/options, original scientific intent, independently verified facts, and the intended role of the correct option and distractors. Its output contains a review verdict (`ACCEPT`, `REVISE`, `REVIEW_REQUIRED`) and explanations, including a review of four option strings **in the same order supplied**. It does not need to reproduce option identity labels. The backend checks the fixed number of reviews and relevant supporting text; no exact-text equality or keyword rule can certify scientific equivalence.

A semantic reviewer is fallible. `REVIEW_REQUIRED`, provider errors, missing/ill-formed fields, multiple plausibly true alternatives, incorrect mathematical facts or possible answer leakage block delivery. If the review is inconclusive, use expert inspection of the specific realized item. Never grade the learner on an unverified assessment.

## Subjective writer and Judge

Subjective item writer returns only `{ "question": "..." }`, with the original SOLO evidence role and generated scenario compiled into its prompt. Judge receives the exact frozen question, the learner's response, applicable scientific evidence criteria and rubric. It returns a bounded score + observed structural evidence and uncertainty, or review-required. Internal session IDs, scientific slot IDs, and arbitrary keyword echoes must not be required from the model.

## Fault handling

A format error can trigger a small bounded technical retry. Repeated failure becomes an explicit `TECHNICAL_FAILURE`/`REVIEW_REQUIRED` state, **not** a wrong learner answer or automatic progression. The LLM must never be instructed to emit a magic readiness phrase. Actual learning and pedagogical fidelity require evaluation of real learner/model dialogue, not phrase detectors.

## Distinguish the two correct uses of identifiers

- **Good:** Backend associates the generated text with the already-selected internal contract, and uses fixed schema field names like `stem` and `correct_option`.
- **Bad:** Backend refuses a scientifically correct generated question because the LLM omitted/misspelled `C3-A2-Q1`, `M7`, `R4`, or a special option ID string.

**Status:** Implementation interface proposal; check against the provider's structured-output capabilities and existing transport. No real-provider or Docker behavior is claimed here.
