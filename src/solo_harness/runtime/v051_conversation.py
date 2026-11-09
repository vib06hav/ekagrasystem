"""Strict contract and prompt assembly for the candidate v0.5.1 Conversation Judge."""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Wire(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RequiredContentStatus(_Wire):
    ref: str
    status: Literal["DELIVERED", "MISSING", "INVALID"]
    supporting_excerpt_or_reason: str = Field(min_length=1, max_length=2000)


class ObligationEvidence(_Wire):
    """A semantic claim anchored to one exact, learner-visible Tutor turn.

    The Judge may use one turn for several obligations, but it cannot turn a
    bare turn id into evidence for every obligation in the subsection.
    """
    obligation_id: str
    message_id: str
    supporting_excerpt: str = Field(min_length=1, max_length=2000)


class ConversationJudgeOutput(_Wire):
    active_subsection_id: str
    decision: Literal["CONTINUE_TEACHING", "CLARIFY_OR_SCAFFOLD", "CONSOLIDATE", "ADVANCE_SUBSECTION", "DELIVERY_EXCEPTION"]
    completed_move_ids: list[str]
    required_content_status: list[RequiredContentStatus]
    pedagogy_fidelity: Literal["SATISFIED", "DEVIATION", "UNCERTAIN"]
    learner_signal: str = Field(min_length=1, max_length=2000)
    open_doubts: list[str]
    evidence_refs: list[str]
    move_evidence: list[ObligationEvidence] = Field(default_factory=list)
    content_evidence: list[ObligationEvidence] = Field(default_factory=list)
    next_allowed_instruction: str = Field(min_length=1, max_length=4000)
    delivery_exception_reason: str | None = Field(default=None, max_length=2000)
    confidence: Literal["HIGH", "MEDIUM", "LOW"]


class V051TutorOutput(_Wire):
    """The candidate Tutor's learner-facing turn and non-authoritative trace."""
    learner_message: str = Field(min_length=1, max_length=4000)
    proposed_move_ids: list[str] = Field(default_factory=list)
    proposed_content_ids: list[str] = Field(default_factory=list)
    proposes_subsection_close: bool = False
    fidelity_note: str = Field(min_length=1, max_length=2000)


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
        "required_move_ids": progress.required_move_ids,
        "required_content_ids": progress.required_content_ids,
        "persisted_delivery_ledger": {
            "move_evidence": progress.move_evidence,
            "content_evidence": progress.content_evidence,
            "clarification_evidence_ids": progress.clarification_evidence_ids,
            "instructional_state": progress.instructional_state,
        },
        "previous_conversation_judge_guidance": judge_guidance,
        "verified_instructional_instance": instructional_instance,
        "dialogue": dialogue,
        "runtime_rules": {
            "no_mastery_gate": True,
            "tutor_completion_is_non_authoritative": True,
            "offer_final_optional_doubt_window_before_closure": True,
            "no_assessment_content_or_keys": True,
        },
    }
    return (compiled.authored["v051"]["prompts"]["TUTOR_PROMPT.md"]
            + "\n\n[V051_ACTIVE_SUBSECTION_TUTOR_CONTEXT]\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n\n[OUTPUT_SCHEMA]\n"
            + json.dumps(V051TutorOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))


def conversation_judge_prompt(compiled, progress, context: dict, dialogue: list[dict], latest_learner_message_id: str | None, allowance: dict) -> str:
    source = compiled.authored["v051"]["scientific"]
    payload = {
        "active_section_id": context["parent_cell"]["transition_id"], "active_subsection": context["subsection"],
        "global_pedagogy": context["global_pedagogy"], "section_pedagogy_cell": context["parent_cell"],
        "subsection_pedagogy_cell": context["child_cell"], "restrictions": context["restrictions"],
        "dialogue_turn_ids_and_text": dialogue, "persisted_evidence_ledger": {
            "required_move_ids": progress.required_move_ids, "required_content_ids": progress.required_content_ids,
            "move_evidence": progress.move_evidence, "content_evidence": progress.content_evidence,
            "clarification_evidence_ids": progress.clarification_evidence_ids, "instructional_state": progress.instructional_state,
        },
        "latest_learner_message_id": latest_learner_message_id, "candidate_exposure_usage": allowance,
        "conversation_judge_spec": source["conversation_judge.yaml"],
    }
    return compiled.authored["v051"]["prompts"]["CONVERSATION_JUDGE_PROMPT.md"] + "\n\n[V051_CONVERSATION_JUDGE_CONTEXT]\n" + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
