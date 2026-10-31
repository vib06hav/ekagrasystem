# EkagraAI F1 v0.4.1 — Typed scenario policies and no-model-ID boundary

This **candidate companion** fills two missing engineering-facing specifications without replacing or deleting any v0.4 scientific files:

1. `INSTANCE_POLICY_MAPPING_CANDIDATE.yaml` — 64 source contract IDs mapped to **variable, typed** scenario requirements and 81 case specifications, with mathematical bounds inherited from v0.4. The backend uses the ID to select a policy, but the sampler uses only the policy parameters and generic mathematical predicates. The LLM does **not** have to return the ID.
2. `POLICY_EXECUTION_CONTRACT.md` — definitions of the typed mathematical policy operators, comparison semantics and private/public fact separation. Prose scientific purpose and SOLO evidence remain in original v0.4 source.
3. `LLM_OUTPUT_AND_REVIEW_BOUNDARY.md` — consistent output schemas where the LLM writes actual prose but never arbitrary source IDs, answer letters, or a self-certified answer key.
4. `COVERAGE_CHECK.json` — programmatically checked IDs, types and scenario-family references; **not** a claim of scientific or live-model validation.

**Why needed:** v0.4 had 64 richly authored intent contracts, but operational requirements such as "two DATA flips in SAME row and DIFFERENT columns" were only in English. Code then branched on text substrings and slot-specific IDs. This companion provides structured predicates without hardcoded bit strings, displayed answer positions or test-specific numerical values.

**No new production activation, no executed sampler/LLM/Docker test.** The companion is a candidate bridge; engineering must implement and use it in the existing app. Any ambiguous scientific interpretation must be reviewed, not guessed, and only supported slots should be enabled for bounded live development experiments. All 64 mappings are present; early live-provider tests need not wait for every case operator to be implemented.

**Source files remain authoritative:** `08_SCIENTIFIC_YAML/assessment_families.yaml`, `scenario_rules.yaml`, `knowledge.yaml` and the other original v0.4 files. The companion adds only the machine-verifiable scenario layer and the model I/O boundary. It is explicitly not 64 hardcoded questions or 64 Python `if` branches.
