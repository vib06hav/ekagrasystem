"""Scientific regression coverage for the v0.5.1 typed scenario executor."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from solo_harness.runtime.v04_assessment import RecordedResult
from solo_harness.runtime.v04_native import MCQProse, SemanticReview, SubjectiveProse, SubjectiveReview
from solo_harness.runtime.v051_assessment import construct_v051_assessment
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051
from solo_harness.studies.v051_scenarios import (
    V051ScenarioError, resolve_v051_instructional_instance, resolve_v051_typed_case,
    typed_policy, validate_v051_case,
)

ROOT = Path("studies/networks_error_detection_parity_f1/v0.5.1")


def _compiled(): return compile_v051(load_scientific_v051(ROOT))
def _slots(compiled): return [item for blueprint in compiled.authored["v051"]["scientific"]["assessment_families.yaml"]["blueprints"] for item in blueprint["items"]]


def test_every_v051_slot_has_typed_policy_and_many_independently_checked_instances():
    compiled = _compiled(); slots = _slots(compiled)
    assert len(slots) == 64
    for slot in slots:
        policy = typed_policy(compiled, slot["id"])
        assert policy["type"] == slot["type"] and policy["source_scenario_family"] == slot["scenario_family"]
        identities = set()
        for seed in range(8):
            case = resolve_v051_typed_case(compiled, slot["id"], seed=seed)
            validate_v051_case(compiled, slot["id"], case)
            identities.add(case["instance_id"])
        assert len(identities) > 1


def test_known_corrected_contracts_enforce_their_specific_scientific_relations():
    compiled = _compiled()
    for seed in range(12):
        c1 = resolve_v051_typed_case(compiled, "C1-A2-Q1", seed); assert c1["cases"][0]["public"]["convention"] == "odd"
        c2 = resolve_v051_typed_case(compiled, "C2-A1-Q1", seed); assert {len(item["oracle"]["flipped_positions"]) % 2 for item in c2["cases"]} == {0, 1}
        c3 = resolve_v051_typed_case(compiled, "C3-A1-Q3", seed); assert c3["cases"][0]["public"]["valid_transmitted_grid"] == c3["cases"][1]["public"]["valid_transmitted_grid"]
        mimic = resolve_v051_typed_case(compiled, "C3-A4-Q1", seed); assert mimic["cases"][0]["oracle"]["syndrome"] == mimic["cases"][1]["oracle"]["syndrome"]
        evidence = resolve_v051_typed_case(compiled, "C3-A4-Q3", seed); assert len(evidence["cases"][0]["oracle"]["candidate_patterns"]) >= 2
        assert resolve_v051_typed_case(compiled, "C4-A1-Q3", seed)["cases"][0]["oracle"]["syndrome"]["passes"]
        assert resolve_v051_typed_case(compiled, "C4-A2-Q3", seed)["cases"][0]["oracle"]["syndrome"]["passes"]
        assert resolve_v051_typed_case(compiled, "C4-A3-Q3", seed)["cases"][0]["oracle"]["added_group_detects_witness"]


def test_post_generation_boundary_rejects_tampered_oracle_and_preserves_visibility_boundaries():
    compiled = _compiled()
    candidate = resolve_v051_typed_case(compiled, "C3-A1-Q3", seed=17)
    broken = copy.deepcopy(candidate); broken["cases"][0]["oracle"]["syndrome"]["passes"] = not broken["cases"][0]["oracle"]["syndrome"]["passes"]
    with pytest.raises(V051ScenarioError, match="oracle mismatch"):
        validate_v051_case(compiled, "C3-A1-Q3", broken)
    hidden = resolve_v051_typed_case(compiled, "C1-A3-Q3", seed=9)
    assert "flipped_positions" not in hidden["public"]["cases"][0]
    instruction = resolve_v051_instructional_instance(compiled, "C2.2", "P3", seed=9)
    assert instruction["instruction_only"] and instruction["verified"] and instruction["instance_id"].startswith("INSTRUCTION_ONLY:")


def test_all_sixteen_blueprints_construct_through_writer_reviewer_and_freeze_interfaces():
    compiled = _compiled()
    async def invoke(role, messages, schema, audit):
        assert audit["v051"] and "V051_ASSESSMENT_CONTEXT" in messages[0].content
        if schema is MCQProse: value = MCQProse(stem="Which verified conclusion follows?", correct_option="Verified conclusion.", distractors=["Unsupported A.", "Unsupported B.", "Unsupported C."])
        elif schema is SubjectiveProse: value = SubjectiveProse(question="Explain the verified result from the shown facts.")
        elif schema is SemanticReview: value = SemanticReview(verdict="ACCEPT", stem_matches_contract=True, assumptions_visible=True, exactly_one_defensible_option=True, option_assessments=[{"truth_status":"TRUE","matches_intended_meaning":True,"scientific_reason":"verified"}, *[{"truth_status":"FALSE","matches_intended_meaning":True,"scientific_reason":"unsupported"} for _ in range(3)]], rationale="verified")
        else: value = SubjectiveReview(verdict="ACCEPT", elicits_slot_evidence=True, assumes_only_visible_facts=True, scientifically_consistent=True, does_not_reveal_answer=True, rationale="verified")
        return RecordedResult(call_id=f"{role}-{audit['slot_id']}", parsed=value)
    for family in compiled.assessment_families.values():
        for blueprint in family["forms"]:
            accepted = {}
            async def checkpoint(label, record): accepted[label] = record
            operation = construct_v051_assessment(compiled, blueprint, invoke, checkpoint)
            try: operation.send(None)
            except StopIteration as done: package = done.value
            else: raise AssertionError("controlled construction unexpectedly suspended")
            assert list(accepted) == ["MCQ1", "MCQ2", "MCQ3", "SUB1"]
            assert len(package["public"]["mcqs"]) == 3 and package["private"]["subjective_resolved"]["case"]["verified"] is not False
