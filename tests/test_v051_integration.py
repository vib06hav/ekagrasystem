from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from solo_harness.studies.catalog import StudyCatalog
from solo_harness.studies.scientific_v051 import ScientificV051Error, load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051, resolve_v051_tutor_context
from solo_harness.studies.canonicalization import content_identity


ROOT = Path("studies/networks_error_detection_parity_f1/v0.5.1")


def test_v051_load_compile_and_snapshot_preserve_every_authored_context():
    study = load_scientific_v051(ROOT)
    compiled = compile_v051(study)
    snapshot = compiled.to_snapshot()
    restored = compiled.from_snapshot(snapshot)
    source = restored.authored["v051"]["scientific"]
    assert len(study.source_hashes) == 19
    assert len(source["subsection_interventions.yaml"]["cells"]) == 39
    assert len(source["curriculum.yaml"]["subsections"]) == 13
    assert sum(len(form["v051_item_contracts"]) for family in restored.assessment_families.values() for form in family["forms"]) == 64
    for child in source["subsection_interventions.yaml"]["cells"]:
        context = resolve_v051_tutor_context(restored, child["subsection_id"], child["pedagogy_id"])
        assert context["global_pedagogy"]["id"] == child["pedagogy_id"]
        assert context["parent_cell"]["id"] == child["parent_cell_id"]
        assert context["child_cell"]["required_content_refs"] == [item["id"] for item in context["subsection"]["required_content"]]
        assert context["child_cell"]["core_moves"]


def test_v051_role_contexts_are_isolated():
    study = load_scientific_v051(ROOT)
    conversation = study.conversation_judge_context("C2.1", "P2")
    formal = study.subjective_judge_context("C2-A1")
    assert conversation["global_pedagogy"]["id"] == "P2"
    assert "assessment_families.yaml" not in conversation
    assert "interventions.yaml" not in formal and "conversation_judge.yaml" not in formal
    assert formal["subjective_contract"]["type"] == "SUBJECTIVE"
    assert "items" not in formal["blueprint"]


def test_v051_rejects_missing_duplicate_and_incompatible_sources():
    import shutil
    with TemporaryDirectory(dir=Path.cwd()) as temp:
        copied = Path(temp) / "v0.5.1"
        shutil.copytree(ROOT, copied)
        (copied / "08_SCIENTIFIC_YAML/curriculum.yaml").write_text("schema: incompatible.schema\n", encoding="utf-8")
        with pytest.raises(ScientificV051Error):
            load_scientific_v051(copied)
        shutil.copytree(ROOT, copied, dirs_exist_ok=True)
        (copied / "07_PROMPT_CONTRACTS/CONVERSATION_JUDGE_PROMPT.md").unlink()
        with pytest.raises(ScientificV051Error, match="missing required"):
            load_scientific_v051(copied)
        shutil.copytree(ROOT, copied, dirs_exist_ok=True)
        path = copied / "08_SCIENTIFIC_YAML/subsection_interventions.yaml"
        path.write_text(path.read_text(encoding="utf-8") + "\n- id: C1.1-P1\n", encoding="utf-8")
        with pytest.raises(ScientificV051Error):
            load_scientific_v051(copied)
        shutil.copytree(ROOT, copied, dirs_exist_ok=True)
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("parent_cell_id: C1-P1", "parent_cell_id: C4-P3", 1), encoding="utf-8")
        with pytest.raises(ScientificV051Error, match="broken child parent"):
            load_scientific_v051(copied)


def test_catalog_reloads_v051_snapshot_and_runtime_gate_is_detectable():
    study = load_scientific_v051(ROOT)
    compiled = compile_v051(study)

    class Version:
        id = "v051"
        content_hash = "x" * 64
        compiler_contract_version = "3.1"
        snapshot_schema_version = "3"
        compiled_snapshot = compiled.to_snapshot()

    from solo_harness.studies.canonicalization import snapshot_identity
    Version.snapshot_hash = snapshot_identity(Version.content_hash, Version.compiled_snapshot)

    class Db:
        def get(self, model, key): return Version

    restored = StudyCatalog().load(Db(), Version.id)
    assert restored.authored["v051"]["candidate_only"] is True
    from types import SimpleNamespace
    from solo_harness.runtime.engine import SessionRuntime
    with pytest.raises(ValueError, match="not participant-executable"):
        SessionRuntime(SimpleNamespace(load=lambda db, version_id: restored)).create_session(SimpleNamespace(), "v051")


def test_v051_content_identity_is_stable_and_tracks_locked_source():
    import shutil
    baseline = compile_v051(load_scientific_v051(ROOT))
    with TemporaryDirectory(dir=Path.cwd()) as temp:
        copied = Path(temp) / "v0.5.1"
        shutil.copytree(ROOT, copied)
        locked = copied / "CURRICULUM_SOURCE_LOCKED.md"
        locked.write_text(locked.read_text(encoding="utf-8") + "\n<!-- provenance test -->\n", encoding="utf-8")
        altered = compile_v051(load_scientific_v051(copied))
    assert content_identity(baseline.authored)[1] == content_identity(compile_v051(load_scientific_v051(ROOT)).authored)[1]
    assert content_identity(baseline.authored)[1] != content_identity(altered.authored)[1]
