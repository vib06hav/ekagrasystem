# Assessment Pack — F1 v0.4: **64 individually authored generative item contracts**



This document is the human-readable scientific authority for 48 MCQ and 16 subjective reusable **question classes** across 16 assessment blueprints. The matching executable authoritative contracts are in `08_SCIENTIFIC_YAML/assessment_families.yaml`. The data are intentionally identical in scientific meaning, not two competing models.



## Structural contract

Each blueprint has three different MCQ roles plus one subjective reasoning task. Every MCQ slot has a specific scientific purpose, scenario-generation family, independent truth condition, three misconception-target meanings and explicit boundaries. A role is NOT a frozen learner-facing question. Each subjectively assessed slot has specific elicitation purpose, target reasoning and scoring/equivalence rules.



The same blueprint can generate many different bit sequences, valid outcomes, distinct option wording and option positions. Randomness alone is insufficient: the science of each realized instance must be checked. The final answer key is computed/mapped **after the instance is created**, not found in this reusable contract.



### Shared response-role hierarchy

**C1:** 1. sender rule or parity-bit interpretation | 2. complete-frame receiver test | 3. stated detection consequence | 4. elicitation of one usable parity aspect with opportunity for sender-receiver connection



**C2:** 1. independent one-dimensional property | 2. independent two-dimensional property | 3. distinct boundary/comparison property | 4. separate correct aspects spanning one- and two-dimensional parity



**C3:** 1. causal effect on one-dimensional constraint | 2. causal relation among full two-dimensional checks | 3. causal limitation or cross-constraint comparison | 4. integrated case-specific constraint -> alteration -> observations -> inference



**C4:** 1. interpret a newly defined check-group model | 2. derive consequence under new groups | 3. evaluate general limitation or principled modification | 4. derive general evasion condition plus nontrivial justified consequence



## C1-A1 — Build/check even-parity frame

**SOLO requirement:** One usable component is sufficient for U. Do not require parity flip-count theorem or 2D understanding.

**Relevant source IDs:** K1, K2, K3, R1



### C1-A1-Q1 — MCQ 1

**Specific scientific task:** Select the sender check bit for a freshly generated even-parity payload

**Scenario family:** `sender_parity`. Choose a fresh data string and explicit parity convention; ask about the sender check bit.

**Required case conditions:** Force stated even convention; sample at least two independently generated data patterns

**Correctness for generated instance:** Appended bit completes an even total number of ones

**Independent oracle:** Parity bit is the one value making full-frame number-of-ones parity equal the stated convention.

**Three distinct misconception-targeted distractor meanings:** (1) Apply odd-parity convention; (2) Count length rather than ones; (3) Assume fixed appended bit.

**SOLO evidence role:** one applicable sender rule

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Build/check even-parity frame; Mandatory parity convention for this blueprint: even; numerical values not fixed.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A1-Q2 — MCQ 2

**Specific scientific task:** Interpret the receiver check on a clean even-parity full frame

**Scenario family:** `receiver_parity`. Start from a valid single-parity frame; create valid or specified altered received frame.

**Required case conditions:** Use an even-parity full frame and explicitly mark the appended bit

**Correctness for generated instance:** Count complete received frame including appended bit and compare with even convention

**Independent oracle:** Receiver pass is parity(received full frame)==agreed convention; pass is not proof of no flips.

**Three distinct misconception-targeted distractor meanings:** (1) Exclude check bit; (2) Count zeroes; (3) Treat successful check as proof no corruption.

**SOLO evidence role:** one applicable receiver check

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Build/check even-parity frame; Mandatory parity convention for this blueprint: even; numerical values not fixed.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A1-Q3 — MCQ 3

**Specific scientific task:** Interpret a single stated transmitted-bit alteration under even parity

**Scenario family:** `single_flip_1d`. Choose valid full frame then flip exactly one transmitted position, possibly the check bit.

**Required case conditions:** Use exactly one flip in the transmitted full frame with even convention

**Correctness for generated instance:** A single alteration violates the originally satisfied even check

**Independent oracle:** One flip toggles complete-frame parity, so receiver test fails.

**Three distinct misconception-targeted distractor meanings:** (1) Claim the bit is repaired; (2) Claim unchanged check result; (3) Claim location is known.

**SOLO evidence role:** a usable consequence of the parity test

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Build/check even-parity frame; Mandatory parity convention for this blueprint: even; numerical values not fixed.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A1-S — Subjective

**Specific scientific task:** Explain how an even-parity check bit is chosen and what the receiver checks

**Scenario family:** `receiver_parity`. Start from a valid single-parity frame; create valid or specified altered received frame.

**Required case conditions:** Use a fresh even-convention full frame; ask for a conceptual rule not only a bit

**Required target evidence:** at least one correct sender or complete-frame receiver aspect; linking both merits full credit

**Partial / borderline evidence:** correct isolated rule with reason

**Material misconception to reject:** equating parity with block length

**Acceptable alternative reasoning:** equivalent concise numerical or verbal reasoning

**Proposed points:** 0 — No usable or materially correct parity aspect in the actual question context. 1 — At least one correct usable sender-rule or complete-frame receiver-test aspect with identifiable reasoning, not a numerical guess. 2 — Correctly links sender choice and full-frame receiver check and appropriately interprets the actual case.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C1-A2 — Odd-parity convention

**SOLO requirement:** One usable component is sufficient for U. Do not require parity flip-count theorem or 2D understanding.

**Relevant source IDs:** K1, K2, K3, R1



### C1-A2-Q1 — MCQ 1

**Specific scientific task:** Choose an odd-parity appended check bit for a generated payload

**Scenario family:** `sender_parity`. Choose a fresh data string and explicit parity convention; ask about the sender check bit.

**Required case conditions:** Force odd convention, not a silent switch from even

**Correctness for generated instance:** Complete frame must have an odd number of ones

**Independent oracle:** Parity bit is the one value making full-frame number-of-ones parity equal the stated convention.

**Three distinct misconception-targeted distractor meanings:** (1) Use even-parity convention; (2) Use data length parity; (3) Ignore appended check bit.

**SOLO evidence role:** usable odd-parity rule

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Odd-parity convention; Mandatory parity convention for this blueprint: odd; numerical values not fixed.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A2-Q2 — MCQ 2

**Specific scientific task:** Recognize odd-parity complete-frame validity after receiving a generated frame

**Scenario family:** `receiver_parity`. Start from a valid single-parity frame; create valid or specified altered received frame.

**Required case conditions:** Use a complete odd-parity received frame including its check bit

**Correctness for generated instance:** Full received frame must have odd number of ones

**Independent oracle:** Receiver pass is parity(received full frame)==agreed convention; pass is not proof of no flips.

**Three distinct misconception-targeted distractor meanings:** (1) Count only data; (2) Accept even count under odd convention; (3) Infer all bits unchanged from pass.

**SOLO evidence role:** receiver convention correctly applied

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Odd-parity convention; Mandatory parity convention for this blueprint: odd; numerical values not fixed.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A2-Q3 — MCQ 3

**Specific scientific task:** State the receiver consequence of one altered bit in a valid odd-parity frame

**Scenario family:** `single_flip_1d`. Choose valid full frame then flip exactly one transmitted position, possibly the check bit.

**Required case conditions:** Use exactly one altered bit of a valid odd frame

