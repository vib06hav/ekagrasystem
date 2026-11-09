"""Minimal semantic contracts and prompt assembly for v0.5.1 conversation."""
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
                          "wait_for_a_real_learner_turn_before_judge_review": True,
                          "no_assessment_content_or_keys": True},
    }
    return (compiled.authored["v051"]["prompts"]["TUTOR_PROMPT.md"]
            + "\n\n[V051_ACTIVE_SUBSECTION_TUTOR_CONTEXT]\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n\n[OUTPUT_SCHEMA]\n"
            + json.dumps(V051TutorOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))


def conversation_judge_prompt(compiled, progress, context: dict, dialogue: list[dict], latest_learner_message_id: str, instructional_instance: dict | None) -> str:
    payload = {
        "active_section_id": context["parent_cell"]["transition_id"], "active_subsection": context["subsection"],
        "global_pedagogy": context["global_pedagogy"], "section_pedagogy_cell": context["parent_cell"],
        "subsection_pedagogy_cell": context["child_cell"], "locked_knowledge": context["knowledge"],
        "restrictions": context["restrictions"], "verified_instructional_instance": instructional_instance,
        "dialogue": dialogue, "latest_learner_message_id": latest_learner_message_id,
    }
    return (compiled.authored["v051"]["prompts"]["CONVERSATION_JUDGE_PROMPT.md"]
            + "\n\n[V051_CONVERSATION_JUDGE_CONTEXT]\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n\n[OUTPUT_SCHEMA]\n"
            + json.dumps(ConversationJudgeOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))
