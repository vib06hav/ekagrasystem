"""Regression tests for v0.5.1 scientific-instance integrity and scoped teaching."""
import copy
from dataclasses import replace
from pathlib import Path

import pytest

from solo_harness.runtime import v051_assessment
from solo_harness.runtime.v04_assessment import ScientificReviewHold
from solo_harness.studies.scientific_v04 import _oracle
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051
from solo_harness.studies.v051_scenarios import (
    V051ScenarioError, resolve_v051_instructional_instance,
    resolve_v051_typed_case, scientific_case_fingerprint, typed_policy,
    validate_v051_case,
)

ROOT = Path("studies/networks_error_detection_parity_f1/v0.5")


def compiled():
    return compile_v051(load_scientific_v051(ROOT))


def test_instructional_scoping_and_pedagogy_examples_all_39_combinations():
    c = compiled()
    subs = [item["id"] for item in c.authored["v051"]["scientific"]["curriculum.yaml"]["subsections"]]
    assert len(subs) == 13
    for sub in subs:
        for pedagogy in ("P1", "P2", "P3"):
            identities = set()
            for seed in range(12):
                case = resolve_v051_instructional_instance(c, sub, pedagogy, seed)
                assert case["verified"] and case["instruction_only"]
                assert case["subsection_id"] == sub and case["pedagogy_id"] == pedagogy
                assert "source_slot_id" not in case
                instances = case["public"]["cases"]
                assert instances
                identities.add(case["instance_id"])
                if sub == "C1.1":
                    assert all(x["family"] == "bit_sequence_intro" for x in instances)
                    assert all("convention" not in x and "check_bit" not in str(x) for x in instances)
                elif sub == "C1.2":
                    assert all(x["family"] == "transmission_flip_intro" for x in instances)
                    assert all("convention" not in x for x in instances)
                elif sub == "C1.3":
                    assert all(x["family"] == "checkbit_motivation" for x in instances)
                    assert all("convention" not in x and "received_frame" not in x for x in instances)
                elif sub == "C1.4":
                    assert {x["convention"] for x in instances} == {"even", "odd"}
                    assert {x["family"] for x in instances} == {"sender_parity", "receiver_parity"}
                elif sub == "C2.2":
                    assert all(x["family"] == "full2d_build" for x in instances)
                    assert all("flipped_positions" not in x for x in instances)
                elif sub == "C2.3":
                    assert {x["family"] for x in instances} == {"full2d_single", "full2d_checkbit"}
                    assert instances[0]["valid_transmitted_grid"] == instances[1]["valid_transmitted_grid"]
                elif sub == "C4.3":
                    assert [x["family"] for x in instances] == ["grouped_evasion", "grouped_add_check"]
                    assert instances[0]["groups"] == instances[1]["groups"]
                    assert instances[0]["flipped_positions"] == instances[1]["flipped_positions"]
                if pedagogy == "P3" and sub not in {"C1.4", "C2.1", "C2.3", "C3.1", "C3.2", "C4.3"}:
                    assert len(instances) >= 2, (sub, pedagogy)
            assert len(identities) > 1, (sub, pedagogy)


def test_invalid_initial_one_d_frame_is_rejected_even_if_oracle_fields_are_consistent():
    c = compiled()
    case = resolve_v051_typed_case(c, "C1-A2-Q1", seed=11)
    bad = copy.deepcopy(case)
    x = bad["cases"][0]
    old = x["oracle"]["sent_frame"]
    sent = old[:-1] + str(1 - int(old[-1]))
    x["oracle"]["sent_frame"] = sent
    x["oracle"]["sender_check_bit"] = int(sent[-1])
    o = _oracle(Path("studies/networks_error_detection_parity_f1/v0.4"))
    received = o.flip_positions(tuple(map(int, sent)), x["oracle"]["flipped_positions"])
    x["oracle"]["received_frame"] = "".join(map(str, received))
    x["oracle"]["receiver_passes"] = o.receiver_pass(received, x["public"]["convention"])
    with pytest.raises(V051ScenarioError, match="invalid initial 1D parity frame"):
        validate_v051_case(c, "C1-A2-Q1", bad)


def test_source_family_mutations_are_rejected_for_original_and_corrected_contracts():
    c = compiled()
    for slot in ("C1-A1-Q1", "C3-A4-Q1"):
        modified = replace(c, authored=copy.deepcopy(c.authored))
        contract = next(item for blueprint in modified.authored["v051"]["scientific"]["assessment_families.yaml"]["blueprints"] for item in blueprint["items"] if item["id"] == slot)
        contract["scenario_family"] = "grouped_checks"
        with pytest.raises(V051ScenarioError, match="family disagreement"):
            typed_policy(modified, slot)


def test_fingerprints_ignore_labels_but_detect_scientific_changes():
    c = compiled()
    r = resolve_v051_typed_case(c, "C3-A4-Q2", seed=17)
    original = r["cases"][0]
    labeled = copy.deepcopy(original)
    labeled["name"] = "New label"
    labeled["public"]["name"] = "Different descriptive title"
    labeled["public"]["description"] = "Some different wording"
    assert scientific_case_fingerprint(original) == scientific_case_fingerprint(labeled)
    changed = copy.deepcopy(original)
    old = changed["public"]["valid_transmitted_grid"][0]
    changed["public"]["valid_transmitted_grid"][0] = str(1 - int(old[0])) + old[1:]
    assert scientific_case_fingerprint(original) != scientific_case_fingerprint(changed)


def test_assessment_rejects_numerical_reuse_with_instruction_before_writer_call():
    c = compiled()
    blueprint = next(blueprint for family in c.assessment_families.values() for blueprint in family["forms"])
    first = resolve_v051_typed_case(c, blueprint["v051_item_contracts"][0]["id"], seed=5)
    exclusion = {scientific_case_fingerprint(case) for case in first["cases"]}
    original = v051_assessment.fresh_verified_case
    calls = []

    def fixed_case(compiled, contract, seed=None):
        out = copy.deepcopy(first)
        for case in out["cases"]:
            case["name"] = f"different label {len(calls)}"
        calls.append(contract["id"])
        return out

    async def invoke(*args):
        raise AssertionError("Writer must not receive an instruction-reused numerical case")

    async def checkpoint(*args):
        raise AssertionError("No checkpoints should have been accepted")

    v051_assessment.fresh_verified_case = fixed_case
    try:
        coro = v051_assessment.construct_v051_assessment(c, blueprint, invoke, checkpoint,
                                                            prior_instructional_fingerprints=exclusion)
        with pytest.raises(ScientificReviewHold, match="collided with recorded instructional"):
            coro.send(None)
        assert len(calls) == 2
    finally:
        v051_assessment.fresh_verified_case = original