**Correctness for generated instance:** One flip changes odd to even; check fails

**Independent oracle:** One flip toggles complete-frame parity, so receiver test fails.

**Three distinct misconception-targeted distractor meanings:** (1) Claim odd parity always detects and repairs; (2) Assume parity-bit flips are exempt; (3) Infer exact corrupted position.

**SOLO evidence role:** mismatch recognition

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Odd-parity convention; Mandatory parity convention for this blueprint: odd; numerical values not fixed.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A2-S — Subjective

**Specific scientific task:** Explain the sender/receiver use of an explicitly agreed odd-parity convention

**Scenario family:** `receiver_parity`. Start from a valid single-parity frame; create valid or specified altered received frame.

**Required case conditions:** Retain explicitly stated odd convention in learner task

**Required target evidence:** one usable parity rule or complete-frame receiver test; complete causal link merits stronger credit

**Partial / borderline evidence:** accurate one-aspect application

**Material misconception to reject:** switching silently to even parity

**Acceptable alternative reasoning:** any mathematically equivalent statement of odd parity

**Proposed points:** 0 — No usable or materially correct parity aspect in the actual question context. 1 — At least one correct usable sender-rule or complete-frame receiver-test aspect with identifiable reasoning, not a numerical guess. 2 — Correctly links sender choice and full-frame receiver check and appropriately interprets the actual case.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C1-A3 — Receiver accepts/rejects frames

**SOLO requirement:** One usable component is sufficient for U. Do not require parity flip-count theorem or 2D understanding.

**Relevant source IDs:** K1, K2, K3, R1



### C1-A3-Q1 — MCQ 1

**Specific scientific task:** Identify which count the sender makes before transmission under a declared convention

**Scenario family:** `sender_parity`. Choose a fresh data string and explicit parity convention; ask about the sender check bit.

**Required case conditions:** State either even or odd convention before sender chooses the bit

**Correctness for generated instance:** Sender selects check bit satisfying complete-frame parity

**Independent oracle:** Parity bit is the one value making full-frame number-of-ones parity equal the stated convention.

**Three distinct misconception-targeted distractor meanings:** (1) Choose bit by frame length alone; (2) Transmitter predicts error position; (3) Check bit always one.

**SOLO evidence role:** sender parity application

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Receiver accepts/rejects frames.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A3-Q2 — MCQ 2

**Specific scientific task:** Decide whether a given received complete frame passes its declared test

**Scenario family:** `receiver_parity`. Start from a valid single-parity frame; create valid or specified altered received frame.

**Required case conditions:** Generate passing or failing received case; declare the convention

**Correctness for generated instance:** Receiver compares all received frame positions to agreed parity condition

**Independent oracle:** Receiver pass is parity(received full frame)==agreed convention; pass is not proof of no flips.

**Three distinct misconception-targeted distractor meanings:** (1) Drop the parity position; (2) Use other convention; (3) Read pass as proof of integrity.

**SOLO evidence role:** receiver check application

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Receiver accepts/rejects frames.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A3-Q3 — MCQ 3

**Specific scientific task:** Distinguish a failing check from unique localization or data correction

**Scenario family:** `single_flip_1d`. Choose valid full frame then flip exactly one transmitted position, possibly the check bit.

**Required case conditions:** Present a failing check; do not provide actual bit-location information

**Correctness for generated instance:** Check violation supports detection of inconsistency, not self-correction

**Independent oracle:** One flip toggles complete-frame parity, so receiver test fails.

**Three distinct misconception-targeted distractor meanings:** (1) Assume check repairs; (2) Assume check gives position; (3) Treat mismatch as normal.

**SOLO evidence role:** correct interpretation of detection

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Receiver accepts/rejects frames.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A3-S — Subjective

**Specific scientific task:** Explain the meaning of receiver pass and fail for a generated full frame

**Scenario family:** `receiver_parity`. Start from a valid single-parity frame; create valid or specified altered received frame.

**Required case conditions:** Present received complete frame and stated convention; ask what results do and do not show

**Required target evidence:** correctly interpret at least one check result; stronger credit links sender rule and test

**Partial / borderline evidence:** valid pass or fail inference with rationale

**Material misconception to reject:** pass guarantees faithful transmission

**Acceptable alternative reasoning:** explain using ones count or parity XOR

**Proposed points:** 0 — No usable or materially correct parity aspect in the actual question context. 1 — At least one correct usable sender-rule or complete-frame receiver-test aspect with identifiable reasoning, not a numerical guess. 2 — Correctly links sender choice and full-frame receiver check and appropriately interprets the actual case.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C1-A4 — Correct a friend's length misconception

**SOLO requirement:** One usable component is sufficient for U. Do not require parity flip-count theorem or 2D understanding.

**Relevant source IDs:** K1, K2, K3, R1



### C1-A4-Q1 — MCQ 1

**Specific scientific task:** Distinguish frame-length parity from number-of-ones parity in sender construction

**Scenario family:** `sender_parity`. Choose a fresh data string and explicit parity convention; ask about the sender check bit.

**Required case conditions:** Select patterns where number of ones and parity of length yield distinct conclusions

**Correctness for generated instance:** Required appended bit follows ones-count convention not evenness of frame length

**Independent oracle:** Parity bit is the one value making full-frame number-of-ones parity equal the stated convention.

**Three distinct misconception-targeted distractor meanings:** (1) Equate even length with even parity; (2) Inspect number of zeroes only; (3) Pick arbitrary fixed bit.

**SOLO evidence role:** recognition of correct count

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Correct a friend's length misconception.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A4-Q2 — MCQ 2

**Specific scientific task:** Identify that the received check bit participates in the receiver recount

**Scenario family:** `checkbit_1d`. Generate a valid full frame with marked data and parity positions, optionally flip check bit.

**Required case conditions:** Mark check-bit position; require its inclusion in count

**Correctness for generated instance:** Receiver counts data and transmitted check bit together

**Independent oracle:** Parity-check bit is included in tested frame; flip alters test exactly as any single bit.

**Three distinct misconception-targeted distractor meanings:** (1) Exclude check bit; (2) Treat check bit as automatic correction; (3) Count frame length.

**SOLO evidence role:** complete-frame rule

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Correct a friend's length misconception.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A4-Q3 — MCQ 3

**Specific scientific task:** Correct a claim that a particular frame is valid because it has an even length

**Scenario family:** `receiver_parity`. Start from a valid single-parity frame; create valid or specified altered received frame.

**Required case conditions:** Present a peer claim based on frame length and an independently verified counterexample

**Correctness for generated instance:** Validity follows number-of-ones parity under agreed convention

**Independent oracle:** Receiver pass is parity(received full frame)==agreed convention; pass is not proof of no flips.

**Three distinct misconception-targeted distractor meanings:** (1) Accept due to eight positions; (2) Assume extra bit always one; (3) Conclude error-free from passing parity.

**SOLO evidence role:** detect length misconception

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Correct a friend's length misconception.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C1-A4-S — Subjective

**Specific scientific task:** Respond to a peer who thinks even parity means an even-length message

**Scenario family:** `sender_parity`. Choose a fresh data string and explicit parity convention; ask about the sender check bit.

**Required case conditions:** Pose a peer misconception; do not demand a specific response sentence

**Required target evidence:** explain the relevant number-of-ones rule with a concrete generated context

**Partial / borderline evidence:** correct distinction even without complete sender-receiver link

