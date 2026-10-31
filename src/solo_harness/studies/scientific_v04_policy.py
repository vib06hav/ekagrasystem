"""F1 v0.4 typed scenario executor.

Authoritative science lives in the shipped v0.4 YAML, not this sampler.
All mathematical choices come from typed family/parameter records. The entire
multi-case contract is retained, with postcondition checks against the independent
reference oracle. Unsupported policies raise; nothing silently falls back.
"""
from __future__ import annotations

import hashlib
import json
from itertools import combinations
import random
import secrets
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from solo_harness.studies.scientific_v04 import ScientificStudyV04, ScientificV04Error, _oracle

COMPANION = "EKAGRAAI_F1_V04_TYPED_POLICY_AND_LLM_BOUNDARY_COMPANION_CANDIDATE"
SCHEMA = "ekagra.scientific.typed_instance_policies.v0.4.1-CANDIDATE"
ONE_D = {"sender_parity", "receiver_parity", "single_flip_1d", "multiflip_1d", "checkbit_1d"}
TWO_D = {"full2d_single", "full2d_pair", "full2d_rectangle", "full2d_compare", "full2d_checkbit", "full2d_four_compare"}
GROUPED = {"grouped_checks", "grouped_two_flip", "grouped_uncovered", "grouped_evasion", "grouped_add_check"}
BASE_KEYS = {"flip_count", "position_universe"}
ALLOWED_PARAMS = {
    "sender_parity": {"convention", "contrast_length_vs_ones", "false_length_claim"},
    "receiver_parity": {"convention", "receiver_state", "mark_check_bit", "false_length_claim"},
    "single_flip_1d": {"convention", *BASE_KEYS},
    "multiflip_1d": {"convention", "must_include_check_bit", *BASE_KEYS},
    "checkbit_1d": {"convention", "mark_check_bit", "alter_check_bit", *BASE_KEYS},
    "full2d_single": BASE_KEYS,
    "full2d_pair": {*BASE_KEYS, "pair_geometry", "forbid_unique_two_error_inference"},
    "full2d_rectangle": {*BASE_KEYS, "geometry"},
    "full2d_compare": {*BASE_KEYS, "pair_geometry", "check_scheme"},
    "full2d_checkbit": {*BASE_KEYS, "check_cell_kind"},
    "full2d_four_compare": {*BASE_KEYS, "geometry"},
    "grouped_checks": {"group_count", "group_map", "require_distinct_data_positions"},
    "grouped_two_flip": {*BASE_KEYS, "pair_signature_relation", "group_map", "quantified_check"},
    "grouped_uncovered": {*BASE_KEYS, "group_map"},
    "grouped_evasion": {*BASE_KEYS, "all_checks_pass"},
    "grouped_add_check": {*BASE_KEYS, "group_map", "additional_group_relation"},
}
RELATIONS = {None, "independent_cases", "same_valid_grid_distinct_error_patterns", "same_grid_same_data_flips", "same_data_same_error_universe", "same_scheme_same_witness"}


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ScientificV04Error(message)


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_policy(root: Path) -> dict[str, dict[str, Any]]:
    path = root / COMPANION / "INSTANCE_POLICY_MAPPING_CANDIDATE.yaml"
    reader = YAML(typ="safe")
    reader.allow_duplicate_keys = False
    document = reader.load(path.read_text(encoding="utf-8"))
    _require(isinstance(document, dict) and document.get("schema") == SCHEMA, "unexpected typed policy schema")
    contracts = document.get("contracts")
    _require(isinstance(contracts, dict), "missing typed contracts")
    return contracts


