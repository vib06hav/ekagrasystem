"""Fixed C2/C3 content, input isolation, numerical truth and Jinja grid tests. # CHANGED"""
from copy import deepcopy
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from solo_harness.runtime.assessment_grading import evaluate_f1_response
from solo_harness.runtime.fixed_assessment import (
    FixedAssessmentError, construct_fixed_assessment, validate_fixed_bank,
)
from solo_harness.runtime.v051_assessment import v051_judge_messages
from solo_harness.runtime.v051_judge import V05SubjectiveJudgment
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051

ROOT = Path(__file__).resolve().parents[1]


def _compiled():
    return compile_v051(load_scientific_v051(ROOT / 'studies/networks_error_detection_parity_f1/v0.5'))


@pytest.mark.parametrize('section', ['C2', 'C3'])
def test_each_set_is_verified_and_frozen_without_any_writer_or_reviewer(section):
    compiled = _compiled()
    bank = compiled.authored['v051']['fixed_assessment_banks'][section]
    validate_fixed_bank(bank, section)
    assert len(compiled.assessment_families[section]['forms']) == 3
    for form in compiled.assessment_families[section]['forms']:
        package = construct_fixed_assessment(compiled, form)
        set_id = form['fixed_bank_set_id']
        assert package['metadata']['fixed_set_id'] == set_id
        assert package['metadata']['generation_method'] == 'verified_authored_fixed_no_writer_reviewer'
        assert [x['id'] for x in package['public']['mcqs']] == ['MCQ1', 'MCQ2', 'MCQ3']
        assert package['public']['subjective']['id'] == 'SUB1'
        assert 'correct_option_id' not in str(package['public'])
        assert 'subjective_resolved' not in package['public']
        for mcq, answer, authored in zip(package['public']['mcqs'], package['private']['mcqs'],
                                           bank['sets'][set_id]['private']['mcqs']):
            chosen_text = next(o['text'] for o in mcq['options'] if o['id'] == answer['correct_option_id'])
            assert chosen_text == authored['correct_answer']
        if section == 'C2':
            assert len([q for q in package['public']['mcqs'] if 'grid' in q]) == 1
        else:
            assert len([q for q in package['public']['mcqs'] if 'grid' in q]) == 3
            assert 'R1C2' in package['public']['notation']


@pytest.mark.parametrize('section', ['C2', 'C3'])
def test_corrupted_received_grid_is_rejected(section):
    compiled = _compiled()
    bank = deepcopy(compiled.authored['v051']['fixed_assessment_banks'][section])
    if section == 'C2':
        bank['sets']['A']['private']['mcqs'][1]['oracle']['received_grid'][0] = '0000'
    else:
        bank['sets']['B']['private']['mcqs'][0]['oracle']['received_grid'][0] = '0000'
    with pytest.raises(FixedAssessmentError):
        validate_fixed_bank(bank, section)


def test_c2_calibration_one_point_requires_two_independent_patterns():
    bank = _compiled().authored['v051']['fixed_assessment_banks']['C2']
    for form in bank['sets'].values():
        contract = form['private']['subjective_resolved']['contract']
        assert 'at least two' in contract['score_anchor']['1'].lower()
        calibration = next(example for example in contract['calibration_examples'] if example['expected_points'] == 1)
        assert 'same-row' in calibration['response'] and 'same-column' in calibration['response']


@pytest.mark.parametrize('section', ['C2', 'C3'])
def test_subjective_judge_sees_item_rubric_not_mcq_keys_or_calibration_answers(section):
    compiled = _compiled()
    form = compiled.assessment_families[section]['forms'][0]
    package = construct_fixed_assessment(compiled, form)
    context = v051_judge_messages(compiled, package['private']['subjective_resolved'],
                                  package['public']['subjective']['prompt'], 'A hypothetical response')[0].content
    assert 'FIXED_ITEM_SCORING_PRIORITY' in context
    assert 'score_anchor' in context and 'verified_scenario' in context
    assert 'correct_option_id' not in context
    assert 'calibration_examples' not in context
    assert 'reference_answer_for_calibration_only' not in context
    assert 'global_pedagogy' not in context
    if section == 'C2':
        assert 'at least two' in context.lower()
        assert 'Do not require an unasked 1D discussion' in context
    else:
        assert 'one correctly explained case-linked causal direction' in context


@pytest.mark.parametrize('section', ['C2', 'C3'])
def test_scoring_uses_displayed_private_ids_and_existing_gate(section):
    compiled = _compiled()
    package = construct_fixed_assessment(compiled, compiled.assessment_families[section]['forms'][0])
    answers = {item['id']: item['correct_option_id'] for item in package['private']['mcqs']}
    passed = evaluate_f1_response(package['public'], package['private'], answers, 'Sample response',
                                  V05SubjectiveJudgment(subjective_points=1, reason='Scripted minimum structural evidence.'))
    assert passed.passed and passed.mcq_points == 3 and passed.subjective_points == 1


def test_c2_c3_frontend_shows_grid_notation_and_preserves_subjective_newlines():
    compiled = _compiled()
    environment = Environment(loader=FileSystemLoader(str(ROOT / 'src/solo_harness/templates')),
                              autoescape=select_autoescape(['html']))
    tpl = environment.get_template('partials/session_main.html')
    from test_v051_frontend import _view
    for section in ('C2', 'C3'):
        package = construct_fixed_assessment(compiled, compiled.assessment_families[section]['forms'][0])
        view = _view(phase='ASSESSMENT_ACTIVE', f1_public_assessment=package['public'])
        html = tpl.render(view=view, new_key='test', settings=None)
        assert html.count('class="assessment-bit-grid"') == (1 if section == 'C2' else 3)
        assert '1 1 1 0' in html or '1 1 0 0' in html  # one of the displayed grids
        assert 'class="assessment-subjective-prompt"' in html
        assert 'name="mcq1_answer"' in html and 'name="mcq3_answer"' in html
        assert 'correct_option_id' not in html and 'score_anchor' not in html
        if section == 'C3':
            assert 'class="assessment-notation"' in html and 'R1C2' in html
        else:
            assert 'class="assessment-notation"' not in html
