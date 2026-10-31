# Consistency validation and release gates — actually checked on v0.4 authoring output

**Status:** Authoring integrity verified by local scripts; this is NOT model-behavior or scientific validity approval.

## Executed validations

| Check | Result | Evidence |
|---|---|---|
| YAML parsing | PASS | All 7 YAML documents parsed with PyYAML |
| Assessment slot coverage | PASS | 16 blueprints × 4 contracts = 64 unique IDs, 48 MCQs, 16 subjective |
| Original blueprint identity | PASS | Four transition families and original 16 blueprint titles retained |
| Intervention completeness | PASS | 12 unique C1–C4 × P1–P3 cells |
| Contract scientific references | PASS | All blueprint K/R IDs resolve to F1 knowledge set |
| Scenario refs | PASS | Every MCQ and subjective uses an explicitly specified scenario family |
| Contract answer authority | PASS | No reusable item has fixed stem, bit string, options, `correct_index`, or fixed key |
| MCQ distractors | PASS | Each item has THREE separately authored diagnostic misconception meanings |
| Subjective content | PASS | All 16 have specific target evidence, partial/border case, mistake, alternate reasoning and 0/1/2 anchors |
| Mathematical oracle | PASS | `PASS: 36938 independent parity test assertions / cases (including exhaustive small-case enumeration)` |
| Example oracle cases | PASS | 11 computed fixture cases, explicitly nonruntime |
| Judge calibration | PASS, structural only | 20 synthetic illustrative cases, NOT human labeled |
| Provider model responses | NOT RUN | No provider credentials or actual model calls in authoring |
| Docker browser/database lifecycle | NOT RUN | Must be performed by Codex at integration Gate B |
| Semantic quality and equivalence | NOT CERTIFIED | Require generated-item review and expert calibration |
| Scientific/domain approval | NOT OBTAINED | Block real participants |

## Key logical checks and qualifications

- 1D full-frame parity tested for both even and odd conventions including parity-bit flip positions.
- Full 2D parity tested on exhaustive small grids for all single and double transmitted-bit error positions; rectangle miss checked.
- Group checks tested by exhaustive subsets for small data schemes, including equal-membership two-bit theorem.
- The historical FULL checksum scope is excluded from new study; historical IDs K10–K14, R5–R6, M10–M12 are not repurposed.
- The <=8-bit learner manual counting rule is preserved; no required eleven-bit parity problem.
- Some approved 2D conceptual cases display more total bits but use provided syndromes/check status; this must be monitored empirically for cognitive load.

## Important limitations / work for runtime acceptance

1. We did not *execute* an LLM prose generator, semantic reviewer, Tutor or Judge here. Markdown prompt contracts are fully authored but behavioral validity is untested.
2. An LLM can make a semantically false claim while returning correct IDs or valid JSON. Semantic QA is fallible; uncertain outputs must be reviewed and real item samples audited.
3. The four blueprints per transition have not been shown psychometrically equivalent or sufficient for a specific retry policy. No form-reuse policy was invented.
4. The code reference is deterministic and independent from the generative LLM, not a complete numerical scenario sampler; Codex must implement sampler and wire it in Docker.
5. Numerical ranges within the historical <=8 bound are pragmatic candidate variation envelopes, not empirically validated difficulty equivalence.
6. Human ratings are needed for C1 one-aspect thresholds, C4 class-level EA thresholds and the preserved 2/3+1/2 conjunctive progression.
7. Historical pre-v0.3 topic and blueprint themes and v0.3 scientific definitions were reconciled; every reusable item was individually re-authored as a flexible contract. Human scientific review still required.

## Release condition

Real-participant activation MUST remain blocked until scientific/domain expert review of genuine generated questions and Judge behavior; this is not a declaration of study readiness.