def _validate_spec(family: str, p: dict[str, Any]) -> None:
    _require(family in ALLOWED_PARAMS, f"unsupported family {family}")
    _require(isinstance(p, dict), f"invalid parameters for {family}")
    unknown = set(p) - ALLOWED_PARAMS[family]
    _require(not unknown, f"unimplemented typed parameters for {family}: {sorted(unknown)}")
    accepted = {
        "convention": {"even", "odd", "sample_even_or_odd"},
        "position_universe": {"data_bits_only", "transmitted_full_frame", "check_bit_only",
            "data_cells", "transmitted_full_grid", "full2d_check_cells", "uncovered_data_positions"},
        "receiver_state": {"valid", "invalid", "sample_valid_or_invalid"},
        "pair_geometry": {"same_row_distinct_columns"},
        "geometry": {"nondegenerate_rectangle", "non_rectangle"},
        "check_scheme": {"row_only", "full_row_column", "global_parity_on_data"},
        "check_cell_kind": {"sample_row_column_corner"},
        "group_count": {"2_or_3"},
        "group_map": {"fresh_nonempty_subsets", "must_have_uncovered_position"},
        "pair_signature_relation": {"sample_equal_or_different"},
        "quantified_check": {"all_distinct_data_pairs"},
        "additional_group_relation": {"must_cover_witness", "sample_detects_or_not"},
    }
    for key, value in p.items():
        if key in accepted:
            _require(value in accepted[key], f"unsupported value for {family}.{key}: {value!r}")
        elif key in {"mark_check_bit", "alter_check_bit", "false_length_claim", "contrast_length_vs_ones",
                     "must_include_check_bit", "forbid_unique_two_error_inference", "all_checks_pass"}:
            _require(type(value) is bool, f"{family}.{key} must be boolean")
        elif key == "require_distinct_data_positions":
            _require(type(value) is int and 3 <= value <= 8, "unsupported minimum data positions")
        elif key == "flip_count":
            _require((type(value) is int and 1 <= value <= 8) or value in {
                "odd_bounded", "even_nonzero_bounded", "sample_bounded_data_flips",
                "nonempty_even_overlap_witness"}, "unsupported bounded flip count")


def _count(value: Any, maximum: int, rng: random.Random) -> int:
    _require(maximum >= 1, "empty legal flip universe")
    if isinstance(value, int) and not isinstance(value, bool):
        choices = [value]
    elif value == "odd_bounded":
        choices = [n for n in range(1, maximum + 1, 2)]
    elif value == "even_nonzero_bounded":
        choices = [n for n in range(2, maximum + 1, 2)]
    elif value == "nonempty_even_overlap_witness":
        # The constraint is EVEN overlap with every check, NOT an even error count.
        choices = list(range(1, maximum + 1))
    elif value == "sample_bounded_data_flips":
        choices = list(range(1, maximum + 1))
    else:
        raise ScientificV04Error(f"unsupported flip-count expression {value!r}")
    _require(bool(choices) and all(1 <= n <= maximum for n in choices), "unsatisfiable flip-count policy")
    return rng.choice(choices)


def _convention(p: dict[str, Any], rng: random.Random) -> str:
    choice = p.get("convention", "even")
    if choice == "sample_even_or_odd":
        return rng.choice(["even", "odd"])
    _require(choice in ("even", "odd"), "unrecognized convention")
    return choice


def _bits(rng: random.Random, n: int) -> tuple[int, ...]:
    return tuple(rng.randrange(2) for _ in range(n))


