"""Build the normalized operational YAML study from the authoritative Markdown packs.

The generated YAML is the executable study definition. Markdown remains its
human-authored provenance; no runtime prompt receives an entire source pack.
"""
from __future__ import annotations

from pathlib import Path
import re

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/python_fibonacci_memoization/v0.1"
YAML_READER = YAML(typ="safe")


def heading_index(text: str):
    return [
        (match.start(), match.end(), len(match.group(1)), match.group(2).strip())
        for match in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", text, re.MULTILINE)
    ]


def section(text: str, title_pattern: str, level: int) -> tuple[str, str]:
    headings = heading_index(text)
    for index, (start, heading_end, found_level, title) in enumerate(headings):
        if found_level == level and re.fullmatch(title_pattern, title):
            end = len(text)
            for next_start, _next_end, next_level, _next_title in headings[index + 1 :]:
                if next_level <= found_level:
                    end = next_start
                    break
            return title, text[heading_end:end].strip()
    raise KeyError(f"missing heading level {level}: {title_pattern}")


def direct_children(block: str, level: int) -> list[tuple[str, str]]:
    headings = heading_index(block)
    children = []
    for index, (_start, heading_end, found_level, title) in enumerate(headings):
        if found_level != level:
            continue
        end = len(block)
        for next_start, _next_end, next_level, _next_title in headings[index + 1 :]:
            if next_level <= level:
                end = next_start
                break
        children.append((title, block[heading_end:end].strip()))
    return children


def child_map(block: str, level: int) -> dict[str, str]:
    return {title: body for title, body in direct_children(block, level)}


def literal(value: str) -> LiteralScalarString:
    return LiteralScalarString(value.strip() + "\n")


def bullets(value: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"^\s*-\s+(.+?)\s*$", value, re.MULTILINE)]


def name_after_dash(title: str) -> str:
    return re.split(r"\s+[—-]\s+", title, maxsplit=1)[-1].strip()


def slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value or "section"


def load_yaml(path: Path) -> dict:
    return YAML_READER.load(path.read_text(encoding="utf-8"))


def dump_yaml(path: Path, value: dict) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 120
    yaml.indent(mapping=2, sequence=4, offset=2)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.dump(value, handle)


def build_knowledge(markdown: str) -> None:
    base = load_yaml(STUDY / "knowledge.yaml")
    _, prerequisite_text = section(markdown, r"3\. Prerequisite assumptions", 1)
    _, frontier = section(markdown, r"4\. Bounded conceptual frontier", 1)
    frontier_parts = child_map(frontier, 2)
    base["prerequisite_assumptions"] = literal(prerequisite_text)
    base["conceptual_frontier"] = {
        "in_scope": literal(frontier_parts["4.1 In scope"]),
        "out_of_scope": literal(frontier_parts["4.2 Out of scope"]),
    }
    base["in_scope"] = bullets(frontier_parts["4.1 In scope"])
    base["out_of_scope"] = bullets(frontier_parts["4.2 Out of scope"])

    for item in base["knowledge_components"]:
        title, body = section(markdown, rf"{item['id']}\s+[—-]\s+.+", 2)
        item["name"] = name_after_dash(title)
        item["definition"] = literal(body)
    for item in base["relations"]:
        title, body = section(markdown, rf"{item['id']}\s+[—-]\s+.+", 2)
        item["name"] = name_after_dash(title)
        item["definition"] = literal(body)
    for item in base["misconceptions"]:
        title, body = section(markdown, rf"{item['id']}\s+[—-]\s+.+", 2)
        item["name"] = name_after_dash(title)
        item["definition"] = literal(body)
    for item in base["solo_states"]:
        _title, body = section(markdown, rf"{item['id']}\s+[—-]\s+.+", 2)
        item["definition"] = literal(body)

    for item in base["transitions"]:
        transition_id = item["id"]
        _title, body = section(markdown, rf"{transition_id}\s+[—-]\s+.+", 1)
        parts = child_map(body, 2)
        item["structural_change"] = literal(parts["Structural change"])
        item["assumed_at_entry"] = literal(parts["Assumed at entry"])
        item["target_structure"] = {
            slug(title): literal(value)
            for title, value in parts.items()
            if title not in {"Structural change", "Assumed at entry", "Relevant misconceptions"}
            and not title.startswith("Not required")
        }
        item["relevant_misconception_guidance"] = literal(parts["Relevant misconceptions"])
        not_required = next((value for title, value in parts.items() if title.startswith("Not required")), None)
        item["not_yet_required"] = literal(not_required) if not_required else literal("No additional boundary beyond the authored target and conceptual frontier.")
        _slice_title, slice_body = section(markdown, rf"{transition_id} slice", 2)
        item["canonical_slice"] = literal(slice_body)
    dump_yaml(STUDY / "knowledge.yaml", base)


