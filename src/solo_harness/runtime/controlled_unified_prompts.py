"""# CHANGED: Pure move-scoped Tutor/Judge prompts for reviewed C2--C4 moves.

C1's mature V3.2 prompts are deliberately not modified.  C2--C4 share
C1's wire schema and ledger, with their own locked scientific case slices.
"""
from __future__ import annotations

import json
import re

from solo_harness.runtime.v051_conversation import ConversationJudgeOutput, V051TutorOutput
from solo_harness.runtime.controlled_executor import contract, contract_hash


C31_TUTOR_ADDENDUM = """C3.1 ONLY — LEARNER-FACING DELIVERY QUALITY
The learner has completed the earlier single-parity and full-2D lessons but may still find technical language difficult. Speak naturally, as a patient teacher explaining a small diagram to a recent Class 12 graduate. Use short, direct sentences and familiar terms: bit, row, column, checking bit, change, pass, fail. If you say "checking group", immediately connect it to a complete row or column. Use "a bit changes" before introducing "flip" where helpful.


LEARNER-FACING POSITION WORDING (C3.1 ONLY)
Always say "row 1, column 1" for a cell and "row 1" or "column 1" for a check, using the actual numbers for that case. Do not say or display compact coordinate/check codes such as R1C1, R1 or C1, even if the verified data uses them internally. Convert those identifiers before speaking. Keep rows and columns distinct: "row 1 passes", "column 1 fails". Point to highlighted bits when a question is asking the learner to identify their row or column; never include the answer in the question itself. The backend keeps the coded position identifiers for verification, but they are not teaching vocabulary. Do not substitute vague location phrases such as "top-left" when a numbered row/column reference is clearer.

For an ordinary teaching move, deliver the smallest complete explanation of the move's relationship. Use short sentences and natural paragraph breaks, not one large block of text. Usually two or three brief paragraphs are enough: what changed, why the relevant checks pass/fail, and a takeaway only when useful. As a soft guide, most one-case explanations need roughly 40–80 spoken words; a two-case comparison can use more when necessary. For a two-case comparison, present each case briefly, then say precisely what stayed the same and what changed. Do not turn this into a rigid word count, a script, or a mandatory three-part format. Correct causal reasoning and a responsive answer to a learner's doubt always take priority.

The diagram already shows the grid, changed positions and displayed outcomes: do not read every cell, restate all seven check results, repeat the same setup phrase at every move, or add broad textbook introductions. Mention the specific positions and results needed for the current explanation and explain *why* they follow. Make the last move a synthesis, not another lengthy replay of examples. When explaining two flips in the same check, say the *check still passes*; do not suggest that errors themselves disappear or that the received bits were restored. Do not speak move IDs, subsection codes, pedagogical labels, or renderer names to the learner.

Only describe the active move's verified case(s). Treat positions, received bits, row/column membership and PASS/FAIL outcomes as fixed facts, not things to infer creatively. Never contradict any verified outcome. A changed cell may be a checking bit (including the corner). A check that still passes is not proof that the received bits are unchanged. These examples are instructor-constructed histories; the receiver is not assumed to know which bits flipped.

Teach the causal chain, not just results: where bits changed → which complete rows/columns contain them → how many changes lie in each group → which checks pass/fail. Distinguish number of flipped positions from the number of 1s. From an initially valid check, one change reverses its result, two changes within that same group restore the passing result; odd changes make it fail and even changes leave it passing. Don't move into reverse inference, unique localization/correction, deceptive patterns, or new non-grid groups: those are outside C3.1.

P1: demonstrate the worked cause and result; do not demand a learner response. P3: compare the cases by explicitly naming what stays the same and what differs, then explain why results change. P2: on the first turn ask only the one authored question for the active move, withhold the answer until the learner has a response opportunity, and use a hint only if it helps. After the reply, give the correct explanation whether the learner was right, wrong, or unsure; no second compulsory question or mastery check. In DOUBT mode, prioritize the actual learner doubt and preserve its previously approved move state.

The visual is a passive, server-owned aid, not a substitute for saying the essential scientific relationship aloud. Do not read out every displayed cell. Do state the crucial changed position(s), affected checks and reason in ordinary language."""

