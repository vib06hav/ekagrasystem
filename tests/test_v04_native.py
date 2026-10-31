from pathlib import Path

from solo_harness.runtime.v04_native import assessment_messages, judge_messages, resolve_slot, review_messages
from solo_harness.studies.scientific_v04 import load_scientific_v04
from solo_harness.studies.scientific_v04_policy import load_policy, resolve_typed_case


ROOT = Path("studies/networks_error_detection_parity_f1/v0.4")


def test_authoritative_v04_loads_every_contract_and_policy():
    study = load_scientific_v04(ROOT)
    policies = load_policy(ROOT)
    assert len(policies) == 64
    assert len(study.source_hashes) == 15
    for contract_id in policies:
        assert resolve_typed_case(study, contract_id, 17)["policy"]["scientific_contract_id"] == contract_id


def test_native_contracts_keep_identity_private_and_judge_blind():
    study = load_scientific_v04(ROOT)
    mcq = resolve_slot(study, "C1-A2-Q1", 11)
    subjective = resolve_slot(study, "C1-A2-S", 12)
    # v0.4 provides the authored slot to the writer's private contract so it
    # can realize the exact scientific family.  The learner projection is
    # assembled separately and never receives a correct-option identifier.
    assert "correct_option_id" not in assessment_messages(study, mcq)[0].content
    assert len(review_messages(study, mcq, {"stem": "x", "options": ["a", "b", "c", "d"]})) == 1
    judge = judge_messages(study, subjective, "Explain the received frame.", "I check every transmitted bit.")[0].content
    # The authored Judge contract names these as denied inputs; no actual tutor
    # content or MCQ response is compiled into the runtime payload.
    assert "I check every transmitted bit." in judge
    assert "tutor_transcript" not in judge and "mcq_answers" not in judge
