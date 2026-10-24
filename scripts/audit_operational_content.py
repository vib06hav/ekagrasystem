"""Validate normalized study coverage and write a machine-readable audit artifact."""
from __future__ import annotations

import json
from pathlib import Path

from solo_harness.studies.compiler import compile_study
from solo_harness.studies.loader import load
from solo_harness.studies.validation import validate

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/python_fibonacci_memoization/v0.1"
OUTPUT = ROOT / "artifacts/content_audit.json"


def main() -> None:
    study = load(STUDY)
    validate(study)
    compiled = compile_study(study)
    report = {
        "study_id": compiled.study_id,
        "content_version": compiled.content_version,
        "knowledge_components": {
            item.id: len(item.definition.strip()) for item in study.knowledge.knowledge_components
        },
        "relations": {item.id: len(item.definition.strip()) for item in study.knowledge.relations},
        "misconceptions": {
            item.id: len(item.definition.strip()) for item in study.knowledge.misconceptions
        },
        "transitions": {
            item.id: {
                "target_kc_ids": item.target_kc_ids,
                "target_relation_ids": item.target_relation_ids,
                "relevant_misconception_ids": item.relevant_misconception_ids,
                "canonical_slice_characters": len(item.canonical_slice.strip()),
            }
            for item in study.knowledge.transitions
        },
        "pedagogies": {
            item.id: {
                "mechanism_characters": len(item.core_mechanism.strip()),
                "role_characters": len(item.tutor_role.strip()),
                "fidelity_characters": len(item.treatment_fidelity_test.strip()),
            }
            for item in study.pedagogies
        },
        "intervention_cells": {
            item.id: {
                "move_count": len(item.moves),
                "move_ids": item.move_ids,
                "blueprint_characters": sum(len(move.material_blueprint.strip()) for move in item.moves),
            }
            for item in study.cells
        },
        "assessments": {
            form.id: {
                "scenario_seed_characters": len(form.scenario_seed.strip()),
                "required_response_features": len(form.required_response_features),
                "target_evidence_ids": form.target_evidence_ids,
            }
            for family in study.assessment_families
            for form in family.forms
        },
        "rubrics": {
            rubric.id: {
                "transition_id": rubric.transition_id,
                "evidence_definitions": {
                    criterion.id: len(criterion.definition.strip())
                    for criterion in rubric.evidence_criteria
                },
                "success_rule": rubric.success_rule,
                "success_rule_characters": len(rubric.success_rule_text.strip()),
            }
            for rubric in study.judge_rubrics
        },
        "coverage": {
            "knowledge_components": len(study.knowledge.knowledge_components),
            "relations": len(study.knowledge.relations),
            "misconceptions": len(study.knowledge.misconceptions),
            "transitions": len(study.knowledge.transitions),
            "pedagogies": len(study.pedagogies),
            "intervention_cells": len(study.cells),
            "assessments": sum(len(family.forms) for family in study.assessment_families),
            "rubrics": len(study.judge_rubrics),
            "evidence_criteria": sum(len(rubric.evidence_criteria) for rubric in study.judge_rubrics),
        },
        "validation": "PASSED",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["coverage"], sort_keys=True))


if __name__ == "__main__":
    main()
