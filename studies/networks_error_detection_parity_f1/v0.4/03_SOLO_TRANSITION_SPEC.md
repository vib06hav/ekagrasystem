# SOLO Transition Specification — v0.4 candidate



SOLO describes **observed structure in a task response**, not a permanent property of the learner. The 0/1/2 scoring choices here are proposed operational indicators, not psychometrically certified measurements. The Judge records structural evidence separately from answer correctness.



## C1: P → U

**Entry:** No demonstrated topic-level understanding; prerequisites separately screened.

**Target:** One usable sender-computed-parity / receiver-test aspect; learner identifies that an agreed check bit makes a complete frame satisfy the receiver test.

**Sufficient evidence:** Accurately identifies the data-dependent check bit or the corresponding complete-frame receiver test on a stated example; can link them when the prompt supplies context.

**Below:** Only vague extra bit / error prevention, no usable correct parity aspect.

**Not required:** No multi-flip laws, 2D parity, causal derivation or scheme comparison.

**Borderline:** A correct isolated selection may demonstrate one relevant feature, but cannot establish that the learner can independently explain the full mechanism.

**Domain references:** K1, K2, K3, R1.



**Generative validity note:** Correct meaning must be present for the generated instance; no fixed answer prose, bit string or prescribed calculation may define the transition.



## C2: U → M

**Entry:** At least one usable sender/receiver parity aspect.

**Target:** Several separately relevant features of 1D and 2D parity; multiple properties must be present without requiring a unified causal account.

**Sufficient evidence:** At least two distinct correctly identified properties, one pertaining to 1D parity and one to 2D parity, under prompted comparable situations.

**Below:** One correct property repeated in different wording or two variations of the same single example.

**Not required:** Explanations of WHY row/column constraints detect, why flips toggle parity, or how overhead trades against coverage; those are C3-level integration.

**Borderline:** A list of 1D and 2D facts is M even when there is no connective causal explanation. Requiring a polished because-chain here would bias toward R.

**Domain references:** K4, K5, K6, K7, K8, K9.



**Generative validity note:** Correct meaning must be present for the generated instance; no fixed answer prose, bit string or prescribed calculation may define the transition.



## C3: M → R

**Entry:** Several correct 1D/2D properties available but not necessarily causally integrated.

**Target:** A connected, correct explanation using sender-enforced relation → specified flips alter/preserve constraints → failed/passed tests → warranted detection/localization claim, with relevant limitations.

**Sufficient evidence:** The learner links at least two causal steps explicitly: what is tested, how the defined alteration affects that test, why the receiver concludes pass/fail/location. May express chain in any order.

**Below:** Correct but disconnected list (odd/even, rows/columns, 8 checks) without a case-linked causal explanation.

**Not required:** Unfamiliar check-group generalization or new theorem-level counterexample; C4 reserved.

**Borderline:** Can explain one concrete 2D alteration relationally without asserting a law for all possible partitions.

**Domain references:** K15, K16, R2, R3, R4, R7, R8.



**Generative validity note:** Correct meaning must be present for the generated instance; no fixed answer prose, bit string or prescribed calculation may define the transition.



## C4: R → EA

**Entry:** Connected causal explanation of 1D/2D parity constraints and their limitations.

**Target:** Principle-level abstraction: independently derive a generally applicable evasion/detection condition for a freshly defined subset-check system, then justify a counterexample or principled modification beyond one worked case.

**Sufficient evidence:** States a meaningful general condition covering a class of alterations, demonstrates why it follows from the group membership, and uses it to derive a nontrivial valid instance, counterexample, or generalizable design implication.

**Below:** One correctly predicted unfamiliar-pattern result by applying a supplied rule; that can show Relational application but is not by itself EA.

**Not required:** Transfer to CRC, Hamming codes, other networking layers, formal algebra, probabilistic error detection or completely new domains.

**Borderline:** A correct observation that one pair of flips passes, without explaining the arbitrary-group even-count condition, is not EA.

**Domain references:** K17, K18, K19, R9, R10, R11.



**Generative validity note:** Correct meaning must be present for the generated instance; no fixed answer prose, bit string or prescribed calculation may define the transition.



## Boundary analysis

**C1/C3:** A correct rule about the parity bit does not need a complete causal chain to establish U. If the learner spontaneously provides one, record but do not require it for C1.

**C2/C3:** Two independent correct parity properties support M even when no causal relationship is justified. C3 requires connecting the actual checked constraints, error pattern and receiver inference.

**C3/C4:** Predicting one unfamiliar-scheme result can remain Relational. EA needs a derived general condition applying across a class and a justified new consequence, counterexample or principled repair.

**Assessment limits:** Three selected-response items plus one subjective answer can miss understanding or reward guessing. Maintain the study gate only as a provisional operational rule pending expert calibration.