**Material misconception to reject:** length rather than ones

**Acceptable alternative reasoning:** ordinary-language or symbolic parity explanation

**Proposed points:** 0 — No usable or materially correct parity aspect in the actual question context. 1 — At least one correct usable sender-rule or complete-frame receiver-test aspect with identifiable reasoning, not a numerical guess. 2 — Correctly links sender choice and full-frame receiver check and appropriately interprets the actual case.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C2-A1 — Stated alterations and outcomes

**SOLO requirement:** At least one distinct correct 1D and one distinct correct 2D aspect; do not turn item into an unrequired derivation.

**Relevant source IDs:** K4, K5, K6, K7, K8, K9



### C2-A1-Q1 — MCQ 1

**Specific scientific task:** Distinguish odd-count from even-count alterations under single parity

**Scenario family:** `multiflip_1d`. Choose valid full frame and a bounded set of distinct flipped transmitted positions.

**Required case conditions:** Use one odd-count and one even-count bounded alteration for contrast

**Correctness for generated instance:** Odd flips are detected and even flips preserve the parity check

**Independent oracle:** Receiver fails iff number of flips is odd; cannot infer error count from one failure.

**Three distinct misconception-targeted distractor meanings:** (1) Any corruption fails; (2) Even means frame length; (3) Passing means untouched.

**SOLO evidence role:** one 1D property

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Stated alterations and outcomes.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A1-Q2 — MCQ 2

**Specific scientific task:** Identify the single-bit location implication of full row/column checks

**Scenario family:** `full2d_single`. Generate full small even-parity row-column block incl corner and exactly one flipped transmitted position.

**Required case conditions:** Exactly one altered transmitted position in full 2D with explicit assumption

**Correctness for generated instance:** Under exactly one altered transmitted bit, one failed row and column intersect at its position

**Independent oracle:** Exactly one row and one column fail, whose intersection is the altered position under exactly-one-flip assumption.

**Three distinct misconception-targeted distractor meanings:** (1) A global parity check locates; (2) Intersection without one-flip assumption always identifies every error; (3) 2D has only one global check.

**SOLO evidence role:** one 2D property

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Stated alterations and outcomes.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A1-Q3 — MCQ 3

**Specific scientific task:** Contrast a 1D failure with the absence of unique position evidence

**Scenario family:** `single_flip_1d`. Choose valid full frame then flip exactly one transmitted position, possibly the check bit.

**Required case conditions:** Show global 1D failure without enough information to locate position

**Correctness for generated instance:** Global parity detects its violation but does not reveal which frame bit changed

**Independent oracle:** One flip toggles complete-frame parity, so receiver test fails.

**Three distinct misconception-targeted distractor meanings:** (1) Failed 1D check gives bit index; (2) 1D repairs automatically; (3) One failed global check proves two flips.

**SOLO evidence role:** different 1D diagnostic property

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Stated alterations and outcomes.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A1-S — Subjective

**Specific scientific task:** List distinct verified features of single parity and full 2D parity on stated changes

**Scenario family:** `full2d_single`. Generate full small even-parity row-column block incl corner and exactly one flipped transmitted position.

**Required case conditions:** Show one 1D and one full 2D case with separate inferable properties

**Required target evidence:** at least one materially correct 1D feature and one distinct 2D feature; causal chain not required

**Partial / borderline evidence:** one correct feature from each scheme

**Material misconception to reject:** two restatements of single parity

**Acceptable alternative reasoning:** valid separate facts in any order

**Proposed points:** 0 — Does not provide distinct materially correct facts spanning one-dimensional and full two-dimensional parity. 1 — At least one correct distinct property of each of 1D and 2D parity relevant to the presented task. 2 — Multiple accurate, differentiated properties spanning both schemes, including pertinent limitations; no causal derivation required.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C2-A2 — Odd/even and same-row changes

**SOLO requirement:** At least one distinct correct 1D and one distinct correct 2D aspect; do not turn item into an unrequired derivation.

**Relevant source IDs:** K4, K5, K6, K7, K8, K9



### C2-A2-Q1 — MCQ 1

**Specific scientific task:** Classify two transmitted flips under one global parity check

**Scenario family:** `multiflip_1d`. Choose valid full frame and a bounded set of distinct flipped transmitted positions.

**Required case conditions:** Exactly two distinct transmitted flips in a valid 1D frame

**Correctness for generated instance:** Two flips preserve the single parity constraint

**Independent oracle:** Receiver fails iff number of flips is odd; cannot infer error count from one failure.

**Three distinct misconception-targeted distractor meanings:** (1) All changes fail; (2) Two flips always locate; (3) Pass means no change.

**SOLO evidence role:** even-flip 1D property

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Odd/even and same-row changes.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A2-Q2 — MCQ 2

**Specific scientific task:** Classify two data-bit flips in the same row but different columns in full 2D

**Scenario family:** `full2d_pair`. Generate a full small even-parity row-column block with two distinct altered transmitted positions.

**Required case conditions:** Exactly two DATA flips in SAME row and DIFFERENT columns of full 2D

**Correctness for generated instance:** Row parity stays valid while the two changed columns fail

**Independent oracle:** Compute failed-row and failed-column sets from row/column syndromes; at least one fails; no unconditional unique two-flip inference.

**Three distinct misconception-targeted distractor meanings:** (1) Entire 2D check passes; (2) Row and only row fails; (3) Two failed columns uniquely identify both positions without assumptions.

**SOLO evidence role:** 2D row/column property

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Odd/even and same-row changes.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A2-Q3 — MCQ 3

**Specific scientific task:** Recognize that two-flip syndrome does not establish unconditional unique locations

**Scenario family:** `full2d_pair`. Generate a full small even-parity row-column block with two distinct altered transmitted positions.

**Required case conditions:** Exactly two flips in full 2D, do not assume a unique two-error decoding

**Correctness for generated instance:** Syndrome gives failed constraints, not guaranteed exact two-error locations

**Independent oracle:** Compute failed-row and failed-column sets from row/column syndromes; at least one fails; no unconditional unique two-flip inference.

**Three distinct misconception-targeted distractor meanings:** (1) Any two failed checks identify exactly two bits; (2) 2D cannot detect any two flips; (3) Number of flips is always determined.

**SOLO evidence role:** distinct location limitation

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Odd/even and same-row changes.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A2-S — Subjective

**Specific scientific task:** State one 1D two-flip property and one distinct 2D same-row pair property

**Scenario family:** `full2d_pair`. Generate a full small even-parity row-column block with two distinct altered transmitted positions.

**Required case conditions:** Present 1D double flip and same-row full 2D double flip as distinct cases

**Required target evidence:** at least one correct property of each of 1D and 2D parity; integration optional

**Partial / borderline evidence:** separate correct 1D and 2D outcomes

**Material misconception to reject:** claim same-row pair always undetected by full 2D

**Acceptable alternative reasoning:** alternate concise descriptions of row/column failures

**Proposed points:** 0 — Does not provide distinct materially correct facts spanning one-dimensional and full two-dimensional parity. 1 — At least one correct distinct property of each of 1D and 2D parity relevant to the presented task. 2 — Multiple accurate, differentiated properties spanning both schemes, including pertinent limitations; no causal derivation required.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C2-A3 — Flipped parity bit and missed errors

