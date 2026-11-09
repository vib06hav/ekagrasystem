# EkagraAI — Final Course Content Ground Truth (C1–C4)

**Status:** CURRICULUM CONTENT LOCKED  
**Version:** 1.0 · 8 November 2026  
**Domain:** Parity-based error detection in transmitted digital data  
**Audience:** Learners who have recently completed Indian Class 12, with **no assumed prior knowledge of bits, computer networks, or error-detection methods**  
**Purpose:** Authoritative reference for **what** the course teaches, its conceptual order, its section/subsection learning goals, and its scientific scope. This document is the curriculum baseline for subsequent system integration.

> **Scope of this lock:** The four major sections, 13 subsections, their content, teaching goals, and conceptual boundaries are locked from the course-design discussion. This does **not** certify experimental effectiveness, revise the study protocol, implement runtime changes, or lock how the material will be taught or assessed.

---

## 1. Course purpose and structure

The course teaches **error detection**, not computer science or networking in general. Foundational material about data, bits, and transmission is included only insofar as it is necessary to understand parity-based error detection.

**Overall conceptual progression:**

**Digital data and bit representation → transmission and corruption → extra checking information → even/odd parity and receiver verification → limits of single parity → full two-dimensional parity → single-error localization/correction and two-error detection → causal interpretation of checking results → generalization to unfamiliar checking groups and evaluation of additional checks.**

| Section | SOLO transition | Main learning progression | Subsections | Content status |
|---|---|---|---:|---|
| **C1 — Fundamentals of Error Detection** | Prestructural → Unistructural (P → U) | Establish a basic parity-based detection mechanism | 4 | Locked |
| **C2 — Capabilities and Limitations of Parity-Based Error Detection** | Unistructural → Multistructural (U → M) | Learn several correct properties of single and full 2D parity | 4 | Locked |
| **C3 — Understanding and Interpreting Parity-Check Results** | Multistructural → Relational (M → R) | Integrate checking mechanisms, observations, and justified inferences | 2 | Locked |
| **C4 — Generalizing and Evaluating Parity-Based Error Detection** | Relational → Extended Abstract (R → EA) | Generalize the parity principle and use it to predict and evaluate unfamiliar arrangements | 3 | Locked |

**SOLO interpretation:** These transitions denote the **section-level target for the structure of the learner's demonstrated understanding**. Introducing new prerequisite concepts may naturally involve smaller learning progressions inside a section; that does not create additional formal SOLO transitions. Neither the number of concepts taught nor the apparent difficulty of a question, by itself, establishes a SOLO level.

**Assessment boundary:** The study retains **one independent formal assessment at the end of each major section attempt**, not after each subsection. The design, formats, scoring rules, Paas timing, retries, advancement logic, and pedagogy assignment are governed by their separate study contracts and are **not specified or changed here**.

---

## 2. C1 — Fundamentals of Error Detection

**SOLO target:** P → U  
**Section objective:** Establish the foundational concepts required to understand how parity-based error detection works, without assuming any previous knowledge of bits or digital communication. The learner should acquire a basic, usable understanding of parity-bit construction and receiver-side checking.

### 1.1 — Data and Bits

**Content**

- What information and data mean in the context of digital communication.
- The idea that information exchanged between digital systems is represented as bits.
- What a bit is and why its possible values are `0` and `1`, at an introductory conceptual level.
- How individual bits form sequences representing digital data.
- Basic recognition of bit positions and counting `1`s, only as needed for later parity work.

**Teaching goal:** Understand what is being transmitted between computer systems and how that information is represented using bits.

**Depth boundary:** A brief, sufficient introduction; **not** a lesson on binary arithmetic, numeric-base conversion, character encoding, bytes, physical electronics, or computer architecture.

### 1.2 — Data Communication and Transmission Errors

**Content**

- Communication between systems: sender, receiver, and transmission channel/medium.
- What it means to send and receive a sequence of bits.
- What transmission corruption means: a mismatch between the bit sequence sent and the bit sequence received.
- The bit-flip model: a sent `0` arriving as `1`, or a sent `1` arriving as `0`.
- Where the relevant error occurs: **during transmission**, as represented by a changed received bit value.
- Why the receiver ordinarily lacks a direct copy of the original data and cannot simply inspect the received sequence to know whether it was altered.
- The consequent need for a way to detect possible corruption.

