"""One visual card per controlled move: presentation projection over immutable traces."""
import copy
from types import SimpleNamespace as NS

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from solo_harness.runtime.controlled_executor import contract, instance, visual_descriptor
from solo_harness.web import project_move_visuals


def msg(seq, role="TUTOR", move=None, visual=None):
    trace = {}
    if move:
        trace["pilot_move_id"] = move
    if visual:
        trace["pilot_visual"] = visual
    return NS(sequence_no=seq, role=role, instructional_trace=trace)


def vis(stage, component="bit_grid"):
    return {"component": component, "mode": "m", "stage": stage}


def test_guided_move_shows_single_card_upgraded_to_complete():
    msgs = [msg(1, move="A", visual=vis("prompt")), msg(2, "LEARNER"), msg(3, move="A", visual=vis("complete"))]
    before = copy.deepcopy([m.instructional_trace for m in msgs])
    shown = project_move_visuals(msgs)
    assert shown == {1: vis("complete")}           # one card, at the first message
    assert [m.instructional_trace for m in msgs] == before   # audit traces untouched


def test_prompt_stage_stays_concealed_without_continuation():
    shown = project_move_visuals([msg(1, move="A", visual=vis("prompt")), msg(2, "LEARNER", )])
    assert shown == {1: vis("prompt")}


def test_repeated_prompt_or_complete_is_idempotent():
    msgs = [msg(1, move="A", visual=vis("prompt")), msg(2, move="A", visual=vis("prompt")),
            msg(3, move="A", visual=vis("complete")), msg(4, move="A", visual=vis("complete"))]
    assert project_move_visuals(msgs) == {1: vis("complete")}


def test_distinct_moves_and_non_guided_keep_their_own_cards():
    msgs = [msg(1, move="A", visual=vis("prompt")), msg(2, move="B", visual=vis("complete", "x")),
            msg(3, move="A", visual=vis("complete")), msg(4, move="C", visual=vis("prompt"))]
    assert project_move_visuals(msgs) == {1: vis("complete"), 2: vis("complete", "x"), 4: vis("prompt")}


def test_messages_without_visual_and_learner_rows_yield_nothing():
    msgs = [msg(1, move="A"), msg(2, "LEARNER", visual=vis("complete"))]
    assert project_move_visuals(msgs) == {}


def test_visuals_without_move_id_are_unchanged():
    assert project_move_visuals([msg(1, visual=vis("complete")), msg(2, visual=vis("complete"))]) == {
        1: vis("complete"), 2: vis("complete")}


def test_c2_c4_projected_visual_still_renders_both_stages():
    template = Environment(loader=FileSystemLoader('src/solo_harness/templates'),
        undefined=StrictUndefined).get_template('partials/session/controlled_c11_visual.html')
    move = contract('C4')['subsections']['C4.1']['moves_by_pedagogy']['P2'][1]
    inst = instance('C4.1', 'P2')
    p, c = (visual_descriptor(move, inst, s) for s in ('prompt', 'complete'))
    msgs = [msg(1, move=move['id'], visual=p), msg(2, "LEARNER"), msg(3, move=move['id'], visual=c)]
    shown = project_move_visuals(msgs)
    assert list(shown) == [1] and shown[1]['stage'] == 'complete'
    assert template.render(item={'visual': shown[1]}).count('<figure') == 1


# --- completion association: learner reply must fall inside the move's own window ---
from solo_harness.runtime.ai import move_answer_reply_exists


def test_reply_to_move_a_cannot_complete_move_b():
    rows = [msg(1, move="A", visual=vis("prompt")), msg(2, "LEARNER"), msg(3, move="A", visual=vis("complete")),
            msg(4, move="B", visual=vis("prompt"))]
    assert move_answer_reply_exists(rows, "A", 5) is True
    assert move_answer_reply_exists(rows, "B", 5) is False      # B has no reply of its own


def test_reply_inside_own_window_completes_and_repeats_are_consistent():
    rows = [msg(1, move="A"), msg(2, "LEARNER"), msg(3, "LEARNER"), msg(4, move="B"), msg(5, "LEARNER")]
    assert move_answer_reply_exists(rows, "B", 6) is True
    assert move_answer_reply_exists(rows, "B", 6) is True       # pure / idempotent
    assert move_answer_reply_exists(rows, "A", 4) is True


def test_no_reply_before_the_message_or_unknown_move_never_completes():
    rows = [msg(1, move="A"), msg(2, move="A"), msg(3, "LEARNER")]
    assert move_answer_reply_exists(rows, "A", 3) is False      # reply is not before the new message
    assert move_answer_reply_exists(rows, "Z", 9) is False


# --- Point 4: C1.3 / C1.4 passive visual rendering defects ---
import re
from pathlib import Path
from solo_harness.studies import controlled_c1 as c1