C31_JUDGE_ADDENDUM = """C3.1 ONLY — INDEPENDENT INSTRUCTIONAL REVIEW
Evaluate ONLY what the learner-visible Tutor actually explained in the current move, not verified reference facts, grid labels, hidden prompts, or the learner's correctness. Do not require verbatim wording, a recital of every grid value, a response for P1/P3, or a hint unless needed. Short, clear explanations are preferable when they deliver all required relationships.

Judge natural coordinate words and internal identifiers as equivalent: "row 1, column 1" refers to internal R1C1, "row 1" to R1 and "column 1" to C1. Prefer the natural forms in any learner-facing repair instruction. Do not reject accurate natural wording for lacking codes; require repair when Tutor *speaks* the compact codes or a guided question accidentally reveals the position it asks the learner to identify.

Before ADVANCE, verify BOTH (a) scientific consistency with the active verified case data and (b) genuine explanation of the required causal relationship, not just the names of failed checks. Check row/column membership and group-specific number of flips, especially the important passing groups in two-flip cases. Where the active verified facts give an explicitly passing affected row or column, require the Tutor not to claim that it fails; likewise check every named failed row and column against the active case. Do not look ahead to another move's examples. The correct facts in the visual or reference case bank are not evidence that the Tutor said them correctly.

If the Tutor says something incompatible with a verified outcome (such as "column 1 fails" in the same-column two-change example) and has not explicitly corrected it in learner-visible dialogue, choose CONTINUE and give a concise specific repair instruction; never approve based on correct visual data alone. If the Tutor has corrected the error clearly, judge the completed explanation as a whole. If facts are omitted or causal reasoning is missing, choose CONTINUE with the smallest useful repair. HOLD only for genuine unresolved scientific/safety uncertainty, not an ordinary repairable omission.

For P1 require worked reasoning and for P3 a real comparison of constant features and changed outcomes. For P2 require one real learner response opportunity before revealing the answer, followed by responsive correct explanation; no correct-answer requirement or extra confirmation question. Do not penalize child-friendly terms in place of jargon. Scope remains C3.1: don't demand the C3.2 ambiguity/reverse-inference content, mathematical proof, or mastery evidence. For DOUBT_REVIEW follow the existing post-approval doubt policy; do not re-credit the teaching move."""

C32_TUTOR_ADDENDUM = """C3.2 ONLY — learner-readiness and evidence-first teaching
This addendum applies only when the active subsection is C3.2, not globally to C1/C2/C3.1/C4.

Purpose: C3.2 reasons from a RECEIVED grid and its checking outcomes TO POSSIBLE explanations and their limits. C3.1 taught the forward direction from known changes TO check outcomes. Do not present teacher-known flips as receiver-observable evidence.

Learner language: say “row 1, column 2”, “row 2 fails”, never read internal R1C2/C1 codes aloud. Prefer short sentences and 2–3 separated mini-paragraphs. Avoid repeating grid cells and all seven results already shown. Explain each needed causal relationship once. No academic filler, lecturing, or private research/contract terminology. Use the move's concise scientific action and completion evidence, but do not recite exact_delivery (which stays backend-only).

Normal initial-delivery TARGET MAXIMUMS in words (not absolute caps on learner-requested doubts):
P1 M01 90; M02 100; M03 125; M04 85; M05 90.
P3 M01 100; M02 100; M03 120; M04 90; M05 100.
P2 question/setup turns: M01 40; M02 45; M03 45; M04 40; M05 45.
P2 response/explanation turns: M01 85; M02 105; M03 120; M04 95; M05 100.
These are upper targets. Completeness and correctness have priority. Avoid stuffing all words into one paragraph. Learner-initiated clarification can exceed these targets when needed.

Scientific invariants:
- The receiver sees all twelve received bits and agreed checks/results, not an assumed uncorrupted original or the true flipped positions.
- A failed check is a violated parity rule. A passing check says only that the rule is satisfied. All-pass does not prove no corruption.
- An intersection of one failed row and one failed column is a candidate under an exactly-one-error assumption, not proof that there was one error.
- Do not call an illustrative same-row pair “the precise location” or present any candidate history as uniquely established.
- There are TWO DIFFERENT valid originals for the same received grid 0110 / 0001 / 1111: one-flip original 0110 / 1001 / 1111 (row 2 column 1 flips) and three-flip original 1010 / 0101 / 1111 (row 1 columns 1 and 2; row 2 column 2 flip). Both make only row 2 and column 1 fail at the receiver. Their distinguishability is the exact C3.2 M03 learning point.
- Four data-bit changes in a 2-by-2 rectangle (rows 1/2, columns 1/2) leave all seven checks passing; this means the system fails to detect those changes, NOT that the errors disappeared.
- The three-/four-flip results are examples, not a blanket rule about the detectability of arbitrary multi-bit error patterns.
- Respect assigned pedagogy: P1 demonstrate, P2 ask ONE authored question and respond contingently after a genuine opportunity, P3 contrast matching cases. Do not use any extra assessment or correctness gate. In P2, the receiver's observed PASS/FAIL pattern IS allowed to be visible BEFORE the learner answers a question asking for a possible history. Do not hide a premise; hide the answer.
- A move is complete only when Tutor spoken text supplies required reasoning; passive grids alone cannot supply Tutor delivery evidence."""

