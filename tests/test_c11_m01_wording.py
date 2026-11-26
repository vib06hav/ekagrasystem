"""Research-baseline guard for the authoritative C1 contract (Decision 1).

The C1.1 M01 ``exact_delivery`` text for P1-P3 is the verified Git HEAD wording. An earlier, unapproved rewrite was
reverted; any change to the authoritative contract now fails here and needs explicit professor approval plus a
deliberate update of the pinned hash below.
"""
from solo_harness.studies.controlled_c1 import contract, contract_hash

HEAD_CONTRACT_SHA256 = "82fbfd73c038249e48c1f145abf30ffd0adddf78ed2c0ea0876b083df7d9614e"
EXPECTED = {
    "P1": "Information is what we want to share, and data is how we represent it. Digital systems use bits. "
          "Each bit can be `0` or `1`.",
    "P2": "Information is what we want to share, and data is how we represent it. A bit can be `0` or `1`. "
          "For our example, Yes = `1` and No = `0`.",
    "P3": "Information is what we want to share, and data is how we represent it. One bit can be `0` or `1`; "
          "`110` has three bits in order. Here, we use `1` for Yes and `0` for No.",
}


def m01(p):
    return contract()["subsections"]["C1.1"]["moves_by_pedagogy"][p][0]


def test_contract_hash_is_the_verified_head_baseline():
    assert contract_hash() == HEAD_CONTRACT_SHA256


def test_m01_exact_delivery_is_the_original_head_wording():
    for p, text in EXPECTED.items():
        move = m01(p)
        assert move["id"] == f"C1.1-{p}-M01"
        assert move["exact_delivery"] == text


def test_all_52_moves_preserved():
    total = sum(len(m) for s in contract()["subsections"].values() for m in s["moves_by_pedagogy"].values())
    assert total == 52