def _render_c1(sub, ped, move_id, stage):
    t = Environment(loader=FileSystemLoader('src/solo_harness/templates'),
                    undefined=StrictUndefined).get_template('partials/session/controlled_c11_visual.html')
    move = next(m for m in c1.contract()['subsections'][sub]['moves_by_pedagogy'][ped] if m['id'] == move_id)
    return t.render(item={'visual': c1.visual_descriptor(move, c1.c1_instance(sub, ped), stage)})


def test_c13_shows_payload_cells_with_distinct_checking_position_in_one_row():
    html = _render_c1('C1.3', 'P1', 'C1.3-P1-M02', 'complete')
    assert html.count('c11-bit-cell') == 6 and html.count('is-parity') == 1 and html.count('<figure') == 1
    assert html.index('is-parity') > html.rindex('<span class="c11-value">0</span>')   # p follows the data bits


def test_c14_prompt_shows_payload_but_not_the_frame_or_parity_bit():
    html = _render_c1('C1.4', 'P2', 'C1.4-P2-M02', 'prompt')
    assert html.count('c11-bit-cell') == 5 and 'is-parity' not in html
    assert '101101' not in re.sub(r'<[^>]+>|\s', '', html)


def test_c14_complete_marks_parity_bit_and_uses_the_move_s_parity_type():
    even = _render_c1('C1.4', 'P2', 'C1.4-P2-M02', 'complete')
    odd = _render_c1('C1.4', 'P2', 'C1.4-P2-M03', 'complete')
    flat = lambda h: re.sub(r'<[^>]+>|\s', '', h)
    assert 'even parity' in even and 'odd parity' not in even and even.count('is-parity') == 1
    assert 'odd parity' in odd and 'even parity' not in odd and odd.count('is-parity') == 1
    assert flat(odd).endswith('100100') or '101100' not in flat(even)


def test_visual_surfaces_use_theme_tokens_not_hardcoded_white():
    css = Path('src/solo_harness/templates/session.html').read_text()
    rules = [l for l in css.splitlines() if 'c11-' in l or 'controlled-c11-visual' in l]
    assert rules and not any('background:#fff' in l for l in rules)
    assert css.count('--panel:') == 3      # light root + both dark theme blocks


# --- Point 4 follow-up: exact C1.4 / C1.3 values, derived independently from the contract ---
C14 = c1.contract()['fixed_cases']['C1.4']
C14_PAYLOAD, C14_EVEN, C14_ODD = C14['payload_bits'], C14['even_frame'], C14['odd_frame']
C14_PARITY_MOVES = [(ped, m['id'], m['visual']['mode'], m['learner_response_policy'])
                    for ped, ms in c1.contract()['subsections']['C1.4']['moves_by_pedagogy'].items()
                    for m in ms if m.get('visual') and m['visual']['component'] == 'parity']


def _frames(html):
    """label -> (cells, [is_parity flags]) parsed from the rendered frame rows."""
    out = {}
    for label, body in re.findall(r'aria-label="([^"]+)"><div class="c11-bit-row">(.*?)</div></div>', html, re.S):
        cells = re.findall(r'<div class="c11-bit-cell( is-parity)?">.*?<span class="c11-value">([^<]*)</span>', body, re.S)
        out[label] = ''.join(v for _, v in cells), [bool(f) for f, _ in cells]
    return out


def test_contract_frames_are_arithmetically_correct():
    ones = C14_PAYLOAD.count('1')
    assert ones == 3 and C14['data_ones'] == 3
    assert C14_EVEN == C14_PAYLOAD + str(ones % 2) and C14_EVEN.count('1') % 2 == 0 and C14_EVEN.count('1') == 4
    assert C14_ODD == C14_PAYLOAD + str((ones + 1) % 2) and C14_ODD.count('1') % 2 == 1 and C14_ODD.count('1') == 3


def test_c14_complete_frames_exact_bits_order_and_parity_cell():
    expected = {'sender_even_prompt': {'Even-parity frame': C14_EVEN},
                'sender_odd_prompt': {'Odd-parity frame': C14_ODD},
                'sender_both': {'Even-parity frame': C14_EVEN, 'Odd-parity frame': C14_ODD}}
    checked = 0
    for ped, move_id, mode, _ in C14_PARITY_MOVES:
        if mode not in expected:
            continue
        frames = _frames(_render_c1('C1.4', ped, move_id, 'complete'))
        assert frames.pop('Payload bits') == (C14_PAYLOAD, [False] * 5)
        assert {k: v[0] for k, v in frames.items()} == expected[mode], move_id
        for label, (bits, flags) in frames.items():
            assert flags == [False] * 5 + [True]               # only the final cell is the parity bit
            assert (bits.count('1') % 2 == 0) == (label == 'Even-parity frame')
            assert bits[:5] == C14_PAYLOAD
        checked += 1
    assert checked == 4      # P1-M02, P2-M02, P2-M03, P3-M01