def _make_one_d(oracle, family: str, p: dict, rng: random.Random, shared=None) -> dict:
    convention = shared["convention"] if shared and "sent_frame" in shared else _convention(p, rng)
    # Keep a clean instructional frame fixed when an authored lesson contrasts errors.
    for _ in range(64):
        if shared and "sent_frame" in shared:
            frame = tuple(int(x) for x in shared["sent_frame"])
            data = frame[:-1]
            _require(frame == oracle.make_frame(data, convention), "shared clean frame invalid")
        else:
            data = _bits(rng, rng.randint(3, 7))
            frame = oracle.make_frame(data, convention)
        sender_shortcut_wrong = (len(data) % 2) != oracle.sender_bit(data, convention)
        length_false_claim_counterexample = (len(frame) % 2) == int(convention == "odd")
        if (p.get("contrast_length_vs_ones") and not sender_shortcut_wrong):
            continue
        if (p.get("false_length_claim") and family == "sender_parity" and not sender_shortcut_wrong):
            continue
        if (p.get("false_length_claim") and family == "receiver_parity" and not length_false_claim_counterexample):
            continue
        break
    else:
        raise ScientificV04Error("cannot realize required one-dimensional contrast")
    check = len(frame) - 1
    universe_name = p.get("position_universe", "transmitted_full_frame")
    universes = {"transmitted_full_frame": list(range(len(frame))), "data_bits_only": list(range(check)), "check_bit_only": [check]}
    _require(universe_name in universes, "illegal one-dimensional position universe")
    universe = universes[universe_name]
    if family == "sender_parity" or (family == "checkbit_1d" and p.get("alter_check_bit") is False):
        flips: list[int] = []
    elif family == "receiver_parity":
        state = p.get("receiver_state", "valid")
        _require(state in ("valid", "invalid", "sample_valid_or_invalid"), "unsupported receiver state")
        state = rng.choice(["valid", "invalid"]) if state == "sample_valid_or_invalid" else state
        flips = [] if state == "valid" else [rng.choice(universe)]
    else:
        default = 2 if family == "multiflip_1d" else 1
        wanted = _count(p.get("flip_count", default), len(universe), rng)
        if p.get("must_include_check_bit") is True:
            _require(check in universe, "check bit excluded by policy")
            flips = [check, *rng.sample([x for x in universe if x != check], wanted - 1)]
        else:
            flips = rng.sample(universe, wanted)
    received = oracle.flip_positions(frame, flips)
    passes = oracle.receiver_pass(received, convention)
    _require(passes == (len(flips) % 2 == 0), "invalid 1D oracle postcondition")
    if family == "sender_parity" and p.get("contrast_length_vs_ones") is True:
        # A length-parity shortcut (number of positions rather than number of 1s)
        # must disagree with the true appended check bit for this instance.
        _require((len(data) % 2) != oracle.sender_bit(data, convention), "length contrast not satisfied")
    if family == "sender_parity":
        public = {"convention": convention, "data_bits": "".join(map(str, data)), "check_bit_position": check}
    else:
        public = {"convention": convention, "received_frame": "".join(map(str, received)), "check_bit_position": check}
        if family != "receiver_parity":
            public.update({"sent_frame": "".join(map(str, frame)), "flipped_positions": list(flips)})
    if p.get("mark_check_bit"):
        public["check_bit_is_last_position"] = True
    if p.get("false_length_claim"):
        public["peer_claim_to_evaluate"] = "A frame is valid whenever its length has the required parity, regardless of bit values."
    private = {"sender_check_bit": int(frame[-1]), "sent_frame": "".join(map(str, frame)),
               "received_frame": "".join(map(str, received)), "flipped_positions": list(flips),
               "receiver_passes": passes, "ones_in_received_frame": sum(received)}
    return {"family": family, "public": public, "oracle": private}


def _is_rectangle(coords: list[tuple[int, int]]) -> bool:
    return len(coords) == 4 and len({r for r, _ in coords}) == 2 and len({c for _, c in coords}) == 2 and { (r, c) for r in {x[0] for x in coords} for c in {x[1] for x in coords}} == set(coords)