**SOLO requirement:** At least one distinct correct 1D and one distinct correct 2D aspect; do not turn item into an unrequired derivation.

**Relevant source IDs:** K4, K5, K6, K7, K8, K9



### C2-A3-Q1 — MCQ 1

**Specific scientific task:** Treat a flipped transmitted parity bit as a genuine single-parity error

**Scenario family:** `checkbit_1d`. Generate a valid full frame with marked data and parity positions, optionally flip check bit.

**Required case conditions:** Exactly one flipped transmitted 1D parity/check bit

**Correctness for generated instance:** An altered parity/check bit changes the received full-frame test

**Independent oracle:** Parity-check bit is included in tested frame; flip alters test exactly as any single bit.

**Three distinct misconception-targeted distractor meanings:** (1) Receiver excludes check bit; (2) Only payload flips matter; (3) Wrong check bit repairs itself.

**SOLO evidence role:** 1D check-bit inclusion

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Flipped parity bit and missed errors.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A3-Q2 — MCQ 2

**Specific scientific task:** Distinguish row, column and corner check-bit errors under exactly one full 2D flip

**Scenario family:** `full2d_checkbit`. Generate full 2D block and flip one named row, column, or corner check-bit position.

**Required case conditions:** Exactly one altered row, column or corner check bit in full 2D

**Correctness for generated instance:** The failed row and column intersect at the changed check-bit coordinate

**Independent oracle:** Compute syndrome including the altered check-bit coordinate; single-flip intersection applies.

**Three distinct misconception-targeted distractor meanings:** (1) Only data cells are locatable; (2) Check bit is not in any parity constraint; (3) Any check-bit error passes.

**SOLO evidence role:** 2D check-bit scope

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Flipped parity bit and missed errors.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A3-Q3 — MCQ 3

**Specific scientific task:** Contrast odd and even total transmitted flips including a parity position

**Scenario family:** `multiflip_1d`. Choose valid full frame and a bounded set of distinct flipped transmitted positions.

**Required case conditions:** Contrast one transmitted flip with a two-flip pattern that includes check bit

**Correctness for generated instance:** Single global check depends on flip-count parity including check bit

**Independent oracle:** Receiver fails iff number of flips is odd; cannot infer error count from one failure.

**Three distinct misconception-targeted distractor meanings:** (1) Check-bit changes never count; (2) Every pair triggers alarm; (3) Passing proves no alteration.

**SOLO evidence role:** independent 1D parity property

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Flipped parity bit and missed errors.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A3-S — Subjective

**Specific scientific task:** Describe at least one 1D and one full 2D consequence of altered check bits

**Scenario family:** `full2d_checkbit`. Generate full 2D block and flip one named row, column, or corner check-bit position.

**Required case conditions:** One case each for 1D check bit and 2D check-bit syndrome

**Required target evidence:** accurate separate properties for each scheme; no compulsory causal derivation

**Partial / borderline evidence:** distinguish valid 1D and 2D results

**Material misconception to reject:** ignore check-bit positions in all receiver tests

**Acceptable alternative reasoning:** valid coordinate or verbal descriptions

**Proposed points:** 0 — Does not provide distinct materially correct facts spanning one-dimensional and full two-dimensional parity. 1 — At least one correct distinct property of each of 1D and 2D parity relevant to the presented task. 2 — Multiple accurate, differentiated properties spanning both schemes, including pertinent limitations; no causal derivation required.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C2-A4 — Four flips / check limits

**SOLO requirement:** At least one distinct correct 1D and one distinct correct 2D aspect; do not turn item into an unrequired derivation.

**Relevant source IDs:** K4, K5, K6, K7, K8, K9



### C2-A4-Q1 — MCQ 1

**Specific scientific task:** Classify four distinct flips in a single-parity full frame

**Scenario family:** `multiflip_1d`. Choose valid full frame and a bounded set of distinct flipped transmitted positions.

**Required case conditions:** Exactly four DISTINCT flipped positions of a <=8-bit complete 1D frame

**Correctness for generated instance:** Four flips preserve the single parity test

**Independent oracle:** Receiver fails iff number of flips is odd; cannot infer error count from one failure.

**Three distinct misconception-targeted distractor meanings:** (1) Four always fail; (2) Four are auto-corrected; (3) Pass means data unchanged.

**SOLO evidence role:** one 1D even-flip property

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Four flips / check limits.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A4-Q2 — MCQ 2

**Specific scientific task:** Recognize an undetected four-data-bit rectangle under full 2D

**Scenario family:** `full2d_rectangle`. Generate a valid small 2D grid and change all four data bits at corners of a nondegenerate rectangle.

**Required case conditions:** Flip four corners of a nondegenerate rectangle in full 2D data cells

**Correctness for generated instance:** Four rectangle corners change twice per affected row and column and pass all checks

**Independent oracle:** Every affected row and column has two changes and hence all parity tests pass; corruption remains undetected.

**Three distinct misconception-targeted distractor meanings:** (1) All four-bit changes must fail; (2) All four-bit changes correctable; (3) 2D has no misses.

**SOLO evidence role:** one 2D limitation

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Four flips / check limits.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A4-Q3 — MCQ 3

**Specific scientific task:** Distinguish a rectangle miss from a generic four-flip claim

**Scenario family:** `full2d_four_compare`. Generate both rectangle and non-rectangle four-data-flip patterns on a full row-column grid, computing each resulting syndrome independently.

**Required case conditions:** Use a grid with enough data cells to create rectangle and NONrectangle four-bit patterns

**Correctness for generated instance:** 2D pass/fail depends on each row and column, not just total flip count

**Independent oracle:** Pass if and only if every row and column has an even flip count; total count four alone is insufficient.

**Three distinct misconception-targeted distractor meanings:** (1) Every four-bit pattern invisible to 2D; (2) Only global number of flips matters; (3) 2D always locates four flips.

**SOLO evidence role:** independent 2D case distinction

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Four flips / check limits.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C2-A4-S — Subjective

**Specific scientific task:** State one single-parity four-flip outcome and a distinct 2D limitation

**Scenario family:** `full2d_rectangle`. Generate a valid small 2D grid and change all four data bits at corners of a nondegenerate rectangle.

**Required case conditions:** Present one full-frame 1D four-flip fact and one 2D rectangular-miss fact

**Required target evidence:** at least one accurate 1D property and one accurate 2D property; no theorem derivation demanded

**Partial / borderline evidence:** separate correct claims

**Material misconception to reject:** claim all 2D four-flip patterns are invisible

**Acceptable alternative reasoning:** description of rectangle or row/column check result

**Proposed points:** 0 — Does not provide distinct materially correct facts spanning one-dimensional and full two-dimensional parity. 1 — At least one correct distinct property of each of 1D and 2D parity relevant to the presented task. 2 — Multiple accurate, differentiated properties spanning both schemes, including pertinent limitations; no causal derivation required.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C3-A1 — Row check passes, columns detect

**SOLO requirement:** Require meaningful constraint-to-syndrome causal integration rather than listing facts; no abstract theorem demand.

**Relevant source IDs:** K15, K16, R2, R3, R4, R7, R8



### C3-A1-Q1 — MCQ 1

**Specific scientific task:** Explain why two flips preserve the global parity constraint

**Scenario family:** `multiflip_1d`. Choose valid full frame and a bounded set of distinct flipped transmitted positions.

**Required case conditions:** Exactly two distinct transmitted positions under single parity

