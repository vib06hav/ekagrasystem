"""Strict loader and context resolver for the unapproved F1 v0.5.1 source."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class ScientificV051Error(ValueError):
    pass


YAML_FILES = (
    "knowledge.yaml", "transitions.yaml", "interventions.yaml", "assessment_families.yaml",
    "judge.yaml", "protocol.yaml", "scenario_rules.yaml", "curriculum.yaml",
    "subsection_interventions.yaml", "conversation_judge.yaml",
)
PROMPT_FILES = (
    "TUTOR_PROMPT.md", "CONVERSATION_JUDGE_PROMPT.md", "ASSESSMENT_GENERATION_PROMPT.md",
    "SEMANTIC_REVIEW_PROMPT.md", "SUBJECTIVE_JUDGE_PROMPT.md",
)
EXPECTED_SCHEMAS = {
    "knowledge.yaml": "ekagra.scientific.knowledge.v0.5-candidate",
    "transitions.yaml": "ekagra.scientific.transitions.v0.5-candidate",
    "interventions.yaml": "ekagra.scientific.interventions.v0.5-candidate",
    "assessment_families.yaml": "ekagra.scientific.assessment_families.v0.5-candidate",
    "judge.yaml": "ekagra.scientific.judge.v0.5-candidate",
    "protocol.yaml": "ekagra.scientific.protocol.v0.5-candidate",
    "scenario_rules.yaml": "ekagra.scientific.scenarios.v0.5-candidate",
    "curriculum.yaml": "ekagra.scientific.curriculum.v0.5-candidate",
    "subsection_interventions.yaml": "ekagra.scientific.subsection_interventions.v0.5-candidate",
    "conversation_judge.yaml": "ekagra.scientific.conversation_judge.v0.5-candidate",
}
SOURCE_FILES = (
    *(f"08_SCIENTIFIC_YAML/{name}" for name in YAML_FILES),
    *(f"07_PROMPT_CONTRACTS/{name}" for name in PROMPT_FILES),
    "CURRICULUM_SOURCE_LOCKED.md",
    "09_REFERENCE_AND_VALIDATION/v04_reference_parity_oracle.py",
    "09_REFERENCE_AND_VALIDATION/MOVE_CONTENT_ALIGNMENT_AUDIT.csv",
    "09_REFERENCE_AND_VALIDATION/ASSESSMENT_ALIGNMENT_INDEX.csv",
)


def _read_yaml(path: Path) -> dict[str, Any]:
    parser = YAML(typ="safe")
    parser.allow_duplicate_keys = False
    try:
        value = parser.load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ScientificV051Error(f"invalid v0.5.1 YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ScientificV051Error(f"v0.5.1 YAML must be an object: {path}")
    return value


def _by_id(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    result = {item.get("id"): item for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)}
    if len(result) != len(items):
        raise ScientificV051Error(f"duplicate or missing {label} id")
    return result


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ScientificV051Error(message)


def _compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class ScientificStudyV051:
    root: Path
    source_hashes: dict[str, str]
    source: dict[str, dict[str, Any]]
    prompts: dict[str, str]
    locked_curriculum: str

    @property
    def study_id(self) -> str:
        return self.source["knowledge.yaml"]["study_id"]

    @property
    def content_version(self) -> str:
        return "v0.5.1"

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(_compact(self.source_hashes).encode()).hexdigest()

    def tutor_context(self, subsection_id: str, pedagogy_id: str) -> dict[str, Any]:
        curriculum = _by_id(self.source["curriculum.yaml"]["subsections"], "subsection")
        parents = _by_id(self.source["interventions.yaml"]["cells"], "parent cell")
        children = _by_id(self.source["subsection_interventions.yaml"]["cells"], "child cell")
        pedagogies = _by_id(self.source["interventions.yaml"]["pedagogies"], "pedagogy")
        child = children.get(f"{subsection_id}-{pedagogy_id}")
        if child is None:
            raise ScientificV051Error(f"unknown v0.5.1 child context {subsection_id}-{pedagogy_id}")
        parent = parents[child["parent_cell_id"]]
        return {
            "global_pedagogy": pedagogies[pedagogy_id], "parent_cell": parent, "child_cell": child,
            "subsection": curriculum[subsection_id], "knowledge": self.source["knowledge.yaml"],
            "restrictions": [*parent.get("scope_boundary", "").splitlines(), *child.get("scope_boundaries", [])],
            "tutor_prompt": self.prompts["TUTOR_PROMPT.md"],
        }

    def compile_tutor(self, subsection_id: str, pedagogy_id: str) -> str:
        return self.prompts["TUTOR_PROMPT.md"] + "\n\n[V051_ACTIVE_SUBSECTION_TUTOR_CONTEXT]\n" + _compact(self.tutor_context(subsection_id, pedagogy_id))

    def conversation_judge_context(self, subsection_id: str, pedagogy_id: str) -> dict[str, Any]:
        context = self.tutor_context(subsection_id, pedagogy_id)
        return {key: context[key] for key in ("global_pedagogy", "parent_cell", "child_cell", "subsection", "knowledge", "restrictions")} | {
            "conversation_judge": self.source["conversation_judge.yaml"],
            "conversation_judge_prompt": self.prompts["CONVERSATION_JUDGE_PROMPT.md"],
        }

    def subjective_judge_context(self, blueprint_id: str) -> dict[str, Any]:
        blueprints = _by_id(self.source["assessment_families.yaml"]["blueprints"], "blueprint")
        blueprint = blueprints[blueprint_id]
        subjective = next(item for item in blueprint["items"] if item["type"] == "SUBJECTIVE")
        return {"blueprint": {key: blueprint[key] for key in ("id", "transition_id", "title", "blueprint_focus", "required_solo_structure")},
                "subjective_contract": subjective, "judge": self.source["judge.yaml"], "knowledge": self.source["knowledge.yaml"],
                "subjective_judge_prompt": self.prompts["SUBJECTIVE_JUDGE_PROMPT.md"]}


def load_scientific_v051(root: Path) -> ScientificStudyV051:
    yaml_root, prompt_root = root / "08_SCIENTIFIC_YAML", root / "07_PROMPT_CONTRACTS"
    missing = [name for name in SOURCE_FILES if not (root / name).is_file()]
    if missing:
        raise ScientificV051Error(f"v0.5.1 source missing required file(s): {', '.join(missing)}")
    if {path.name for path in yaml_root.glob("*.yaml")} != set(YAML_FILES):
        raise ScientificV051Error("v0.5.1 source must contain exactly the ten supported YAML files")
    source = {name: _read_yaml(yaml_root / name) for name in YAML_FILES}
    for name, schema in EXPECTED_SCHEMAS.items():
        _require(source[name].get("schema") == schema, f"unsupported v0.5.1 schema in {name}")
        _require(str(source[name].get("status", "")).startswith("CANDIDATE_UNAPPROVED"), f"{name} is not candidate-only")
    study = ScientificStudyV051(root, {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in SOURCE_FILES}, source,
                                {name: (prompt_root / name).read_text(encoding="utf-8") for name in PROMPT_FILES},
                                (root / "CURRICULUM_SOURCE_LOCKED.md").read_text(encoding="utf-8"))
    _validate(study)
    return study


def _validate(study: ScientificStudyV051) -> None:
    source = study.source
    sections = _by_id(source["curriculum.yaml"].get("sections", []), "section")
    subsections = _by_id(source["curriculum.yaml"].get("subsections", []), "subsection")
    _require(list(sections) == ["C1", "C2", "C3", "C4"] and len(subsections) == 13, "v0.5.1 requires four sections and thirteen subsections")
    for section_id, expected in {"C1": 4, "C2": 4, "C3": 2, "C4": 3}.items():
        actual = [item["id"] for item in subsections.values() if item.get("section_id") == section_id]
        _require(sections[section_id].get("subsection_ids") == actual and len(actual) == expected, f"invalid {section_id} subsection order")
    content_ids: set[str] = set()
    for subsection in subsections.values():
        _require(subsection.get("teaching_goal") in study.locked_curriculum, f"locked curriculum goal missing for {subsection['id']}")
        for content in subsection.get("required_content", []):
            _require(content.get("id") not in content_ids and content.get("required_fact") in study.locked_curriculum, f"invalid locked content in {subsection['id']}")
            content_ids.add(content["id"])
    knowledge = source["knowledge.yaml"]
    known = set().union(*({item["id"] for item in knowledge.get(key, [])} for key in ("components", "relations", "misconceptions")))
    _require(len(known) == sum(len(knowledge.get(key, [])) for key in ("components", "relations", "misconceptions")), "duplicate knowledge id")
    transitions = _by_id(source["transitions.yaml"].get("transitions", []), "transition")
    _require(set(transitions) == set(sections), "v0.5.1 requires C1-C4 transitions")
    for transition in transitions.values():
        _require(set().union(*(set(transition.get(key, [])) for key in ("components", "relations", "misconceptions"))) <= known, f"broken transition reference {transition['id']}")
    pedagogies = _by_id(source["interventions.yaml"].get("pedagogies", []), "pedagogy")
    _require(list(pedagogies) == ["P1", "P2", "P3"], "v0.5.1 requires P1/P2/P3 global pedagogies")
    parents = _by_id(source["interventions.yaml"].get("cells", []), "parent cell")
    _require(set(parents) == {f"C{i}-P{j}" for i in range(1, 5) for j in range(1, 4)}, "v0.5.1 requires all 12 parent cells")
    for parent in parents.values():
        _require(set(parent.get("target_refs", [])) <= known, f"broken parent science reference {parent['id']}")
        _require(parent.get("subsection_order") == sections[parent["transition_id"]]["subsection_ids"], f"invalid parent child order {parent['id']}")
    children = _by_id(source["subsection_interventions.yaml"].get("cells", []), "child cell")
    _require(len(children) == 39 and set(children) == {f"{subsection_id}-{pedagogy_id}" for subsection_id in subsections for pedagogy_id in pedagogies}, "v0.5.1 requires all 39 child cells")
    for child in children.values():
        subsection = subsections[child["subsection_id"]]
        _require(child.get("parent_cell_id") == f"{subsection['section_id']}-{child['pedagogy_id']}", f"broken child parent {child['id']}")
        required = {item["id"] for item in subsection["required_content"]}
        _require(set(child.get("required_content_refs", [])) == required, f"child content mismatch {child['id']}")
        moves = child.get("core_moves", [])
        _require(len(moves) >= 3 and set().union(*(set(move.get("covers_content_refs", [])) for move in moves)) == required, f"child moves do not cover locked content {child['id']}")
        _require(all(set(move.get("covers_content_refs", [])) <= required for move in moves), f"child move has out-of-scope content {child['id']}")
    scenarios = _by_id(source["scenario_rules.yaml"].get("families", []), "scenario family")
    blueprints = _by_id(source["assessment_families.yaml"].get("blueprints", []), "blueprint")
    _require(len(blueprints) == 16 and {blueprint["transition_id"] for blueprint in blueprints.values()} == set(sections), "v0.5.1 requires sixteen blueprints")
    item_ids: set[str] = set()
    for blueprint in blueprints.values():
        items = blueprint.get("items", [])
        _require(len(items) == 4 and [item.get("type") for item in items] == ["MCQ", "MCQ", "MCQ", "SUBJECTIVE"], f"invalid assessment slots {blueprint['id']}")
        _require(blueprint.get("curriculum_subsection_refs") == sections[blueprint["transition_id"]]["subsection_ids"], f"invalid assessment scope {blueprint['id']}")
        for item in items:
            _require(item.get("id") not in item_ids and item.get("transition_id") == blueprint["transition_id"] and item.get("scenario_family") in scenarios, f"invalid assessment item in {blueprint['id']}")
            _require(set(item.get("mapped_locked_subsections", [])) <= set(sections[blueprint["transition_id"]]["subsection_ids"]), f"assessment item outside section {item['id']}")
            if blueprint["transition_id"] == "C2":
                text = " ".join(str(item.get(key, "")) for key in ("scientific_purpose", "generation_instruction", "correctness_condition", "target_structural_evidence")).lower()
                _require(not any(term in text for term in ("rectangle", "four-corner", "three-flip", "3-bit mimic", "four-data-bit")), f"C2 exceeds course boundary {item['id']}")
            item_ids.add(item["id"])
    _require(len(item_ids) == 64, "v0.5.1 requires 64 unique assessment slots")
    _require("NOT the formal Subjective Judge" in study.prompts["CONVERSATION_JUDGE_PROMPT.md"], "Conversation Judge prompt lacks scoring isolation")
    _require("Do NOT receive" in study.prompts["SUBJECTIVE_JUDGE_PROMPT.md"], "Subjective Judge prompt lacks input isolation")