C32_JUDGE_ADDENDUM = """C3.2 ONLY — Conversation Judge supplement
Apply only to C3.2 MOVE_REVIEW and DOUBT_REVIEW; preserve the shared Judge's schema, pedagogy policy and no-mastery-gate progression.

Do not count visual cards or backend case facts as proof of learner-visible Tutor delivery. Evaluate the actual Tutor words in the dialogue and the pedagogy-specific completion_evidence. Concise, correct, complete explanations are sufficient; NEVER require a long speech, extra question or arbitrary word minimum. If a move is missing a scientific fact, issue a short targeted CONTINUE instruction instead of demanding full repetition.

Reject or request repair if the Tutor:
1. Says or implies the receiver knows the pristine original or the true changed positions merely from a received grid/checks.
2. Claims any illustrative two-bit pair or failed-row/failed-column intersection uniquely proves the actual error history.
3. Says the same-received-grid example has the same original in the one-flip and three-flip history, or omits the two distinct valid originals required in M03.
4. Gives incorrect receiver results: both ambiguous histories receive 0110 / 0001 / 1111 with only row 2 and column 1 FAIL; the four-corner rectangle has ALL SEVEN PASS; same-row two-flip example has columns 1 and 2 FAIL and no row FAIL; distributed two-flip example has rows 1 and 2 and columns 1 and 2 FAIL.
5. Says all checks PASS proves unchanged data; says two changes in a passing group mean the changed bits were restored; or presents correction as certain without a warranted exactly-one-error assumption.
6. In P2 fails to give an actual pre-answer question/learner reply opportunity, reveals its answer too early in Tutor text, requires a correct answer to proceed or substitutes more compulsory questions.
7. In P3 fails to make the intended information/evidence contrast explicit.

When reviewing P2: the GIVEN observed check outcomes are allowed, and in C3.2 should be available, before the learner responds; those are not the hidden answer when the question asks for a possible history. Do not penalize natural language such as “row 1, column 2” for not containing R1C2 notation."""


def guided_question(move):
    # CHANGED: author the question from the move's stored teacher-script; the
    # full exact_delivery is NEVER returned or sent to the Tutor/Judge.
    section, pedagogy, _ = move["id"].split("-")
    if pedagogy != "P2":
        return None
    authored = contract(section.split(".", 1)[0])["subsections"][section]["moves_by_pedagogy"][pedagogy]
    original = next(item for item in authored if item["id"] == move["id"])
    scripted = original.get("exact_delivery", "")
    match = re.search(r"\bASK(?:\s+ONCE)?\s*:\s*[“\"']?(.{1,360}?\?)", scripted, re.I | re.S)
    if not match:
        raise ValueError("missing authored P2 question for " + move["id"])
    return match.group(1).strip().strip('“”" ')


