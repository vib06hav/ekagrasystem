from pathlib import Path
import shutil

import pytest

from solo_harness.studies.canonicalization import content_identity, snapshot_identity
from solo_harness.studies.compiler import compile_study
from solo_harness.studies.loader import StudyLoadError, load, source_bundle
from solo_harness.studies.authored.models import AuthoredStudy
from solo_harness.studies.validation import StudyValidationError, validate


STUDY = Path(__file__).parents[1] / "studies/python_fibonacci_memoization/v0.1"
CANDIDATE = Path(__file__).parents[1] / "studies/python_fibonacci_memoization/v0.5"

def test_valid_study_compiles_and_hashes_are_stable():
    study = load(STUDY); validate(study); compiled = compile_study(study)
    canonical, content_hash = content_identity(compiled.authored)
    assert len(canonical) > 0 and len(content_hash) == 64
    assert snapshot_identity(content_hash, compiled.to_snapshot()) == snapshot_identity(content_hash, compiled.to_snapshot())
    assert compiled.knowledge_slices["C3"]["transition"]["target_state_id"] == "R"
    assert "C4:P3" in compiled.cells

def test_semantic_change_changes_content_hash():
    study = load(STUDY); first = compile_study(study)
    first_hash = content_identity(first.authored)[1]
    changed = first.authored.copy(); changed["knowledge"] = changed["knowledge"].copy(); changed["knowledge"]["topic"] = "Changed"
    assert first_hash != content_identity(changed)[1]

def test_invalid_yaml_fails(tmp_path):
    path = tmp_path / "bad.yaml"; path.write_text("a: [broken", encoding="utf-8")
    from solo_harness.studies.loader import _yaml
    with pytest.raises(StudyLoadError): _yaml(path)

def test_incomplete_matrix_fails(tmp_path):
    copy = tmp_path / "study"; shutil.copytree(STUDY, copy)
    cell = copy / "intervention/cells/c4.yaml"; cell.write_text(cell.read_text(encoding="utf-8").replace("  - id: C4-P3", "  # removed\n  # id: C4-P3"), encoding="utf-8")
    with pytest.raises(Exception):
        validate(load(copy))

def test_broken_knowledge_reference_fails():
    raw = load(STUDY).model_dump(mode="python", by_alias=True)
    raw["cells"][0]["target_kc_ids"] = ["K999"]
    with pytest.raises(StudyValidationError, match="broken knowledge"):
        validate(AuthoredStudy.model_validate(raw))

def test_insufficient_assessment_capacity_fails():
    raw = load(STUDY).model_dump(mode="python", by_alias=True)
    raw["assessment_families"][0]["forms"] = raw["assessment_families"][0]["forms"][:2]
    with pytest.raises(StudyValidationError, match="insufficient forms"):
        validate(AuthoredStudy.model_validate(raw))


def test_runtime_content_is_normalized_into_domain_yaml():
    assert not (STUDY / "authored_content.yaml").exists()
    study = load(STUDY); validate(study); compiled = compile_study(study)
    assert len(compiled.knowledge_slices["C4"]["knowledge_components"][0]["definition"]) > 100
    assert len(compiled.cells["C3:P2"]["move_ids"]) >= 6
    assert "one line is missing" in compiled.assessment_families["C1"]["forms"][0]["scenario_seed"]
    assert len(compiled.intervention_moves) >= 12
    assert set(compiled.tutor_prompt_recipes) == {"P1", "P2", "P3"}
    assert {item["id"] for item in compiled.rubrics["C4"]["evidence_criteria"]} == {f"C4-E{i}" for i in range(1, 7)}


def test_placeholder_semantics_fail_validation():
    raw = load(STUDY).model_dump(mode="python", by_alias=True)
    raw["knowledge"]["knowledge_components"][0]["definition"] = "placeholder"
    with pytest.raises(StudyValidationError, match="placeholder-like"):
        validate(AuthoredStudy.model_validate(raw))


def test_candidate_v05_validates_and_legacy_v04_blank_features_remain_readable():
    legacy = load(STUDY); candidate = load(CANDIDATE)
    validate(legacy); validate(candidate)
    assert legacy.manifest.content_version == "v0.4"
    assert candidate.manifest.content_version == "v0.5"


@pytest.mark.parametrize("mutation", ["misconception", "foreign_evidence", "bad_rule", "unknown_form", "impossible_gate", "blank_feature", "wrong_target_state"])
def test_study_cross_reference_mutations_fail_closed(mutation):
    raw = load(CANDIDATE).model_dump(mode="python", by_alias=True)
    if mutation == "misconception": raw["assessment_families"][0]["forms"][0]["relevant_misconception_ids"] = ["M999"]
    elif mutation == "foreign_evidence": raw["assessment_families"][0]["forms"][0]["target_evidence_ids"] = ["C2-E1"]
    elif mutation == "bad_rule": raw["judge_rubrics"][0]["success_rule"]["requires"] = ["C999"]
    elif mutation == "unknown_form": raw["judge_rubrics"][0]["success_rule"]["required_by_assessment_form"]["C1-UNKNOWN"] = ["C1-E1"]
    elif mutation == "impossible_gate": raw["judge_rubrics"][0]["success_rule"]["requires"] = ["C1-E3"]
    elif mutation == "blank_feature": raw["assessment_families"][0]["forms"][0]["required_response_features"].append(" ")
    else: raw["judge_rubrics"][0]["target_state_id"] = "M"
    with pytest.raises(StudyValidationError): validate(AuthoredStudy.model_validate(raw))


def test_source_bundle_is_relative_utf8_and_hashed():
    bundle = source_bundle(CANDIDATE)
    assert bundle["schema_version"] == "1.0"
    assert set(bundle["files"]) >= {"study.yaml", "knowledge.yaml", "protocol.yaml"}
    assert all(".." not in path and len(item["sha256"]) == 64 for path, item in bundle["files"].items())


def test_snapshot_identity_preserves_legacy_contract_hash_inputs():
    compiled = compile_study(load(STUDY)); content_hash = content_identity(compiled.authored)[1]
    assert snapshot_identity(content_hash, compiled.to_snapshot(), "3.0", "3") == snapshot_identity(content_hash, compiled.to_snapshot(), "3.0", "3")