**Teaching goal:** Understand how data may become corrupted during communication, precisely what transmission error is being studied, and why a receiver needs an error-detection mechanism.

**Depth boundary:** The course does not study software bugs, wrong calculations, lost packets, or detailed physical noise processes as its error model.

### 1.3 — Additional Checking Information and Parity Bits

**Content**

- The motivation for transmitting extra information that helps the receiver check for corruption.
- **Redundancy:** additional transmitted information used for checking rather than being part of the original payload.
- Introducing a **parity bit** as one extra checking bit whose value depends on the original data.
- The principle that the parity bit is determined by an **agreed rule**, not selected arbitrarily.
- Why sender and receiver must use the same checking convention.

**Teaching goal:** Understand why additional checking information is introduced, what a parity bit is, and why its value depends on the original data and an agreed rule.

**Boundary with 1.4:** Establish the *purpose and definition* of a check bit here. **Do not require calculation of a concrete parity-bit value before introducing the even/odd rule in 1.4.**

### 1.4 — Even and Odd Parity Rules and Error Detection

**Content**

- **Even parity:** choose the parity bit so that the **complete transmitted bit sequence**, including that bit, contains an even number of `1`s.
- **Odd parity:** choose the parity bit so that the complete transmitted bit sequence contains an odd number of `1`s.
- Counting the `1`s in the original data and calculating/appending the parity bit under **both** conventions.
- Receiver-side checking: count the `1`s in the **complete received sequence, including the parity bit**, and test the agreed convention.
- Interpreting the result: a **failed** check detects a violation of the convention; a **passed** check means that this convention was satisfied, not that transmission was certainly error-free.
- Basic distinction among **detecting**, **locating**, and **correcting** an error. The detailed limitations are developed in C2.

**Teaching goal:** Understand how both even- and odd-parity conventions allow the sender to construct a checkable message and the receiver to detect a parity-rule violation.

**Boundary with C2:** C1 requires counting the number of `1`s in a message to construct/check parity. It does **not** require the general theorem about **odd versus even numbers of flipped transmitted bits**. Those are different counts, and the detection-limit theorem is C2 content.

### C1 section-level outcome — P → U

The learner has encountered the basic sender–receiver parity-checking mechanism and can correctly identify or apply **at least one meaningful, usable aspect** of parity-bit construction or receiver verification. A comprehensive integrated causal account is **not** the minimum required evidence at this stage.

**C1 excludes:** Detailed odd/even *flip-count* detection properties; 2D parity; localization procedures; multi-error causal analysis; generalized checking groups.

**C1 dependency chain:** **What is transmitted? → What can go wrong? → Why is extra checking information useful? → What shared parity rule makes detection possible?**

---

## 3. C2 — Capabilities and Limitations of Parity-Based Error Detection

**SOLO target:** U → M  
**Section objective:** Extend the learner's understanding of the mechanism from C1 by exploring the two primary limitations of single parity, then introducing **full two-dimensional parity** and its separate single-error correction and two-error detection capabilities.

### 2.1 — Limitations of Single Parity

**Content**

- Briefly reconnect with the parity construction and verification learned in C1; do not reteach it as a new mechanism.
- What happens when one or several transmitted bits flip.
- The rule that **odd numbers of flipped bits are detected**, whereas **even numbers of flipped bits leave a single parity check satisfied**, assuming the transmitted sequence initially met its rule. This applies to either even- or odd-parity convention.
- Why a single overall parity check cannot, on its own, identify **which bit** changed, even if exactly one bit flipped.
- Detection versus localization versus correction, in relation to the limitations above.
- The **two distinct limitations** motivating a richer checking arrangement: inability to locate an error, and failure to detect particular multi-bit error patterns.

**Teaching goal:** Understand the two major limitations of a single parity check: lack of error localization and missed even-flip error patterns.

**Scientific qualification:** Do **not** say single parity cannot detect multiple errors generally. It detects odd numbers of flips, including three, five, etc.

### 2.2 — Introduction and Construction of Two-Dimensional Parity

**Content**