**Correctness for generated instance:** Two toggles cancel within a single parity check

**Independent oracle:** Receiver fails iff number of flips is odd; cannot infer error count from one failure.

**Three distinct misconception-targeted distractor meanings:** (1) Two flips cannot occur; (2) Check repairs one flip; (3) Even parity refers to length.

**SOLO evidence role:** specific cancellation mechanism

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Row check passes, columns detect.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A1-Q2 — MCQ 2

**Specific scientific task:** Infer which checks fail for two changes in the same row of full 2D parity

**Scenario family:** `full2d_pair`. Generate a full small even-parity row-column block with two distinct altered transmitted positions.

**Required case conditions:** Exactly two DATA flips in same row, distinct columns of full 2D block

**Correctness for generated instance:** Both altered columns fail while the common row check passes

**Independent oracle:** Compute failed-row and failed-column sets from row/column syndromes; at least one fails; no unconditional unique two-flip inference.

**Three distinct misconception-targeted distractor meanings:** (1) Row fails because bits changed; (2) Every check passes; (3) Syndrome uniquely fixes the two bits without assumptions.

**SOLO evidence role:** row-column constraint mechanism

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Row check passes, columns detect.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A1-Q3 — MCQ 3

**Specific scientific task:** Explain the added value of columns over row-only testing on the same pair

**Scenario family:** `full2d_compare`. Hold data and error universe fixed while contrasting global single parity and full 2D row-column checks.

**Required case conditions:** Compare row-only checks with full row-and-column checks on the SAME two data flips

**Correctness for generated instance:** Independent column checks detect pair that cancels within its row check

**Independent oracle:** Compute each scheme’s applicable checks separately; check-bit-error comparisons require explicitly matched error universes.

**Three distinct misconception-targeted distractor meanings:** (1) Extra check bits alone guarantee all detection; (2) Row-only detects a same-row pair; (3) A passing row guarantees no corruption.

**SOLO evidence role:** mechanism of independent constraints

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Row check passes, columns detect.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A1-S — Subjective

**Specific scientific task:** Explain causally why a same-row pair can pass row checks yet be detected by columns

**Scenario family:** `full2d_pair`. Generate a full small even-parity row-column block with two distinct altered transmitted positions.

**Required case conditions:** Require explicit common-row cancellation and affected-column failures

**Required target evidence:** connect changed positions→row cancellation and column violation→warranted receiver inference

**Partial / borderline evidence:** sound causal relation but incomplete limitation

**Material misconception to reject:** list row and column facts without linking them

**Acceptable alternative reasoning:** constraint-toggle or parity-preservation explanation

**Proposed points:** 0 — Facts are disconnected from the case or proposed mechanism is materially false. 1 — A materially correct, case-linked causal chain relates checked constraint, alteration and receiver result. 2 — A coherent and supported causal account additionally addresses a relevant limit, assumption or contrast.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C3-A2 — Single flip intersection vs two flips

**SOLO requirement:** Require meaningful constraint-to-syndrome causal integration rather than listing facts; no abstract theorem demand.

**Relevant source IDs:** K15, K16, R2, R3, R4, R7, R8



### C3-A2-Q1 — MCQ 1

**Specific scientific task:** Explain how one transmitted-bit flip changes global parity

**Scenario family:** `single_flip_1d`. Choose valid full frame then flip exactly one transmitted position, possibly the check bit.

**Required case conditions:** One flip of transmitted 1D frame; check bit may be selected

**Correctness for generated instance:** One toggle violates the clean full-frame constraint

**Independent oracle:** One flip toggles complete-frame parity, so receiver test fails.

**Three distinct misconception-targeted distractor meanings:** (1) Check bit immune; (2) Global check returns unique location; (3) Parity counts frame length.

**SOLO evidence role:** whole-frame causal relation

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Single flip intersection vs two flips.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A2-Q2 — MCQ 2

**Specific scientific task:** Explain why one flipped 2D position yields an intersecting row/column syndrome

**Scenario family:** `full2d_single`. Generate full small even-parity row-column block incl corner and exactly one flipped transmitted position.

**Required case conditions:** One flip anywhere in full 2D INCLUDING check bits; state one-flip assumption

**Correctness for generated instance:** Affected row and column each toggle, intersection locates under one-flip assumption

**Independent oracle:** Exactly one row and one column fail, whose intersection is the altered position under exactly-one-flip assumption.

**Three distinct misconception-targeted distractor meanings:** (1) One failed row sufficient; (2) Any syndrome implies single flip; (3) The corner bit cannot change.

**SOLO evidence role:** 2D causal localization

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Single flip intersection vs two flips.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A2-Q3 — MCQ 3

**Specific scientific task:** Explain why a two-flip syndrome does not justify unconditional unique localization

**Scenario family:** `full2d_pair`. Generate a full small even-parity row-column block with two distinct altered transmitted positions.

**Required case conditions:** Two distinct transmitted 2D flips and their syndrome; no hidden assumption that count known

**Correctness for generated instance:** Observed failures can arise from multiple candidate error patterns unless error-count information is justified

**Independent oracle:** Compute failed-row and failed-column sets from row/column syndromes; at least one fails; no unconditional unique two-flip inference.

**Three distinct misconception-targeted distractor meanings:** (1) Two-column failures always identify exact pair; (2) Any failed check uniquely repairs; (3) 2D cannot detect two flips.

**SOLO evidence role:** assumption-aware limitation

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Single flip intersection vs two flips.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A2-S — Subjective

**Specific scientific task:** Explain how the full 2D syndrome supports single-flip location and why two flips differ

**Scenario family:** `full2d_pair`. Generate a full small even-parity row-column block with two distinct altered transmitted positions.

**Required case conditions:** Compare a one-flip example with a two-flip case and explain the assumption boundary

**Required target evidence:** connect check membership, syndrome and single-flip assumption; state limits for multiple flips

**Partial / borderline evidence:** correct mechanism with partially stated caveat

**Material misconception to reject:** infer unique pair from failures alone

**Acceptable alternative reasoning:** algebraic or coordinate intersection reasoning

**Proposed points:** 0 — Facts are disconnected from the case or proposed mechanism is materially false. 1 — A materially correct, case-linked causal chain relates checked constraint, alteration and receiver result. 2 — A coherent and supported causal account additionally addresses a relevant limit, assumption or contrast.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C3-A3 — One mechanism, three outcomes

**SOLO requirement:** Require meaningful constraint-to-syndrome causal integration rather than listing facts; no abstract theorem demand.

**Relevant source IDs:** K15, K16, R2, R3, R4, R7, R8



### C3-A3-Q1 — MCQ 1

**Specific scientific task:** Relate odd and even transmitted flip counts to preservation of one global parity constraint

**Scenario family:** `multiflip_1d`. Choose valid full frame and a bounded set of distinct flipped transmitted positions.

**Required case conditions:** Use odd and even flip counts on valid single-parity frames

**Correctness for generated instance:** A check toggles once for each flipped member; odd changes fail and even changes pass

**Independent oracle:** Receiver fails iff number of flips is odd; cannot infer error count from one failure.

**Three distinct misconception-targeted distractor meanings:** (1) All flips detected; (2) Check identifies every changed bit; (3) Only data not parity-bit flips count.

**SOLO evidence role:** causal invariance 1D

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: One mechanism, three outcomes.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A3-Q2 — MCQ 2

