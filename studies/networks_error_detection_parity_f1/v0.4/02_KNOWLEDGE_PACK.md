# Authoritative F1 Knowledge Pack — v0.4 candidate

## Scope and mathematical convention
Single parity uses one appended transmitted check bit; even parity means the total number of **1s in the complete frame** is even, odd parity means odd. The receiver receives a frame, not the original unmodified message. A pass demonstrates conformity to the tested relation **only**, never proof of error-free delivery. For a clean valid frame, toggling k transmitted bits changes the check exactly when k is odd. The transmitted check bit is included in the flip universe when stated.

The full 2D scheme is the conventional **full** row-column even-parity block. Each transmitted position, including its row, column and corner check-bit positions, lies in one checked row and one checked column. A single flip causes one failing row and one failing column; exactly one flip is required to treat their intersection as the error position. Two flips are detected but cannot be assumed uniquely located from syndrome alone. A 2×2 rectangle of four **data** flips is an undetected corruption. These statements are construction-conditional.

A general group-check scheme declares subsets G₁,...,Gₘ of data positions, each with an independent parity check bit. Under **data-only** error set E, group j fails iff |E ∩ Gⱼ| is odd. A nonempty E is invisible iff all intersections are even. Under this same fixed error universe, adding a check can detect additional patterns but does not guarantee correction, nor dominance across mismatched encodings or check-bit-error classes.

### Knowledge components
**K1.** A bit can change in transmission; sender adds check bit computed from data; receiver cannot observe untransmitted original.

**K2.** A sender selects a single parity bit so that the complete transmitted frame (data plus check bit) meets the explicitly agreed even/odd number-of-ones convention; do not fix the data length or values.

**K3.** Receiver tests data and parity bit together; failure detects a violation, not the original error location or repair.

**K4.** For complete-frame single parity, every odd number of flipped bits toggles agreement and is detected.

**K5.** For complete-frame single parity, every even number of flipped bits leaves agreement unchanged and passes; passing does not certify identity with sent data.

**K6.** One global parity check alone does not uniquely locate an altered bit; it only indicates violated parity.

**K7.** Full 2D even parity enforces an independent constraint in each transmitted row and column, including row/column check bits and a corner bit. The verified historical 3×4 data / 4×5 transmitted construction is a reference, not a compulsory generated instance.

**K8.** In a properly constructed full 2D row-column parity block, exactly one altered transmitted bit yields one failed row and one failed column and can be uniquely located at their intersection under the single-flip assumption.

**K9.** In a full 2D parity block, two distinct transmitted-bit flips violate at least one check, but arbitrary multiple-flip syndromes cannot be treated as uniquely locatable without additional assumptions.

**K15.** Detection occurs exactly when the received frame violates at least one receiver-tested constraint; an undetected corruption preserves all tested constraints.

**K16.** For a fixed data universe and fixed error class, appending genuinely informative checks to existing checks cannot reduce detection of data errors, but extra check bits alone do not imply dominance across different schemes; location, correction and overhead are distinct outcomes.

**K17.** Reason scheme-conditionally: whole-frame parity depends on flip-count parity; 2D parity depends on row-wise and column-wise flip-count parity; group checks depend on each explicitly checked group. Presentation conventions alone preserve data-error detection only when an equivalent relation is tested.

**K18.** Predict detect/pass/unique-location outcomes of a stated alteration by inspecting which declared constraints it preserves or violates and what assumption (such as exactly one flip) supports unique localization.

**K19.** Derive a general necessary and sufficient evasion condition for a newly defined parity-check arrangement and justify a counterexample or principle-based modification; applying a provided rule to one novel frame alone does not establish Extended Abstract evidence.

### Mechanism relations
**R1.** The sender chooses the parity bit to make the complete frame obey the receiver’s shared test; together these form one check mechanism.

**R2.** Every flip toggles parity of its containing single-parity check; two toggles cancel within that check, yielding the odd/even detection law.

**R3.** In a full 2D parity grid a flipped bit participates in one row and one column; under exactly one flip their failing intersection identifies it.

**R4.** Compared with one global data-parity check, the 2D arrangement adds separate row/column constraints and check-bit overhead; the comparison is restricted to stated data-only alterations unless specified otherwise.

**R7.** Undetected errors are precisely error patterns that preserve every checked parity relation; a 2x2 rectangle of four data flips is a counterexample to perfect 2D detection.

**R8.** A passing check establishes satisfaction of tests, not faithful transmission. A failed check permits location only under justified assumptions.

**R9.** An invariant is a property of the tested relation, not of the surface placement/naming of the check bits.

**R10.** For explicitly specified group membership, a pattern passes if and only if every group, including its associated check bit, sees an even number of flips.

**R11.** The group-wise even-flip condition supports construction of an evading pattern and an explanation of how newly added independent checks change its detectability.

### Diagnostic misconceptions
**M1.** Detection prevents corruption or reconstructs the original data without evidence.

**M2.** Parity is about whether frame length or numeric value is even.

**M3.** Confuses the given even/odd convention.

**M4.** Excludes the transmitted parity/check bit from its own receiver check.

**M5.** All corrupted frames necessarily fail a one-dimensional parity check.

**M6.** A passing parity check proves no bits changed.

**M7.** A single failed global parity check uniquely identifies the erroneous bit.

**M8.** 2D parity is merely repeating one global parity check, not row and column checks.

**M9.** Every detected multi-bit corruption can be uniquely located/corrected by 2D parity.

**M13.** A single universal flip-count threshold determines detection for all parity arrangements.

**M14.** A larger check-bit count unconditionally implies better detection in every comparison.

**M15.** Surface presentation changes always alter detection power, or changing actual checked groups cannot change detection.

## Prerequisite and projection boundaries
Binary counting (including 1s in a short binary string) is a prerequisite, but inability to count is not automatically Prestructural parity understanding. F1 excludes historical FULL checksum K10–K14, R5–R6, M10–M12; old IDs are not repurposed. Learner-facing manually computed parity constraints may involve at most eight bits; bigger 2D diagrams are used for stated syndromes/mechanism reasoning, not unbounded manual recount.

## Academic provenance limitations
Original Phase 2 Knowledge Pack and the v0.3 candidate are source drafts. The algebraic consequences here follow from modulo-two parity and can be checked independently. No claim is made that a textbook validates these specific SOLO probes or that the experimental instrument has passed expert review.