PEDAGOGIES = {
    "P1": (r"3\. Pedagogy family: Worked-Example Instruction", "Worked-Example Instruction"),
    "P2": (r"4\. Pedagogy family: Guided Questioning", "Guided Questioning"),
    "P3": (r"5\. Pedagogy family: Contrasting-Case Instruction", "Contrasting-Case Instruction"),
}
CELL_NAMES = {"P1": "Worked Example", "P2": "Guided Questioning", "P3": "Contrasting Cases"}

PROMPT_RECIPES = {
    "P1": {
        "id": "RECIPE-P1", "pedagogy_id": "P1",
        "role_instruction": "Teach by visibly modelling an organized solution. Generate a fresh example from the current move blueprint.",
        "move_generation_instruction": "Explain the reasoning steps and why they are valid; do not merely state an answer.",
        "learner_check_instruction": "End with one concise learner check tied to the modelled reasoning.",
        "completion_instruction": "Complete when the move's completion evidence is present or the configured turn budget is exhausted.",
        "prohibited_behavior": ["Do not turn the primary mechanism into discovery questioning.", "Do not use contrasting cases as the primary mechanism."],
    },
    "P2": {
        "id": "RECIPE-P2", "pedagogy_id": "P2",
        "role_instruction": "Guide the learner to construct the target relationship through one bounded question at a time.",
        "move_generation_instruction": "Generate the next concise question from the current move blueprint and the learner's latest answer.",
        "learner_check_instruction": "Ask for prediction, justification, or synthesis without revealing the complete answer first.",
        "completion_instruction": "Complete when the learner has constructed the move's target relationship or the turn budget is exhausted.",
        "prohibited_behavior": ["Do not provide the complete solution before the learner constructs it.", "Do not silently switch to a worked example."],
    },
    "P3": {
        "id": "RECIPE-P3", "pedagogy_id": "P3",
        "role_instruction": "Teach through controlled comparison of aligned cases generated from the current move blueprint.",
        "move_generation_instruction": "Keep irrelevant features stable, vary the diagnostic feature, and ask the learner to compare.",
        "learner_check_instruction": "Ask what difference matters and what rule or mechanism follows from it.",
        "completion_instruction": "Complete when the learner states the intended inference from the contrast or the turn budget is exhausted.",
        "prohibited_behavior": ["Do not label one case and simply explain the answer.", "Do not collapse into a generic question sequence without a meaningful contrast."],
    },
}