**Specific scientific task:** Explain contrasting one-flip and two-flip syndromes in full 2D

**Scenario family:** `full2d_pair`. Generate a full small even-parity row-column block with two distinct altered transmitted positions.

**Required case conditions:** Provide separately checked one-flip and two-flip full 2D examples

**Correctness for generated instance:** Single flip violates its row and column; two flips may cancel shared constraints while violating others

**Independent oracle:** Compute failed-row and failed-column sets from row/column syndromes; at least one fails; no unconditional unique two-flip inference.

**Three distinct misconception-targeted distractor meanings:** (1) Two flips undetected always; (2) Row and column check are a single test; (3) Single flip cannot be located.

**SOLO evidence role:** causal relation across cases

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: One mechanism, three outcomes.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A3-Q3 — MCQ 3

**Specific scientific task:** Explain why four rectangle flips evade every row/column check

**Scenario family:** `full2d_rectangle`. Generate a valid small 2D grid and change all four data bits at corners of a nondegenerate rectangle.

**Required case conditions:** Four rectangle-corner data flips plus independently verified syndrome

**Correctness for generated instance:** Each affected constraint sees two flips, so all checks preserve their parity

**Independent oracle:** Every affected row and column has two changes and hence all parity tests pass; corruption remains undetected.

**Three distinct misconception-targeted distractor meanings:** (1) Any four flips pass; (2) Rectangle is detected by four failed checks; (3) 2D corrects rectangle.

**SOLO evidence role:** causal mechanism for miss

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: One mechanism, three outcomes.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A3-S — Subjective

**Specific scientific task:** Relate three different generated 1D/2D alteration cases using their constraint behavior

**Scenario family:** `full2d_rectangle`. Generate a valid small 2D grid and change all four data bits at corners of a nondegenerate rectangle.

**Required case conditions:** Provide multiple cases so learner links behavior to constraints not to memorized outcomes

**Required target evidence:** connected constraint→flip effects→receiver conclusion for at least two cases, with justified contrast

**Partial / borderline evidence:** causal chain for one case and partial comparison

**Material misconception to reject:** list three outcomes without relating them

**Acceptable alternative reasoning:** general parity-toggle logic without formal notation

**Proposed points:** 0 — Facts are disconnected from the case or proposed mechanism is materially false. 1 — A materially correct, case-linked causal chain relates checked constraint, alteration and receiver result. 2 — A coherent and supported causal account additionally addresses a relevant limit, assumption or contrast.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C3-A4 — Coverage versus cost

**SOLO requirement:** Require meaningful constraint-to-syndrome causal integration rather than listing facts; no abstract theorem demand.

**Relevant source IDs:** K15, K16, R2, R3, R4, R7, R8



### C3-A4-Q1 — MCQ 1

**Specific scientific task:** Explain why one global parity check can miss some data-only changes

**Scenario family:** `multiflip_1d`. Choose valid full frame and a bounded set of distinct flipped transmitted positions.

**Required case conditions:** Even-count data-only changes of an otherwise valid single-parity frame

**Correctness for generated instance:** Even data-flip count preserves sole tested constraint

**Independent oracle:** Receiver fails iff number of flips is odd; cannot infer error count from one failure.

**Three distinct misconception-targeted distractor meanings:** (1) More parity bits always catch everything; (2) Global check corrects errors; (3) Check passing proves no change.

**SOLO evidence role:** single-check limitation

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Coverage versus cost.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A4-Q2 — MCQ 2

**Specific scientific task:** Analyze what independent 2D row/column checks add on a matched data-only alteration

**Scenario family:** `full2d_compare`. Hold data and error universe fixed while contrasting global single parity and full 2D row-column checks.

**Required case conditions:** Same DATA-only error on same data represented by global vs full 2D scheme

**Correctness for generated instance:** Additional independent constraints may catch patterns missed by global parity when data-only universe fixed

**Independent oracle:** Compute each scheme’s applicable checks separately; check-bit-error comparisons require explicitly matched error universes.

**Three distinct misconception-targeted distractor meanings:** (1) More check bits guarantee all possible patterns; (2) 2D is identical to one global parity; (3) Check-bit errors counted inconsistently.

**SOLO evidence role:** matched comparison mechanism

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Coverage versus cost.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A4-Q3 — MCQ 3

**Specific scientific task:** Distinguish additional checking coverage from universally better decoding

**Scenario family:** `full2d_compare`. Hold data and error universe fixed while contrasting global single parity and full 2D row-column checks.

**Required case conditions:** State matched data-only error universe; do not compare check-bit-error outcomes as identical

**Correctness for generated instance:** Added independent constraints can increase detection on fixed data error class, not automatically correction or dominance across mismatched schemes

**Independent oracle:** Compute each scheme’s applicable checks separately; check-bit-error comparisons require explicitly matched error universes.

**Three distinct misconception-targeted distractor meanings:** (1) Count alone proves superiority; (2) More checks guarantee unique multi-error location; (3) Comparing different error universes is valid.

**SOLO evidence role:** bounded tradeoff reasoning

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Coverage versus cost.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C3-A4-S — Subjective

**Specific scientific task:** Explain how added independent constraints may change detection and what overhead does not prove

**Scenario family:** `full2d_compare`. Hold data and error universe fixed while contrasting global single parity and full 2D row-column checks.

**Required case conditions:** Require a justified detection improvement example and explain overhead/limits

**Required target evidence:** connect specific missed pattern, added checked relations and matched-data comparison; acknowledge limits

**Partial / borderline evidence:** correct causal improvement on stated case with partial caveat

**Material misconception to reject:** unconditional superiority by bit count

**Acceptable alternative reasoning:** explain via independent failed tests, not slogans

**Proposed points:** 0 — Facts are disconnected from the case or proposed mechanism is materially false. 1 — A materially correct, case-linked causal chain relates checked constraint, alteration and receiver result. 2 — A coherent and supported causal account additionally addresses a relevant limit, assumption or contrast.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C4-A1 — Split parity

**SOLO requirement:** Require a general condition over a class of alterations, with a justified consequence; no CRC/other-topic transfer.

**Relevant source IDs:** K17, K18, K19, R9, R10, R11



### C4-A1-Q1 — MCQ 1

**Specific scientific task:** Identify the actual checked subsets in a newly generated split-group parity scheme

**Scenario family:** `grouped_checks`. Generate <=8 data positions and 2–3 explicitly declared nonempty checked subsets with an independent even-parity check bit for each.

**Required case conditions:** Construct a NEW group/subset membership map with explicitly declared check bits

**Correctness for generated instance:** Each check covers its declared subset and its own transmitted parity bit

**Independent oracle:** For data-only flips, check j fails iff number of flipped data positions in subset j is odd.

**Three distinct misconception-targeted distractor meanings:** (1) All checks cover every data bit; (2) Names/positions alone determine checks; (3) One global parity always replaces groups.

**SOLO evidence role:** interpret novel constraints

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Split parity.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A1-Q2 — MCQ 2

**Specific scientific task:** Predict whether a pair of data flips in one or two groups violates checks

**Scenario family:** `grouped_two_flip`. Generate a grouped-check scheme with pairs sharing or differing in checked-subset membership.

**Required case conditions:** Generate pair with either equal or unequal check-membership signatures

