"""Capture synthetic DEV examples of the final C3 isolated-pilot system prompts."""
from __future__ import annotations

import argparse
from pathlib import Path

from solo_harness.runtime import controlled_executor as executor
from solo_harness.runtime.controlled_c3_pilot_prompts import judge_prompt, tutor_prompt


def _dialogue(move_id: str):
    return [{"id": "SYNTHETIC-DEV-TUTOR", "role": "TUTOR",
             "content": "Synthetic DEV completed Tutor delivery for prompt assembly.",
             "instructional_trace": {"pilot_move_id": move_id}}]


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for subsection in ("C3.1", "C3.2"):
        for pedagogy in ("P1", "P2", "P3"):
            for index, move in enumerate(executor.contract("C3")["subsections"][subsection]["moves_by_pedagogy"][pedagogy]):
                label = move["id"].replace(".", "_").replace("-", "_")
                stages = ("QUESTION", "HINT_1", "HINT_2", "FINAL") if pedagogy == "P2" else (None,)
                for stage in stages:
                    suffix = f"_{stage}" if stage else ""
                    (output / f"{label}{suffix}_TUTOR.txt").write_text(
                        tutor_prompt(None, {}, [], None, None, move, index, p2_stage=stage), encoding="utf-8")
                (output / f"{label}_JUDGE.txt").write_text(
                    judge_prompt(None, {}, _dialogue(move["id"]), None, move, index, False, {}), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
