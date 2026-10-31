# F1 v0.4.1 typed scenario-policy companion — execution semantics

**Authority and status:** Candidate scientific-to-engineering bridge derived from the 64 authored v0.4 slot contracts. It does **not** replace `assessment_families.yaml` or change SOLO, progression or the F1 numerical scope. It converts *scenario-selection* requirements into typed constraints, not into prewritten questions. Every item retains its full prose scientific purpose, misconception and evidence requirements from v0.4. Review the flagged interpretation before treating this as approved science.

## Separation of concerns

1. **Backend-owned scientific identity:** The backend selects an item contract, resolves its typed scenario policy by ID, and stores that identity. It must never require the Tutor, question writer, semantic reviewer or Judge to echo an arbitrary contract ID. ID lookup by backend is legitimate; `if slot_id == ...` branches in the sampler are not.
2. **Reusable mathematical sampler:** A small library implements the supported case families and generic predicates below. It samples variable parameters, computes independent oracle outputs and verifies every declared predicate. It rejects an unsatisfiable policy instead of faking or substituting a generic scenario.
3. **Public projection:** A reviewed task-specific projection includes only the inputs needed to answer the question. Do not serialize entire scenario/oracle objects to the learner. The generator receives verified facts as private guidance, not all private facts to reproduce verbatim. The semantic reviewer receives relevant truth and the output text.
4. **LLM language and meaning:** Tutor, assessment writer, independent semantic reviewer and blind Judge perform their language/interpretation roles. The mathematical verifier never substitutes for semantic review. Parsing/formatting errors are technical retries or review holds, not learner failures.

## Generic case-family operators

- `sender_parity`: sample data length 3–7, data bits, and stated `convention` (even/odd); calculate appended check bit from parity rule. No fixed bit pattern, ones count or option index.
- `receiver_parity`: generate full valid frame; if `receiver_state=invalid`, alter the full received frame so the stated check fails; `sample_valid_or_invalid` samples both outcomes across instances. A passing receiver check is not evidence of zero flips.
- `single_flip_1d`: generate valid full frame and exactly one flip from the specified universe; recompute pass/fail.
- `multiflip_1d`: generate distinct flips of requested count; `odd_bounded` means randomly choose a feasible **positive odd** count, `even_nonzero_bounded` a feasible **positive even** count, within the available permitted universe and F1 cap. `must_include_check_bit` restricts selected sets to contain exactly/at least one check bit as stated (single global parity provides one).
- `checkbit_1d`: generate the valid frame with an explicitly marked check-bit position; `position_universe=check_bit_only` requires a check-bit flip; `alter_check_bit=false` means only mark it and do not alter.
- `full2d_single`, `full2d_pair`, `full2d_rectangle`, `full2d_checkbit`, `full2d_four_compare`, `full2d_compare`: generate a valid full row+column parity block with corner included. Check-bit coordinates are part of the transmitted grid. For `full2d_pair`, choose two distinct legal positions. For `same_row_distinct_columns`, both must be **data cells** in the same row with unequal columns. `nondegenerate_rectangle` uses exactly four distinct DATA cells in two rows and two columns; `non_rectangle` uses four distinct DATA cells not forming such a rectangle. Recompute row/column check syndromes with the oracle. `full2d_compare` additionally declares which check scheme is applied to the matched data/error universe; NEVER compare nonmatching check-bit error universes.
- `grouped_checks`: generate 2–3 independently declared nonempty parity-check subsets over at most 8 data positions; allow overlaps and uncovered positions when permitted. Check that each group's parity bit is correct.
- `grouped_two_flip`: generate/check two distinct DATA flips. `pair_signature_relation=sample_equal_or_different` means sample from **existing feasible** equal/different signature pairs with varied outcomes across instances; do not force both to exist in every scheme unless the task requires comparison. `quantified_check=all_distinct_data_pairs` requires exhaustive evaluation of all distinct unordered pairs in that bounded data universe, with a witness if the universal detection claim fails.
- `grouped_uncovered`: construct a scheme with at least one data position belonging to no group. With `position_universe=uncovered_data_positions`, select the flipped position from that set.
- `grouped_evasion`: construct and oracle-verify a **nonempty** data-only flip set whose intersection with each checked group is even. It may vary in size/positions; group map and error universe are bounded and explicit.
- `grouped_add_check`: use a scheme and a specific existing witness. Add an independently described additional group. `must_cover_witness` means its overlap with the witness has odd cardinality (so the new check detects it); `sample_detects_or_not` permits odd or even witness overlap, with oracle verification. Never claim a new check guarantees detection of every possible error.

