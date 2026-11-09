"""Compile candidate v0.5.1 into the existing immutable study snapshot shape."""
from types import MappingProxyType

from solo_harness.studies.scientific_v051 import ScientificV051Error
from solo_harness.studies.v04_types import CompiledStudy


def compile_v051(study):
    knowledge_source = study.source["knowledge.yaml"]
    states = [{"id": state, "definition": state} for state in ("P", "U", "M", "R", "EA")]
    transitions = [{"id": item["id"], "from_state_id": item["from"], "target_state_id": item["to"],
                    "target_kc_ids": item["components"], "target_relation_ids": item["relations"],
                    "relevant_misconception_ids": item["misconceptions"], "state_order": {state["id"]: index for index, state in enumerate(states)}}
                   for item in study.source["transitions.yaml"]["transitions"]]
    knowledge = {"knowledge_components": [{"id": item["id"], "name": item["id"], "definition": item.get("claim", item.get("definition", ""))} for item in knowledge_source["components"]],
                 "relations": [{"id": item["id"], "name": item["id"], "definition": item.get("definition", ""), "kc_ids": []} for item in knowledge_source["relations"]],
                 "misconceptions": [{"id": item["id"], "name": item["id"], "definition": item.get("error", ""), "conflicts_with": []} for item in knowledge_source["misconceptions"]],
                 "solo_states": states, "transitions": transitions}
    pedagogies = [{"id": item["id"], "name": item["label"], "core_mechanism": item["mechanism"], "permissions": item["must"], "prohibitions": item["must_not"], "tutor_role": item["mechanism"], "prohibited_behavior": "; ".join(item["must_not"]), "treatment_fidelity_test": item["runtime_contract"]} for item in study.source["interventions.yaml"]["pedagogies"]]
    cells, moves, recipes = {}, {}, {}
    parents = study.source["interventions.yaml"]["cells"]
    children = study.source["subsection_interventions.yaml"]["cells"]
    for pedagogy in pedagogies:
        recipes[pedagogy["id"]] = {"id": "v051-" + pedagogy["id"], "pedagogy_id": pedagogy["id"], "role_instruction": pedagogy["tutor_role"], "move_generation_instruction": study.prompts["TUTOR_PROMPT.md"], "learner_check_instruction": "Candidate-only; persisted Conversation Judge supervision is required before subsection advancement.", "completion_instruction": "Do not declare SOLO success; closure remains non-authoritative until the Conversation Judge and runtime gates accept obligation-level evidence.", "prohibited_behavior": pedagogy["prohibitions"]}
    for parent in parents:
        key = f"{parent['transition_id']}:{parent['pedagogy_id']}"
        parent_children = [child for child in children if child["parent_cell_id"] == parent["id"]]
        move_ids = []
        for child in parent_children:
            for move in child["core_moves"]:
                move_ids.append(move["id"])
                moves[move["id"]] = {"id": move["id"], "transition_id": parent["transition_id"], "pedagogy_id": parent["pedagogy_id"], "title": child["id"], "purpose": move["instructional_action"], "kc_ids": [], "relation_ids": [], "misconception_ids": [], "material_blueprint": child["subsection_id"], "allowed_behavior": move, "prohibited_behavior": child["scope_boundaries"], "completion_evidence": move["completion_evidence"], "next_move_ids": []}
        cells[key] = {"id": parent["id"], "transition_id": parent["transition_id"], "pedagogy_id": parent["pedagogy_id"], "instructional_intent": parent["scientific_goal"], "missing_structure": parent["scientific_goal"], "target_kc_ids": [ref for ref in parent["target_refs"] if ref.startswith("K")], "target_relation_ids": [ref for ref in parent["target_refs"] if ref.startswith("R")], "relevant_misconception_ids": [], "move_ids": move_ids, "prohibitions": [parent["prohibition"]], "completion_condition": parent["completion"], "treatment_constraints": parent["fidelity_observation"], "max_tutor_turns": 0}
    families, rubrics = {}, {}
    blueprints = study.source["assessment_families.yaml"]["blueprints"]
    for transition in transitions:
        forms = [{"id": blueprint["id"], "title": blueprint["title"], "task_type": "V051_FOUR_ITEM_CANDIDATE", "generation_goal": blueprint["blueprint_focus"], "scenario_seed": "candidate-only", "equivalence_constraints": [], "required_response_features": [], "misconception_probes": [], "prohibited_leakage": [], "target_kc_ids": [ref for ref in blueprint["target_refs"] if ref.startswith("K")], "target_relation_ids": [ref for ref in blueprint["target_refs"] if ref.startswith("R")], "target_evidence_ids": [], "relevant_misconception_ids": transition["relevant_misconception_ids"], "v051_item_contracts": blueprint["items"]} for blueprint in blueprints if blueprint["transition_id"] == transition["id"]]
        families[transition["id"]] = {"id": "v051-" + transition["id"], "transition_id": transition["id"], "forms": forms}
        rubrics[transition["id"]] = {"id": "v051-" + transition["id"], "transition_id": transition["id"], "target_state_id": transition["target_state_id"], "evidence_criteria": [], "success_rule": {"minimum_evidence": 0}}
    authored = {"manifest": {"study_id": study.study_id, "content_version": study.content_version, "study_schema_version": "v051-native-1", "markdown_provenance": {"locked_curriculum_sha256": study.source_hashes["CURRICULUM_SOURCE_LOCKED.md"]}}, "knowledge": knowledge, "pedagogies": pedagogies, "cells": list(cells.values()), "shared_intervention_envelope": {}, "v051": {"candidate_only": True, "source_hashes": study.source_hashes, "locked_curriculum": study.locked_curriculum, "scientific": study.source, "prompts": study.prompts}}
    slices = {transition["id"]: {"transition": transition, "knowledge_components": [], "relations": [], "misconceptions": []} for transition in transitions}
    return CompiledStudy(study.study_id, study.content_version, authored, MappingProxyType(slices), MappingProxyType(cells), MappingProxyType(moves), MappingProxyType(recipes), MappingProxyType(families), MappingProxyType(rubrics), {"initial_state_id": "P", "transition_ids": ["C1", "C2", "C3", "C4"], "pedagogy_ids": ["P1", "P2", "P3"], "max_attempts_per_transition": 3, "assessment_strategy": "candidate_not_executable", "pedagogy_strategy": "random_without_replacement"})