- Motivation for checking information organized into multiple constraints instead of one overall parity check.
- Arranging original data bits in **rows and columns**.
- Calculating and adding a parity bit for each data row and each data column.
- The **corner parity bit** and the complete transmitted rectangular grid.
- Using an agreed parity convention to make each **complete row and complete column** satisfy its parity rule.
- How the receiver verifies all row and column checks of the **full transmitted grid**, including the check-bit cells.

**Teaching goal:** Understand how full two-dimensional parity is constructed and how multiple row and column checks operate on the transmitted bits.

**Scientific qualification:** The course consistently uses **full 2D parity with the corner check bit**, not a partially specified row-only/column-only variant.

### 2.3 — Single-Bit Error Localization and Correction

**Content**

- A transmission in which **exactly one transmitted bit** flips.
- The resulting failed row and column checks.
- Identifying the affected position at their intersection, including the possibility that the position is a check-bit cell.
- Correcting that one changed bit by reversing its received value.
- The **exactly-one-error assumption** required for reliable localization and correction.
- How this capability addresses the localization limitation of single parity.

**Teaching goal:** Understand how full two-dimensional parity can locate and correct a single flipped transmitted bit **under the stated single-error assumption**.

**Scientific qualification:** The pattern “one failed row and one failed column” does not **prove** that exactly one bit changed; other error patterns can yield the same checks (developed in C3).

### 2.4 — Two-Bit Error Detection

**Content**

- A transmission in which **two distinct transmitted bits** flip.
- The fact that **full two-dimensional parity detects every two-bit error pattern**.
- Comparison with single parity, which misses every two-bit flip pattern.
- The distinction between **detecting** the two-bit corruption and uniquely **locating/correcting both** changed bits.
- The fact that full 2D parity does **not generally** correct arbitrary two-bit errors uniquely.
- The contrast between single-error conditional correction and two-error detection.

**Teaching goal:** Understand full 2D parity's two-bit detection guarantee and distinguish that guarantee from reliable location or correction of both errors.

**Boundary with C3:** C2 establishes the capabilities and caveats. It does not require a unified derivation of all row/column outcomes or complex patterns such as deceptive three-bit results or undetected four-bit rectangles.

### C2 section-level outcome — U → M

The learner can demonstrate **several distinct, materially correct properties** of single parity and full 2D parity: single-parity detection/localization limitations; 2D construction; conditional localization/correction of one error; and detection of two errors without guaranteed unique correction. A single integrated causal explanation of all these aspects is **not yet required**.

**C2 dependency chain:** **Limitations of one check → Construction of multiple checks → Localizing/correcting one error → Detecting two errors.**

---

## 4. C3 — Understanding and Interpreting Parity-Check Results

**SOLO target:** M → R  
**Section objective:** Develop an integrated causal understanding of how changed bits affect parity-checking rules, how the observed results arise, and what the receiver is or is not justified in concluding. The emphasis is on **interpreting the meaning of the checking evidence**, not repeating row/column calculations or introducing another technique.

### 3.1 — Understanding the Relationships Behind Checking Results

**Content**

- How changing one transmitted bit affects **every check that includes that bit**.
- How multiple flipped bits combine within a given check.
- Why an **odd** number of flips within a checking group reverses whether that check passes, while an **even** number leaves its result unchanged, relative to an initially valid transmitted group.
- How the **positions and combinations** of changes determine which familiar row and column checks pass or fail.
- Connecting these causal relationships to the single- and two-dimensional parity properties already learned in C2.
- Reasoning **from an error pattern to checking results**, explaining *why* the observations arise rather than memorizing outcomes.

**Teaching goal:** Develop an integrated explanation of how bit positions, checking-group membership, and the combined effects of changes produce observed parity-check results.

### 3.2 — Interpreting Checking Evidence and Its Limitations

**Content**

- Reasoning **from observed checking results to possible error patterns**, without assuming that the original data are directly available to the receiver.
- Understanding that **different actual error patterns can produce identical checking results**.
- Explaining how a multi-bit pattern can imitate the checking result of one changed bit, so correction based on a presumed one-error case may be unjustified.
- Explaining how some multiple-error arrangements remain undetected, including the familiar **four-corner rectangle** in a row/column parity grid.
- Understanding how the number-of-errors assumption affects justified localization/correction claims.
- Integrating changed positions, affected rules, pass/fail patterns, ambiguity, and limits of receiver inference into coherent explanations.

