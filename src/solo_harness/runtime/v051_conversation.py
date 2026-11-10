"""Minimal semantic contracts and prompt assembly for the v0.5 candidate."""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Wire(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ConversationJudgeOutput(_Wire):
    """The Judge makes the semantic decision; persistence owns its provenance."""
    decision: Literal["CONTINUE", "ADVANCE", "HOLD"]
    guidance: str = Field(min_length=1, max_length=4000)


class V051TutorOutput(_Wire):
    """Natural learner-facing instruction plus a non-authoritative review hint."""
    learner_message: str = Field(min_length=1, max_length=4000)
    ready_for_judge: bool = False


def v051_tutor_prompt(compiled, progress, context: dict, dialogue: list[dict], judge_guidance: dict | None, instructional_instance: dict | None = None) -> str:
    """Compile only the persisted candidate snapshot into a Tutor request."""
    payload = {
        "active_section_id": context["parent_cell"]["transition_id"],
        "active_subsection": context["subsection"],
        "global_pedagogy": context["global_pedagogy"],
        "section_pedagogy_cell": context["parent_cell"],
        "subsection_pedagogy_cell": context["child_cell"],
        "locked_knowledge": context["knowledge"],
        "scope_restrictions": context["restrictions"],
        "previous_conversation_judge_guidance": judge_guidance,
        "verified_instructional_instance": instructional_instance,
        "dialogue": dialogue,
        "runtime_rules": {"no_mastery_gate": True, "tutor_readiness_is_non_authoritative": True,
                          "judge_review_follows_tutor_readiness_without_mandatory_learner_turn": True,
                          "no_assessment_content_or_keys": True},
    }
    return (compiled.authored["v051"]["prompts"]["TUTOR_PROMPT.md"]
            + "\n\n[V051_ACTIVE_SUBSECTION_TUTOR_CONTEXT]\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n\n[OUTPUT_SCHEMA]\n"
            + json.dumps(V051TutorOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))


def conversation_judge_prompt(compiled, progress, context: dict, dialogue: list[dict], instructional_instance: dict | None) -> str:
    payload = {
        "active_section_id": context["parent_cell"]["transition_id"], "active_subsection": context["subsection"],
        "global_pedagogy": context["global_pedagogy"], "section_pedagogy_cell": context["parent_cell"],
        "subsection_pedagogy_cell": context["child_cell"], "locked_knowledge": context["knowledge"],
        "restrictions": context["restrictions"], "verified_instructional_instance": instructional_instance,
        "dialogue": dialogue,
    }
    return (compiled.authored["v051"]["prompts"]["CONVERSATION_JUDGE_PROMPT.md"]
            + "\n\n[V051_CONVERSATION_JUDGE_CONTEXT]\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n\n[OUTPUT_SCHEMA]\n"
            + json.dumps(ConversationJudgeOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))


def controlled_c11_tutor_prompt(compiled, context: dict, dialogue: list[dict], guidance: dict | None,
                                instructional_instance: dict, move: dict, index: int,
                                verified_learner_reply: dict | None = None) -> str:
    """Pilot-only: expose exactly one authored move, not a free whole-subsection setlist."""
    from solo_harness.studies.controlled_c1 import contract_hash
    local_cell = dict(context["child_cell"])
    local_cell["core_moves"] = [source for source in local_cell["core_moves"] if source["id"] == move["id"]]
    payload = {
        "controlled_pilot": "C1.1_ONLY", "contract_sha256": contract_hash(),
        "active_subsection": context["subsection"], "global_pedagogy": context["global_pedagogy"],
        "section_pedagogy_cell": context["parent_cell"], "active_child_cell": local_cell,
        "current_move": move, "move_index_zero_based": index,
        "verified_instructional_instance": instructional_instance["public"],
        "locked_knowledge": context["knowledge"], "scope_restrictions": context["restrictions"],
        "prior_judge_guidance": guidance, "dialogue": dialogue,
        "unambiguous_learner_reply_fact_check": verified_learner_reply,
        "runtime_rules": {
            "one_active_move_at_a_time": True, "no_new_scientific_examples": True,
            "do_not_emit_diagrams_or_control_visuals": True,
            "frontend_owns_static_visuals": True,
            "no_mastery_gate": True, "no_assessment_content": True,
            "ready_for_judge_means_current_move_ready_for_semantic_review": True,
            "learner_doubts_are_answered_before_resuming_current_move": True,
        },
    }
    instruction = """
[CONTROLLED_C11_PILOT_EXECUTION_RULES]
Only teach the CURRENT_MOVE. All other C1.1 moves will be supplied by the backend later.
Facts, mapping, examples, verified bit sequences and position/count results are fixed by the backend.
Do not invent or vary numeric examples; do not teach encoding, binary arithmetic or future subsections.
The frontend will render the optional passive visual. You never generate HTML, visual commands,
interactive exercises or descriptions of frontend behavior. Your prose must be intelligible
without the visual. A displayed visual alone is NOT evidence of instructional delivery.
P1: explicitly MODEL the example and why each step follows; no correctness checkpoint.
P2: supply prerequisites before asking. For response_policy 'guided', first ask one focused
question and set ready_for_judge=false. When the learner replies (including IDK), give a
contingent explanation or bounded hint, eventually state the verified answer, and only then
request review. Do not require correctness to proceed. Do not run an endless quiz.
P3: show why the matched cases are meaningfully similar/different and draw an explicit inference;
do not convert to a long guided-question chain.
At the end of a completed current move, ready_for_judge=true requests JUDGE REVIEW OF THIS MOVE,
not authority to advance. The backend alone advances after the independent review.
Use normal natural language and respond to learner doubts. No internal IDs in learner_message.
"""
    # A distinct pilot instruction prevents the legacy whole-subsection Tutor
    # prompt from inadvertently encouraging an LLM to execute later moves.
    return ("You are EkagraAI's beginner-facing Tutor in an internal C1.1 pilot. "
            "Obey the fixed assigned P1/P2/P3 teaching mechanism and the CURRENT authored move. "
            "Never score a learner, claim mastery, or advance the study yourself. "
            "Only output the specified strict JSON schema.\n" + instruction
            + "\n[CONTROLLED_C11_CURRENT_TUTOR_CONTEXT]\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n[OUTPUT_SCHEMA]\n"
            + json.dumps(V051TutorOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))


def controlled_c11_judge_prompt(compiled, context: dict, dialogue: list[dict], instructional_instance: dict,
                                move: dict, index: int, last_move: bool, previous_evidence: dict) -> str:
    """Reuse the durable Conversation Judge role but review one scoped move at a time."""
    payload = {
        "controlled_pilot": "C1.1_ONLY", "current_move": move, "current_move_index": index,
        "final_move_requires_whole_subsection_review": last_move,
        "prior_reviewed_move_evidence": previous_evidence,
        "active_subsection": context["subsection"], "global_pedagogy": context["global_pedagogy"],
        "scientific_scope": context["restrictions"],
        "verified_instructional_instance": instructional_instance["public"],
        "dialogue_with_move_traces": dialogue,
    }
    instruction = """
[CONTROLLED_C11_MOVE_REVIEW_RULES]
Return ADVANCE ONLY if the CURRENT move has been ACTUALLY taught accurately and in the
assigned pedagogy, supported by Tutor message evidence for this move. An unanswered
question, a Tutor readiness claim, and a frontend visual alone cannot establish delivery.
For P2 guided moves, require a learner reply following the guided prompt and a Tutor
response that treats that reply appropriately and provides correct resolution.
A wrong or IDK learner answer is NOT a failure: judge instructional delivery only.
If instruction is insufficient but repairable, CONTINUE with concrete missing teaching
guidance for the CURRENT move. If irreparably unsafe or unsupported, HOLD.
If this is the final C1.1 move, ALSO review whole-subsection factual coverage, prior
move evidence, and scientific/pedagogy boundaries. Do not advance on superficial mentions.
Return only the supplied ConversationJudgeOutput schema; do not claim learner mastery.
"""
    # Use a pilot-specific Judge policy instead of the stock whole-subsection
    # policy: reviewing a single move must not accidentally demand the complete
    # subsection until this is its final move.
    return ("You are the Conversation Judge for a controlled C1.1 teaching pilot. "
            "Evaluate delivered instruction, never learner mastery or assessment.\n" + instruction
            + "\n[CONTROLLED_C11_MOVE_JUDGE_CONTEXT]\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n[OUTPUT_SCHEMA]\n"
            + json.dumps(ConversationJudgeOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))
