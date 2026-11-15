"""Authoritative fixed C1 contract and the opt-in controlled C1 pilot.

Source-ordered scientific core moves remain in the immutable v0.5 study.
This separate, versioned pilot contract adds deterministic delivery instructions.
The source contract retains C1.2--C1.4's ``design_only`` provenance.  The
separate execution overlay, validated by the prompt-context module, is the
only opt-in authority that makes those source moves executable.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path


class ControlledC1Error(ValueError):
    """Pilot definition does not match the persisted scientific context."""


@lru_cache(maxsize=1)
def contract() -> dict:
    data = json.loads(Path(__file__).with_name("controlled_c1_contracts.json").read_text(encoding="utf-8"))
    if data.get("contract_id") != "EKAGRAAI_CONTROLLED_C1_V1":
        raise ControlledC1Error("unexpected controlled C1 contract version")
    return data


def contract_hash() -> str:
    return hashlib.sha256(json.dumps(contract(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def new_c11_state() -> dict:
    # This state is kept on the existing subsection ledger so the C1.1 pilot
    # remains migration-free and recoverable under the ordinary session lock.
    return {
        "contract_id": contract()["contract_id"],
        "contract_sha256": contract_hash(),
        "move_index": 0,
        "status": "TEACHING",
        "approval_version": 0,
    }


def new_c1_state() -> dict:
    """Fresh full-C1 state; old C1.1-only attempts retain ``new_c11_state``."""
    from solo_harness.runtime.controlled_c1_prompt_context import execution_overlay_hash
    return {**new_c11_state(), "execution_overlay_sha256": execution_overlay_hash(),
            "pilot_scope": "C1.1_TO_C1.4"}


def is_controlled_c11(progress) -> bool:
    return (progress is not None and progress.subsection_id == "C1.1"
            and isinstance(progress.instructional_state, dict)
            and isinstance(progress.instructional_state.get("controlled_c11"), dict))


def is_controlled_c1(progress) -> bool:
    """True for compatible C1.1 ledgers and all fresh full-C1 ledgers."""
    if progress is None or not isinstance(progress.instructional_state, dict):
        return False
    state = progress.instructional_state.get("controlled_c11")
    if not isinstance(state, dict):
        return False
    if progress.subsection_id == "C1.1":
        return True
    return (progress.subsection_id in ("C1.2", "C1.3", "C1.4")
            and state.get("pilot_scope") == "C1.1_TO_C1.4")


def active_move(compiled, progress) -> tuple[dict, int]:
    if not is_controlled_c1(progress):
        raise ControlledC1Error("controlled C1 is not enabled on this subsection ledger")
    state = progress.instructional_state["controlled_c11"]
    if state.get("contract_id") != contract()["contract_id"] or state.get("contract_sha256") != contract_hash():
        raise ControlledC1Error("controlled C1 contract changed during a persisted attempt")
    subsection_id = progress.subsection_id
    if subsection_id not in contract()["subsections"]:
        raise ControlledC1Error("controlled C1 subsection is unknown")
    if subsection_id != "C1.1":
        from solo_harness.runtime.controlled_c1_prompt_context import execution_overlay_hash, execution_overlay
        if state.get("pilot_scope") != "C1.1_TO_C1.4" or state.get("execution_overlay_sha256") != execution_overlay_hash():
            raise ControlledC1Error("controlled C1 execution overlay changed during a persisted attempt")
        execution_overlay()  # validates the separate 39-move opt-in overlay.
    cells = contract()["subsections"][subsection_id]["moves_by_pedagogy"]
    moves = cells.get(progress.pedagogy_id)
    if not moves or [m["id"] for m in moves] != list(progress.required_move_ids):
        raise ControlledC1Error("pilot move IDs disagree with the persisted scientific move order")
    source = compiled.authored["v051"]["scientific"]["subsection_interventions.yaml"]["cells"]
    authored = next((c for c in source if c["id"] == f"{subsection_id}-{progress.pedagogy_id}"), None)
    if not authored or len(authored["core_moves"]) != len(moves):
        raise ControlledC1Error("pilot context disagrees with scientific subsection cell")
    for local, locked in zip(moves, authored["core_moves"]):
        if (local["id"] != locked["id"]
                or local["source_instructional_action"] != locked["instructional_action"]
                or local["required_content_refs"] != locked["covers_content_refs"]):
            raise ControlledC1Error("pilot move is not aligned to its locked source action")
    position = state.get("move_index")
    if type(position) is not int or position < 0 or position >= len(moves):
        raise ControlledC1Error("invalid persisted C1 move position")
    return moves[position], position


def c11_instance(pedagogy_id: str) -> dict:
    """Return only the fixed verified Yes/No representations; no randomization."""
    if pedagogy_id not in ("P1", "P2", "P3"):
        raise ControlledC1Error("unknown C1.1 pedagogy")
    facts = contract()["fixed_cases"]["C1.1"]
    primary = {"name": "primary", "family": "bit_sequence_intro", "answers": facts["primary_answers"],
               "bit_sequence": facts["primary_bits"], "position_labels": facts["positions"],
               "number_of_ones": facts["one_counts"][facts["primary_bits"]]}
    contrast = {"name": "contrast", "family": "bit_sequence_intro", "answers": facts["contrast_answers"],
                "bit_sequence": facts["contrast_bits"], "position_labels": facts["positions"],
                "number_of_ones": facts["one_counts"][facts["contrast_bits"]]}
    for case in (primary, contrast):
        if ("".join(facts["rule"][answer] for answer in case["answers"]) != case["bit_sequence"]
                or case["number_of_ones"] != case["bit_sequence"].count("1")
                or case["position_labels"] != list(range(1, len(case["bit_sequence"]) + 1))):
            raise ControlledC1Error("invalid fixed C1.1 verified case")
    cases = [primary, contrast] if pedagogy_id == "P3" else [primary]
    from solo_harness.studies.v051_scenarios import scientific_case_fingerprints
    public = {"rule": facts["rule"], "cases": cases, "case_relation": "same_mapping_single_changed_position" if pedagogy_id == "P3" else "single_mapping"}
    identity = hashlib.sha256(json.dumps(public, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"instruction_only": True, "verified": True, "subsection_id": "C1.1",
            "pedagogy_id": pedagogy_id, "public": public,
            "private_oracle": {"cases": [{"name": case["name"], "bit_count": len(case["bit_sequence"]),
                                           "ones_count": case["number_of_ones"]} for case in cases]},
            "case_fingerprints": scientific_case_fingerprints([{"public": c} for c in cases]),
            "instance_id": "INSTRUCTION_ONLY:C11_CONTROLLED:" + identity}


def c1_instance(subsection_id: str, pedagogy_id: str) -> dict:
    """Deterministic locked instance for any full-C1 subsection.

    C1.1 keeps its existing public mapper contract.  Later visuals receive
    only verified fixed-case data from the immutable source contract.
    """
    if subsection_id == "C1.1":
        return c11_instance(pedagogy_id)
    if subsection_id not in ("C1.2", "C1.3", "C1.4") or pedagogy_id not in ("P1", "P2", "P3"):
        raise ControlledC1Error("unknown controlled C1 fixed instance")
    from solo_harness.runtime.controlled_c1_prompt_context import science_library
    facts = science_library(subsection_id)  # validates fixed arithmetic/structure.
    public = {"facts": facts, "fixed_cases": contract()["fixed_cases"][subsection_id]}
    identity = hashlib.sha256(json.dumps(public, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"instruction_only": True, "verified": True, "subsection_id": subsection_id,
            "pedagogy_id": pedagogy_id, "public": public, "private_oracle": {},
            "case_fingerprints": [], "instance_id": "INSTRUCTION_ONLY:C1_CONTROLLED:" + identity}


def visual_descriptor(move: dict, instructional_instance: dict, stage: str = "complete") -> dict | None:
    """Frontend-only render data, never sourced from LLM prose or HTML."""
    requested = move["visual"]
    if not requested:
        return None
    if stage not in ("prompt", "complete"):
        raise ControlledC1Error("invalid visual reveal stage")
    descriptor = {"component": requested["component"], "mode": requested["mode"], "stage": stage,
                  "subsection_id": move["id"].split("-")[0]}
    if descriptor["subsection_id"] == "C1.1":
        return {**descriptor, "rule": instructional_instance["public"]["rule"],
                "cases": instructional_instance["public"]["cases"]}
    # The template renders these passive, verified fields without LLM prose.
    return {**descriptor, "facts": instructional_instance["public"]["facts"],
            "fixed_cases": instructional_instance["public"]["fixed_cases"]}


def unambiguous_reply_feedback(move: dict, learner_text: str | None, instructional_instance: dict) -> dict | None:
    """Optional deterministic hint for a literal chat answer; never a mastery score.

    Other responses (including doubts, explanations and mixed prose) remain for
    the LLM to interpret naturally. Only the current guided move is checked.
    """
    if (learner_text is None or move["learner_response_policy"] != "guided"
            or not move["id"].startswith("C1.1-")):
        return None
    answer = learner_text.strip()
    expected = instructional_instance["public"]["cases"][0]
    if move["id"] == "C1.1-P2-M03" and len(answer) == len(expected["bit_sequence"]) and set(answer) <= {"0", "1"}:
        return {"kind": "bit_sequence", "submitted": answer,
                "verified_expected": expected["bit_sequence"], "matches": answer == expected["bit_sequence"],
                "purpose": "formative feedback, not mastery or progression"}
    if move["id"] == "C1.1-P2-M04" and answer.isascii() and answer.isdecimal() and len(answer) <= 2:
        return {"kind": "ones_count", "submitted": int(answer),
                "verified_expected": expected["number_of_ones"],
                "matches": int(answer) == expected["number_of_ones"],
                "purpose": "formative feedback, not mastery or progression"}
    return None
