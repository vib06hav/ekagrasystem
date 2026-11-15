from solo_harness.studies.controlled_c23 import contract, move, section_move_count


def test_reviewed_c2_c3_contract_coverage_and_prompt_safe_active_move():
    assert section_move_count("C2") == 60
    assert section_move_count("C3") == 30
    assert len(contract("C2")["subsections"]) == 4
    assert len(contract("C3")["subsections"]) == 2
    active = move("C2.2", "P2", 0)
    assert active["id"] == "C2.2-P2-M01"
    assert "exact_delivery" not in active