def _make_two_d(oracle, family: str, p: dict, rng: random.Random, shared: dict | None = None) -> dict:
    if shared and "grid" in shared:
        grid = tuple(tuple(int(c) for c in row) for row in shared["grid"])
    else:
        rows, cols = rng.choice([2, 3]), rng.choice([2, 3, 4])
        # Four-data comparison needs enough data positions for a nonrectangle.
        if family == "full2d_four_compare" and rows * cols == 4:
            cols = 3
        grid = oracle.full_grid([_bits(rng, cols) for _ in range(rows)])
    rows, cols = len(grid) - 1, len(grid[0]) - 1
    data_positions = [(r, c) for r in range(rows) for c in range(cols)]
    full_positions = [(r, c) for r in range(rows + 1) for c in range(cols + 1)]
    check_positions = [x for x in full_positions if x not in data_positions]
    universe_name = p.get("position_universe", "transmitted_full_grid")
    universes = {"data_cells": data_positions, "transmitted_full_grid": full_positions, "full2d_check_cells": check_positions}
    _require(universe_name in universes, "illegal full2d position universe")
    universe = universes[universe_name]
    if shared and "flipped_positions" in shared:
        flips = [tuple(x) for x in shared["flipped_positions"]]
        _require(set(flips).issubset(set(universe)), "shared flips violate position universe")
    elif family in ("full2d_rectangle", "full2d_four_compare") and p.get("geometry") == "nondegenerate_rectangle":
        r1, r2 = rng.sample(range(rows), 2)
        c1, c2 = rng.sample(range(cols), 2)
        flips = [(r1, c1), (r1, c2), (r2, c1), (r2, c2)]
    elif family == "full2d_four_compare" and p.get("geometry") == "non_rectangle":
        candidates = [list(x) for x in combinations(data_positions, 4) if not _is_rectangle(list(x))]
        _require(bool(candidates), "no nonrectangle set in selected dimensions")
        flips = rng.choice(candidates)
    elif p.get("pair_geometry") == "same_row_distinct_columns":
        _require(len(data_positions) >= 2, "pair geometry not possible")
        r = rng.randrange(rows)
        flips = [(r, c) for c in rng.sample(range(cols), 2)]
    elif family == "full2d_checkbit" and p.get("check_cell_kind") == "sample_row_column_corner":
        category = rng.choice(["row_check", "column_check", "corner_check"])
        choices = {"row_check": [(r, cols) for r in range(rows)],
                   "column_check": [(rows, c) for c in range(cols)], "corner_check": [(rows, cols)]}
        flips = [rng.choice(choices[category])]
    else:
        default = 4 if family in ("full2d_rectangle", "full2d_four_compare") else (2 if family == "full2d_pair" else 1)
        flips = rng.sample(universe, _count(p.get("flip_count", default), len(universe), rng))
    _require(len(flips) == len(set(flips)), "duplicate 2D flip")
    if "flip_count" in p and isinstance(p["flip_count"], int):
        _require(len(flips) == p["flip_count"], "wrong 2D flip count")
    if p.get("geometry") == "nondegenerate_rectangle":
        _require(_is_rectangle(flips), "invalid rectangle")
    if p.get("geometry") == "non_rectangle":
        _require(len(flips) == 4 and not _is_rectangle(flips) and set(flips).issubset(set(data_positions)), "invalid nonrectangle")
    if p.get("pair_geometry") == "same_row_distinct_columns":
        _require(len(flips) == 2 and flips[0][0] == flips[1][0] and flips[0][1] != flips[1][1] and all(x in data_positions for x in flips), "invalid same-row pair")
    syndrome = oracle.grid_syndrome(grid, flips)
    if family in ("full2d_rectangle", "full2d_four_compare") and p.get("geometry") == "nondegenerate_rectangle":
        _require(syndrome["passes"], "four-rectangle parity postcondition failed")
    if family == "full2d_four_compare" and p.get("geometry") == "non_rectangle":
        _require(not syndrome["passes"], "nonrectangle four-flip comparison must fail at least one check")
    if family == "full2d_single":
        _require(len(syndrome["failing_rows"]) == 1 and len(syndrome["failing_cols"]) == 1,
                 "single-position syndrome must identify exactly one row and column")
    scheme = p.get("check_scheme", "full_row_column")
    _require(scheme in ("row_only", "full_row_column", "global_parity_on_data"), "unknown checking scheme")
    if scheme == "row_only":
        check_passes = not syndrome["failing_rows"]
    elif scheme == "global_parity_on_data":
        _require(all(x in data_positions for x in flips), "global data parity cannot share check-bit errors")
        check_passes = len(flips) % 2 == 0
    else:
        check_passes = syndrome["passes"]
    # The independent oracle computes all schemes, but the active scheme is explicit.
    private = {"syndrome": syndrome, "check_scheme": scheme, "scheme_passes": check_passes,
               "global_data_parity_passes": len(flips) % 2 == 0 if all(x in data_positions for x in flips) else None,
               "is_rectangle": _is_rectangle(flips), "flipped_positions": [list(x) for x in flips]}
    public = {"valid_transmitted_grid": ["".join(map(str, row)) for row in grid],
              "flipped_positions": [list(x) for x in flips], "check_scheme": scheme,
              "data_rows": rows, "data_columns": cols}
    if family == "full2d_checkbit":
        x = flips[0]
        public["flipped_check_bit_kind"] = "corner" if x == (rows, cols) else "row" if x[1] == cols else "column"
    if p.get("forbid_unique_two_error_inference"):
        private["forbid_unique_two_error_inference"] = True
    return {"family": family, "public": public, "oracle": private}