**Teaching goal:** Interpret checking evidence using a causal model, explain why ambiguous or undetected outcomes arise, and distinguish justified inference from unsupported assumptions.

**Explanatory role of representative patterns:** Same-row versus different-row/column two-bit changes, a deceptive three-bit arrangement, and an undetected four-corner rectangle are examples supporting the **relational mechanism**, **not** independent error-pattern procedures to memorize or an exhaustive enumeration requirement.

### C3 section-level outcome — M → R

The learner can give an **integrated, causal explanation** linking:

**Changed bit positions → checks covering those bits → combined flip effects within each check → observed pass/fail results → warranted and unwarranted receiver conclusions.**

This reasoning works in **both directions**: from errors to observations, and from observations to plausible errors and their uncertainty. Merely calculating a failed row/column intersection, which was taught in C2, is **not sufficient** as the defining C3 achievement.

**C3 excludes:** Newly designed or unfamiliar non-grid checking arrangements; abstract general characterizations of arbitrary checking systems; formal code-design principles and algebraic coding theory. These are outside the familiar mechanism and reserved, where appropriate, for C4.

**C3 dependency chain:** **Explain how observations arise → Explain what those observations do and do not establish.**

---

## 5. C4 — Generalizing and Evaluating Parity-Based Error Detection

**SOLO target:** R → EA  
**Section objective:** Extend the integrated model developed in C3 beyond familiar single-parity and 2D-parity arrangements. Develop and justify general principles, use them to reason about unfamiliar small checking arrangements, and critically evaluate what additional checking information would or would not accomplish.

### 4.1 — Generalizing Parity Checking Beyond Rows and Columns

**Content**

- Revisiting single parity and 2D parity as **specific instances** of systems imposing parity rules over selected bits.
- Recognizing that a parity check does **not inherently require** a complete message, a row, or a column: it can apply to an **explicitly chosen group of bits**.
- Understanding how multiple checking groups may **overlap**, so one bit may participate in several rules.
- Connecting a group's members and its associated check information with how the receiver verifies its rule.
- Relating this generalized representation back to the familiar rule established in C1–C3.

**Teaching goal:** Recognize the broader structure shared by familiar parity systems, and understand how a checking rule can apply to explicitly defined groups outside a row/column grid.

**Critical prerequisite boundary:** Introduce the meaning of an unfamiliar **checking group** clearly before demanding analysis. This is still parity checking, **not a new error-detection algorithm**.

### 4.2 — Developing General Principles of Error Detection

**Content**

- Extending the familiar bit-flip/check-outcome relationships to **multiple overlapping groups**.
- Reasoning about the effects of an error pattern on all relevant checking rules.
- Developing and justifying the general condition for **detection**: at least one checking rule is violated by the received message.
- Developing and justifying the condition for **non-detection**: all checking rules remain satisfied despite corruption.
- In an initially valid parity system, establishing the equivalent flip-count condition: **every checking group contains an even number of flipped transmitted bits** for the corruption to escape every check.
- Supporting or challenging general claims using reasoned examples and counterexamples.

**Teaching goal:** Formulate and justify a principle that predicts when parity-based checking arrangements detect or miss an error, **independently of the spatial arrangement of their checks**.

**Scope qualification:** Group membership includes any transmitted checking bits that participate in a rule. The parity-preservation condition holds for either even- or odd-parity conventions, provided the convention was satisfied before transmission.

### 4.3 — Applying and Evaluating Generalized Checking Principles

**Content**

- Applying generalized checking principles to **small, unfamiliar and explicitly defined** overlapping groups.
- Predicting and justifying which specified error patterns are detected or undetected.
- Identifying valid **counterexamples** to overbroad claims about a checking arrangement.
- Evaluating whether one additional checking rule would detect a **specified previously undetected error pattern**.
- Recognizing that an extra rule may be redundant for the error patterns of interest, and therefore may not add detection capability.
- Recognizing the **redundancy overhead** of additional independent checking information and the trade-off with detection capability.
- Formulating and defending modest hypotheses or predictions about the consequences of changing a checking arrangement.

**Teaching goal:** Transfer a generalized parity principle to unfamiliar systems, and use it for **justified prediction, counterexample, and critical evaluation**, not merely more parity calculations.

