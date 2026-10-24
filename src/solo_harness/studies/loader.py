from pathlib import Path

from ruamel.yaml import YAML

from solo_harness.studies.authored.models import AuthoredStudy, StudyManifest


class StudyLoadError(ValueError):
    pass


def _yaml(path: Path) -> dict:
    parser = YAML(typ="safe")
    parser.allow_duplicate_keys = False
    try:
        value = parser.load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise StudyLoadError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StudyLoadError(f"expected object in {path}")
    return value


def load(study_dir: Path) -> AuthoredStudy:
    manifest_raw = _yaml(study_dir / "study.yaml")
    manifest = StudyManifest.model_validate(manifest_raw)
    files = manifest.files
    def read(key: str):
        target = files[key]
        if isinstance(target, list):
            return [_yaml(study_dir / str(item)) for item in target]
        return _yaml(study_dir / str(target))
    try:
        knowledge = read("knowledge")
        pedagogy_document = read("pedagogy_families")
        pedagogies = pedagogy_document["pedagogies"]
        tutor_prompt_recipes = pedagogy_document["tutor_prompt_recipes"]
        shared_intervention_envelope = pedagogy_document["shared_envelope"]
        cells = [cell for doc in read("intervention_cells") for cell in doc["cells"]]
        families = [family for doc in read("assessment_families") for family in doc["assessment_families"]]
        judge_contract = read("judge_contract")
        judge_rubrics = read("judge_rubrics")["judge_rubrics"]
        protocol = read("protocol")
    except KeyError as exc:
        raise StudyLoadError(f"study manifest missing file entry {exc}") from exc
    return AuthoredStudy.model_validate({"manifest": manifest_raw, "knowledge": knowledge, "pedagogies": pedagogies, "tutor_prompt_recipes": tutor_prompt_recipes, "cells": cells, "assessment_families": families, "judge_contract": judge_contract, "judge_rubrics": judge_rubrics, "protocol": protocol, "shared_intervention_envelope": shared_intervention_envelope})
