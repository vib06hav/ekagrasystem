from dataclasses import dataclass
from types import MappingProxyType

from solo_harness.studies.authored.models import AuthoredStudy
from solo_harness.studies.canonicalization import COMPILER_CONTRACT_VERSION, SNAPSHOT_SCHEMA_VERSION


@dataclass(frozen=True)
class CompiledStudy:
    study_id: str
    content_version: str
    authored: dict
    knowledge_slices: MappingProxyType
    cells: MappingProxyType
    intervention_moves: MappingProxyType
    tutor_prompt_recipes: MappingProxyType
    assessment_families: MappingProxyType
    rubrics: MappingProxyType
    protocol: dict

    def to_snapshot(self) -> dict:
        return {"schema_version": SNAPSHOT_SCHEMA_VERSION, "study_id": self.study_id, "content_version": self.content_version, "authored": self.authored, "knowledge_slices": dict(self.knowledge_slices), "cells": dict(self.cells), "intervention_moves": dict(self.intervention_moves), "tutor_prompt_recipes": dict(self.tutor_prompt_recipes), "assessment_families": dict(self.assessment_families), "rubrics": dict(self.rubrics), "protocol": self.protocol}

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> "CompiledStudy":
        return cls(snapshot["study_id"], snapshot["content_version"], snapshot["authored"], MappingProxyType(snapshot["knowledge_slices"]), MappingProxyType(snapshot["cells"]), MappingProxyType(snapshot["intervention_moves"]), MappingProxyType(snapshot["tutor_prompt_recipes"]), MappingProxyType(snapshot["assessment_families"]), MappingProxyType(snapshot["rubrics"]), snapshot["protocol"])


def compile_study(study: AuthoredStudy) -> CompiledStudy:
    authored = study.model_dump(mode="json", by_alias=True)
    kc = {item["id"]: item for item in authored["knowledge"]["knowledge_components"]}
    relations = {item["id"]: item for item in authored["knowledge"]["relations"]}
    misconceptions = {item["id"]: item for item in authored["knowledge"]["misconceptions"]}
    state_order = {state["id"]: index for index, state in enumerate(authored["knowledge"]["solo_states"])}
    slices = {}
    for transition in authored["knowledge"]["transitions"]:
        resolved_transition = {**transition, "state_order": state_order}
        transition_id = transition["id"]
        slices[transition_id] = {
            "transition": resolved_transition,
            "prerequisite_assumptions": authored["knowledge"]["prerequisite_assumptions"],
            "conceptual_frontier": authored["knowledge"]["conceptual_frontier"],
            "knowledge_components": [kc[key] for key in transition["target_kc_ids"]],
            "relations": [relations[key] for key in transition["target_relation_ids"]],
            "misconceptions": [misconceptions[key] for key in transition["relevant_misconception_ids"]],
        }
    cells = {f'{cell["transition_id"]}:{cell["pedagogy_id"]}': {key: value for key, value in cell.items() if key != "moves"} for cell in authored["cells"]}
    moves = {move["id"]: move for cell in authored["cells"] for move in cell["moves"]}
    recipes = {recipe["pedagogy_id"]: recipe for recipe in authored["tutor_prompt_recipes"]}
    families = {family["transition_id"]: family for family in authored["assessment_families"]}
    rubrics = {
        rubric["transition_id"]: {**rubric, "judge_contract": authored["judge_contract"]}
        for rubric in authored["judge_rubrics"]
    }
    return CompiledStudy(study.manifest.study_id, study.manifest.content_version, authored, MappingProxyType(slices), MappingProxyType(cells), MappingProxyType(moves), MappingProxyType(recipes), MappingProxyType(families), MappingProxyType(rubrics), authored["protocol"])