def build_interventions(markdown: str) -> None:
    pedagogy_doc = load_yaml(STUDY / "intervention/pedagogies.yaml")
    _title, envelope = section(markdown, r"2\. Shared intervention envelope", 1)
    pedagogy_doc["shared_envelope"] = {
        slug(title): literal(body) for title, body in direct_children(envelope, 2)
    }
    for pedagogy in pedagogy_doc["pedagogies"]:
        pattern, authored_name = PEDAGOGIES[pedagogy["id"]]
        _title, body = section(markdown, pattern, 1)
        parts = child_map(body, 2)
        pedagogy["name"] = authored_name
        pedagogy["core_mechanism"] = literal(parts["Core mechanism"])
        pedagogy["tutor_role"] = literal(parts["Tutor role"])
        pedagogy["prohibited_behavior"] = literal(parts["Tutor must not"])
        pedagogy["treatment_fidelity_test"] = literal(parts["Treatment-fidelity test"])
    pedagogy_doc["tutor_prompt_recipes"] = list(PROMPT_RECIPES.values())
    dump_yaml(STUDY / "intervention/pedagogies.yaml", pedagogy_doc)

    for transition_number in range(1, 5):
        path = STUDY / f"intervention/cells/c{transition_number}.yaml"
        doc = load_yaml(path)
        for cell in doc["cells"]:
            transition_id = cell["transition_id"]
            pedagogy_id = cell["pedagogy_id"]
            _title, body = section(markdown, rf"{transition_id}\s+×\s+{re.escape(CELL_NAMES[pedagogy_id])}", 2)
            sections = direct_children(body, 3)
            objective = next(value for title, value in sections if title == "Instructional objective")
            cell["instructional_intent"] = literal(objective)
            instructional = [
                (title, value)
                for title, value in sections
                if title != "Instructional objective"
                and "completion condition" not in title.lower()
                and "prohibition" not in title.lower()
                and "boundary" not in title.lower()
                and not title.lower().startswith("must not")
            ]
            expanded_instructional = []
            for title, value in instructional:
                nested_stages = direct_children(value, 4)
                expanded_instructional.extend(nested_stages or [(title, value)])
            move_parts = expanded_instructional or [("Instructional objective", objective)]
            completion = next((value for title, value in sections if "completion condition" in title.lower()), None)
            if completion is None:
                completion = next((value for title, value in sections if title in {"Intended inference", "Intended C2 result", "Desired learner construction"}), cell["completion_condition"])
            cell["completion_condition"] = literal(completion)
            restrictions = [
                f"{title}:\n{value}" for title, value in sections
                if "prohibition" in title.lower() or "boundary" in title.lower() or title.lower().startswith("must not")
            ]
            cell["treatment_constraints"] = literal("\n\n".join(restrictions) if restrictions else "Follow the shared intervention envelope and assigned pedagogy without switching treatments.")
            move_ids = [f"{cell['id']}-MOVE-{index}" for index in range(1, len(move_parts) + 1)]
            cell["move_ids"] = move_ids
            cell["moves"] = []
            for index, (move_title, move_body) in enumerate(move_parts):
                cell["moves"].append({
                    "id": move_ids[index],
                    "transition_id": transition_id,
                    "pedagogy_id": pedagogy_id,
                    "title": move_title,
                    "purpose": literal(objective),
                    "kc_ids": list(cell["target_kc_ids"]),
                    "relation_ids": list(cell["target_relation_ids"]),
                    "misconception_ids": list(cell["relevant_misconception_ids"]),
                    "material_blueprint": literal(move_body),
                    "allowed_behavior": list(next(p for p in pedagogy_doc["pedagogies"] if p["id"] == pedagogy_id).get("permissions", [])),
                    "prohibited_behavior": [cell["treatment_constraints"].strip()],
                    "completion_evidence": cell["completion_condition"],
                    "next_move_ids": move_ids[index + 1:index + 2],
                })
            cell.pop("procedure_stages", None)
            cell.pop("authored_guidance", None)
            cell.pop("material_ids", None)
        dump_yaml(path, doc)


