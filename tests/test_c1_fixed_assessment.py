"""# CHANGED: static C1 bank, private scoring and placeholder lifecycle contracts."""
from copy import deepcopy
from pathlib import Path

import pytest

from solo_harness.runtime.fixed_assessment import (  # CHANGED
    FixedAssessmentError, construct_fixed_c1_assessment, validate_c1_bank,
)
from solo_harness.runtime.v051_assessment import v051_judge_messages  # CHANGED
from solo_harness.studies.scientific_v051 import load_scientific_v051  # CHANGED
from solo_harness.studies.v051_native_compiler import compile_v051  # CHANGED

ROOT = Path(__file__).resolve().parents[1] / 'studies/networks_error_detection_parity_f1/v0.5'  # CHANGED


def _study():  # CHANGED
    return compile_v051(load_scientific_v051(ROOT))


def test_three_fixed_sets_have_correct_parity_and_private_keys():  # CHANGED
    compiled = _study()
    bank = compiled.authored['v051']['fixed_assessment_banks']['C1']
    validate_c1_bank(bank)
    assert [bank['sets'][x]['private']['subjective_resolved']['case']['receiver_check_result'] for x in 'ABC'] == ['FAIL', 'PASS', 'FAIL']
    for blueprint in compiled.assessment_families['C1']['forms']:
        frozen = construct_fixed_c1_assessment(compiled, blueprint)
        assert [item['id'] for item in frozen['public']['mcqs']] == ['MCQ1','MCQ2','MCQ3']
        assert frozen['public']['subjective']['id'] == 'SUB1'
        assert frozen['metadata']['generation_method'] == 'verified_authored_fixed_no_writer_reviewer'
        assert 'correct_option_id' not in repr(frozen['public'])
        for mcq, answer in zip(frozen['public']['mcqs'], frozen['private']['mcqs']):
            original = bank['sets'][blueprint['fixed_bank_set_id']]['private']['mcqs'][int(mcq['id'][-1])-1]
            actual = next(o['text'] for o in mcq['options'] if o['id'] == answer['correct_option_id'])
            assert actual == original['correct_answer']
            assert [o['id'] for o in mcq['options']] == ['A','B','C','D']


def test_randomized_display_order_never_changes_scoring_truth():  # CHANGED
    compiled = _study()
    form = compiled.assessment_families['C1']['forms'][0]
    orders = set()
    for _ in range(25):
        package = construct_fixed_c1_assessment(compiled, form)
        orders.add(tuple(o['text'] for o in package['public']['mcqs'][0]['options']))
        correct = package['private']['mcqs'][0]['correct_option_id']
        assert next(o['text'] for o in package['public']['mcqs'][0]['options'] if o['id']==correct) == compiled.authored['v051']['fixed_assessment_banks']['C1']['sets']['A']['private']['mcqs'][0]['correct_answer']
    assert len(orders) > 1


def test_assessment_judge_gets_item_specific_receiver_rubric_without_mcq_keys():  # CHANGED
    compiled = _study()
    pkg = construct_fixed_c1_assessment(compiled, compiled.assessment_families['C1']['forms'][1])
    resolved = pkg['private']['subjective_resolved']
    message = v051_judge_messages(compiled, resolved, pkg['public']['subjective']['prompt'], 'Three ones, the odd parity rule passes.')[0].content
    assert 'FIXED_C1_ITEM_SCORING_PRIORITY' in message
    assert 'fixed_c1_receiver_only' in message
    assert 'complete_received_frame' in message
    assert 'No usable correct parity-checking evidence' in message
    assert 'correct_option_id' not in message
    assert 'global_pedagogy' not in message


def test_bank_mutation_is_rejected_and_placeholders_have_no_forms():  # CHANGED
    compiled = _study()
    bank = deepcopy(compiled.authored['v051']['fixed_assessment_banks']['C1'])
    bank['sets']['B']['private']['subjective_resolved']['case']['receiver_check_result'] = 'FAIL'
    with pytest.raises(FixedAssessmentError, match='receiver answer oracle'):
        validate_c1_bank(bank)
    for section in ('C2','C3'):  # CHANGED: both newly verified banks are active.
        assert len(compiled.assessment_families[section]['forms']) == 3
    section = 'C4'  # CHANGED: final fixed bank replaces last placeholder.
    assert len(compiled.assessment_families[section]['forms']) == 3
    holder = compiled.authored['v051']['fixed_assessment_banks'][section]
    assert set(holder['sets']) == {'A', 'B', 'C'}
