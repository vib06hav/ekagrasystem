"""v0.5 formal grading boundary: semantic score, not copied quotes.

Pure contract/grading tests; the existing PostgreSQL suite separately exercises
persistence and the reserve/receive/finalize operation chain.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from solo_harness.runtime.v04_grading import evaluate_f1_response
from solo_harness.runtime.v04_native import SubjectiveJudgment
from solo_harness.runtime.v051_assessment import v051_judge_messages
from solo_harness.runtime.v051_judge import V05SubjectiveJudgment
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051

ROOT = Path("studies/networks_error_detection_parity_f1/v0.5")


def _package():
    public = {"mcqs": [{"id": f"MCQ{i}", "options": [{"id": x, "text": x} for x in "ABCD"]}
                       for i in range(1, 4)]}
    private = {"mcqs": [{"id": f"MCQ{i}", "correct_option_id": "A"} for i in range(1, 4)]}
    return public, private, {"MCQ1": "A", "MCQ2": "A", "MCQ3": "B"}


@pytest.mark.parametrize("points,expected_pass", [(0, False), (1, True), (2, True)])
def test_v05_grade_uses_rubric_score_without_exact_learner_quotes(points, expected_pass):
    public, private, answers = _package()
    judgement = V05SubjectiveJudgment(subjective_points=points,
                                     reason="Semantically evaluated relevant causal explanation.")
    # The reason is not a literal substring of the learner's answer; that is fine.
    score = evaluate_f1_response(public, private, answers, "My analysis uses two checking groups.", judgement)
    assert score.subjective_points == points
    assert score.mcq_points == 2
    assert score.passed is expected_pass
    assert score.judge_evidence == {"subjective_points": points, "reason": judgement.reason}


def test_v05_null_means_review_not_a_zero_or_failed_transition():
    public, private, answers = _package()
    judgment = V05SubjectiveJudgment(subjective_points=None,
                                    reason="Frozen item facts are inconsistent; staff review required.")
    with pytest.raises(ValueError, match="REVIEW_REQUIRED"):
        evaluate_f1_response(public, private, answers, "A technically valid answer.", judgment)


def test_v05_judge_rejects_extra_bookkeeping_and_invalid_scores():
    assert set(V05SubjectiveJudgment.model_fields) == {"subjective_points", "reason"}
    with pytest.raises(ValidationError):
        V05SubjectiveJudgment.model_validate({"subjective_points": 1, "reason": "sufficient", "verbatim_quotes": ["x"]})
    with pytest.raises(ValidationError):
        V05SubjectiveJudgment(subjective_points=3, reason="invalid score")
    with pytest.raises(ValidationError):
        V05SubjectiveJudgment(subjective_points=1, reason="   ")


def test_v04_exact_quote_validation_is_not_changed():
    public, private, answers = _package()
    v04 = SubjectiveJudgment(
        gradable_status="GRADABLE", subjective_points=1, observed_solo_structure="U",
        material_correctness="CORRECT", criterion_evidence=[], misconception_evidence=[],
        verbatim_quotes=["This quote was never present"], alternative_reasoning_used=False,
        unverified_claims=[], review_reason=None, score_justification="Minimum structure")
    with pytest.raises(ValueError, match="absent"):
        evaluate_f1_response(public, private, answers, "My actual learner answer.", v04)


def test_compiled_scientific_contract_and_judge_prompt_are_aligned():
    compiled = compile_v051(load_scientific_v051(ROOT))
    source = compiled.authored["v051"]
    assert source["scientific"]["judge.yaml"]["output_fields"] == ["subjective_points", "reason"]
    assert source["scientific"]["conversation_judge.yaml"]["output_contract"]["decision"] == "CONTINUE|ADVANCE|HOLD"
    policy = source["scientific"]["protocol.yaml"]["instructional_lifecycle"]
    assert policy["final_optional_doubt_window"] is False
    assert "automatically" in policy["at_subsection_advance"]
    contract = {"type": "SUBJECTIVE", "transition_id": "C1"}
    context = {"contract": contract, "case": {"public": {"data": "010"}, "oracle": {"expected": "even"}}}
    prompt = v051_judge_messages(compiled, context, "Explain how parity helps.", "It checks the total.")[0].content
    assert "V051_BLIND_SUBJECTIVE_JUDGE_CONTEXT" in prompt
    assert "[OUTPUT_SCHEMA]" in prompt
    assert '"subjective_points"' in prompt and '"reason"' in prompt
    assert "verbatim_quotes" not in prompt
    assert "assigned_pedagogy" not in prompt
