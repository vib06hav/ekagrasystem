"""Reviewed C2/C3 contract access for the existing move-scoped runtime.

The contracts are authoring data: callers select one move and verified facts;
they must never expose ``exact_delivery`` to a Tutor prompt.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


class ControlledC23Error(ValueError):
    pass


@lru_cache(maxsize=2)
def contract(section: str) -> dict:
    if section not in {"C2", "C3"}:
        raise ControlledC23Error("unknown reviewed section")
    path = Path(__file__).with_name(f"controlled_{section.lower()}_contracts.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    expected = 60 if section == "C2" else 30
    moves = [move for cell in data["subsections"].values()
             for pedagogy in cell["moves_by_pedagogy"].values() for move in pedagogy]
    if len(moves) != expected or len({move["id"] for move in moves}) != expected:
        raise ControlledC23Error(f"invalid {section} reviewed move coverage")
    return data


def move(subsection_id: str, pedagogy_id: str, index: int) -> dict:
    section = subsection_id.split(".", 1)[0]
    data = contract(section)
    try:
        result = data["subsections"][subsection_id]["moves_by_pedagogy"][pedagogy_id][index]
    except (KeyError, IndexError) as exc:
        raise ControlledC23Error("unknown reviewed active move") from exc
    # Authoring examples remain deliberately unavailable to prompt builders.
    return {key: value for key, value in result.items() if key != "exact_delivery"}


def section_move_count(section: str) -> int:
    return sum(len(moves) for cell in contract(section)["subsections"].values()
               for moves in cell["moves_by_pedagogy"].values())