ASSESSMENT_EVIDENCE = {
    "C1-A1": ["C1-E1", "C1-E2"], "C1-A2": ["C1-E1", "C1-E2", "C1-E3"],
    "C1-A3": ["C1-E1", "C1-E2", "C1-E3"], "C1-A4": ["C1-E1", "C1-E2", "C1-E3"],
    "C2-A1": ["C2-E1", "C2-E2", "C2-E3"], "C2-A2": ["C2-E1", "C2-E3", "C2-E4", "C2-E5"],
    "C2-A3": ["C2-E1", "C2-E2", "C2-E3", "C2-E4", "C2-E5"], "C2-A4": ["C2-E1", "C2-E3", "C2-E4", "C2-E5"],
    "C3-A1": ["C3-E1", "C3-E2", "C3-E3", "C3-E4", "C3-E5", "C3-E6"],
    "C3-A2": ["C3-E1", "C3-E2", "C3-E3", "C3-E4", "C3-E5"],
    "C3-A3": ["C3-E1", "C3-E2", "C3-E3", "C3-E4", "C3-E5", "C3-E6"],
    "C3-A4": ["C3-E1", "C3-E2", "C3-E3", "C3-E4", "C3-E6"],
    "C4-A1": ["C4-E1", "C4-E3", "C4-E5"], "C4-A2": ["C4-E1", "C4-E3", "C4-E4"],
    "C4-A3": ["C4-E1", "C4-E2", "C4-E3"], "C4-A4": ["C4-E1", "C4-E2", "C4-E6"],
}
MISCONCEPTIONS_BY_TRANSITION = {
    "C1": ["M1"], "C2": ["M3", "M5", "M6", "M8"],
    "C3": ["M3", "M4", "M5", "M6", "M7", "M8", "M9"], "C4": ["M6", "M7", "M8", "M10"],
}


def build_assessments(markdown: str) -> None:
    knowledge = load_yaml(STUDY / "knowledge.yaml")
    transitions = {item["id"]: item for item in knowledge["transitions"]}
    _title, global_body = section(markdown, r"2\. Global assessment rules", 1)
    global_rules = {slug(title): literal(body) for title, body in direct_children(global_body, 2)}
    for number in range(1, 5):
        transition_id = f"C{number}"
        path = STUDY / f"assessment/c{number}.yaml"
        doc = load_yaml(path)
        family = doc["assessment_families"][0]
        _title, family_body = section(markdown, rf"{number + 2}\. {transition_id} Assessment Family\s+[—-]\s+.+", 1)
        parts = child_map(family_body, 2)
        family["construct"] = literal(parts["Construct"])
        family["required_evidence_overview"] = literal(parts.get("Required evidence", "Evidence is defined by the transition rubric and selected item."))
        family["equivalence_envelope"] = literal(parts["Equivalence envelope"])
        family["global_rules"] = global_rules
        for form in family["forms"]:
            title, form_body = section(markdown, rf"{form['id']}\s+[—-]\s+.+", 2)
            hidden_heading = re.search(r"^###\s+Hidden scoring context\s*$", form_body, re.MULTILINE)
            if hidden_heading is None:
                raise KeyError(f"missing hidden scoring context for {form['id']}")
            learner = form_body[: hidden_heading.start()].strip()
            hidden = form_body[hidden_heading.end() :].strip()
            form["title"] = name_after_dash(title)
            material_seed = learner.split("**Question**", 1)[0].strip()
            expected = [line.strip().lstrip("-").strip() for line in hidden.splitlines() if line.strip().startswith("-")]
            form["task_type"] = slug(form["title"])
            form["generation_goal"] = literal(f"Generate a fresh assessment task that tests: {form['title']}. The prose must be newly generated for this AssessmentInstance.")
            form["scenario_seed"] = literal(material_seed or f"Create a new scenario suitable for the task type: {form['title']}.")
            form["equivalence_constraints"] = bullets(family["equivalence_envelope"])
            form["required_response_features"] = expected
            form["misconception_probes"] = MISCONCEPTIONS_BY_TRANSITION[transition_id]
            form["prohibited_leakage"] = ["Do not reveal scoring criteria or expected answers.", "Do not reproduce the scenario seed verbatim."]
            form["target_kc_ids"] = list(transitions[transition_id]["target_kc_ids"])
            form["target_relation_ids"] = list(transitions[transition_id]["target_relation_ids"])
            form["target_evidence_ids"] = ASSESSMENT_EVIDENCE[form["id"]]
            form["relevant_misconception_ids"] = MISCONCEPTIONS_BY_TRANSITION[transition_id]
            form.pop("prompt", None)
            form.pop("hidden_scoring_context", None)
        dump_yaml(path, doc)


