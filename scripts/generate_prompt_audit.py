"""Generate non-participant development copies of representative compiled prompts."""
from pathlib import Path
from types import SimpleNamespace
import uuid

from solo_harness.runtime.ai import PromptCompiler
from solo_harness.studies.canonicalization import content_identity, snapshot_identity
from solo_harness.studies.compiler import compile_study
from solo_harness.studies.loader import load

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/python_fibonacci_memoization/v0.1"
OUT = ROOT / "artifacts/prompt_audit"


def version(compiled):
    _, content_hash = content_identity(compiled.authored)
    return SimpleNamespace(id=uuid.uuid4(), content_hash=content_hash, compiler_contract_version="1.0", snapshot_hash=snapshot_identity(content_hash, compiled.to_snapshot()))


def main():
    compiled = compile_study(load(STUDY)); compiler = PromptCompiler(); study_version = version(compiled)
    OUT.mkdir(parents=True, exist_ok=True)
    for pedagogy_id, name in (("P1", "c1_worked_example_opening"), ("P2", "c1_guided_questioning_opening"), ("P3", "c1_contrasting_cases_opening")):
        envelope = compiler.compile_tutor(study_version, compiled, compiled.cells[f"C1:{pedagogy_id}"], None, [], opening=True)
        (OUT / f"{name}.txt").write_text(envelope.canonical_prompt_text, encoding="utf-8")
    dialogue = [SimpleNamespace(role="TUTOR", content_text="What two smaller Fibonacci values does fib(5) depend on?", instructional_trace={"current_move_id": "C1-P2-MOVE-1", "next_move_id": "C1-P2-MOVE-2", "progress_summary": "The learner is identifying two predecessors."}), SimpleNamespace(role="LEARNER", content_text="fib(4) and fib(3).", instructional_trace=None)]
    history = {"attempts": [{"pedagogy_id": "P1", "exposure": "base cases and recurrence were modeled", "learner_evidence": "two predecessors identified; base-case explanation partial"}]}
    envelope = compiler.compile_tutor(study_version, compiled, compiled.cells["C1:P2"], history, dialogue)
    (OUT / "c1_later_tutor_turn.txt").write_text(envelope.canonical_prompt_text, encoding="utf-8")
    form = compiled.assessment_families["C1"]["forms"][0]
    assessment = SimpleNamespace(id=uuid.uuid4(), transition_id="C1", assessment_form_id=form["id"], blueprint_snapshot=form, resolved_component_ids={}, prompt_snapshot="Explain how a recursive Fibonacci function combines its two smaller calls and terminates.", hidden_scoring_context_snapshot="Look for two predecessors, addition, and valid base cases.")
    response = SimpleNamespace(response_text="For n above 1, return fib(n-1) + fib(n-2). The base cases stop recursion.")
    envelope = compiler.compile_judge(study_version, compiled, assessment, response)
    (OUT / "c1_judge.txt").write_text(envelope.canonical_prompt_text, encoding="utf-8")


if __name__ == "__main__":
    main()