def resolve_v051_tutor_context(compiled: CompiledStudy, subsection_id: str, pedagogy_id: str) -> dict:
    scientific = compiled.authored.get("v051", {}).get("scientific")
    if scientific is None:
        raise ScientificV051Error("compiled study is not v0.5.1")
    subsection = next((item for item in scientific["curriculum.yaml"]["subsections"] if item["id"] == subsection_id), None)
    child = next((item for item in scientific["subsection_interventions.yaml"]["cells"] if item["id"] == f"{subsection_id}-{pedagogy_id}"), None)
    parent = next((item for item in scientific["interventions.yaml"]["cells"] if child and item["id"] == child["parent_cell_id"]), None)
    pedagogy = next((item for item in scientific["interventions.yaml"]["pedagogies"] if item["id"] == pedagogy_id), None)
    if not all((subsection, child, parent, pedagogy)):
        raise ScientificV051Error(f"unknown v0.5.1 compiled child context {subsection_id}-{pedagogy_id}")
    return {"global_pedagogy": pedagogy, "parent_cell": parent, "child_cell": child, "subsection": subsection,
            "knowledge": scientific["knowledge.yaml"], "restrictions": [parent["scope_boundary"], *child["scope_boundaries"]],
            "tutor_prompt": compiled.authored["v051"]["prompts"]["TUTOR_PROMPT.md"]}
