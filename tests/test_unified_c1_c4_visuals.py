"""# CHANGED: all C2-C4 visuals derive from fixed backend cases, never LLM markup."""
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from solo_harness.runtime.controlled_executor import contract, instance, visual_descriptor


def test_all_unified_passive_visuals_render_at_both_reveal_stages():
    template = Environment(loader=FileSystemLoader('src/solo_harness/templates'),
        undefined=StrictUndefined).get_template('partials/session/controlled_c11_visual.html')
    count = 0
    for section in ('C2', 'C3', 'C4'):
        for subsection, block in contract(section)['subsections'].items():
            for pedagogy, moves in block['moves_by_pedagogy'].items():
                for move in moves:
                    if not move.get('visual'):
                        continue
                    count += 1
                    for phase in ('prompt', 'complete'):
                        descriptor = visual_descriptor(move, instance(subsection,pedagogy), phase)
                        html = template.render(item={'visual': descriptor})
                        assert 'data-unified-visual=' in html
                        assert 'exact_delivery' not in html
                        assert '<script' not in html
    assert count >= 100  # all authored visually supported moves, not a pilot subset


def test_c4_guided_check_bit_is_concealed_until_response():
    template = Environment(loader=FileSystemLoader('src/solo_harness/templates'),
        undefined=StrictUndefined).get_template('partials/session/controlled_c11_visual.html')
    move=contract('C4')['subsections']['C4.1']['moves_by_pedagogy']['P2'][1]
    source=instance('C4.1','P2')
    hidden=template.render(item={'visual':visual_descriptor(move,source,'prompt')})
    shown=template.render(item={'visual':visual_descriptor(move,source,'complete')})
    assert '<span class="c11-position">P</span>\n        <span class="c11-value">?</span>' in hidden
    assert '<span class="c11-position">P</span>\n        <span class="c11-value">0</span>' in shown


def test_c4_alternative_added_checks_show_correct_distinction():
    template = Environment(loader=FileSystemLoader('src/solo_harness/templates'),
        undefined=StrictUndefined).get_template('partials/session/controlled_c11_visual.html')
    move=contract('C4')['subsections']['C4.3']['moves_by_pedagogy']['P3'][2]
    source=instance('C4.3','P3')
    full=template.render(item={'visual':visual_descriptor(move,source,'complete')})
    assert 'New check: FAIL' in full
    assert 'New check: PASS' in full
    hidden=template.render(item={'visual':visual_descriptor(move,source,'prompt')})
    assert 'New check: FAIL' not in hidden
    assert 'New check: PASS' not in hidden


# CHANGED: C4.1 M02 must not reveal Q or Group B before they are taught.
def test_c4_group_a_introduction_does_not_preview_group_b():
    template = Environment(loader=FileSystemLoader('src/solo_harness/templates'),
        undefined=StrictUndefined).get_template('partials/session/controlled_c11_visual.html')
    for pedagogy in ('P1', 'P2', 'P3'):
        move = contract('C4')['subsections']['C4.1']['moves_by_pedagogy'][pedagogy][1]
        descriptor = visual_descriptor(move, instance('C4.1', pedagogy), 'complete')
        facts = descriptor['fixed_cases']
        assert facts['position_order'] == ['D1', 'D2', 'D3', 'D4', 'P']
        assert facts['initial_complete_sequence'] == '11000'
        assert tuple(facts['groups']) == ('A',)
        html = template.render(item={'visual': descriptor})
        assert 'Group B' not in html
        assert '<span class="c11-position">Q</span>' not in html
    p3 = contract('C4')['subsections']['C4.1']['moves_by_pedagogy']['P3'][1]
    html = template.render(item={'visual': visual_descriptor(p3, instance('C4.1','P3'), 'complete')})
    assert 'data-group-a-parity-contrast' in html
    assert '1100' in html and '1101' in html
    assert '2 ones · PASS' in html and '3 ones · FAIL' in html


# CHANGED: no section's approved visual may be a caption-only science card.
def test_c2_conditional_correction_and_c3_receiver_inference_are_visible():
    template = Environment(loader=FileSystemLoader('src/solo_harness/templates'),
        undefined=StrictUndefined).get_template('partials/session/controlled_c11_visual.html')
    for subsection, pedagogy, move_index, marker, expected in (
        ('C2.3', 'P1', 3, 'data-correction-example', 'Proposed corrected grid:'),
        ('C2.3', 'P2', 3, 'data-correction-example', 'Proposed corrected grid:'),
        ('C3.2', 'P3', 4, 'data-receiver-inference-summary', 'Passing all checks does not prove'),
        ('C3.2', 'P2', 4, 'data-receiver-inference-summary', 'Passing all checks does not prove'),
    ):
        move = contract(subsection[:2])['subsections'][subsection]['moves_by_pedagogy'][pedagogy][move_index]
        source = instance(subsection, pedagogy)
        rendered = template.render(item={'visual': visual_descriptor(move,source,'complete')})
        assert marker in rendered
        assert expected in rendered
        prompt = template.render(item={'visual': visual_descriptor(move,source,'prompt')})
        assert marker in prompt
        assert expected not in prompt
