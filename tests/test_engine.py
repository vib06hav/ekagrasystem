import random
from solo_harness.runtime.engine import JudgeObservation, RandomSelector, RubricEvaluator
from solo_harness.studies.compiler import compile_study
from solo_harness.studies.loader import load

from test_studies import STUDY

def test_random_selector_is_auditable_and_seeded():
    decision = RandomSelector(random.Random(4), "seeded_random", "4").choose(["P3", "P1"], ["P2"])
    assert decision.selected_id in decision.eligible_candidate_ids
    assert decision.eligible_candidate_ids == ("P1", "P3")
    assert decision.excluded_candidate_ids == ("P2",)

def test_rubrics_use_compiled_study_not_hardcoded_rules():
    compiled = compile_study(load(STUDY)); evaluator = RubricEvaluator()
    for transition_id in compiled.protocol["transition_ids"]:
        transition = compiled.knowledge_slices[transition_id]["transition"]
        rubric = compiled.rubrics[transition_id]
        evidence = tuple(rubric["evidence_ids"])
        result = evaluator.evaluate(transition, rubric, JudgeObservation(True, "CORRECT", transition["target_state_id"], evidence))
        assert result.passed

def test_above_target_observation_is_evidence_not_routing():
    compiled = compile_study(load(STUDY)); transition=compiled.knowledge_slices["C2"]["transition"]; rubric=compiled.rubrics["C2"]
    result=RubricEvaluator().evaluate(transition,rubric,JudgeObservation(True,"CORRECT","R",tuple(rubric["evidence_ids"][:3])))
    assert result.passed

def test_below_target_observation_fails_deterministically():
    compiled = compile_study(load(STUDY)); transition=compiled.knowledge_slices["C2"]["transition"]; rubric=compiled.rubrics["C2"]
    result=RubricEvaluator().evaluate(transition,rubric,JudgeObservation(True,"CORRECT","U",tuple(rubric["evidence_ids"][:3])))
    assert not result.passed and "OBSERVED_STATE_BELOW_TARGET" in result.reasons


def test_c4_requires_both_abstraction_and_transfer_evidence_groups():
    compiled = compile_study(load(STUDY)); transition=compiled.knowledge_slices["C4"]["transition"]; rubric=compiled.rubrics["C4"]
    result=RubricEvaluator().evaluate(transition,rubric,JudgeObservation(True,"CORRECT","EA",("C4-E1",)))
    assert not result.passed and "MISSING_REQUIRED_EVIDENCE_GROUP" in result.reasons


def test_item_specific_evidence_is_enforced_by_assessment_id():
    compiled = compile_study(load(STUDY)); transition=compiled.knowledge_slices["C1"]["transition"]; rubric=compiled.rubrics["C1"]
    result=RubricEvaluator().evaluate(transition,rubric,JudgeObservation(True,"CORRECT","U",("C1-E1","C1-E2")),"C1-A3")
    assert not result.passed and "MISSING_ITEM_SPECIFIC_EVIDENCE" in result.reasons
