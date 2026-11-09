"""Typed, oracle-backed v0.5.1 scenario realization.

The corrected v0.5.1 contracts retain the stable F1 slot identifiers.  We
reuse the mature v0.4 typed executor only as a mathematical sampler, validate
the resulting cases against the persisted v0.5.1 contract, and replace the
seven corrected-policy entries whose scientific family changed in v0.5.1.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import secrets
from functools import lru_cache
from pathlib import Path

from solo_harness.studies.scientific_v04 import _oracle
from solo_harness.studies.scientific_v04_policy import (
    GROUPED, ONE_D, TWO_D, _make_grouped, _make_one_d, _make_two_d,
    _shared_context, _validate_spec, load_policy,
)


class V051ScenarioError(ValueError):
    pass


def _require(ok, message):
    if not ok: raise V051ScenarioError(message)


def _compact(value): return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _v04_root() -> Path:
    return Path(__file__).resolve().parents[3] / "studies" / "networks_error_detection_parity_f1" / "v0.4"


@lru_cache(maxsize=1)
def _base_policies(): return load_policy(_v04_root())


# These are explicit replacements for the seven source contracts corrected
# between v0.4 and v0.5.1.  The remaining 57 policies are independently
# checked against the v0.5.1 source family and type on every resolution.
_CORRECTED = {
    "C2-A4-Q2": {"case_relation": None, "cases": [{"name": "a", "family": "full2d_pair", "parameters": {"flip_count": 2, "position_universe": "transmitted_full_grid", "forbid_unique_two_error_inference": True}}]},
    "C2-A4-Q3": {"case_relation": None, "cases": [{"name": "a", "family": "full2d_pair", "parameters": {"flip_count": 2, "position_universe": "transmitted_full_grid", "forbid_unique_two_error_inference": True}}]},
    "C2-A4-S": {"case_relation": None, "cases": [{"name": "a", "family": "full2d_pair", "parameters": {"flip_count": 2, "position_universe": "transmitted_full_grid", "forbid_unique_two_error_inference": True}}]},
    "C3-A4-Q1": {"case_relation": "three_flip_mimic", "cases": [{"name": "one_flip", "family": "full2d_three_mimic", "parameters": {}}]},
    "C3-A4-Q2": {"case_relation": None, "cases": [{"name": "a", "family": "full2d_rectangle", "parameters": {"flip_count": 4, "position_universe": "data_cells", "geometry": "nondegenerate_rectangle"}}]},
    "C3-A4-Q3": {"case_relation": "receiver_evidence_candidates", "cases": [{"name": "receiver_evidence", "family": "full2d_evidence", "parameters": {}}]},
    "C3-A4-S": {"case_relation": "receiver_evidence_candidates", "cases": [{"name": "receiver_evidence", "family": "full2d_evidence", "parameters": {}}]},
}

# v0.5.1 deliberately changed seven v0.4 contract families.  These are
# expected SOURCE family names, not values to copy into the typed policy.
_REVISED_SOURCE_FAMILIES = {
    "C2-A4-Q2": "full2d_pair", "C2-A4-Q3": "full2d_pair", "C2-A4-S": "full2d_pair",
    "C3-A4-Q1": "full2d_three_mimic", "C3-A4-Q2": "full2d_rectangle",
    "C3-A4-Q3": "full2d_evidence", "C3-A4-S": "full2d_evidence",
}


def typed_policy(compiled, slot_id: str) -> dict:
    slots = {item["id"]: item for blueprint in compiled.authored["v051"]["scientific"]["assessment_families.yaml"]["blueprints"] for item in blueprint["items"]}
    slot = slots.get(slot_id); _require(slot is not None, f"unknown v0.5.1 slot: {slot_id}")
    base = _base_policies().get(slot_id); _require(base is not None, f"missing typed v0.5.1 policy: {slot_id}")
    policy = copy.deepcopy(base)
    expected = _REVISED_SOURCE_FAMILIES.get(slot_id, base["source_scenario_family"])
    _require(slot["scenario_family"] == expected, f"typed policy/source family disagreement: {slot_id}")
    if slot_id in _CORRECTED:
        policy.update(copy.deepcopy(_CORRECTED[slot_id]))
        policy["source_scenario_family"] = expected
    _require(policy["type"] == slot["type"], f"typed policy type disagreement: {slot_id}")
    _require(policy["source_scenario_family"] == slot["scenario_family"], f"typed policy family disagreement: {slot_id}")
    _require(bool(policy.get("cases")), f"typed policy has no cases: {slot_id}")
    return policy


def _mimic_case(oracle, rng):
    data = [[rng.randrange(2) for _ in range(3)] for _ in range(2)]
    grid = oracle.full_grid(data)
    r, c = rng.randrange(2), rng.randrange(3)
    r2, c2 = 1 - r, next(value for value in range(3) if value != c)
    one, three = [(r, c)], [(r, c2), (r2, c), (r2, c2)]
    a, b = oracle.grid_syndrome(grid, one), oracle.grid_syndrome(grid, three)
    _require(a == b and len(one) == 1 and len(three) == 3, "three-flip mimic syndrome mismatch")
    public_grid = ["".join(map(str, row)) for row in grid]
    return [{"name": "one_flip", "family": "full2d_three_mimic", "public": {"valid_transmitted_grid": public_grid, "receiver_syndrome": a, "candidate_pattern": [list(x) for x in one], "data_rows": 2, "data_columns": 3}, "oracle": {"actual_flipped_positions": [list(x) for x in one], "syndrome": a}}, {"name": "three_flip", "family": "full2d_three_mimic", "public": {"valid_transmitted_grid": public_grid, "receiver_syndrome": b, "candidate_pattern": [list(x) for x in three], "data_rows": 2, "data_columns": 3}, "oracle": {"actual_flipped_positions": [list(x) for x in three], "syndrome": b}}]


def _evidence_case(oracle, rng):
    cases = _mimic_case(oracle, rng)
    # The receiver sees one syndrome and is shown multiple candidate patterns;
    # the private record retains independently computed syndrome facts.
    observed = cases[0]["oracle"]["syndrome"]
    public = {"valid_transmitted_grid": cases[0]["public"]["valid_transmitted_grid"], "receiver_observation": observed,
              "candidate_error_patterns": [cases[0]["public"]["candidate_pattern"], cases[1]["public"]["candidate_pattern"]], "data_rows": 2, "data_columns": 3}
    return [{"name": "receiver_evidence", "family": "full2d_evidence", "public": public,
             "oracle": {"observed_syndrome": observed, "candidate_syndromes": [cases[0]["oracle"]["syndrome"], cases[1]["oracle"]["syndrome"]], "candidate_patterns": [cases[0]["oracle"]["actual_flipped_positions"], cases[1]["oracle"]["actual_flipped_positions"]]}}]


def _redact(case, slot_id):
    public = copy.deepcopy(case["public"])
    # Detection-without-location contracts cannot disclose the answer through
    # the scenario facts.  The private oracle still records exact flips.
    if slot_id in {"C1-A3-Q3", "C2-A1-Q3"}:
        public.pop("flipped_positions", None)
    return public


def _independently_verify(cases, oracle):
    """Recompute every displayed mathematical outcome from source facts.

    The check deliberately does not trust the generator's saved oracle dict.
    """
    for case in cases:
        public, private, family = case["public"], case["oracle"], case["family"]
        if family in ONE_D:
            sent = private["sent_frame"]
            _require(isinstance(sent, str) and len(sent) >= 2 and set(sent) <= {"0", "1"}, "invalid 1D sent frame")
            _require(public.get("convention") in {"even", "odd"}, "invalid declared 1D convention")
            frame = tuple(int(x) for x in sent)
            _require(frame == oracle.make_frame(frame[:-1], public["convention"]), "invalid initial 1D parity frame")
            _require(private.get("sender_check_bit") == frame[-1], "invalid sender check bit")
            _require(public.get("check_bit_position") == len(frame) - 1, "invalid marked check-bit position")
            if "data_bits" in public:
                _require(public["data_bits"] == sent[:-1], "public 1D data disagrees with sender")
            if "sent_frame" in public:
                _require(public["sent_frame"] == sent, "public 1D transmitted frame disagreement")
            received = oracle.flip_positions(frame, private["flipped_positions"])
            _require("".join(map(str, received)) == private["received_frame"], "1D received frame mismatch")
            if "received_frame" in public:
                _require(public["received_frame"] == private["received_frame"], "public received frame mismatch")
            if "flipped_positions" in public:
                _require(public["flipped_positions"] == private["flipped_positions"], "public 1D flipped positions mismatch")
            _require(oracle.receiver_pass(received, public["convention"]) == private["receiver_passes"], "1D parity oracle mismatch")
        elif family in {"full2d_evidence", "full2d_three_mimic"}:
            grid = tuple(tuple(int(x) for x in row) for row in public["valid_transmitted_grid"])
            _require(grid == oracle.full_grid([row[:-1] for row in grid[:-1]]), "invalid initial deceptive 2D grid")
            if family == "full2d_three_mimic":
                actual = oracle.grid_syndrome(grid, [tuple(x) for x in public["candidate_pattern"]])
                _require(actual == private["syndrome"] and actual == public["receiver_syndrome"], "three-flip mimic oracle mismatch")
                continue
            actual = [oracle.grid_syndrome(grid, [tuple(x) for x in pattern]) for pattern in private["candidate_patterns"]]
            _require(actual == private["candidate_syndromes"] and all(item == private["observed_syndrome"] for item in actual) and private["observed_syndrome"] == public["receiver_observation"], "receiver-evidence candidate mismatch")
        elif family in TWO_D and "valid_transmitted_grid" in public:
            grid = tuple(tuple(int(x) for x in row) for row in public["valid_transmitted_grid"])
            _require(grid == oracle.full_grid([row[:-1] for row in grid[:-1]]), "invalid initial full 2D grid including corner")
            flips = [tuple(x) for x in private.get("flipped_positions", private.get("actual_flipped_positions", []))]
            actual = oracle.grid_syndrome(grid, flips)
            expected = private.get("syndrome", private.get("observed_syndrome"))
            _require(actual == expected, "2D syndrome oracle mismatch")
        elif family in GROUPED:
            public_groups = public["groups"]
            actual = oracle.group_syndrome(public["data_positions"], public_groups, private["flipped_positions"])
            _require(actual == private["syndrome"], "grouped-check oracle mismatch")
            data = tuple(int(x) for x in public["data_bits"])
            _require(all(oracle.receiver_pass(tuple(data[i] for i in group) + (bit,), "even") for group, bit in zip(public_groups, private["group_check_bits"])), "group check-bit baseline mismatch")
            if "added_group" in public:
                detects = len(set(public["added_group"]) & set(private["flipped_positions"])) % 2 == 1
                _require(detects == private["added_group_detects_witness"], "added-group oracle mismatch")


def _validate(slot_id, slot, policy, cases, oracle):
    # A source slot names its primary scenario family.  Several subjective and
    # contrast contracts deliberately include supporting cases from another
    # family (for example, 1D plus full 2D); the typed policy is the explicit
    # authority for those multi-case relationships.
    _require(policy["source_scenario_family"] == slot["scenario_family"], "typed policy violates source family")
    _independently_verify(cases, oracle)
    if slot_id == "C1-A2-Q1": _require(cases[0]["public"]["convention"] == "odd", "C1-A2 must use odd parity")
    if slot_id == "C2-A1-Q1":
        counts = [len(case["oracle"]["flipped_positions"]) for case in cases]
        _require(any(value % 2 for value in counts) and any(value and value % 2 == 0 for value in counts), "C2-A1 requires odd/even contrast")
    if slot_id == "C3-A1-Q3":
        _require(cases[0]["public"]["valid_transmitted_grid"] == cases[1]["public"]["valid_transmitted_grid"] and cases[0]["public"]["flipped_positions"] == cases[1]["public"]["flipped_positions"], "C3-A1 requires matched error conditions")
    if slot_id == "C3-A4-Q1": _require(cases[0]["oracle"]["syndrome"] == cases[1]["oracle"]["syndrome"], "C3-A4 requires identical deceptive syndrome")
    if slot_id in {"C3-A4-Q3", "C3-A4-S"}: _require(len(cases[0]["oracle"]["candidate_patterns"]) >= 2 and len({tuple(x["failing_rows"]) + tuple(x["failing_cols"]) for x in cases[0]["oracle"]["candidate_syndromes"]}) == 1, "C3-A4 requires multiple receiver-consistent patterns")
    if slot_id == "C4-A1-Q3": _require(bool(cases[0]["oracle"]["flipped_positions"]) and cases[0]["oracle"]["syndrome"]["passes"], "C4-A1 requires nonempty undetected witness")
    if slot_id == "C4-A2-Q3": _require(len(cases[0]["oracle"]["flipped_positions"]) == 2 and cases[0]["oracle"]["syndrome"]["passes"], "C4-A2 requires missed two-data-bit pattern")
    if slot_id in {"C4-A3-Q3", "C4-A4-Q3"}: _require(cases[0]["oracle"].get("added_group_detects_witness") is True, "added check must detect the prior witness")


def resolve_v051_typed_case(compiled, slot_id: str, seed: int | None = None) -> dict:
    policy = typed_policy(compiled, slot_id)
    slots = {item["id"]: item for blueprint in compiled.authored["v051"]["scientific"]["assessment_families.yaml"]["blueprints"] for item in blueprint["items"]}; slot = slots[slot_id]
    rng = random.Random(seed if seed is not None else secrets.randbits(64)); oracle = _oracle(_v04_root())
    for _ in range(96):
        if policy.get("case_relation") == "three_flip_mimic": cases = _mimic_case(oracle, rng)
        elif policy.get("case_relation") == "receiver_evidence_candidates": cases = _evidence_case(oracle, rng)
        else:
            cases = []
            for spec in policy["cases"]:
                family, params = spec["family"], spec.get("parameters", {})
                _validate_spec(family, params)
                shared = _shared_context(cases[0]) if cases and policy.get("case_relation") in {"same_valid_grid_distinct_error_patterns", "same_grid_same_data_flips", "same_data_same_error_universe", "same_scheme_same_witness"} else None
                if policy.get("case_relation") == "same_valid_grid_distinct_error_patterns" and shared: shared.pop("flipped_positions", None)
                if family in ONE_D: case = _make_one_d(oracle, family, params, rng, shared)
                elif family in TWO_D: case = _make_two_d(oracle, family, params, rng, shared)
                elif family in GROUPED: case = _make_grouped(oracle, family, params, rng, shared)
                else: raise V051ScenarioError(f"unsupported typed family: {family}")
                case["name"] = spec.get("name", chr(97 + len(cases))); cases.append(case)
        try: _validate(slot_id, slot, policy, cases, oracle)
        except V051ScenarioError: continue
        public_cases = [{"name": case["name"], "family": case["family"], **_redact(case, slot_id)} for case in cases]
        public = {"case_relation": policy.get("case_relation") or "single", "cases": public_cases}
        private = {"cases": [{"name": case["name"], "family": case["family"], "oracle": case["oracle"]} for case in cases]}
        identity = hashlib.sha256(_compact({"slot_id": slot_id, "public": public, "private": private}).encode()).hexdigest()
        return {"policy": policy, "family": slot["scenario_family"], "public": public, "oracle": private, "cases": cases, "instance_id": identity, "verified": True}
    raise V051ScenarioError(f"unable to satisfy typed policy: {slot_id}")


# Identity intentionally ignores descriptive labels, case names and private
# oracle summaries.  It describes scientific facts that could be re-exposed to
# a learner, not the item slot or the author's prose.
_PRESENTATION_ONLY = frozenset({"name", "family", "title", "label", "description", "display_name", "case_name", "note", "observer_note", "perspective", "peer_claim_to_evaluate"})


def scientific_case_fingerprint(case: dict) -> str:
    """Canonical numerical identity for one instructional/assessment case."""
    payload = case.get("public", case)
    _require(isinstance(payload, dict), "scientific case must be an object")
    facts = {key: value for key, value in payload.items() if key not in _PRESENTATION_ONLY}
    return hashlib.sha256(_compact(facts).encode("utf-8")).hexdigest()


def scientific_case_fingerprints(cases: list[dict]) -> list[str]:
    return sorted({scientific_case_fingerprint(case) for case in cases})


def _intro_case(subsection_id: str, rng: random.Random, contrasting: bool) -> list[dict]:
    """Novice-only scientific demonstrations with no premature parity calculation."""
    if subsection_id == "C1.1":
        n = rng.randint(3, 7)
        sequence = "".join(str(rng.randrange(2)) for _ in range(n))
        variants = [sequence]
        if contrasting:
            index = rng.randrange(n)
            other = sequence[:index] + str(1 - int(sequence[index])) + sequence[index + 1:]
            variants.append(other)
        return [{"name": f"bits_{i}", "family": "bit_sequence_intro", "public": {
            "bit_sequence": bits, "bit_values": list(map(int, bits)),
            "position_labels": list(range(len(bits))), "number_of_ones": bits.count("1"),
            "perspective": "introductory bit representation; not a number-base conversion"
        }, "oracle": {"bit_count": len(bits), "ones_count": bits.count("1")}} for i, bits in enumerate(variants)]
    if subsection_id == "C1.2":
        n = rng.randint(3, 7)
        sent = "".join(str(rng.randrange(2)) for _ in range(n))
        index = rng.randrange(n)
        altered = sent[:index] + str(1 - int(sent[index])) + sent[index + 1:]
        receivers = [sent, altered] if contrasting else [altered]
        return [{"name": f"transmission_{i}", "family": "transmission_flip_intro", "public": {
            "instructor_visible_sent_bits": sent, "received_bits": bits,
            "channel": "transmission channel", "sender": "sender", "receiver": "receiver",
            "observer_note": "Only the outside instructor is shown the original sent bits; the receiver ordinarily is not",
            "changed_positions_for_instructor": [j for j in range(n) if sent[j] != bits[j]],
        }, "oracle": {"flip_count": sum(a != b for a, b in zip(sent, bits))}} for i, bits in enumerate(receivers)]
    if subsection_id == "C1.3":
        bits = "".join(str(rng.randrange(2)) for _ in range(rng.randint(3, 7)))
        return [{"name": f"redundancy_{i}", "family": "checkbit_motivation", "public": {
            "payload_bits": bits,
            "checking_position": "p (symbolic extra checking bit; no value calculated)",
            "transmitted_layout": "payload + p" if with_check else "payload only",
            "shared_rule_needed": bool(with_check),
            "note": "No even/odd rule or numerical parity calculation is assumed here",
        }, "oracle": {"checking_bit_value_defined": False}} for i, with_check in enumerate(([False, True] if contrasting else [True]))]
    raise V051ScenarioError(f"unsupported introductory subsection: {subsection_id}")


def _verified_teaching_cases(oracle, subsection_id: str, rng: random.Random, contrasting: bool) -> list[dict]:
    if subsection_id in {"C1.1", "C1.2", "C1.3"}:
        return _intro_case(subsection_id, rng, contrasting)
    if subsection_id == "C1.4":
        # Both conventions must be taught, not sampled as mutually exclusive alternatives.
        cases = []
        for convention in ("even", "odd"):
            sender = _make_one_d(oracle, "sender_parity", {"convention": convention}, rng)
            cases.append(sender)
            cases.append(_make_one_d(oracle, "receiver_parity", {"convention": convention, "receiver_state": "invalid"}, rng,
                                     shared={"sent_frame": sender["oracle"]["sent_frame"], "convention": convention}))
        return cases
    if subsection_id == "C2.1":
        first = _make_one_d(oracle, "single_flip_1d", {"convention": "sample_even_or_odd", "flip_count": 1}, rng)
        second = _make_one_d(oracle, "multiflip_1d", {"flip_count": 2}, rng,
                             shared={"sent_frame": first["oracle"]["sent_frame"], "convention": first["public"]["convention"]})
        return [first, second]
    if subsection_id == "C2.2":
        rows, cols = rng.choice((2, 3)), rng.choice((2, 3, 4))
        grid = oracle.full_grid([[rng.randrange(2) for _ in range(cols)] for _ in range(rows)])
        _require(oracle.grid_syndrome(grid, [])["passes"], "2D constructed grid invalid")
        grids = [grid]
        if contrasting:
            data = [list(row[:-1]) for row in grid[:-1]]
            r, c = rng.randrange(rows), rng.randrange(cols)
            data[r][c] ^= 1
            grids.append(oracle.full_grid(data))
        return [{"family": "full2d_build", "public": {
            "valid_transmitted_grid": ["".join(map(str, row)) for row in valid],
            "data_rows": rows, "data_columns": cols,
            "row_check_column": cols, "column_check_row": rows,
            "corner_check_position": [rows, cols], "convention": "even",
            "coordinate_convention": "zero-based (row, column)",
        }, "oracle": {"passes": True}} for valid in grids]
    if subsection_id == "C2.3":
        # Demonstrate the same intersection logic on one data cell and one
        # checking cell, without claiming the observed syndrome proves one flip.
        case = _make_two_d(oracle, "full2d_single", {"flip_count": 1, "position_universe": "data_cells"}, rng)
        grid = case["public"]["valid_transmitted_grid"]
        rows, cols = case["public"]["data_rows"], case["public"]["data_columns"]
        for _ in range(20):
            another = _make_two_d(oracle, "full2d_checkbit", {"position_universe": "full2d_check_cells", "check_cell_kind": "sample_row_column_corner"}, rng,
                                  shared={"grid": grid})
            if another["public"]["flipped_positions"] != case["public"]["flipped_positions"]:
                return [case, another]
        raise V051ScenarioError("unable to realize data/check-bit localization examples")
    if subsection_id == "C2.4":
        case = _make_two_d(oracle, "full2d_pair", {"flip_count": 2, "position_universe": "transmitted_full_grid"}, rng)
        return [case] if not contrasting else [case, _make_two_d(oracle, "full2d_pair", {"flip_count": 2, "position_universe": "transmitted_full_grid"}, rng)]
    if subsection_id == "C3.1":
        first = _make_two_d(oracle, "full2d_pair", {"flip_count": 2, "position_universe": "data_cells", "pair_geometry": "same_row_distinct_columns"}, rng)
        another = _make_two_d(oracle, "full2d_single", {"flip_count": 1, "position_universe": "data_cells"}, rng,
                               shared={"grid": first["public"]["valid_transmitted_grid"]})
        return [first, another]
    if subsection_id == "C3.2":
        cases = _mimic_case(oracle, rng)
        return [*cases, _make_two_d(oracle, "full2d_rectangle", {"flip_count": 4, "position_universe": "data_cells", "geometry": "nondegenerate_rectangle"}, rng)]
    if subsection_id == "C4.1":
        for _ in range(64):
            case = _make_grouped(oracle, "grouped_checks", {"group_map": "fresh_nonempty_subsets"}, rng)
            groups = case["public"]["groups"]
            if any(set(a) & set(b) for i, a in enumerate(groups) for b in groups[i + 1:]):
                if not contrasting: return [case]
                # Hold the original data fixed while changing a specified check.
                alternate = copy.deepcopy(groups)
                shared_position = next(iter(set(groups[0]) & set(groups[1]))) if set(groups[0]) & set(groups[1]) else None
                if shared_position is None: continue
                replacement = sorted(set(alternate[1]) ^ {shared_position})
                if not replacement: replacement = [x for x in range(case["public"]["data_positions"]) if x != shared_position][:1]
                if not replacement: continue
                alternate[1] = replacement
                other = _make_grouped(oracle, "grouped_checks", {}, rng, shared={
                    "data_positions": case["public"]["data_positions"],
                    "data_bits": case["public"]["data_bits"], "groups": alternate,
                })
                return [case, other]
        raise V051ScenarioError("could not construct overlapping introductory checking groups")
    if subsection_id == "C4.2":
        for _ in range(64):
            try:
                missed = _make_grouped(oracle, "grouped_evasion", {"flip_count": "nonempty_even_overlap_witness", "all_checks_pass": True}, rng)
                _independently_verify([missed], oracle)
                shared = _shared_context(missed)
                shared.pop("flipped_positions", None)
                detected = _make_grouped(oracle, "grouped_two_flip", {"flip_count": 1}, rng, shared=shared)
                if detected["oracle"]["syndrome"]["passes"]: continue
                return [missed, detected]
            except (V051ScenarioError, ValueError):
                continue
        raise V051ScenarioError("could not construct correct evasion witness")
    if subsection_id == "C4.3":
        for _ in range(64):
            try:
                missed = _make_grouped(oracle, "grouped_evasion", {"flip_count": "nonempty_even_overlap_witness", "all_checks_pass": True}, rng)
                _independently_verify([missed], oracle)
                added = _make_grouped(oracle, "grouped_add_check", {"additional_group_relation": "must_cover_witness"}, rng, shared=_shared_context(missed))
                _require(added["oracle"]["added_group_detects_witness"] is True, "new check did not detect witness")
                _require(added["oracle"]["syndrome"]["passes"], "base system must miss witness")
                _independently_verify([added], oracle)
                return [missed, added]
            except (V051ScenarioError, ValueError):
                continue
        raise V051ScenarioError("could not construct missed-and-caught evaluation")
    raise V051ScenarioError(f"unknown locked subsection {subsection_id}")


def _verify_conceptual_cases(cases: list[dict], subsection_id: str) -> None:
    for case in cases:
        p = case["public"]
        if subsection_id == "C1.1":
            bits = p["bit_sequence"]
            _require(bool(bits) and set(bits) <= {"0", "1"}, "invalid introductory bits")
            _require(p["number_of_ones"] == bits.count("1") and p["position_labels"] == list(range(len(bits))), "wrong introductory bit metadata")
        elif subsection_id == "C1.2":
            sent, recv = p["instructor_visible_sent_bits"], p["received_bits"]
            changed = [i for i, (a, b) in enumerate(zip(sent, recv)) if a != b]
            _require(len(sent) == len(recv) and set(sent + recv) <= {"0", "1"} and changed == p["changed_positions_for_instructor"] and len(changed) <= 1, "incorrect introductory transmission")
        elif subsection_id == "C1.3":
            _require(set(p["payload_bits"]) <= {"0", "1"} and p["checking_position"].startswith("p (symbolic") and case["oracle"]["checking_bit_value_defined"] is False, "premature parity calculation")


def resolve_v051_instructional_instance(compiled, subsection_id: str, pedagogy_id: str, seed: int | None = None) -> dict:
    """Realize subsection-scoped scientific cases, not assessment slot fixtures.

    The Tutor still chooses the language and pedagogical explanations; these
    cases constrain only examples whose mathematical facts we can verify.
    """
    subsections = [x["id"] for x in compiled.authored["v051"]["scientific"]["curriculum.yaml"]["subsections"]]
    _require(subsection_id in subsections, f"unknown curriculum subsection: {subsection_id}")
    _require(pedagogy_id in {"P1", "P2", "P3"}, f"unknown pedagogy: {pedagogy_id}")
    rng = random.Random(seed if seed is not None else secrets.randbits(64))
    oracle = _oracle(_v04_root())
    cases = _verified_teaching_cases(oracle, subsection_id, rng, pedagogy_id == "P3")
    if subsection_id in {"C1.1", "C1.2", "C1.3"}:
        _verify_conceptual_cases(cases, subsection_id)
    elif subsection_id != "C2.2":
        _independently_verify(cases, oracle)
    public = {"case_relation": "pedagogy_scoped_instruction", "cases": [
        {"name": case.get("name", chr(97 + i)), "family": case["family"], **case["public"]} for i, case in enumerate(cases)]}
    private = {"cases": [{"name": case.get("name", chr(97 + i)), "family": case["family"], "oracle": case["oracle"]} for i, case in enumerate(cases)]}
    identity = hashlib.sha256(_compact(public).encode("utf-8")).hexdigest()
    return {"instruction_only": True, "verified": True, "subsection_id": subsection_id,
            "pedagogy_id": pedagogy_id, "public": public, "private_oracle": private,
            "case_fingerprints": scientific_case_fingerprints(cases),
            "instance_id": "INSTRUCTION_ONLY:" + identity}


def validate_v051_case(compiled, slot_id: str, candidate: dict) -> None:
    """Independently verify one candidate using its immutable slot contract."""
    policy = typed_policy(compiled, slot_id)
    slots = {item["id"]: item for blueprint in compiled.authored["v051"]["scientific"]["assessment_families.yaml"]["blueprints"] for item in blueprint["items"]}
    _require(slot_id in slots and isinstance(candidate.get("cases"), list), "invalid candidate or unknown contract")
    _validate(slot_id, slots[slot_id], policy, candidate["cases"], _oracle(_v04_root()))
