"""# CHANGED: independent arithmetic checks for verified C2 and C4 case banks."""
from itertools import combinations
from solo_harness.runtime.controlled_executor import contract


def _status(bits, members, index):
    return 'PASS' if sum(int(bits[index[name]]) for name in members) % 2 == 0 else 'FAIL'


def _flip(bits, index, positions):
    seq = list(bits)
    for name in positions:
        i = index[name]
        seq[i] = '1' if seq[i]=='0' else '0'
    return ''.join(seq)


def test_c4_original_error_cases_and_general_detection_rule():
    cases=contract('C4')['fixed_cases']['C4.2']
    initial=cases['initial_complete_sequence']
    positions=cases['position_order']
    ix={k:i for i,k in enumerate(positions)}
    for group in cases['groups'].values():
        assert _status(initial, group['members'], ix)=='PASS'
    checked=0
    for n in range(1,len(positions)+1):
        for flips in combinations(positions,n):
            sequence=_flip(initial,ix,flips)
            observed={name:_status(sequence,g['members'],ix) for name,g in cases['groups'].items()}
            counts={name:len(set(flips)&set(g['members'])) for name,g in cases['groups'].items()}
            assert all((observed[name]=='FAIL')==(counts[name]%2==1) for name in counts)
            checked+=1
    assert checked==63
    for case in cases['error_cases'].values():
        sequence=_flip(initial,ix,case['flipped_positions'])
        assert sequence == case['received_sequence']
        assert {name:_status(sequence,g['members'],ix) for name,g in cases['groups'].items()} == case['group_results']


def test_c4_added_rule_alternatives_and_transfer():
    cases=contract('C4')['fixed_cases']['C4.3']
    target=cases['specified_target']['flipped_positions']
    for label,item in cases['additional_check_alternatives'].items():
        ix={p:i for i,p in enumerate(item['position_order'])}
        observed=_flip(item['initial_complete_sequence'],ix,target)
        assert observed==item['target_received_sequence']
        assert _status(item['initial_complete_sequence'],item['added_group_members'],ix)=='PASS'
        assert _status(observed,item['added_group_members'],ix)==item['target_group_results']['C']
        assert item['new_group_target_flip_count']==len(set(target)&set(item['added_group_members']))
    assert cases['additional_check_alternatives']['candidate_A']['target_group_results']['C']=='FAIL'
    assert cases['additional_check_alternatives']['candidate_B']['target_group_results']['C']=='PASS'
    transfer=cases['transfer_arrangement']
    ix={p:i for i,p in enumerate(transfer['position_order'])}
    for group in transfer['groups'].values():
        assert _status(transfer['initial_complete_sequence'],group['members'],ix)=='PASS'
    for case in transfer['cases'].values():
        seq=_flip(transfer['initial_complete_sequence'],ix,case['flipped_positions'])
        assert seq==case['received_sequence']
        assert {name:_status(seq,g['members'],ix) for name,g in transfer['groups'].items()}==case['group_results']


def test_every_two_bit_change_is_detected_by_full_two_dimensional_parity():
    valid=['1010','0101','1111']
    assert all(sum(int(c) for c in row)%2==0 for row in valid)
    assert all(sum(int(valid[r][col]) for r in range(3))%2==0 for col in range(4))
    for first,second in combinations(range(12),2):
        grid=[list(row) for row in valid]
        for index in (first,second):
            row,col=divmod(index,4)
            grid[row][col]='1' if grid[row][col]=='0' else '0'
        row_failed=any(sum(int(c) for c in row)%2 for row in grid)
        column_failed=any(sum(int(grid[row][col]) for row in range(3))%2 for col in range(4))
        assert row_failed or column_failed
    assert len(list(combinations(range(12),2)))==66
