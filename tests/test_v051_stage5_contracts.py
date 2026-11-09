"""Stage 5 source-contract coverage without enabling candidate enrollment."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from solo_harness.runtime.v04_assessment import RecordedResult
from solo_harness.runtime.v04_native import MCQProse, SemanticReview, SubjectiveProse, SubjectiveReview
from solo_harness.runtime.v051_assessment import construct_v051_assessment, fresh_verified_case, v051_judge_messages
from solo_harness.runtime.v051_conversation import v051_tutor_prompt
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051, resolve_v051_tutor_context

ROOT = Path("studies/networks_error_detection_parity_f1/v0.5")


def test_all_child_contexts_compile_the_real_three_pedagogy_layers():
    compiled = compile_v051(load_scientific_v051(ROOT))
    source = compiled.authored["v051"]["scientific"]
    for child in source["subsection_interventions.yaml"]["cells"]:
        context = resolve_v051_tutor_context(compiled, child["subsection_id"], child["pedagogy_id"])
        progress = SimpleNamespace(required_move_ids=[move["id"] for move in child["core_moves"]], required_content_ids=child["required_content_refs"], move_evidence={}, content_evidence={}, clarification_evidence_ids=[], instructional_state={})
        prompt = v051_tutor_prompt(compiled, progress, context, [], {"last_action": "CONSOLIDATE", "next_allowed_instruction": "Use the next authored move."})
        assert context["global_pedagogy"]["id"] == child["pedagogy_id"]
        assert context["parent_cell"]["id"] == child["parent_cell_id"]
        assert child["id"] in prompt and "previous_conversation_judge_guidance" in prompt
        assert "V051_ACTIVE_SUBSECTION_TUTOR_CONTEXT" in prompt


def test_all_v051_item_contracts_have_a_fresh_oracle_checked_case():
    compiled = compile_v051(load_scientific_v051(ROOT))
    contracts = [item for blueprint in compiled.authored["v051"]["scientific"]["assessment_families.yaml"]["blueprints"] for item in blueprint["items"]]
    assert len(contracts) == 64
    for contract in contracts:
        case = fresh_verified_case(compiled, contract)
        assert case["family"] == contract["scenario_family"]
        assert case["public"] and case["oracle"]


def test_v051_constructor_uses_contracts_writer_reviewer_and_freezes_three_plus_one():
    compiled = compile_v051(load_scientific_v051(ROOT))
    blueprint = compiled.assessment_families["C2"]["forms"][0]
    checkpoints = {}

    async def invoke(role, messages, schema, audit):
        assert audit["v051"] is True
        assert "V051_ASSESSMENT_CONTEXT" in messages[0].content
        if schema is MCQProse:
            value = MCQProse(stem="Which stated conclusion follows from the shown verified case?", correct_option="The oracle-backed conclusion.", distractors=["A different unsupported claim.", "Another unsupported claim.", "A final unsupported claim."])
        elif schema is SubjectiveProse:
            value = SubjectiveProse(question="Explain the stated parity result using the displayed facts.")
        elif schema is SemanticReview:
            value = SemanticReview(verdict="ACCEPT", stem_matches_contract=True, assumptions_visible=True, exactly_one_defensible_option=True, option_assessments=[{"truth_status": "TRUE", "matches_intended_meaning": True, "scientific_reason": "Oracle-backed."}, *[{"truth_status": "FALSE", "matches_intended_meaning": True, "scientific_reason": "Not supported."} for _ in range(3)]], rationale="Contract and oracle are respected.")
        else:
            value = SubjectiveReview(verdict="ACCEPT", elicits_slot_evidence=True, assumes_only_visible_facts=True, scientifically_consistent=True, does_not_reveal_answer=True, rationale="Contract and oracle are respected.")
        return RecordedResult(call_id=f"{role}-{audit['slot_id']}", parsed=value)

    async def checkpoint(label, record): checkpoints[label] = record
    # The controlled invoker/checkpoint coroutines complete synchronously; run
    # the constructor without opening a Windows event-loop self-pipe.
    operation = construct_v051_assessment(compiled, blueprint, invoke, checkpoint)
    try:
        operation.send(None)
    except StopIteration as done:
        package = done.value
    else:  # pragma: no cover - this fixture must remain I/O-free
        raise AssertionError("controlled constructor unexpectedly suspended")
    assert list(checkpoints) == ["MCQ1", "MCQ2", "MCQ3", "SUB1"]
    assert [item["id"] for item in package["public"]["mcqs"]] == ["MCQ1", "MCQ2", "MCQ3"]
    assert package["private"]["subjective_resolved"]["contract"]["transition_id"] == "C2"
    prompt = v051_judge_messages(compiled, package["private"]["subjective_resolved"], package["public"]["subjective"]["prompt"], "A learner response.")[0].content
    assert "V051_BLIND_SUBJECTIVE_JUDGE_CONTEXT" in prompt
    assert "global_pedagogy" not in prompt and "conversation_judge" not in prompt