def _make_grouped(oracle, family: str, p: dict, rng: random.Random, shared: dict | None = None) -> dict:
    if shared and "groups" in shared:
        n, groups = shared["data_positions"], [list(g) for g in shared["groups"]]
    else:
        n = rng.randint(max(4, int(p.get("require_distinct_data_positions", 3))), 8)
        count = rng.choice([2, 3]) if p.get("group_count", "2_or_3") == "2_or_3" else None
        _require(count is not None, "unsupported grouped check count")
        groups = [sorted(rng.sample(range(n), rng.randint(1, n - 1))) for _ in range(count)]
    _require(len(groups) in (2, 3) and all(g and len(set(g)) == len(g) and set(g).issubset(set(range(n))) for g in groups), "invalid group map")
    group_mode = p.get("group_map")
    _require(group_mode in (None, "fresh_nonempty_subsets", "must_have_uncovered_position"), "unsupported group map")
    if group_mode == "must_have_uncovered_position" and not (shared and "groups" in shared):
        missing = rng.randrange(n)
        groups = [sorted([x for x in g if x != missing] or [(missing + 1) % n]) for g in groups]
    uncovered = sorted(set(range(n)) - set().union(*(set(g) for g in groups)))
    if group_mode == "must_have_uncovered_position":
        _require(bool(uncovered), "uncovered position missing")
    # Every group has its own correct even-parity check bit for the same data.
    data = tuple(int(x) for x in shared["data_bits"]) if shared and "data_bits" in shared else _bits(rng, n)
    _require(len(data) == n, "shared grouped data does not match the scheme")
    check_bits = [int(oracle.sender_bit((data[i] for i in group), "even")) for group in groups]
    _require(all(oracle.receiver_pass(tuple(data[i] for i in g) + (b,), "even")
                 for g, b in zip(groups, check_bits)), "invalid grouped baseline parity")
    signatures = [oracle.signature(n, groups, i) for i in range(n)]
    pair_relation = p.get("pair_signature_relation")
    _require(pair_relation in (None, "sample_equal_or_different"), "unsupported pair signature relation")
    if shared and "flipped_positions" in shared:
        flips = list(shared["flipped_positions"])
    elif family == "grouped_checks" or (family == "grouped_uncovered" and "flip_count" not in p):
        flips = []
    elif family == "grouped_evasion" or p.get("flip_count") == "nonempty_even_overlap_witness":
        possible = [list(x) for size in range(1, n + 1) for x in combinations(range(n), size) if oracle.group_syndrome(n, groups, x)["passes"]]
        if not possible:
            # Construct a fresh scheme that admits a two-flip witness without fixing bits/positions.
            a, b = rng.sample(range(n), 2)
            groups = [sorted(set([a, b, *rng.sample([x for x in range(n) if x not in (a, b)], rng.randint(0, n - 2))])) for _ in range(len(groups))]
            signatures = [oracle.signature(n, groups, i) for i in range(n)]
            possible = [[a, b]]
        flips = rng.choice(possible)
    elif family == "grouped_uncovered" or p.get("position_universe") == "uncovered_data_positions":
        _require(bool(uncovered), "uncovered flip impossible")
        flips = rng.sample(uncovered, _count(p.get("flip_count", 1), len(uncovered), rng))
    elif pair_relation:
        same = bool(rng.randrange(2))
        eligible = [(i, j) for i in range(n) for j in range(i + 1, n) if (signatures[i] == signatures[j]) == same]
        if not eligible:
            eligible = [(i, j) for i in range(n) for j in range(i + 1, n)]
        flips = list(rng.choice(eligible))
    elif family == "grouped_add_check":
        flips = rng.sample(range(n), _count(p.get("flip_count", 2), n, rng))
    else:
        flips = rng.sample(range(n), _count(p.get("flip_count", 2), n, rng))
    _require(len(flips) == len(set(flips)) and set(flips).issubset(set(range(n))), "invalid grouped error positions")
    if p.get("position_universe") == "uncovered_data_positions":
        _require(set(flips).issubset(set(uncovered)), "error outside uncovered positions")
    syndrome = oracle.group_syndrome(n, groups, flips)
    if family == "grouped_evasion" or p.get("all_checks_pass"):
        _require(bool(flips) and syndrome["passes"], "nonempty evasion witness failed")
    private = {"syndrome": syndrome, "signatures": [list(s) for s in signatures],
               "flipped_positions": list(flips), "group_check_bits": check_bits}
    if len(flips) == 2:
        private["pair_signatures_equal"] = signatures[flips[0]] == signatures[flips[1]]
    if p.get("quantified_check") is not None:
        _require(p["quantified_check"] == "all_distinct_data_pairs", "unsupported pair quantifier")
        private["all_two_data_flips_detectable"] = oracle.detectable_every_two_data_flips(n, groups)
        private["undetected_pairs"] = [[i, j] for i in range(n) for j in range(i + 1, n) if signatures[i] == signatures[j]]
    public = {"data_positions": n, "data_bits": "".join(map(str, data)), "groups": groups,
              "group_check_bits": check_bits, "flipped_positions": list(flips), "error_universe": "data_bits_only"}
    if family == "grouped_add_check":
        relation = p.get("additional_group_relation", "sample_detects_or_not")
        _require(relation in ("must_cover_witness", "sample_detects_or_not"), "unsupported added-check relation")
        _require(bool(flips), "additional check requires nonempty witness")
        desired = True if relation == "must_cover_witness" else bool(rng.randrange(2))
        candidates = [list(g) for size in range(1, min(n, 7) + 1) for g in combinations(range(n), size) if (len(set(g) & set(flips)) % 2 == 1) == desired]
        _require(bool(candidates), "no check subset with desired witness overlap")
        added = rng.choice(candidates)
        detects = len(set(added) & set(flips)) % 2 == 1
        _require(detects == desired, "additional check overlap postcondition failed")
        public["added_group"] = added
        private["added_group_detects_witness"] = detects
        private["syndrome_with_added_group"] = oracle.group_syndrome(n, [*groups, added], flips)
    return {"family": family, "public": public, "oracle": private}