**Boundary:** Designing an optimal detection system, developing CRC, or inventing a new coding algorithm is **not required**. Evaluating a simple added rule is sufficient subject matter for the higher-order reasoning goal.

### C4 section-level outcome — R → EA

The learner can **abstract and defend** a general principle from familiar parity mechanisms and **extend** it beyond the examples previously taught. They can use that principle to derive or defend conclusions about unfamiliar checking arrangements, undetected corruption, and the effects of additional checking rules. Merely counting `1`s in new groups, repeating a rule verbatim, or applying a familiar row-column procedure to a newly drawn diagram is **not, by itself, evidence** of Extended Abstract understanding.

**C4 excludes:** CRC computation, checksums as a separate mechanism, Hamming-code procedures, parity-check matrices, linear algebra, formal coding theory, exhaustive search over large patterns, or optimal code design. CRC may be mentioned **only as optional broader context** for why practical error-detection designs seek useful coverage with limited redundancy; understanding CRC is not a course learning outcome.

**C4 dependency chain:** **Recognize the general checking-group structure → Develop the general detection condition → Transfer, justify, and evaluate.**

---

## 6. Scientific content conventions — mandatory across the course

These definitions and invariants are part of the **content ground truth**. They do not prescribe example selection, UI, pedagogy, or assessment format.

| Topic | Ground-truth convention |
|---|---|
| **Bit** | One binary-valued unit, `0` or `1`; no binary arithmetic prerequisite. |
| **Transmission error** | One or more **transmitted bit values** differ from the corresponding received values. A bit flip is `0 ↔ 1`. |
| **Receiver information** | A receiver checks the received bits and agreed rules; it is **not presumed to possess the uncorrupted original message**. A teaching diagram may show both for explanation, but that is the instructor's outside perspective. |
| **Data vs. checking bits** | Distinguish original data/payload bits from extra transmitted checking bits. Errors can affect either unless a particular case expressly narrows the model. |
| **Parity conventions** | Teach **both even and odd parity** in C1. Each convention refers to the `1`-count in the **complete checked sequence**, including the parity bit(s) participating in that check. |
| **Receiver result** | **Fail** = violation detected; **pass** = that check's rule is satisfied. Pass does **not** guarantee no error occurred. |
| **Single-parity error law** | Starting from a valid transmitted sequence, an **odd** number of flips fails a single parity check; an **even** number leaves it passing. The flip count is not the count of `1`s. |
| **2D construction** | Use **full rectangular 2D parity**, including **all row parity bits, all column parity bits, and the bottom-right corner parity bit**, so every complete transmitted row and column satisfies the agreed convention. |
| **One-bit 2D case** | Exactly one flipped transmitted cell causes one complete row and one complete column check to fail. Their intersection locates that cell, conditional on the exactly-one-error assumption; reversing it corrects that cell. |
| **Two-bit 2D case** | Every pair of **distinct** flipped cells in full 2D parity is detectable. Detectability does **not** imply unique localization or correction of both. |
| **Multi-bit 2D cases** | Some different error patterns have the same check outcomes; a three-bit pattern can mimic a single-error syndrome. Four flipped data bits at the corners of a rectangle can leave all checks passing. |
| **General checking groups** | An agreed check may cover a specified set of transmitted positions. Groups may overlap. For the introductory C4 constructions, any extra checking information needed for an additional rule must be clearly defined. |
| **General non-detection rule** | Given an initially valid system of parity constraints, corruption is undetected **iff every checked group contains an even number of flipped transmitted positions**. A failure in at least one group detects corruption. |
| **Additional checks** | Adding a check is useful against a particular formerly missed pattern **only if that new rule fails for that pattern**. Extra check bits impose overhead; repeating equivalent information may not add detection power. |

**Notation and correctness requirement for later authoring:** Any instructional or assessment example must unambiguously identify (a) which positions are data cells versus checking cells, (b) the parity convention and complete checked groups, (c) position/coordinate convention, and (d) whether the observer is the receiver or an external instructor comparing sent and received data. Every displayed bit count, parity result, and error-position claim must be mathematically verified. This is a scientific-content requirement, not an instruction to use a particular presentation style.

---

## 7. Course-level SOLO boundaries