**Correctness for generated instance:** A group flags when exactly one of the flipped positions belongs to it

**Independent oracle:** A two-data-bit alteration is invisible iff the two positions have identical check-membership signatures.

**Three distinct misconception-targeted distractor meanings:** (1) All pairs undetected; (2) All pairs detected; (3) Membership is irrelevant.

**SOLO evidence role:** derive membership consequence

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Split parity.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A1-Q3 — MCQ 3

**Specific scientific task:** Recognize the general condition for a data-error pattern to evade all group checks

**Scenario family:** `grouped_evasion`. Generate a small bounded grouped-check scheme with a nonempty error subset that preserves every check.

**Required case conditions:** Generate a nonempty even-overlap witness for a new grouped scheme

**Correctness for generated instance:** Every checked group must intersect the flipped positions in even cardinality

**Independent oracle:** All checks pass iff each checked subset contains an even number of flipped data positions; demonstrate a nonempty witness by oracle.

**Three distinct misconception-targeted distractor meanings:** (1) Total number of flips always sole criterion; (2) One passing group means all pass; (3) More checks guarantee no misses.

**SOLO evidence role:** class-level condition

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Split parity.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A1-S — Subjective

**Specific scientific task:** Derive a general pass/fail condition for a newly specified split-check scheme and justify a nonempty case

**Scenario family:** `grouped_evasion`. Generate a small bounded grouped-check scheme with a nonempty error subset that preserves every check.

**Required case conditions:** Require general all-groups condition plus one independently verified nonempty witness

**Required target evidence:** general all-groups even-intersection rule and independently justified witness or impossibility under stated bounds

**Partial / borderline evidence:** correct class rule plus case with incomplete explanation

**Material misconception to reject:** single worked prediction without general condition

**Acceptable alternative reasoning:** explain by membership counts or GF(2) without mandated terms

**Proposed points:** 0 — Only one predicted unfamiliar result or recalled rule without derived class-level criterion. 1 — A generally applicable correct condition is derived and applied to a justified nontrivial case or boundary. 2 — A necessary-and-sufficient general condition, a verified nonempty witness or principled design consequence, and an explicit scope/limit.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C4-A2 — Challenge a claim that all two-bit errors are detected

**SOLO requirement:** Require a general condition over a class of alterations, with a justified consequence; no CRC/other-topic transfer.

**Relevant source IDs:** K17, K18, K19, R9, R10, R11



### C4-A2-Q1 — MCQ 1

**Specific scientific task:** Identify which pair membership signatures a new grouped-check arrangement compares

**Scenario family:** `grouped_checks`. Generate <=8 data positions and 2–3 explicitly declared nonempty checked subsets with an independent even-parity check bit for each.

**Required case conditions:** Generate several distinct data positions with declared groups and membership signatures

**Correctness for generated instance:** Two data positions are distinguishable by checks only when their group membership patterns differ

**Independent oracle:** For data-only flips, check j fails iff number of flipped data positions in subset j is odd.

**Three distinct misconception-targeted distractor meanings:** (1) Group labels alone determine outcomes; (2) Every group contains every bit; (3) All two-bit errors always detectable.

**SOLO evidence role:** check membership meaning

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Challenge a claim that all two-bit errors are detected.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A2-Q2 — MCQ 2

**Specific scientific task:** Find when a two-data-bit flip violates at least one new-group check

**Scenario family:** `grouped_two_flip`. Generate a grouped-check scheme with pairs sharing or differing in checked-subset membership.

**Required case conditions:** Choose two data positions of equal or unequal signatures and verify

**Correctness for generated instance:** A pair is detected iff some group contains exactly one of its positions

**Independent oracle:** A two-data-bit alteration is invisible iff the two positions have identical check-membership signatures.

**Three distinct misconception-targeted distractor meanings:** (1) Two flips always pass; (2) Two flips always fail; (3) Check count alone decides.

**SOLO evidence role:** derive pair condition

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Challenge a claim that all two-bit errors are detected.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A2-Q3 — MCQ 3

**Specific scientific task:** Evaluate an all-two-bit-detectable claim over the permitted data universe

**Scenario family:** `grouped_two_flip`. Generate a grouped-check scheme with pairs sharing or differing in checked-subset membership.

**Required case conditions:** Compare all permissible distinct pairs in bounded data universe; retain same membership map

**Correctness for generated instance:** All pairs are detected iff distinct data positions have distinct group-membership signatures

**Independent oracle:** A two-data-bit alteration is invisible iff the two positions have identical check-membership signatures.

**Three distinct misconception-targeted distractor meanings:** (1) One observed detected pair proves universal claim; (2) One same-group pair proves universal detection; (3) Nonzero membership automatically distinguishes every pair.

**SOLO evidence role:** general claim evaluation

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Challenge a claim that all two-bit errors are detected.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A2-S — Subjective

**Specific scientific task:** Derive whether a given grouped scheme detects every two-data-bit alteration and supply a witness if not

**Scenario family:** `grouped_two_flip`. Generate a grouped-check scheme with pairs sharing or differing in checked-subset membership.

**Required case conditions:** Quantify claim over ALL data-only pairs in the supplied bounded scheme

**Required target evidence:** general pair signature criterion plus valid specific equal-signature counterexample or proof of uniqueness

**Partial / borderline evidence:** accurate general criterion but insufficient witness

**Material misconception to reject:** one case extrapolated to every pair

**Acceptable alternative reasoning:** reason in words using group overlaps instead of bit-vector jargon

**Proposed points:** 0 — Only one predicted unfamiliar result or recalled rule without derived class-level criterion. 1 — A generally applicable correct condition is derived and applied to a justified nontrivial case or boundary. 2 — A necessary-and-sufficient general condition, a verified nonempty witness or principled design consequence, and an explicit scope/limit.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C4-A3 — Uncovered data bits

**SOLO requirement:** Require a general condition over a class of alterations, with a justified consequence; no CRC/other-topic transfer.

**Relevant source IDs:** K17, K18, K19, R9, R10, R11



### C4-A3-Q1 — MCQ 1

**Specific scientific task:** Identify a truly unchecked data position in a new grouped-check coverage map

**Scenario family:** `grouped_uncovered`. Generate a grouped-check scheme with at least one data position in no checked subset.

**Required case conditions:** Guarantee at least one uncovered data position in newly generated groups

**Correctness for generated instance:** Uncovered position participates in no declared parity group

**Independent oracle:** A flip on an uncovered data position violates no check; an added check covering it detects that single data flip.

**Three distinct misconception-targeted distractor meanings:** (1) One group always checks all bits; (2) Any check-bit position counts as coverage; (3) Frame length implies coverage.

**SOLO evidence role:** construct coverage abstraction

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Uncovered data bits.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A3-Q2 — MCQ 2

**Specific scientific task:** Predict check behavior for one data flip at an uncovered position

**Scenario family:** `grouped_uncovered`. Generate a grouped-check scheme with at least one data position in no checked subset.

**Required case conditions:** Exactly one data-only flip at declared uncovered position

**Correctness for generated instance:** No group changes parity when a nonmember bit flips, so all pass

**Independent oracle:** A flip on an uncovered data position violates no check; an added check covering it detects that single data flip.

**Three distinct misconception-targeted distractor meanings:** (1) Every single data error fails; (2) Uncovered bit is corrected; (3) One group must fail regardless of membership.

