# Mathematical reference authority and oracle contracts

## 1. Single full-frame parity

Let data bits be d[0..n−1] and the required complete-frame parity be q, with q=0 for even, q=1 for odd. Define the transmitted check bit as `p = (sum(d) mod 2) XOR q`. The whole frame's modulo-two sum is q. For an error set E of distinct transmitted positions, receiver compliance changes by `|E| mod 2`. A pass does not mean no error. An odd count of flips is detected; even count is not, for this ONE whole-frame parity check.

## 2. Full 2D row-column even parity

For a data matrix D, append a row parity bit at the end of each row, then append a final check row containing the parity of each extended column (including the corner check). Every transmitted row and column has even parity. Flip set E yields failed rows `{r: |E ∩ row(r)| is odd}` and failed columns `{c: |E ∩ col(c)| is odd}`. One flip anywhere creates one failed row and one failed column, whose intersection identifies that position under the exactly-one-flip assumption. Two different flips cannot preserve both every checked row and column in this construction, but multiple-flip syndromes do not generally identify which bits changed. Four flips forming a nondegenerate data rectangle are invisible. Four flips in another shape need not be invisible. The classic 3×4 data / 4×5 transmitted block is a historical verified example only.

## 3. New grouped parity arrangements for C4

A scheme declares groups G[0..m−1], each with its own independently enforced check (and its own transmitted check bit); **data-only** flips form E. Group j fails iff `|E ∩ G[j]| mod 2 = 1`. A nonempty E is invisible iff EVERY checked group sees an even number of altered data positions. For 2-data-bit flips at distinct positions a and b, invisibility is equivalent to identical membership signatures across checked groups; therefore all data-only pairs are detected iff all positions have distinct signatures. An uncovered position has the all-zero signature and is invisible under a single data-only flip. A new check detects a specific previously invisible data-only E iff its subset intersects E oddly. Check-bit errors need a separately modeled error universe and are not silently included in these grouped-data rules.

## 4. Workload constraints

Original F1 restriction: no mandatory manual 1D parity counting over more than eight frame bits. For two-dimensional block reasoning, show the checked rows/columns or give syndrome facts rather than forcing a learner to count an entire 20-bit block. No fabricated increase to eleven bits because of a conversational example.

## 5. Source-of-truth qualification

These arithmetic/logic rules admit exhaustive testing on bounded cases and mathematical proof; they do not certify correctness of arbitrary generated natural-language propositions, SOLO validity or psychometric equivalence. `reference_parity_oracle.py` provides an independent, runnable numerical reference. Codex should implement scenario generation around these functions, not hardcode test cases as runtime prompts.