| Dimension | C1 — U | C2 — M | C3 — R | C4 — EA |
|---|---|---|---|---|
| **Characteristic demonstrated understanding** | One correct, usable parity aspect | Several correct, distinct parity properties | Integrated causal explanation of familiar mechanisms | Generalization and justified reasoning beyond familiar mechanisms |
| **Main subject matter** | Data, communication errors, redundancy, even/odd parity and checking | Single-parity limitations; construction and basic capabilities of full 2D parity | Relations among flips, check outcomes, ambiguity, and evidence | Arbitrary *small* checking groups; general detection principles; prediction and evaluation |
| **Not sufficient as defining evidence** | Merely naming words without a correct usable aspect | Only isolated one-fact recall | Reciting capabilities or rerunning a single-error location procedure | Merely calculating parity on a new diagram or reproducing a taught rule |
| **Do not prematurely require** | General multi-error theorem or 2D mechanism | Unified causal account of complex error patterns | Formal generalization to arbitrary non-grid structures | CRC/Hamming algorithms or optimal coding design |

**Caution:** This table clarifies curriculum intent; it is **not a scoring rubric**, a guarantee that teaching a section causes a SOLO transition, or permission to infer SOLO level solely from topic difficulty. Independent assessment design and empirical validation remain separate.

---

## 8. Locked scope, deferred design, and integration handoff

### Locked by this curriculum

1. **One coherent topic:** parity-based error detection of transmitted bit data.
2. **Four sequential SOLO sections:** C1 P→U, C2 U→M, C3 M→R, C4 R→EA.
3. **Exactly 13 course subsections:** 4 + 4 + 2 + 3, as listed above.
4. **The content boundaries:** C1 basics, C2 multiple distinct capabilities, C3 integrated causal interpretation, C4 abstraction/generalization/evaluation.
5. **Full 2D parity with corner bit**; conditional one-error correction; guaranteed two-error detection; explicitly acknowledged multi-error limitations.
6. **Novice accessibility:** all needed vocabulary and representation conventions must be established before they are relied upon.

### Not decided by this document

- Which pedagogy (P1 Worked Examples, P2 Guided Questioning, P3 Contrasting Cases) teaches which subsection or activity, and how it is delivered.
- Tutor dialogue, examples, scaffolds, pacing, activity boundaries, or when learner checks occur during teaching.
- The independent question-writing prompts, question blueprints, judging/rubric revisions, or assessment validity procedures.
- Study-level timing, Paas instrumentation, randomization, retry behavior, participant flow, and database/runtime contracts.
- Whether the professor's proposed **three-topic Experiment 1** or the narrower existing parity-focused pilot is the active system-integration target. This curriculum defines the **parity course content**; it does not silently resolve that separate research design decision.

### Hand-off rule for implementation

Treat **this Markdown file as the curriculum-content source of truth** when aligning scientific knowledge objects, Tutor authoring scopes, subsection sequencing, and later assessment coverage. If an existing YAML, prompt, or UI text contradicts a locked content statement, flag the conflict for explicit research review; **do not silently rewrite the research protocol or conflate content design with pedagogy/assessment design**.

---

## 9. Disciplinary and educational grounding

The course's scientific subject matter is aligned with standard introductory references; its **C1–C4 subsection structure is a project-specific SOLO-oriented adaptation**, not a textbook syllabus copied verbatim.

- **Kurose & Ross, _Computer Networking: A Top-Down Approach_, §6.2:** Error-detection and correction principles, single parity, 2D parity, and the progression toward other methods.
- **Behrouz A. Forouzan, _Data Communications and Networking_, Chapter 10:** Transmission errors, redundancy, error detection and error correction.
- **Peter L. Dordal, _An Introduction to Computer Networks_:** Parity-based detection/correction principles and reasoning exercises concerning detectable, correctable, and undetectable patterns.
- **OpenStax, _Introduction to Computer Science_:** Bits and basic digital representation as prerequisites, used here only to the depth needed for parity.
- **Biggs and Collis, SOLO taxonomy:** Structural distinction among Unistructural, Multistructural, Relational, and Extended Abstract observed learning outcomes. The transition labels express intended outcomes, not claims of measured learner advancement.

---

**End of authoritative course-content specification.**
