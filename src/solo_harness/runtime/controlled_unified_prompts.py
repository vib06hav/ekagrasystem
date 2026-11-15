"""# CHANGED: Pure move-scoped Tutor/Judge prompts for reviewed C2--C4 moves.

C1's mature V3.2 prompts are deliberately not modified.  C2--C4 share
C1's wire schema and ledger, with their own locked scientific case slices.
"""
from __future__ import annotations

import json
import re

from solo_harness.runtime.v051_conversation import ConversationJudgeOutput, V051TutorOutput
from solo_harness.runtime.controlled_executor import contract, contract_hash


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
    return (rules + "\n[ACTIVE_MOVE_CONTEXT]\n" + json.dumps(payload, ensure_ascii=False,
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
    return (rules + "\n[CURRENT_MOVE_JUDGE_CONTEXT]\n" + json.dumps(payload,
            ensure_ascii=False, sort_keys=True, separators=(",", ":")) +
            "\n[OUTPUT_SCHEMA]\n" + json.dumps(ConversationJudgeOutput.model_json_schema(),
                                                     sort_keys=True, separators=(",", ":")))
