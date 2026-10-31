"""F1 v0.4 model boundary. This is NOT a second application/runtime.

All four authored prompt contracts remain authoritative. Instance identity and
answer keys remain server-owned. JSON schemas avoid provider-rejected optional
properties and unconstrained nested objects; interpretation is semantic review.
"""
from __future__ import annotations

import json
import secrets
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator
from solo_harness.runtime.ai import CanonicalMessage
from solo_harness.studies.scientific_v04 import ScientificStudyV04
from solo_harness.studies.scientific_v04_policy import resolve_typed_case


class StrictWire(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class MCQProse(StrictWire):
    stem: str
    correct_option: str
    distractors: list[str]

    @model_validator(mode="after")
    def valid(self):
        if not (self.stem.strip() and 3 == len(self.distractors)
                and all(x.strip() for x in [self.correct_option, *self.distractors])):
            raise ValueError("empty MCQ text or incorrect option count")
        if max(map(len, [self.correct_option, *self.distractors])) > 1600 or len(self.stem) > 4000:
            raise ValueError("MCQ outside text bounds")
        return self


class TutorProse(StrictWire):
    learner_message: str
    fidelity_note: str
    teaching_complete: bool

    @model_validator(mode="after")
    def valid(self):
        if not self.learner_message.strip() or len(self.learner_message) > 4000:
            raise ValueError("empty or oversized Tutor output")
        return self


class SubjectiveProse(StrictWire):
    question: str

    @model_validator(mode="after")
    def valid(self):
        if not self.question.strip() or len(self.question) > 4000:
            raise ValueError("invalid subjective question")
        return self


class OptionAssessment(StrictWire):
    truth_status: Literal["TRUE", "FALSE", "UNCERTAIN"]
    matches_intended_meaning: bool
    scientific_reason: str


class SemanticReview(StrictWire):
    verdict: Literal["ACCEPT", "REVISE", "REVIEW_REQUIRED"]
    stem_matches_contract: bool
    assumptions_visible: bool
    exactly_one_defensible_option: bool
    option_assessments: list[OptionAssessment]
    rationale: str

    @model_validator(mode="after")
    def valid(self):
        if len(self.option_assessments) != 4 or not self.rationale.strip():
            raise ValueError("review must address exactly four options")
        return self


class SubjectiveReview(StrictWire):
    verdict: Literal["ACCEPT", "REVISE", "REVIEW_REQUIRED"]
    elicits_slot_evidence: bool
    assumes_only_visible_facts: bool
    scientifically_consistent: bool
    does_not_reveal_answer: bool
    rationale: str


class EvidenceFinding(StrictWire):
    criterion: str
    learner_quote: str
    interpretation: str


class SubjectiveJudgment(StrictWire):
    gradable_status: Literal["GRADABLE", "REVIEW_REQUIRED"]
    subjective_points: int | None  # required, nullable, even in REVIEW_REQUIRED
    observed_solo_structure: str | None
    material_correctness: str
    criterion_evidence: list[EvidenceFinding]
    misconception_evidence: list[EvidenceFinding]
    verbatim_quotes: list[str]
    alternative_reasoning_used: bool
    unverified_claims: list[str]
    review_reason: str | None
    score_justification: str

    @model_validator(mode="after")
    def coherent(self):
        if self.gradable_status == "GRADABLE":
            if self.subjective_points not in (0, 1, 2) or self.review_reason is not None:
                raise ValueError("gradable Judge must give 0/1/2 and no review hold")
            if not any(q.strip() for q in self.verbatim_quotes):
                raise ValueError("gradable Judge must cite the learner's actual wording")
        elif self.subjective_points is not None or not self.review_reason:
            raise ValueError("review-required Judge must withhold score and explain")
        return self


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _msg(content: str) -> tuple[CanonicalMessage, ...]:
    return (CanonicalMessage(role="system", content=content),)


def _slot(study: ScientificStudyV04, item_id: str) -> dict:
    matches = [x for b in study.assessments["blueprints"] for x in b["items"] if x["id"] == item_id]
    if len(matches) != 1:
        raise ValueError(f"scientific slot not unique: {item_id}")
    return matches[0]


def resolve_slot(study: ScientificStudyV04, item_id: str, seed: int | None = None) -> dict:
    case = resolve_typed_case(study, item_id, seed if seed is not None else secrets.randbits(64))
    return {"slot": _slot(study, item_id), "case": case, "instance_id": case["instance_id"]}


def tutor_messages(study: ScientificStudyV04, cell_id: str, dialogue: list[dict[str, str]],
                   instructional_instance: dict[str, Any] | None = None) -> tuple[CanonicalMessage, ...]:
    """Caller MUST create an independently verified instructional scenario.

    No assessment scenario is accepted implicitly. The instruction-only instance
    is frozen across turns by the calling session service.
    """
    if not instructional_instance or not instructional_instance.get("instruction_only"):
        raise ValueError("separate, verified instruction-only instance required")
    if instructional_instance.get("assessment_contract_id"):
        raise ValueError("assessment-reserved scenario cannot be used for Tutor")
    if not instructional_instance.get("verified"):
        raise ValueError("Tutor instructional instance is not mathematically verified")
    contract = study.compile_tutor(cell_id, instructional_instance["public"], dialogue)
    contract += "\n\n[OUTPUT_SCHEMA]\n" + _json(TutorProse.model_json_schema())
    contract += "\nThe backend, not the model, authorizes completion. Do not expose assessment keys."
    return _msg(contract)


def assessment_messages(study: ScientificStudyV04, resolved: dict) -> tuple[CanonicalMessage, ...]:
    slot, case = resolved["slot"], resolved["case"]
    payload = {"slot_id": slot["id"], "type": slot["type"],
               "scenario": case["public"], "scientific_purpose": slot["scientific_purpose"],
               "solo_evidence_role": slot.get("solo_evidence_role", slot.get("target_structural_evidence")),
               "equivalence_conditions": slot["equivalence_conditions"],
               "true_meaning": slot.get("correctness_condition"),
               "distractor_meanings": slot.get("distractor_meanings")}
    compiled = study.compile_assessment(slot["blueprint_id"], [payload])
    private = {"verified_math": case["oracle"], "complete_scientific_slot": slot,
               "instruction": "Realize EXACTLY the listed case(s), without inventing numerical facts."
                              " Do not expose verified truth, internal data or an answer key in the stem."}
    schema = MCQProse if slot["type"] == "MCQ" else SubjectiveProse
    compiled += "\n\n[PRIVATE_GENERATION_GUIDANCE]\n" + _json(private)
    compiled += "\n\n[OUTPUT_SCHEMA]\n" + _json(schema.model_json_schema())
    return _msg(compiled)


def review_messages(study: ScientificStudyV04, resolved: dict, rendered: dict) -> tuple[CanonicalMessage, ...]:
    slot, case = resolved["slot"], resolved["case"]
    subjective = slot["type"] != "MCQ"
    payload = {"scientific_contract": slot, "verified_case": {"learner_facts": case["public"], "oracle": case["oracle"]},
               "learner_facing_item": rendered,
               "review_instructions": "Assess actual natural-language meanings, not field names or string equality."
                    " For MCQ, assess options in their submitted order: first intended true, then three intended false."
                    " Treat any scientific uncertainty, incorrect role, implicit premise or multiple defensible options as REVIEW_REQUIRED."
                    " For SUBJECTIVE, assess the question's construct, assumptions and absence of answer leakage."}
    schema = SubjectiveReview if subjective else SemanticReview
    return _msg(study.prompts["SEMANTIC_REVIEW_PROMPT.md"] + "\n\n[V04_REVIEW_CONTEXT]\n" + _json(payload)
                + "\n\n[OUTPUT_SCHEMA]\n" + _json(schema.model_json_schema()))


def judge_messages(study: ScientificStudyV04, resolved: dict, frozen_question: str,
                   learner_response: str) -> tuple[CanonicalMessage, ...]:
    slot, case = resolved["slot"], resolved["case"]
    if slot["type"] != "SUBJECTIVE":
        raise ValueError("Judge must receive subjective contract")
    compiled = study.compile_judge(slot["blueprint_id"], frozen_question,
                                   {"scenario": {"learner_facts": case["public"], "oracle": case["oracle"]},
                                    "contract": slot}, learner_response)
    compiled += "\n\n[OUTPUT_SCHEMA]\n" + _json(SubjectiveJudgment.model_json_schema())
    return _msg(compiled)


def validate_judge_quotes(result: SubjectiveJudgment, exact_learner_response: str) -> None:
    for quote in [*result.verbatim_quotes, *(x.learner_quote for x in result.criterion_evidence),
                  *(x.learner_quote for x in result.misconception_evidence)]:
        if quote and quote not in exact_learner_response:
            raise ValueError("Judge cited text absent from actual learner submission")
