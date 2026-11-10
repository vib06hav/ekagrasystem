"""Authoritative fixed C1 contract and the opt-in C1.1 instructional pilot.

Source-ordered scientific core moves remain in the immutable v0.5 study.
This separate, versioned pilot contract adds deterministic delivery instructions.
Only C1.1 is executable; the remaining C1 definitions are design-only.
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
    return {"contract_id": contract()["contract_id"], "contract_sha256": contract_hash(), "move_index": 0}


def is_controlled_c11(progress) -> bool:
    return (progress is not None and progress.subsection_id == "C1.1"
            and isinstance(progress.instructional_state, dict)
            and isinstance(progress.instructional_state.get("controlled_c11"), dict))


def active_move(compiled, progress) -> tuple[dict, int]:
    if not is_controlled_c11(progress):
        raise ControlledC1Error("controlled C1.1 is not enabled on this subsection ledger")
    state = progress.instructional_state["controlled_c11"]
    if state.get("contract_id") != contract()["contract_id"] or state.get("contract_sha256") != contract_hash():
        raise ControlledC1Error("controlled C1 contract changed during a persisted attempt")
    cells = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]
    moves = cells.get(progress.pedagogy_id)
    if not moves or [m["id"] for m in moves] != list(progress.required_move_ids):
        raise ControlledC1Error("pilot move IDs disagree with the persisted scientific move order")
    source = compiled.authored["v051"]["scientific"]["subsection_interventions.yaml"]["cells"]
    authored = next((c for c in source if c["id"] == f"C1.1-{progress.pedagogy_id}"), None)
    if not authored or len(authored["core_moves"]) != len(moves):
        raise ControlledC1Error("pilot context disagrees with scientific subsection cell")
    for local, locked in zip(moves, authored["core_moves"]):
        if (local["id"] != locked["id"]
                or local["source_instructional_action"] != locked["instructional_action"]
                or local["required_content_refs"] != locked["covers_content_refs"]):
            raise ControlledC1Error("pilot move is not aligned to its locked source action")
    position = state.get("move_index")
    if type(position) is not int or position < 0 or position >= len(moves):
        raise ControlledC1Error("invalid persisted C1.1 move position")
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


def visual_descriptor(move: dict, instructional_instance: dict, stage: str = "complete") -> dict | None:
    """Frontend-only render data, never sourced from LLM prose or HTML."""
    requested = move["visual"]
    if not requested:
        return None
    if stage not in ("prompt", "complete"):
        raise ControlledC1Error("invalid visual reveal stage")
    return {"component": requested["component"], "mode": requested["mode"], "stage": stage,
            "rule": instructional_instance["public"]["rule"],
            "cases": instructional_instance["public"]["cases"]}


def unambiguous_reply_feedback(move: dict, learner_text: str | None, instructional_instance: dict) -> dict | None:
    """Optional deterministic hint for a literal chat answer; never a mastery score.

    Other responses (including doubts, explanations and mixed prose) remain for
    the LLM to interpret naturally. Only the current guided move is checked.
    """
    if learner_text is None or move["learner_response_policy"] != "guided":
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