def build_judge(markdown: str) -> None:
    contract = load_yaml(STUDY / "judge/contract.yaml")
    _title, generic = section(markdown, r"2\. Generic Judge contract", 1)
    _title, output = section(markdown, r"3\. Generic output concepts", 1)
    _title, solo = section(markdown, r"4\. Global SOLO interpretation", 1)
    _title, correctness = section(markdown, r"5\. Correctness policy", 1)
    contract["instructions"] = bullets(generic)
    contract["forbidden_inputs"] = bullets(generic.split("The Judge must not receive or use:", 1)[-1])
    contract["generic_contract"] = literal(generic)
    contract["output_concepts"] = literal(output)
    contract["solo_interpretation"] = {title: literal(body) for title, body in direct_children(solo, 2)}
    contract["correctness_policy"] = literal(correctness)
    dump_yaml(STUDY / "judge/contract.yaml", contract)

    doc = load_yaml(STUDY / "judge/rubrics.yaml")
    for number, rubric in enumerate(doc["judge_rubrics"], 1):
        transition_id = rubric["transition_id"]
        _title, body = section(markdown, rf"{number + 5}\. {transition_id} Rubric\s+[—-]\s+.+", 1)
        parts = child_map(body, 2)
        rubric["target_state_definition"] = literal(parts["Target state"])
        rubric["core_target"] = literal(parts["Core target"])
        rubric["correctness_expectations"] = literal(parts.get("Required correctness", "Apply the global correctness policy and item-specific scoring context."))
        evidence_parent = "Evidence domains" if "Evidence domains" in parts else "Evidence criteria"
        evidence_block = parts[evidence_parent]
        rubric["evidence_criteria"] = []
        for evidence_id in rubric["evidence_ids"]:
            evidence_title, evidence_body = section(evidence_block, rf"{evidence_id}\s+[—-]\s+.+", 3)
            rubric["evidence_criteria"].append({
                "id": evidence_id,
                "name": name_after_dash(evidence_title),
                "definition": literal(evidence_body),
            })
        rubric["state_guidance"] = {
            title: literal(value) for title, value in direct_children(parts["State guidance"], 3)
        }
        rubric["blocking_misconception_guidance"] = literal(parts["Blocking misconceptions"])
        rubric["success_rule_text"] = literal(parts["Deterministic success rule"])
    dump_yaml(STUDY / "judge/rubrics.yaml", doc)


def build_protocol(markdown: str) -> None:
    protocol = load_yaml(STUDY / "protocol.yaml")
    mappings = {
        "formal_states_and_transitions": r"2\. Formal states and transitions",
        "pedagogy_set": r"3\. Pedagogy set",
        "attempt_behavior": r"4\. Attempt behavior",
        "no_renewed_cycle_rule": r"5\. No renewed cycle",
        "assessment_behavior": r"6\. Assessment behavior",
        "intervention_history": r"7\. Intervention history",
        "judge_blindness": r"8\. Judge blindness",
        "intervention_completion_vs_success": r"9\. Intervention completion vs transition success",
        "state_machine": r"10\. POC state machine",
        "session_completion": r"11\. Session completion",
        "deferred_questions": r"12\. Explicitly deferred protocol questions",
    }
    protocol["authored_rules"] = {key: literal(section(markdown, pattern, 1)[1]) for key, pattern in mappings.items()}
    dump_yaml(STUDY / "protocol.yaml", protocol)


def main() -> None:
    knowledge = (ROOT / "01_Knowledge_Pack.md").read_text(encoding="utf-8")
    intervention = (ROOT / "02_Intervention_Pack.md").read_text(encoding="utf-8")
    assessment = (ROOT / "03_Assessment_Pack.md").read_text(encoding="utf-8")
    judge = (ROOT / "04_Judge_Rubric_Pack.md").read_text(encoding="utf-8")
    protocol = (ROOT / "05_Protocol_Config.md").read_text(encoding="utf-8")
    build_knowledge(knowledge)
    build_interventions(intervention)
    build_assessments(assessment)
    build_judge(judge)
    build_protocol(protocol)


if __name__ == "__main__":
    main()