## Shared parameter and predicate definitions

- `convention`: `even`, `odd`, `sample_even_or_odd`; a single generated case must declare the sampled value explicitly.
- `flip_count`: positive integer or `odd_bounded`, `even_nonzero_bounded`, `sample_bounded_data_flips`, `nonempty_even_overlap_witness`. In the latter cases, **sample first**, then verify with the independent oracle; those labels are not output sentences or returned IDs from an LLM.
- `position_universe`: `data_bits_only`, `transmitted_full_frame`, `data_cells`, `transmitted_full_grid`, `check_bit_only`, `full2d_check_cells`, `uncovered_data_positions`. A flip may only target positions in this declared universe.
- `check_cell_kind=sample_row_column_corner`: select a transmitted check-bit coordinate from one of row-check, column-check, or corner-check categories; sample among supported categories.
- `false_length_claim`: include a mistaken peer claim that frame length determines validity; generate an oracle-checked counterexample, without leaking the outcome to learner.
- `contrast_length_vs_ones`: accept only sampled frames whose check-bit truth differs from the answer a length-parity shortcut would suggest. This is an authored C1-A4 diagnostic requirement, not a fixed number of bits or ones.
- `forbid_unique_two_error_inference`: any learner-facing task must not assert that arbitrary two-flip syndrome uniquely identifies both flip locations.
- `group_map=fresh_nonempty_subsets`, `must_have_uncovered_position`: variable membership map; acceptance verified by checking subset nonemptiness and uncovered set, respectively.
- `require_distinct_data_positions=3`: the generated scheme must include at least three data positions with an explicit membership signature per position.

### Cross-case relations

- `independent_cases`: sample the cases independently, declaring all their separate assumptions.
- `same_valid_grid_distinct_error_patterns`: use the **same full 2D valid block** for both cases; one error set forms a rectangle and the other does not.
- `same_grid_same_data_flips`: hold grid and error positions fixed; apply the two explicitly different checking schemes to those positions.
- `same_data_same_error_universe`: hold data and selected data-only flip positions fixed under global single parity vs full row+column checking. Compare results on DATA errors only, not transmitted check-bit errors.
- `same_scheme_same_witness`: hold grouped-check membership map and specific flipped data set fixed, then add a check and calculate the new syndrome.

### Public/private split

`learner_fact_policy: input_facts_only` means the task-specific public projector may include (as needed for the authored task) the declared convention, unaltered data/frame values, generated membership layout, described alteration and/or statement to evaluate. It must NOT automatically include `correct_check_bit`, `correct_option`, `correct_index`, computed detection verdict, receiver syndrome, oracle witness classification, or private rubric evidence. If an item requires giving the learner a check observation as part of the *premise*, that must be explicitly justified and approved per task; do not infer it from the mere presence of the field in internal scenario JSON.

`input_plus_stated_convention` has the same privacy rule but requires explicit learner-visible parity convention.

## Minimal acceptance, **not** a new extensive Python test phase

- Schema validates all 64 source IDs, source item types, and scenario-family/operator references.
- For a handful of representative generated instances, every numeric predicate and cross-case link is checked by an oracle; 100-seed coverage is useful but not a substitute for model evaluation.
- The scientific contract's text is compiled into the relevant LLM prompts and never replaced by this terse policy mapping.
- A schema-valid but scientifically wrong realized option must be held for semantic review, never accepted because its output field or ID matches.
- Unsupported policy capability means **only that affected slot is unavailable for live trials**. Support one representative contract per transition for immediate bounded Docker live-provider experiments, then expand to all 64 without ID-specific branches.

## Explicit source interpretation to review

`C1-A1-Q1` says “sample at least two independently generated data patterns.” This likely describes generation diversity across **attempts**, not two separate data patterns within one MCQ; the companion represents it as a single-variable question family, and this interpretation is **pending scientific confirmation**. Do not make an individual question contain two patterns merely to satisfy a source-text substring.

Other subject-specific comparisons must continue to preserve the distinct scientific role in each of the 64 original contracts. This mapping does not reduce all C3 or C4 tasks to arithmetic problems; the SOLO structural evidence is in the original item/Judge packs.
