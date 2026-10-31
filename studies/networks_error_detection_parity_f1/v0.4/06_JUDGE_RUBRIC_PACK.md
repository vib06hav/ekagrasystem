# Flexible blind subjective Judge — v0.4 candidate



The Judge evaluates the real learner response to the **exact frozen subjective question** and the verified instance facts. A perfect canonical sentence is neither available nor required. The LLM supplies semantic interpretation and evidence; backend checks output schema and computes progression.



## Input allowlist

Exact shown subjective item, actual learner response, necessary generated scenario facts + oracle constraints, the resolved SUBJECTIVE contract for that blueprint, relevant SOLO transition and 0/1/2 anchors.



## Input denylist

Assigned pedagogy, Tutor transcript, previous attempts, MCQ answers or score, learning analytics, future protocol decisions, private participant metadata unrelated to grading.



## Scoring anchors

### C1

**0:** No usable or materially correct parity aspect in the actual question context.

**1:** At least one correct usable sender-rule or complete-frame receiver-test aspect with identifiable reasoning, not a numerical guess.

**2:** Correctly links sender choice and full-frame receiver check and appropriately interprets the actual case.



### C2

**0:** Does not provide distinct materially correct facts spanning one-dimensional and full two-dimensional parity.

**1:** At least one correct distinct property of each of 1D and 2D parity relevant to the presented task.

**2:** Multiple accurate, differentiated properties spanning both schemes, including pertinent limitations; no causal derivation required.



### C3

**0:** Facts are disconnected from the case or proposed mechanism is materially false.

**1:** A materially correct, case-linked causal chain relates checked constraint, alteration and receiver result.

**2:** A coherent and supported causal account additionally addresses a relevant limit, assumption or contrast.



### C4

**0:** Only one predicted unfamiliar result or recalled rule without derived class-level criterion.

**1:** A generally applicable correct condition is derived and applied to a justified nontrivial case or boundary.

**2:** A necessary-and-sufficient general condition, a verified nonempty witness or principled design consequence, and an explicit scope/limit.



## Meaning not keywords

Determine whether the response actually demonstrates the required structural understanding and factual constraints. Equivalent verbal explanations, mathematical or coordinate descriptions, legitimate counterexamples and unanticipated valid constructions must be credited. Do not treat word count, matching vocabulary, order of sentences, or exact reference phrasing as indicators. Do not invent unstated learner reasoning.



## Distinguish verdicts

**GRADABLE:** evidence permits score 0, 1 or 2, with cited text and explanation. **REVIEW_REQUIRED:** material ambiguity, unsupported novel numerical claim the available independent oracle cannot settle, or uncertain alternate interpretation; does not count as learner failure. **TECHNICAL_FAILURE:** missing question, malformed provider response, missing verified instance facts; no learner penalty.



## Evidence and output

Return `subjective_points`, `observed_solo_structure`, `material_correctness`, `criterion_evidence`, `misconception_evidence`, `verbatim_quotes` (actual substrings), `score_justification`, `review_reason`, `alternative_reasoning_used`, `unverified_claims`, and review status. The program must not discard required evidence to satisfy a narrower Pydantic model.



## Item-specific evidence

All 16 subjective slots have their own target evidence, borderline evidence, misconception and acceptable reasoning note; compile them into the Judge request. Shared anchors alone are not adequate.



## Calibration

Synthetic contrasts are hypotheses for human ratings, not gold truth. Run live Judge on alternative valid reasoning, wrong mechanism with correct numerical result, disconnected correct facts, borderlines and genuine C4 abstractions. Report agreement after expert ratings; no reliability claim from passing stubs.
