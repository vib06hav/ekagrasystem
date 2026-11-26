"""Render deterministic, offline C3 visual snapshots for the Phase-3/4 audit."""
from __future__ import annotations

import argparse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from solo_harness.runtime.controlled_executor import contract, instance, visual_descriptor


ROOT = Path(__file__).resolve().parents[2]


def main(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    template = Environment(loader=FileSystemLoader(ROOT / "src" / "solo_harness" / "templates"),
                           undefined=StrictUndefined).get_template("partials/session/controlled_c11_visual.html")
    index = ["# Offline C3 visual snapshots", "", "Rendered only from fixed server-verified cases; no model call was made.", ""]
    for subsection in ("C3.1", "C3.2"):
        for pedagogy, moves in contract("C3")["subsections"][subsection]["moves_by_pedagogy"].items():
            for move in moves:
                label = move["id"].replace(".", "_").replace("-", "_")
                if not move.get("visual"):
                    (output / f"{label}_NONE.txt").write_text("No visual is authored for this move.\n", encoding="utf-8")
                    index.append(f"- `{move['id']}`: no visual")
                    continue
                for stage in ("prompt", "complete"):
                    descriptor = visual_descriptor(move, instance(subsection, pedagogy), stage)
                    html = template.render(item={"visual": descriptor})
                    (output / f"{label}_{stage}.html").write_text(html, encoding="utf-8")
                index.append(f"- `{move['id']}`: prompt and complete snapshots")
    (output / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
