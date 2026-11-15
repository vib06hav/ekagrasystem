"""# CHANGED: One C1-compatible move ledger for the complete C1--C4 study.

The original C1 state key and source validators remain untouched.  The later
sections use an equivalent state machine, backed by their reviewed contracts.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from solo_harness.studies import controlled_c1

SECTIONS = ("C1", "C2", "C3", "C4")
MOVE_COUNTS = {"C1": 52, "C2": 60, "C3": 30, "C4": 45}


def section_of(progress):
    return progress.subsection_id.split(".", 1)[0]


def state_key(progress):
    return "controlled_c11" if section_of(progress) == "C1" else "controlled_executor"


def state(progress):
    return (progress.instructional_state or {}).get(state_key(progress), {})


def write_state(progress, value):
    progress.instructional_state = {**(progress.instructional_state or {}), state_key(progress): value}


@lru_cache(maxsize=3)
def contract(section):
    if section == "C1":
        return controlled_c1.contract()
    if section not in SECTIONS:
        raise ValueError(f"unsupported controlled section: {section}")
    path = Path(__file__).parent.parent / "studies" / f"controlled_{section.lower()}_contracts.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    subsections = result["subsections"]
    actual = [m for cell in subsections.values() for track in cell["moves_by_pedagogy"].values() for m in track]
    if len(actual) != MOVE_COUNTS[section] or len({m["id"] for m in actual}) != len(actual):
        raise ValueError(f"invalid controlled {section} move catalog")
    for subsection_id, cell in subsections.items():
        refs = set(cell["content_reference_legend"])
        for pedagogy in ("P1", "P2", "P3"):
            moves = cell["moves_by_pedagogy"].get(pedagogy, [])
            if len(moves) != 5:
                raise ValueError(f"{subsection_id}-{pedagogy}: expected five moves")
            for index, move in enumerate(moves, 1):
                if (move["id"] != f"{subsection_id}-{pedagogy}-M{index:02d}"
                        or not set(move["required_content_refs"]).issubset(refs)):
                    raise ValueError(f"invalid {section} contract identity/coverage")
    return result


def contract_hash(progress=None):
    if progress is None or section_of(progress) == "C1":
        return controlled_c1.contract_hash()
    payload = json.dumps(contract(section_of(progress)), sort_keys=True,
                         ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def is_controlled(progress):
    if progress is None or not isinstance(progress.instructional_state, dict):
        return False
    if section_of(progress) == "C1":
        return controlled_c1.is_controlled_c1(progress)
    record = state(progress)
    return isinstance(record, dict) and record.get("section") == section_of(progress)


def initial_state(subsection_id, full_c1=False, unified=False):
    section = subsection_id.split(".", 1)[0]
    if section == "C1":
        return {"controlled_c11": controlled_c1.new_c1_state() if full_c1 else controlled_c1.new_c11_state()}
    if not unified or section not in ("C2", "C3", "C4"):
        return {}
    data = contract(section)
    identity = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                         separators=(",", ":")).encode()).hexdigest()
    return {"controlled_executor": {"section": section, "contract_id": data["contract_id"],
                                    "contract_sha256": identity, "move_index": 0,
                                    "status": "TEACHING", "approval_version": 0}}


def moves(progress):
    return contract(section_of(progress))["subsections"][progress.subsection_id]["moves_by_pedagogy"][progress.pedagogy_id]


def active_move(compiled, progress):
    if section_of(progress) == "C1":
        return controlled_c1.active_move(compiled, progress)
    if not is_controlled(progress):
        raise ValueError("this subsection has no controlled-execution ledger")
    current = state(progress)
    if (current.get("contract_id") != contract(section_of(progress))["contract_id"]
            or current.get("contract_sha256") != contract_hash(progress)):
        raise ValueError("persisted controlled contract differs from current section contract")
    authored = moves(progress)
    if [m["id"] for m in authored] != list(progress.required_move_ids):
        raise ValueError("controlled move order differs from persisted ledger")
    index = current.get("move_index")
    if type(index) is not int or not 0 <= index < len(authored):
        raise ValueError("invalid controlled move index")
    # Preserve verified contract instructions but do not leak scripted delivery.
    move = {k: v for k, v in authored[index].items() if k != "exact_delivery"}
    return move, index


def instance(subsection_id, pedagogy_id):
    if subsection_id.startswith("C1."):
        return controlled_c1.c1_instance(subsection_id, pedagogy_id)
    section = subsection_id.split(".", 1)[0]
    fixed = contract(section)["fixed_cases"][subsection_id]
    return {"instruction_only": True, "verified": True,
            "subsection_id": subsection_id, "pedagogy_id": pedagogy_id,
            "public": {"fixed_cases": fixed}, "private_oracle": {},
            "case_fingerprints": [], "instance_id": "INSTRUCTION_ONLY:UNIFIED:" +
                hashlib.sha256(json.dumps([subsection_id, pedagogy_id, fixed],
                                          sort_keys=True, ensure_ascii=False).encode()).hexdigest()}


def visual_descriptor(move, instructional_instance, stage="complete"):
    if move["id"].startswith("C1."):
        return controlled_c1.visual_descriptor(move, instructional_instance, stage)
    if not move.get("visual"):
        return None
    if stage not in ("prompt", "complete"):
        raise ValueError("invalid controlled visual stage")
    # The template uses only server-verified data. P2 prompt-stage hides results.
    # CHANGED: even passive visuals receive ONLY facts scoped to this move.
    from solo_harness.runtime.controlled_unified_prompts import _selected_facts
    return {"component": move["visual"]["component"], "mode": move["visual"]["mode"],
            "stage": stage, "subsection_id": move["id"].split("-")[0],
            "fixed_cases": _selected_facts(move)}


def unambiguous_reply_feedback(move, learner_text, instructional_instance):
    if move["id"].startswith("C1."):
        return controlled_c1.unambiguous_reply_feedback(move, learner_text, instructional_instance)
    return None