**SOLO evidence role:** derive unchecked flip result

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Uncovered data bits.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A3-Q3 — MCQ 3

**Specific scientific task:** Determine a targeted extra constraint that detects the uncovered-position single flip

**Scenario family:** `grouped_add_check`. Generate a scheme and known witness; introduce a candidate new parity subset while holding the data-only error universe fixed.

**Required case conditions:** New group check includes previously uncovered position; hold SAME witness fixed

**Correctness for generated instance:** New check must include that position, yielding odd overlap for that witness

**Independent oracle:** The new check detects that witness iff its overlap with witness positions has odd size; cannot promise universal superiority across arbitrary error universes.

**Three distinct misconception-targeted distractor meanings:** (1) Adding a check anywhere guarantees coverage; (2) Duplicating unrelated group fixes it; (3) One new check catches all error patterns.

**SOLO evidence role:** principled repair with limited claim

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Uncovered data bits.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A3-S — Subjective

**Specific scientific task:** Derive what alteration class is invisible due to missing coverage and how an added check changes it

**Scenario family:** `grouped_uncovered`. Generate a grouped-check scheme with at least one data position in no checked subset.

**Required case conditions:** Require reasoning about an uncovered class, its detection status and targeted addition

**Required target evidence:** general even-intersection criterion applied to unchecked class plus justified targeted repair and limits

**Partial / borderline evidence:** general class rule but incomplete design implication

**Material misconception to reject:** one uncovered bit instance with no generalization

**Acceptable alternative reasoning:** valid set-based or plain-language explanation

**Proposed points:** 0 — Only one predicted unfamiliar result or recalled rule without derived class-level criterion. 1 — A generally applicable correct condition is derived and applied to a justified nontrivial case or boundary. 2 — A necessary-and-sufficient general condition, a verified nonempty witness or principled design consequence, and an explicit scope/limit.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## C4-A4 — Construct an evading pattern

**SOLO requirement:** Require a general condition over a class of alterations, with a justified consequence; no CRC/other-topic transfer.

**Relevant source IDs:** K17, K18, K19, R9, R10, R11



### C4-A4-Q1 — MCQ 1

**Specific scientific task:** Interpret an unfamiliar group-check constraint table

**Scenario family:** `grouped_checks`. Generate <=8 data positions and 2–3 explicitly declared nonempty checked subsets with an independent even-parity check bit for each.

**Required case conditions:** New scheme with explicit membership matrix and independent group parity bits

**Correctness for generated instance:** Every row is a declared parity equation over its member data positions

**Independent oracle:** For data-only flips, check j fails iff number of flipped data positions in subset j is odd.

**Three distinct misconception-targeted distractor meanings:** (1) Table layout changes tested relation; (2) Only total flip count matters; (3) A redundant check always improves detection.

**SOLO evidence role:** correct scheme abstraction

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Construct an evading pattern.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A4-Q2 — MCQ 2

**Specific scientific task:** Select or construct a nonzero alteration that preserves all stated group checks

**Scenario family:** `grouped_evasion`. Generate a small bounded grouped-check scheme with a nonempty error subset that preserves every check.

**Required case conditions:** Generate a verified nonempty all-checks-preserving data-only alteration

**Correctness for generated instance:** Nonempty flip set intersects every group in an even number of positions

**Independent oracle:** All checks pass iff each checked subset contains an even number of flipped data positions; demonstrate a nonempty witness by oracle.

**Three distinct misconception-targeted distractor meanings:** (1) Any even total flips suffice; (2) Any changed group must fail; (3) Check-bits repair errors.

**SOLO evidence role:** derive witness

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Construct an evading pattern.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A4-Q3 — MCQ 3

**Specific scientific task:** Analyze how an additional declared check affects the same previously invisible pattern

**Scenario family:** `grouped_add_check`. Generate a scheme and known witness; introduce a candidate new parity subset while holding the data-only error universe fixed.

**Required case conditions:** Add a candidate new group to SAME scheme and witness, check odd/even overlap

**Correctness for generated instance:** New check exposes witness iff its group overlaps witness oddly

**Independent oracle:** The new check detects that witness iff its overlap with witness positions has odd size; cannot promise universal superiority across arbitrary error universes.

**Three distinct misconception-targeted distractor meanings:** (1) More bits alone guarantee detection; (2) Check unrelated to witness still detects; (3) Added group always fixes all errors.

**SOLO evidence role:** generalizable constraint refinement

**Contract bounds:** Stay inside F1 numerical/cognitive bounds; Generate actual parameters for this attempt; never copy a fixed historical bit string; All assumptions necessary for truth must be visible to learner; Blueprint focus: Construct an evading pattern.

**Equivalence / fidelity:** Preserve the specific construct and slot reasoning operation, not numerical literals; Ensure exactly one correct proposition; three distractors express distinct false claims under THIS realized scenario; Avoid answering another item and avoid unexplained extra cognitive demand; No fixed option-letter mapping or pre-authored learner-facing stem.

**Validation:** Compute scientific outcome from actual generated instance using designated oracle; Check that generated visible propositions preserve distinct intended meanings and have one unequivocally correct alternative; Where semantics cannot be established confidently, flag for review; do not accept solely on syntax, IDs or equality; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



### C4-A4-S — Subjective

**Specific scientific task:** State a general evasion condition for a new check-family and build a verified nonzero witness or explain feasibility

**Scenario family:** `grouped_evasion`. Generate a small bounded grouped-check scheme with a nonempty error subset that preserves every check.

**Required case conditions:** Require class-level necessary+sufficient condition and independently justified witness

**Required target evidence:** necessary-and-sufficient all-groups even-intersection law plus justified independent witness and boundary

**Partial / borderline evidence:** general law plus incomplete witness rationale

**Material misconception to reject:** one lucky example without class statement

**Acceptable alternative reasoning:** logical, matrix, or set-based derivation

**Proposed points:** 0 — Only one predicted unfamiliar result or recalled rule without derived class-level criterion. 1 — A generally applicable correct condition is derived and applied to a justified nontrivial case or boundary. 2 — A necessary-and-sufficient general condition, a verified nonempty witness or principled design consequence, and an explicit scope/limit.

**Equivalence / fidelity:** Generated question must elicit the specified structural understanding, not merely a numerical answer; Do not embed the key explanation or cue a unique expected sentence; Allow materially equivalent explanations and justified alternative witnesses; No identical mandatory stem, bit pattern or response text.

**Validation:** Subjective question retains item reasoning demand within bounded generated scenario; Judge receives the real frozen question, real learner response and true instance facts; never pedagogy or MCQ score; Human calibration required for score and SOLO interpretation; Verify the slot-specific required_instance_conditions, not only the generic scenario family.



## Why not a 48-question fixed bank?

No reusable item records an `authored_stem_intent` containing an exact numerical question, `private_correct_option_id`, literal 4-option list, or required data string. A realized/frozen assessment legitimately does contain its own bit values, prose, four options and correct private identity, because that generated instance must be gradable. Those belong in an **attempt-specific** frozen package, never in the reusable pack.



## Fairness and cueing

Assessments may not receive pedagogy assignment, Tutor dialogue or prior learner results. Within a form avoid giving away a subjective explanation via earlier MCQ stems/distractors. MCQ→subjective order remains inherited but cueing must be empirically reviewed. Blueprint equivalence cannot be declared solely by symmetric YAML.
