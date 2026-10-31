"""Small engineering checks; NOT evidence of pedagogical validity."""
from pathlib import Path
import os

import pytest
from solo_harness.studies.scientific_v04 import load_scientific_v04
from solo_harness.studies.scientific_v04_policy import resolve_typed_case
from solo_harness.studies.v04_instructional import resolve_instructional_instance
from solo_harness.runtime.v04_native import SubjectiveJudgment, MCQProse, SemanticReview, OptionAssessment
from solo_harness.runtime.v04_assessment import validate_mcq, ScientificReviewHold

ROOT = Path(os.environ.get('EKAGRA_V04_STUDY', 'studies/networks_error_detection_parity_f1/v0.4'))


def test_all_contracts_execute_and_multi_cases_preserved():
    study = load_scientific_v04(ROOT)
    count = 0
    multicase = 0
    for bp in study.assessments['blueprints']:
        for item in bp['items']:
            for seed in (1, 7, 19):
                result = resolve_typed_case(study, item['id'], seed)
                assert len(result['cases']) == len(result['policy']['cases'])
                assert len(result['public']['cases']) == len(result['cases'])
                assert result['instance_id']
                count += 1
            multicase += (len(result['cases']) > 1)
    assert count == 192
    assert multicase == 16


def test_repeated_same_grid_and_same_error_comparisons():
    study = load_scientific_v04(ROOT)
    for contract in ('C2-A4-Q3', 'C3-A1-Q3', 'C3-A4-S'):
        value = resolve_typed_case(study, contract, 123)
        a, b = value['public']['cases'][:2]
        assert a['valid_transmitted_grid'] == b['valid_transmitted_grid']
        if value['policy']['case_relation'] == 'same_valid_grid_distinct_error_patterns':
            assert a['flipped_positions'] != b['flipped_positions']
        else:
            assert a['flipped_positions'] == b['flipped_positions']


def test_tutor_instructional_examples_are_separate():
    study = load_scientific_v04(ROOT)
    for cell in study.interventions['cells']:
        example = resolve_instructional_instance(study, cell['id'], 15)
        assert example['instruction_only'] and example['verified']
        assert example['public']['authored_instructional_scenario'] == cell['instructional_scenario']
        assert not example.get('assessment_contract_id')


def test_reviewer_must_assess_each_option_truth():
    good = SemanticReview(verdict='ACCEPT', stem_matches_contract=True,
                          assumptions_visible=True, exactly_one_defensible_option=True,
                          option_assessments=[OptionAssessment(truth_status=t, matches_intended_meaning=True,
                                          scientific_reason='Compared against independent parity oracle')
                             for t in ['TRUE','FALSE','FALSE','FALSE']], rationale='Meaning checked')
    validate_mcq('Fresh valid question', ['True proposition','Wrong claim 1','Wrong claim 2','Wrong claim 3'],good)
    bad = good.model_copy(update={'option_assessments':
                        [good.option_assessments[0]] * 4})
    with pytest.raises(ScientificReviewHold):
        validate_mcq('Fresh valid question', ['True proposition','Wrong claim 1','Wrong claim 2','Wrong claim 3'],bad)


def test_judge_schema_requires_all_properties_with_nullable_fields():
    schema = SubjectiveJudgment.model_json_schema()
    assert set(schema['required']) == set(schema['properties'])
    assert schema['additionalProperties'] is False
    for name in ['criterion_evidence','misconception_evidence']:
        ref = schema['properties'][name]['items']['$ref'].split('/')[-1]
        obj = schema['$defs'][ref]
        assert set(obj['required']) == set(obj['properties'])
        assert obj['additionalProperties'] is False