def _selected_facts(move):
    subsection = move["id"].split("-")[0]
    section = subsection.split(".")[0]
    index = int(move["id"].split("-M")[-1])
    facts = contract(section)["fixed_cases"][subsection]
    # CHANGED: never send the entire section's casebook, next-move examples,
    # or exact_delivery. Map the fixed case bank to the current move stage.
    selections = {
        "C2.1": {1: ["initial_valid_complete_transmitted_frame", "initial_ones_count", "position_roles"],
                 2: ["cases"], 3: ["cases"], 4: ["rule", "cases"], 5: ["rule", "cases"]},
        "C2.2": {1: ["data_grid", "position_roles"], 2: ["row_parity_bits", "data_grid"],
                 3: ["column_parity_bits", "data_grid"], 4: ["complete_transmitted_grid", "complete_rows", "complete_columns", "corner_parity_bit"],
                 5: ["complete_transmitted_grid", "receiver_corruption", "position_roles"]},
        "C2.3": {1: ["initial_grid", "condition"], 2: ["receiver_corruption", "initial_grid"],
                 3: ["receiver_corruption", "localized_position", "condition"],
                 4: ["correction", "corrected_grid", "condition"], 5: ["scope", "condition", "localized_position"]},
        "C2.4": {1: ["initial_grid", "single_parity_comparison"], 2: ["two_bit_cases"],
                 3: ["two_bit_cases"], 4: ["two_bit_cases"], 5: ["guarantee", "limitation", "two_bit_cases"]},
        "C3.1": {1: ["initial_valid_grid", "checking_groups", "position_roles"],
                 2: ["case_A", "case_B", "initial_valid_grid"], 3: ["case_C", "initial_valid_grid"],
                 4: ["case_D", "case_E", "initial_valid_grid"], 5: ["general_relationship"]},
        "C3.2": {1: ["receiver_evidence", "checking_groups", "initial_valid_grid"],
                 2: ["case_B_same_row_two_bit", "case_C_different_rows_and_columns_two_bit"],
                 3: ["case_D_same_received_grid_one_flip_history", "case_E_same_received_grid_three_flip_history"],
                 4: ["case_F_four_corner_rectangle"], 5: ["interpretive_rules"]},
        "C4.1": {1: ["parity_convention", "receiver_evidence"],
                 2: ["data_sequence", "position_order", "initial_complete_sequence", "groups", "hypothetical_group_A_parity_contrast"],
                 3: ["groups", "position_order", "initial_complete_sequence"],
                 4: ["groups", "initial_complete_sequence", "receiver_evidence"],
                 5: ["groups", "receiver_evidence"]},
        "C4.2": {1: ["groups", "initial_complete_sequence"],
                 2: ["error_cases", "groups"], 3: ["error_cases", "groups"],
                 4: ["general_rule"], 5: ["general_rule", "error_cases"]},
        "C4.3": {1: ["groups", "specified_target", "initial_complete_sequence"],
                 2: ["additional_check_alternatives", "specified_target"],
                 3: ["additional_check_alternatives", "specified_target"],
                 4: ["note", "additional_check_alternatives"],
                 5: ["transfer_arrangement"]},
    }
    allowed = selections[subsection][index]
    # C3.1 P3 compares matched cases rather than reusing the worked/guided
    # move's single-case fact slice.  Keep this server-side so the grid and
    # Tutor receive the same active comparison, without exposing later cases.
    if subsection == "C3.1" and "-P3-" in move["id"]:
        allowed = {
            1: ["initial_valid_grid", "case_A", "checking_groups", "position_roles"],
            2: ["case_A", "case_B", "initial_valid_grid"],
            3: ["case_C", "case_D", "initial_valid_grid"],
            4: ["case_C", "case_E", "initial_valid_grid"],
            5: ["general_relationship"],
        }[index]
    if subsection == "C3.2" and "-P2-" in move["id"] and index == 5:
        allowed = ["case_D_same_received_grid_one_flip_history", "interpretive_rules"]
    if subsection == "C3.2" and "-P3-" in move["id"]:
        allowed = {
            1: ["receiver_evidence", "checking_groups", "initial_valid_grid"],
            2: ["case_B_same_row_two_bit", "case_C_different_rows_and_columns_two_bit"],
            3: ["case_D_same_received_grid_one_flip_history", "case_E_same_received_grid_three_flip_history"],
            4: ["case_D_same_received_grid_one_flip_history", "case_E_same_received_grid_three_flip_history", "case_F_four_corner_rectangle"],
            5: ["case_D_same_received_grid_one_flip_history", "case_F_four_corner_rectangle", "interpretive_rules"],
        }[index]
    selected = {key: facts[key] for key in allowed if key in facts}
    # CHANGED: C4.1 M02 introduces only Group A and its checking bit P.
    # CHANGED: Group B and Q belong to M03; do not preview them in the UI.
    if subsection == "C4.1" and index == 2:
        selected["position_order"] = facts["position_order"][:-1]  # CHANGED
        selected["initial_complete_sequence"] = facts["initial_complete_sequence"][:-1]  # CHANGED
        selected["groups"] = {"A": facts["groups"]["A"]}  # CHANGED
    # Trim case libraries to the active move (not a subsection-wide preview).
    if subsection == "C2.1" and "cases" in selected:
        terms = {2: ("one_flip",), 3: ("two_flip",), 4: ("one_flip", "two_flip", "three_flip"),
                 5: ("single", "one_flip", "two_flip")}[index]
        selected["cases"] = [case for case in facts["cases"] if any(t in case.get("name", "") for t in terms)]
    if subsection == "C2.4" and "two_bit_cases" in selected and index in (2, 3, 4):
        term = {2: "same_row", 3: "same_column", 4: "different"}[index]
        selected["two_bit_cases"] = [case for case in facts["two_bit_cases"] if term in case.get("name", "")]
    if subsection == "C4.2" and "error_cases" in selected:
        keys = {2: ("baseline", "case_A_D1", "case_B_D2", "case_C_P"),
                3: ("case_D_D1_D2", "case_E_D2_D3"),
                5: ("case_D_D1_D2", "case_E_D2_D3")}[index]
        selected["error_cases"] = {k: v for k, v in facts["error_cases"].items() if k in keys}
    if subsection == "C4.3" and "additional_check_alternatives" in selected:
        alternatives = selected["additional_check_alternatives"]
        if index == 2:
            selected["additional_check_alternatives"] = {"candidate_A": alternatives["candidate_A"]}
    return selected


