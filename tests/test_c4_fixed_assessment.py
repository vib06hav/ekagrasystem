"""C4 authored fixed bank: objective science, correct keys, isolation and rendering. # CHANGED"""
from copy import deepcopy
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from solo_harness.runtime.assessment_grading import evaluate_f1_response
from solo_harness.runtime.fixed_assessment import (
    FixedAssessmentError, construct_fixed_assessment, validate_c4_bank, validate_fixed_bank,
)
from solo_harness.runtime.v051_assessment import v051_judge_messages
from solo_harness.runtime.v051_judge import V05SubjectiveJudgment
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051

ROOT = Path(__file__).resolve().parents[1]


def _compiled():
    return compile_v051(load_scientific_v051(ROOT / 'studies/networks_error_detection_parity_f1/v0.5'))


def test_all_c4_authored_forms_verify_and_freeze_with_correct_private_keys():
    compiled = _compiled()
    bank = compiled.authored['v051']['fixed_assessment_banks']['C4']
    validate_c4_bank(bank)
    validate_fixed_bank(bank, 'C4')
    assert compiled.content_version == 'v0.5.5'
    assert len(compiled.assessment_families['C4']['forms']) == 3
    assert compiled.protocol['assessment_strategy'] == 'c1_c2_c3_c4_fixed'
    for form in compiled.assessment_families['C4']['forms']:
        frozen = construct_fixed_assessment(compiled, form)
        assert frozen['metadata']['generation_method'] == 'verified_authored_fixed_no_writer_reviewer'
        assert frozen['metadata']['fixed_set_id'] == form['fixed_bank_set_id']
        assert len(frozen['public']['mcqs']) == 3
        assert len(frozen['private']['mcqs']) == 3
        assert 'notation' in frozen['public']
        assert 'arrangement' in frozen['public']['subjective']
        assert 'correct_option_id' not in str(frozen['public'])
        assert 'subjective_resolved' not in str(frozen['public'])
        for mcq, answer, original in zip(frozen['public']['mcqs'], frozen['private']['mcqs'],
                                          bank['sets'][form['fixed_bank_set_id']]['private']['mcqs']):
            assert mcq['arrangement']['groups']
            assert next(option['text'] for option in mcq['options'] if option['id'] == answer['correct_option_id']) == original['correct_answer']


def test_c4_private_answer_mapping_survives_repeated_option_shuffles():
    compiled = _compiled()
    form = compiled.assessment_families['C4']['forms'][0]
    displays = set()
    for _ in range(25):
        frozen = construct_fixed_assessment(compiled, form)
        displays.add(tuple(x['text'] for x in frozen['public']['mcqs'][0]['options']))
        for pub, private in zip(frozen['public']['mcqs'], frozen['private']['mcqs']):
            option = next(o for o in pub['options'] if o['id'] == private['correct_option_id'])
            original = compiled.authored['v051']['fixed_assessment_banks']['C4']['sets']['A']['private']['mcqs'][int(pub['id'][-1])-1]
            assert option['text'] == original['correct_answer']
    assert len(displays) > 1


@pytest.mark.parametrize('bad_edit', ['original_parity', 'received_sequence', 'extra_rule_count', 'wrong_key'])
def test_c4_independent_validator_rejects_corrupt_numerical_facts(bad_edit):
    compiled = _compiled()
    bank = deepcopy(compiled.authored['v051']['fixed_assessment_banks']['C4'])
    if bad_edit == 'original_parity':
        bank['sets']['A']['public']['mcqs'][0]['arrangement']['sent_sequence'] = '0011111'
    elif bad_edit == 'received_sequence':
        bank['sets']['B']['private']['mcqs'][0]['oracle']['received_sequence'] = '1111111'
    elif bad_edit == 'extra_rule_count':
        bank['sets']['C']['private']['subjective_resolved']['case']['added_rule']['flips_inside_H4_by_pattern']['Pattern 2'] = 2
    else:
        bank['sets']['A']['private']['mcqs'][2]['correct_option_id'] = 'A'
    with pytest.raises(FixedAssessmentError):
        validate_c4_bank(bank)


def test_c4_subjective_judge_is_blind_and_uses_extended_abstract_anchors():
    compiled = _compiled()
    frozen = construct_fixed_assessment(compiled, compiled.assessment_families['C4']['forms'][2])
    context = v051_judge_messages(compiled, frozen['private']['subjective_resolved'],
                                  frozen['public']['subjective']['prompt'], 'A hypothetical learner response')[0].content
    assert 'FIXED_ITEM_SCORING_PRIORITY' in context
    assert 'fixed_c4_extended_abstract' in context
    assert 'counterexample' in context.lower()
    assert 'added-rule evaluation' in context
    assert 'calibration_examples' not in context
    assert 'reference_answer_for_calibration_only' not in context
    assert 'correct_option_id' not in context
    assert 'global_pedagogy' not in context
    assert 'learner_identity' not in context


def test_c4_fixed_bank_uses_existing_three_mcq_and_subjective_scoring_gate():
    compiled = _compiled()
    frozen = construct_fixed_assessment(compiled, compiled.assessment_families['C4']['forms'][0])
    correct = {m['id']: m['correct_option_id'] for m in frozen['private']['mcqs']}
    grade = evaluate_f1_response(frozen['public'], frozen['private'], correct,
                                 'A correct generalized counterexample.',
                                 V05SubjectiveJudgment(subjective_points=1, reason='Scripted minimum EA criterion.'))
    assert grade.passed and grade.mcq_points == 3 and grade.subjective_points == 1


def test_c4_frontend_displays_group_membership_and_bit_values_no_keys():
    compiled = _compiled()
    environment = Environment(loader=FileSystemLoader(str(ROOT / 'src/solo_harness/templates')),
                              autoescape=select_autoescape(['html']))
    template = environment.get_template('partials/session_main.html')
    from test_v051_frontend import _view
    for form in compiled.assessment_families['C4']['forms']:
        frozen = construct_fixed_assessment(compiled, form)
        view = _view(phase='ASSESSMENT_ACTIVE', f1_public_assessment=frozen['public'])
        html = template.render(view=view, new_key='test', settings=None)
        assert html.count('class="assessment-position-table"') == 4  # three MCQs and subjective
        assert 'Original transmitted sequence' in html
        assert 'Parity-check groups' in html
        assert '<th scope="col">M1</th>' in html
        assert '<th scope="col">Q1</th>' in html
        assert 'H1' in html and 'H4' in html
        assert 'class="assessment-notation"' in html
        assert 'name="mcq1_answer"' in html and 'name="mcq3_answer"' in html
        assert 'correct_option_id' not in html and 'score_anchor' not in html
