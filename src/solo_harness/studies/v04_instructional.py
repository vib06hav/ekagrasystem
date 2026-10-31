"""Independent, oracle-verified F1 instructional instances.

These are curriculum illustrations, NOT assessment reservations or fixed items.
The authored intervention cell controls pedagogy and which illustration is used;
this service supplies changing verified examples for that curriculum transition.
Never pass a frozen assessment instance into Tutor.
"""
from __future__ import annotations

import hashlib
import json
import random
import secrets
from typing import Any

from solo_harness.studies.scientific_v04 import ScientificStudyV04, _oracle
from solo_harness.studies.scientific_v04_policy import _make_one_d, _make_two_d


def resolve_instructional_instance(study: ScientificStudyV04, cell_id: str, seed: int | None = None) -> dict[str, Any]:
    cell = study.cell(cell_id)
    transition = cell["transition_id"]
    rng = random.Random(seed if seed is not None else secrets.randbits(64))
    oracle = _oracle(study.root)
    # These are verified illustration FAMILIES, independent of assessment IDs.
    if transition == "C1":
        convention = "even" if cell["pedagogy_id"] == "P1" else rng.choice(["even", "odd"])
        for _ in range(64):
            sender = _make_one_d(oracle, "sender_parity", {"convention": convention}, rng)
            if cell["pedagogy_id"] != "P3" or sender["oracle"]["sender_check_bit"] != 0:
                break
        shared = {"sent_frame": sender["oracle"]["sent_frame"], "convention": convention}
        # The same clean frame underlies both the sender rule and receiver alteration.
        examples = [sender, _make_one_d(oracle, "single_flip_1d", {"flip_count": 1}, rng, shared)]
    elif transition == "C2":
        odd = _make_one_d(oracle, "multiflip_1d", {"flip_count": 1}, rng)
        one_d_shared = {"sent_frame": odd["oracle"]["sent_frame"],
                        "convention": odd["public"]["convention"]}
        even = _make_one_d(oracle, "multiflip_1d", {"flip_count": 2}, rng, one_d_shared)
        single = _make_two_d(oracle, "full2d_single", {"flip_count": 1}, rng)
        two_d_shared = {"grid": single["public"]["valid_transmitted_grid"]}
        pair = _make_two_d(oracle, "full2d_pair", {"flip_count": 2,
                      "position_universe": "data_cells"}, rng, two_d_shared)
        examples = [odd, even, single, pair]
    elif transition == "C3":
        pair = _make_two_d(oracle, "full2d_pair", {"flip_count": 2,
                "position_universe": "data_cells", "pair_geometry": "same_row_distinct_columns"}, rng)
        shared = {"grid": pair["public"]["valid_transmitted_grid"],
                  "flipped_positions": pair["public"]["flipped_positions"]}
        examples = [
            _make_two_d(oracle, "full2d_single", {"flip_count": 1}, rng, {"grid": shared["grid"]}),
            _make_two_d(oracle, "full2d_compare", {"check_scheme": "row_only", "flip_count": 2,
                "position_universe": "data_cells", "pair_geometry": "same_row_distinct_columns"}, rng, shared),
            _make_two_d(oracle, "full2d_compare", {"check_scheme": "full_row_column", "flip_count": 2,
                "position_universe": "data_cells", "pair_geometry": "same_row_distinct_columns"}, rng, shared),
            _make_two_d(oracle, "full2d_rectangle", {"geometry": "nondegenerate_rectangle",
                "flip_count": 4, "position_universe": "data_cells"}, rng, {"grid": shared["grid"]}),
        ]
    elif transition == "C4":
        pair = _make_two_d(oracle, "full2d_pair", {"flip_count": 2,
                "position_universe": "data_cells", "pair_geometry": "same_row_distinct_columns"}, rng)
        shared = {"grid": pair["public"]["valid_transmitted_grid"],
                  "flipped_positions": pair["public"]["flipped_positions"]}
        row = _make_two_d(oracle, "full2d_compare", {"check_scheme": "row_only", "flip_count": 2,
              "position_universe": "data_cells", "pair_geometry": "same_row_distinct_columns"}, rng, shared)
        full = _make_two_d(oracle, "full2d_compare", {"check_scheme": "full_row_column", "flip_count": 2,
              "position_universe": "data_cells", "pair_geometry": "same_row_distinct_columns"}, rng, shared)
        # Two identical global checks offer no extra detection for data-only errors.
        data = tuple(rng.randrange(2) for _ in range(rng.randint(3, 7)))
        positions = rng.sample(range(len(data)), 2)
        original_global_check = oracle.parity(data)
        after_error = oracle.flip_positions(data, positions)
        twin = {"family": "redundant_global_data_parity", "public": {
            "data_bits": "".join(map(str, data)), "two_identical_even_parity_checks": True,
            "data_only_flipped_positions": positions,
        }, "oracle": {"original_check_bit": original_global_check,
                      "both_duplicate_checks_pass_after_flips": oracle.parity(after_error) == oracle.parity(data)}}
        examples = [row, full, twin]
    else:
        raise ValueError(f"unknown SOLO transition {transition}")
    public = {"illustrations": [{"family": x["family"], "facts": x["public"]} for x in examples],
              "authored_instructional_scenario": cell["instructional_scenario"],
              "scientific_goal": cell["scientific_goal"],
              "instruction": "Use only examples appropriate to this cell; do not expose assessment instances."}
    raw = json.dumps(public, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    case_fingerprints = [hashlib.sha256(json.dumps(x["public"], sort_keys=True,
                         ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() for x in examples]
    return {"instruction_only": True, "verified": True, "public": public,
            "private_oracle": [x["oracle"] for x in examples],
            "case_fingerprints": case_fingerprints,
            "instance_id": hashlib.sha256(("INSTRUCTION_ONLY:" + raw).encode()).hexdigest()}
