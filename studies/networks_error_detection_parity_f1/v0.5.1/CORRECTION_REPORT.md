# EkagraAI F1 v0.5.1 — Correction and scope audit

**Status:** CORRECTED CANDIDATE — NOT EXPERIMENTALLY APPROVED, NOT RUNTIME-INTEGRATED.

## Actual curriculum source
The uploaded `EkagraAI_C1_C4_Final_Course_Content_Ground_Truth(2).md` and this package's `CURRICULUM_SOURCE_LOCKED.md` have the same SHA-256 digest:
`73d444c32f050d004a49467a7fd028a825e5225f42a9e3ec148f8798e13777cd`.
No content goal, required fact, boundary, section order, or assessment location was changed in the locked curriculum.

## Corrections
- Inspected every required-content-to-move pairing in **39 subsection×pedagogy cells** (**169 teaching moves**); corrected **104 move reference assignments** and clarified **151 instructional actions**. All existing cell and move IDs are preserved.
- Updated completion evidence to require actual learner-visible **substantive** content, including correct resolution of guided questions; an unanswered question or tutor-reported ID is insufficient.
- Rebuilt `TEACHING_COVERAGE_INDEX.csv`; added a row-by-row inspectable `MOVE_CONTENT_ALIGNMENT_AUDIT.csv` and full correction delta JSON.
- Revised **C4-A2-Q1/Q2/Q3/S** to test explicit unfamiliar checking groups, justified error-pattern predictions and counterexamples **without requiring formal membership-signature criteria**. Replaced C4-A4-Q1's parity-*equation* phrasing with explicit stated-check rules. Existing blueprint and item IDs remain the same (16 blueprints / 64 items).
- Extended the validator to compare the actual move assignments to a separately generated alignment audit and fail on an unexpected return of C4-A2 signature demands. The audit is still a curated candidate, **not independent expert review**.

## Preserved boundaries
- C1: bits, transmission, redundancy, even/odd full-frame parity; not the odd/even *flip-count* theorem.
- C2: 1D limitations, full 2D with corner, conditional single-error correction, every-two-distinct-transmitted-bit detection; no deceptive-three-flip/rectangle causal requirement.
- C3: familiar grid causal and reverse inference, three-flip mimic and undetected four-corner rectangle; no unfamiliar arbitrary-group course.
- C4: new small explicit overlapping checking groups, general detection principle and evaluation of added checking information; no formal parity-check-matrix or group-signature procedure as a learning prerequisite.

## Remaining gates
The package now has auditable internal curriculum-to-move and assessment mappings. It still requires researcher/human scientific review, calibration of candidate exposure limits, actual Tutor/Judge transcript trials, and code integration before use in a live study. No service code, database or frontend was changed.