def _shared_context(case: dict) -> dict:
    public = case["public"]
    if case["family"] in TWO_D:
        return {"grid": public["valid_transmitted_grid"], "flipped_positions": public["flipped_positions"]}
    if case["family"] in GROUPED:
        return {"data_positions": public["data_positions"], "data_bits": public["data_bits"],
                "groups": public["groups"], "flipped_positions": public["flipped_positions"]}
    return {}


def resolve_typed_case(study: ScientificStudyV04, contract_id: str, seed: int | None = None) -> dict[str, Any]:
    policy = load_policy(study.root).get(contract_id)
    _require(bool(policy), f"typed policy unavailable: {contract_id}")
    source_items = [s for b in study.assessments["blueprints"] for s in b["items"] if s["id"] == contract_id]
    _require(len(source_items) == 1, f"scientific contract unavailable: {contract_id}")
    slot = source_items[0]
    _require(policy.get("type") == slot["type"] and policy.get("source_scenario_family") == slot["scenario_family"], "policy/science disagreement")
    specs = policy.get("cases")
    _require(isinstance(specs, list) and bool(specs), "missing required cases")
    relation = policy.get("case_relation")
    _require(relation in RELATIONS, "unsupported case relation")
    _require(len(specs) == 1 if policy.get("case_plan") == "single" else len(specs) >= 2, "case-plan cardinality violation")
    rng = random.Random(seed if seed is not None else secrets.randbits(64))
    oracle = _oracle(study.root)
    cases: list[dict] = []
    for index, spec in enumerate(specs):
        family, params = spec["family"], spec.get("parameters", {})
        _validate_spec(family, params)
        shared = _shared_context(cases[0]) if cases and relation in ("same_valid_grid_distinct_error_patterns", "same_grid_same_data_flips", "same_data_same_error_universe", "same_scheme_same_witness") else None
        if relation == "same_valid_grid_distinct_error_patterns" and shared:
            shared.pop("flipped_positions", None)
        if family in ONE_D:
            result = _make_one_d(oracle, family, params, rng, shared)
        elif family in TWO_D:
            result = _make_two_d(oracle, family, params, rng, shared)
        elif family in GROUPED:
            result = _make_grouped(oracle, family, params, rng, shared)
        else:
            raise ScientificV04Error(f"unsupported family {family}")
        result["name"] = spec.get("name", chr(97 + index))
        cases.append(result)
    if relation == "same_valid_grid_distinct_error_patterns":
        _require(cases[0]["public"]["valid_transmitted_grid"] == cases[1]["public"]["valid_transmitted_grid"] and cases[0]["public"]["flipped_positions"] != cases[1]["public"]["flipped_positions"], "same-grid comparison broken")
    if relation in ("same_grid_same_data_flips", "same_data_same_error_universe"):
        _require(all(c["public"]["valid_transmitted_grid"] == cases[0]["public"]["valid_transmitted_grid"] and c["public"]["flipped_positions"] == cases[0]["public"]["flipped_positions"] for c in cases[1:]), "same-flip comparison broken")
    if relation == "same_scheme_same_witness":
        _require(all(c["public"]["groups"] == cases[0]["public"]["groups"] and c["public"]["flipped_positions"] == cases[0]["public"]["flipped_positions"] for c in cases[1:]), "shared grouped witness broken")
    projection = {"case_relation": relation or "single", "cases": [{"name": c["name"], "family": c["family"], **c["public"]} for c in cases]}
    identity = hashlib.sha256(_canonical({"contract": contract_id, "projection": projection}).encode("utf-8")).hexdigest()
    return {"policy": policy, "family": cases[0]["family"], "public": projection, "oracle": {"cases": [{"name": c["name"], **c["oracle"]} for c in cases]}, "cases": cases, "instance_id": identity}