def test_c14_prompt_shows_only_payload_and_leaks_no_frame_anywhere_in_html():
    assert C14_PARITY_MOVES
    for ped, move_id, mode, policy in C14_PARITY_MOVES:
        html = _render_c1('C1.4', ped, move_id, 'prompt')
        frames = _frames(html)
        assert frames == {'Payload bits': (C14_PAYLOAD, [False] * 5)}, move_id
        assert 'is-parity' not in html and 'odd parity' not in html and 'even parity' not in html
        for secret in (C14_EVEN, C14_ODD, C14['even_fail_received']):
            assert secret not in html and secret not in re.sub(r'<[^>]+>|\s', '', html), (move_id, secret)


def test_c13_exact_cells_dashed_p_and_consistent_stages():
    c13 = c1.contract()['fixed_cases']['C1.3']
    assert c13['payload_bits'] == '10110' and c13['checking_position'] == 'p' and c13['p_is_placeholder_only']
    for ped, move_id in (('P1', 'C1.3-P1-M02'), ('P3', 'C1.3-P3-M01')):
        prompt, complete = (_render_c1('C1.3', ped, move_id, s) for s in ('prompt', 'complete'))
        strip = lambda h: re.sub(r'data-visual-stage="[a-z]+"', '', h)
        assert strip(prompt) == strip(complete)            # non-guided: same content at both stages
        cells = re.findall(r'<div class="c11-bit-cell( is-parity)?"><span class="c11-position">([^<]*)</span>'
                           r'<span class="c11-value">([^<]*)</span>', complete)
        assert [v for _, _, v in cells] == list('10110') + ['p']
        assert [pos for _, pos, _ in cells][:5] == ['1', '2', '3', '4', '5']
        assert [bool(f) for f, _, _ in cells] == [False] * 5 + [True]
        assert 'has no value yet' in complete and not re.search(r'checking</span><span class="c11-value">[01]<', complete)


def test_visual_css_uses_only_defined_custom_properties():
    css = Path('src/solo_harness/templates/session.html').read_text()
    defined = set(re.findall(r'(--[a-z0-9-]+):', css))
    used = {m for l in css.splitlines() if 'c11-' in l or 'controlled-c11-visual' in l
            for m in re.findall(r'var\((--[a-z0-9-]+)', l)}
    assert used and used <= defined, used - defined


# --- Receiver pass/fail comparison (C1.4 receiver_examples / receiver_prompt) ---
RECEIVER_MOVES = [x for x in C14_PARITY_MOVES if x[2].startswith('receiver')]
EVEN_PASS, EVEN_FAIL, ODD_PASS = C14['even_pass_received'], C14['even_fail_received'], C14['odd_pass_received']


def _checks(html):
    return re.findall(r'data-receiver-check="(pass|fail)">.*?aria-label="([^"]+)"><div class="c11-bit-row">(.*?)</div></div>'
                      r'.*?<div class="c11-result">([^<]*)</div>', html, re.S)


def test_receiver_complete_shows_exact_pass_and_fail_frames_with_correct_arithmetic():
    assert {m[1] for m in RECEIVER_MOVES} == {'C1.4-P1-M03', 'C1.4-P2-M04', 'C1.4-P3-M03'}
    for ped, move_id, mode, _ in RECEIVER_MOVES:
        html = _render_c1('C1.4', ped, move_id, 'complete')
        rows = _checks(html)
        got = [(status, label, ''.join(re.findall(r'c11-value">([^<]*)<', body)), result) for status, label, body, result in rows]
        assert [(g[0], g[2]) for g in got] == [('pass', EVEN_PASS), ('fail', EVEN_FAIL), ('pass', ODD_PASS)], move_id
        for status, label, bits, result in got:
            ones, odd_rule = bits.count('1'), 'odd-parity' in label
            assert (ones % 2 == 1 if odd_rule else ones % 2 == 0) == (status == 'pass')        # independent arithmetic
            assert result.startswith('PASS' if status == 'pass' else 'FAIL') and f'{ones} ones' in result
        assert (EVEN_PASS.count('1'), EVEN_FAIL.count('1'), ODD_PASS.count('1')) == (4, 3, 3)
        assert html.count('is-parity') == 3 and html.count('PASS') == 2 and html.count('FAIL') == 1


def test_receiver_prompt_conceals_frames_and_results():
    for ped, move_id, mode, _ in RECEIVER_MOVES:
        html = _render_c1('C1.4', ped, move_id, 'prompt')
        flat = re.sub(r'<[^>]+>|\s', '', html)
        assert 'data-receiver-check' not in html and 'PASS' not in html and 'FAIL' not in html
        assert not any(f in flat for f in (EVEN_PASS, EVEN_FAIL, ODD_PASS))


def test_sender_visuals_unchanged_by_receiver_branch():
    for ped, move_id, mode, _ in C14_PARITY_MOVES:
        if mode.startswith('receiver'):
            continue
        html = _render_c1('C1.4', ped, move_id, 'complete')
        assert 'data-receiver-check' not in html and 'PASS' not in html and 'rule is' not in html
        assert any(f in _frames(html).get(l, ('',))[0] for l, f in (('Even-parity frame', C14_EVEN), ('Odd-parity frame', C14_ODD)))