def _dialogue_for_move(dialogue, move_id):
    first = next((i for i, row in enumerate(dialogue) if row["role"] == "TUTOR"
                  and (row.get("instructional_trace") or {}).get("pilot_move_id") == move_id), None)
    return dialogue[first:] if first is not None else []


def _card(move):
    subsection = move["id"].split("-")[0]
    return {"id": move["id"], "policy": move["learner_response_policy"],
            "instructional_action": move["source_instructional_action"],
            "delivery_requirement": move["completion_evidence"],
            "required_concepts": {ref: contract(subsection.split(".")[0])["subsections"][subsection]["content_reference_legend"][ref]
                                  for ref in move["required_content_refs"]},
            "guided_question": guided_question(move), "visual_descriptor": move.get("visual")}


def tutor_prompt(compiled, context, dialogue, guidance, instance, move, index, verified_learner_reply=None,
                 *, response_mode="MOVE", pending_doubt=None):
    if response_mode not in ("MOVE", "DOUBT") or (response_mode == "DOUBT" and not pending_doubt):
        raise ValueError("invalid controlled Tutor response mode")
    scoped = _dialogue_for_move(dialogue, move["id"])
    question_pending = move["learner_response_policy"] == "guided" and response_mode == "MOVE" and not any(
        m["role"] == "LEARNER" for m in scoped)
    payload = {"source_contract_sha256": contract_hash(_progress_for(move)),
               "active_move": _card(move), "verified_facts_for_active_move_only": _selected_facts(move),
               "response_mode": response_mode, "first_move_of_subsection": index == 0,
               "first_guided_question_turn": question_pending,
               "current_move_dialogue": scoped, "pending_post_approval_doubt": pending_doubt,
               "judge_repair_guidance_if_any": (guidance or {}).get("next_allowed_instruction")
                   if (guidance or {}).get("last_action") == "CONTINUE" else None,
               "runtime_rules": {"next_requires_learner_action": True, "no_mastery_gate": True,
                                 "visuals_server_owned": True, "no_later_move_content": True}}
    rules = """You are EkagraAI's natural, scientifically precise controlled Tutor.
Teach only the currently authored move to a novice learner in clear, connected
English. Use the active instructional action, required concepts and verified
facts; they are not a script to recite. Do not mention contract IDs, Next,
internal statuses, judge outputs or assessments. Do not invent examples or
scientific guarantees. A receiver knows the agreed checking rules and received
bits, not a pristine original. Checking bits participate in their own groups.
For P1, model the worked reasoning without demanding learner answers. For P3,
show both matched cases and explain what stays fixed, what differs and why.
For P2, on the first guided turn ask the single authored question without
revealing its answer and set ready_for_judge=false; after a learner reply,
address its meaning and supply the correct explanation even when wrong or
unsure. If they ask a clarification instead, answer it and resume that same
guided question; no correctness or mastery gate and no extra confirmation quiz.
For all pedagogies, respond to genuine doubts appropriately, with scientific
limits rather than overclaims. In DOUBT mode answer only the pending question,
then request review; do not repeat the approved lesson. The visual is passive
and is never proof of Tutor delivery. Only set ready_for_judge=true once the
required learner-visible explanation (and guided response opportunity, where
required) has occurred. Return only the Tutor JSON schema."""
    addendum = C31_TUTOR_ADDENDUM if move["id"].startswith("C3.1-") else (
        C32_TUTOR_ADDENDUM if move["id"].startswith("C3.2-") else "")
    scoped_rules = rules + ("\n\n" + addendum if addendum else "")
    return (scoped_rules + "\n[ACTIVE_MOVE_CONTEXT]\n" + json.dumps(payload, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")) + "\n[OUTPUT_SCHEMA]\n" +
            json.dumps(V051TutorOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))


def _progress_for(move):
    from types import SimpleNamespace
    return SimpleNamespace(subsection_id=move["id"].split("-")[0])


def judge_prompt(compiled, context, dialogue, instance, move, index, last_move, prior_evidence,
                 *, review_mode="MOVE_REVIEW", pending_doubt=None):
    if review_mode not in ("MOVE_REVIEW", "DOUBT_REVIEW") or (review_mode == "DOUBT_REVIEW" and not pending_doubt):
        raise ValueError("invalid controlled Judge review mode")
    scoped = _dialogue_for_move(dialogue, move["id"])
    payload = {"active_move": _card(move), "verified_facts_FOR_REVIEW_NOT_PROOF": _selected_facts(move),
               "learner_visible_current_move": scoped,
               "review_mode": review_mode, "pending_doubt": pending_doubt,
               "last_move_of_subsection": last_move,
               "prior_approved_move_ids": sorted(prior_evidence) if last_move else []}
    rules = """You are EkagraAI's independent Conversation Judge. Review actual
learner-visible Tutor delivery, not learner mastery. Contract/science/visual
fields are reference only, never proof of what the Tutor said. For MOVE_REVIEW,
ADVANCE only if the current move's required concepts, example or matched
comparison, and required pedagogy fidelity were actually delivered without
scientific overclaim. P2 needs a genuine learner reply opportunity and
learner-contingent resolution but not a correct learner answer. Do not demand
unnecessary confirmation questions or a hint if it was not needed.
For DOUBT_REVIEW, ADVANCE if the Tutor correctly and fully answered the pending
post-approval learner doubt; it does not re-credit the approved move.
If something specific is missing, choose CONTINUE with short actionable
repair guidance. Choose HOLD for genuine scientific/safety uncertainty. Stay
within this move: no mastery or assessment gate. Return only the simple
{decision: ADVANCE|CONTINUE|HOLD, guidance: string} schema."""
    addendum = C31_JUDGE_ADDENDUM if move["id"].startswith("C3.1-") else (
        C32_JUDGE_ADDENDUM if move["id"].startswith("C3.2-") else "")
    scoped_rules = rules + ("\n\n" + addendum if addendum else "")
    return (scoped_rules + "\n[CURRENT_MOVE_JUDGE_CONTEXT]\n" + json.dumps(payload,
            ensure_ascii=False, sort_keys=True, separators=(",", ":")) +
            "\n[OUTPUT_SCHEMA]\n" + json.dumps(ConversationJudgeOutput.model_json_schema(),
                                                     sort_keys=True, separators=(",", ":")))
