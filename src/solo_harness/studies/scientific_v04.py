"""Authoritative loader and instance resolver for the unapproved F1 v0.4 source."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class ScientificV04Error(ValueError):
    pass


_YAML = ("knowledge.yaml", "transitions.yaml", "interventions.yaml", "assessment_families.yaml", "judge.yaml", "protocol.yaml", "scenario_rules.yaml")
_PROMPTS = ("TUTOR_PROMPT.md", "ASSESSMENT_GENERATION_PROMPT.md", "SEMANTIC_REVIEW_PROMPT.md", "SUBJECTIVE_JUDGE_PROMPT.md")


def _read_yaml(path: Path) -> dict[str, Any]:
    parser = YAML(typ="safe"); parser.allow_duplicate_keys = False
    try:
        value = parser.load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ScientificV04Error(f"invalid v0.4 YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ScientificV04Error(f"v0.4 YAML must be an object: {path}")
    return value


def _compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class ScientificStudyV04:
    root: Path
    source_hashes: dict[str, str]
    knowledge: dict[str, Any]
    transitions: dict[str, Any]
    interventions: dict[str, Any]
    assessments: dict[str, Any]
    judge: dict[str, Any]
    protocol: dict[str, Any]
    scenarios: dict[str, Any]
    prompts: dict[str, str]

    @property
    def study_id(self) -> str: return self.knowledge["study_id"]
    @property
    def content_version(self) -> str: return "v0.4"
    @property
    def content_hash(self) -> str: return hashlib.sha256(_compact(self.source_hashes).encode()).hexdigest()

    def transition(self, transition_id: str) -> dict[str, Any]:
        return next(x for x in self.transitions["transitions"] if x["id"] == transition_id)

    def cell(self, cell_id: str) -> dict[str, Any]:
        return next(x for x in self.interventions["cells"] if x["id"] == cell_id)

    def blueprint(self, blueprint_id: str) -> dict[str, Any]:
        return next(x for x in self.assessments["blueprints"] if x["id"] == blueprint_id)

    def scoped_knowledge(self, refs: list[str]) -> list[dict[str, Any]]:
        items = {x["id"]: x for x in self.knowledge["components"] + self.knowledge["relations"]}
        return [items[x] for x in refs]

    def compile_tutor(self, cell_id: str, instance: dict[str, Any], dialogue: list[dict[str, str]]) -> str:
        cell = self.cell(cell_id); transition = self.transition(cell["transition_id"])
        pedagogy = next(x for x in self.interventions["pedagogies"] if x["id"] == cell["pedagogy_id"])
        payload = {"transition": transition, "pedagogy": pedagogy, "cell": cell,
                   "knowledge": self.scoped_knowledge(cell["target_refs"]),
                   "misconceptions": [x for x in self.knowledge["misconceptions"] if x["id"] in transition["misconceptions"]],
                   "instruction_instance": instance, "dialogue": dialogue,
                   "prohibitions": ["assessment instances", "assessment keys", "pedagogy switching", "SOLO pass declaration"]}
        return self.prompts["TUTOR_PROMPT.md"] + "\n\n[V04_RESOLVED_TUTOR_CONTEXT]\n" + _compact(payload)

    def compile_assessment(self, blueprint_id: str, resolved_items: list[dict[str, Any]]) -> str:
        blueprint = self.blueprint(blueprint_id)
        public = [{k: item[k] for k in ("slot_id", "type", "scenario", "scientific_purpose", "solo_evidence_role", "equivalence_conditions", "true_meaning", "distractor_meanings") if k in item} for item in resolved_items]
        payload = {"blueprint": {k: blueprint[k] for k in ("id", "transition_id", "blueprint_focus", "required_solo_structure")},
                   "items": public, "source_constraints": self.assessments["question_generation"]}
        return self.prompts["ASSESSMENT_GENERATION_PROMPT.md"] + "\n\n[V04_RESOLVED_ASSESSMENT_CONTEXT]\n" + _compact(payload)

    def compile_judge(self, blueprint_id: str, frozen_question: str, subjective_context: dict[str, Any], learner_response: str) -> str:
        blueprint = self.blueprint(blueprint_id); transition = self.transition(blueprint["transition_id"])
        payload = {"frozen_subjective_question": frozen_question, "learner_response": learner_response,
                   "instance_oracle": subjective_context["scenario"], "subjective_contract": subjective_context["contract"],
                   "transition": transition, "knowledge": self.scoped_knowledge(blueprint["target_refs"]), "judge_contract": self.judge}
        return self.prompts["SUBJECTIVE_JUDGE_PROMPT.md"] + "\n\n[V04_BLIND_JUDGE_CONTEXT]\n" + _compact(payload)


def load_scientific_v04(root: Path) -> ScientificStudyV04:
    yaml_root = root / "08_SCIENTIFIC_YAML"; prompt_root = root / "07_PROMPT_CONTRACTS"
    if not all((yaml_root / name).is_file() for name in _YAML) or not all((prompt_root / name).is_file() for name in _PROMPTS):
        raise ScientificV04Error("v0.4 source must contain all seven YAML files and four prompt contracts")
    source = {name: _read_yaml(yaml_root / name) for name in _YAML}
    expected = {"knowledge.yaml": "ekagra.scientific.knowledge.v0.4", "transitions.yaml": "ekagra.scientific.transitions.v0.4", "interventions.yaml": "ekagra.scientific.interventions.v0.4", "assessment_families.yaml": "ekagra.scientific.assessment_families.v0.4", "judge.yaml": "ekagra.scientific.judge.v0.4", "protocol.yaml": "ekagra.scientific.protocol.v0.4", "scenario_rules.yaml": "ekagra.scientific.scenarios.v0.4"}
    if any(source[name].get("schema") != schema for name, schema in expected.items()): raise ScientificV04Error("unexpected v0.4 scientific schema")
    companion = "EKAGRAAI_F1_V04_TYPED_POLICY_AND_LLM_BOUNDARY_COMPANION_CANDIDATE"
    files = [*(f"08_SCIENTIFIC_YAML/{x}" for x in _YAML), *(f"07_PROMPT_CONTRACTS/{x}" for x in _PROMPTS),
             "09_REFERENCE_AND_TEST_CASES/reference_parity_oracle.py",
             f"{companion}/INSTANCE_POLICY_MAPPING_CANDIDATE.yaml",
             f"{companion}/POLICY_EXECUTION_CONTRACT.md",
             f"{companion}/LLM_OUTPUT_AND_REVIEW_BOUNDARY.md"]
    study = ScientificStudyV04(root, {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}, source["knowledge.yaml"], source["transitions.yaml"], source["interventions.yaml"], source["assessment_families.yaml"], source["judge.yaml"], source["protocol.yaml"], source["scenario_rules.yaml"], {name: (prompt_root / name).read_text(encoding="utf-8") for name in _PROMPTS})
    _validate(study); return study


def _validate(study: ScientificStudyV04) -> None:
    known = {x["id"] for x in study.knowledge["components"] + study.knowledge["relations"]}
    transitions = study.transitions["transitions"]
    if {x["id"] for x in transitions} != {"C1", "C2", "C3", "C4"}: raise ScientificV04Error("v0.4 requires C1-C4")
    for transition in transitions:
        if not set(transition["components"] + transition["relations"]).issubset(known): raise ScientificV04Error("broken transition reference")
    cells = study.interventions["cells"]
    if {(x["transition_id"], x["pedagogy_id"]) for x in cells} != {(f"C{i}", f"P{j}") for i in range(1, 5) for j in range(1, 4)}: raise ScientificV04Error("v0.4 requires all 12 treatment cells")
    blueprints = study.assessments["blueprints"]
    if len(blueprints) != 16 or sum(len(x["items"]) for x in blueprints) != 64: raise ScientificV04Error("v0.4 requires 16 blueprints and 64 contracts")
    families = {x["id"] for x in study.scenarios["families"]}
    for blueprint in blueprints:
        if len(blueprint["items"]) != 4 or sum(x["type"] == "MCQ" for x in blueprint["items"]) != 3: raise ScientificV04Error("each blueprint requires 3 MCQs and 1 subjective")
        if any(item["scenario_family"] not in families for item in blueprint["items"]): raise ScientificV04Error("unknown scenario family")


def _oracle(root: Path):
    spec = importlib.util.spec_from_file_location("f1_v04_reference_oracle", root / "09_REFERENCE_AND_TEST_CASES/reference_parity_oracle.py")
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module