@pytest.mark.asyncio
async def test_four_item_builder_wiring_only():
    """Scripted transport only checks interfaces; its prose has no scientific validity."""
    from solo_harness.runtime.v04_assessment import construct_four_item_assessment, RecordedResult
    from solo_harness.runtime.v04_native import SubjectiveProse, SubjectiveReview
    study = load_scientific_v04(ROOT)
    count, saved = [], {}

    async def recorded_invoke(role, messages, schema, context):
        count.append(role)
        assert messages[0].role == 'system'
        if schema is MCQProse:
            obj = MCQProse(stem=f"Sample {len(count)}", correct_option='Conceptually true wording',
                           distractors=['False claim A', 'False claim B', 'False claim C'])
        elif schema is SemanticReview:
            obj = SemanticReview(verdict='ACCEPT', stem_matches_contract=True, assumptions_visible=True,
                 exactly_one_defensible_option=True, option_assessments=[
                 OptionAssessment(truth_status=t, matches_intended_meaning=True,scientific_reason='Controlled stub')
                 for t in ['TRUE','FALSE','FALSE','FALSE']], rationale='Controlled stub')
        elif schema is SubjectiveProse:
            obj = SubjectiveProse(question='Explain your observation and why.')
        elif schema is SubjectiveReview:
            obj = SubjectiveReview(verdict='ACCEPT', elicits_slot_evidence=True,
                  assumes_only_visible_facts=True, scientifically_consistent=True,
                  does_not_reveal_answer=True, rationale='Controlled stub')
        else:
            raise AssertionError(schema)
        return RecordedResult(call_id=f'db-call-{len(count)}', parsed=obj)

    async def checkpoint(key, item):
        saved[key] = item

    package = await construct_four_item_assessment(study, 'C1-A2', recorded_invoke, checkpoint, prior_instructional_case_fingerprints=set())
    assert len(count) == 8
    assert len(saved) == 4
    assert len(package['public']['mcqs']) == 3
    assert len(package['private']['mcqs']) == 3
    assert package['status'] == 'DEVELOPMENT_ONLY'
    assert 'correct_option_id' not in str(package['public'])
    count.clear()
    restored = await construct_four_item_assessment(study, 'C1-A2', recorded_invoke,
                         checkpoint, completed=saved, prior_instructional_case_fingerprints=set())
    assert count == []  # no regeneration of persisted accepted work
    assert restored['public']['subjective']['id'] == 'SUB1'


def test_authored_tutor_uses_only_independent_instructional_instance():
    from solo_harness.runtime.v04_native import tutor_messages
    study = load_scientific_v04(ROOT)
    example = resolve_instructional_instance(study, 'C4-P3', 91)
    msgs = tutor_messages(study, 'C4-P3', [{'role': 'user', 'content': 'I am confused'}], example)
    assert 'C4-P3' in msgs[0].content
    assert study.prompts['TUTOR_PROMPT.md'] in msgs[0].content
    with pytest.raises(ValueError):
        tutor_messages(study, 'C4-P3', [], {'assessment_contract_id': 'C4-A3-Q2',
                              'instruction_only': True, 'verified': True, 'public': {}})


def test_pure_grading_uses_both_thresholds_and_respects_review_hold():
    from solo_harness.runtime.v04_grading import evaluate_f1_response
    from solo_harness.runtime.v04_native import SubjectiveJudgment
    public = {'mcqs': [{'id': f'MCQ{i}', 'options': [{'id': a, 'text': a} for a in 'ABCD']}
                        for i in range(1,4)]}
    private = {'mcqs': [{'id': f'MCQ{i}', 'correct_option_id': 'A'} for i in range(1,4)]}
    answer = 'Because there are two parity changes.'
    judge = SubjectiveJudgment(gradable_status='GRADABLE', subjective_points=1, observed_solo_structure='U',
        material_correctness='correct', criterion_evidence=[], misconception_evidence=[],
        verbatim_quotes=['two parity changes'], alternative_reasoning_used=False,
        unverified_claims=[], review_reason=None, score_justification='One supported aspect')
    result = evaluate_f1_response(public, private, {'MCQ1':'A', 'MCQ2':'B', 'MCQ3':'A'}, answer, judge)
    assert result.mcq_points == 2 and result.subjective_points == 1 and result.passed
    hold = judge.model_copy(update={'gradable_status':'REVIEW_REQUIRED', 'subjective_points':None,
                                    'review_reason':'unclear'})
    with pytest.raises(ValueError, match='REVIEW_REQUIRED'):
        evaluate_f1_response(public, private, {'MCQ1':'A', 'MCQ2':'A', 'MCQ3':'A'}, answer, hold)
