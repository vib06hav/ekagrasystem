"""Pure F1 v0.4 grading rules; the session engine persists the returned decision.

No legacy Phase-2 rubric or keyword-scoring dependency. A Judge review hold is
never converted to a zero or a failed SOLO transition.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from solo_harness.runtime.v04_native import SubjectiveJudgment, validate_judge_quotes


@dataclass(frozen=True)
class F1Score:
    mcq_points: int
    subjective_points: int
    passed: bool
    mcq_evidence: dict[str, Any]
    judge_evidence: dict[str, Any]


def evaluate_f1_response(
    frozen_public: dict,
    frozen_private: dict,
    mcq_answers: dict[str, str],
    exact_subjective_answer: str,
    judgment: SubjectiveJudgment,
) -> F1Score:
    if judgment.gradable_status != "GRADABLE":
        raise ValueError("REVIEW_REQUIRED: no learner score or failure may be recorded")
    validate_judge_quotes(judgment, exact_subjective_answer)
    public_items = frozen_public.get("mcqs", [])
    private_items = frozen_private.get("mcqs", [])
    if [x.get("id") for x in public_items] != ["MCQ1", "MCQ2", "MCQ3"]:
        raise ValueError("invalid three-question public package")
    if [x.get("id") for x in private_items] != ["MCQ1", "MCQ2", "MCQ3"]:
        raise ValueError("invalid private key package")
    if set(mcq_answers) != {"MCQ1", "MCQ2", "MCQ3"} or not exact_subjective_answer.strip():
        raise ValueError("incomplete learner assessment")
    results = {}
    for pub, priv in zip(public_items, private_items):
        question = pub["id"]
        possible = {o["id"] for o in pub["options"]}
        if len(possible) != 4 or priv["correct_option_id"] not in possible:
            raise ValueError("corrupted frozen option mapping")
        choice = mcq_answers[question]
        if choice not in possible:
            raise ValueError("submitted answer is not a displayed option")
        results[question] = {"selected_option_id": choice, "correct": choice == priv["correct_option_id"]}
    points = sum(item["correct"] for item in results.values())
    subjective = judgment.subjective_points
    assert subjective is not None
    return F1Score(mcq_points=points, subjective_points=subjective,
                   passed=points >= 2 and subjective >= 1,
                   mcq_evidence=results, judge_evidence=judgment.model_dump(mode="json"))
