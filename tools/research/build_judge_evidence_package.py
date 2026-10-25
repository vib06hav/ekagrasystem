"""Build a read-only evidence package from persisted Judge artifacts.

This utility does not contact providers or write to the study database.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LIVE = ROOT / "reports/live-reconstruction/run-20261024T204231Z-71f2519a"
STUDY = ROOT / "studies/python_fibonacci_memoization/v0.1"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def source_excerpt(relative: str, first: int, last: int) -> str:
    path = ROOT / relative
    lines = path.read_text(encoding="utf-8").splitlines()
    rendered = "\n".join(f"{index:4}: {line}" for index, line in enumerate(lines[first - 1:last], first))
    return f"### `{relative}` lines {first}-{min(last, len(lines))}\n\n```python\n{rendered}\n```\n"


def redact_session(record: dict) -> dict:
    """Copy an artifact record without session/participant identity fields."""
    return {key: value for key, value in record.items() if key not in {"session_id", "participant_id"}}


def raw_choice_metadata(call: dict) -> dict:
    response = call.get("response_payload") or {}
    choices = response.get("choices") or []
    choice = choices[0] if choices else {}
    return {
        "finish_reason": choice.get("finish_reason"),
        "native_finish_reason": ((choice.get("message") or {}).get("provider_specific_fields") or {}).get("finish_reason"),
        "usage": response.get("usage"),
    }


def assessment_context(data: dict, assessment_id: str) -> dict:
    assessment = next(item for item in data["assessment_instances"] if item["id"] == assessment_id)
    answer = next(item for item in data["assessment_responses"] if item["assessment_instance_id"] == assessment_id)
    return {
        "assessment_instance": redact_session(assessment),
        "assessment_response": redact_session(answer),
    }


def parse_raw_judgment(raw_response: str):
    try:
        provider = json.loads(raw_response)
        content = provider["choices"][0]["message"]["content"]
        return {"provider_payload": provider, "assistant_content": content, "parsed_judgment": json.loads(content)}
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        return {"raw_response": raw_response, "parse_error": f"{type(exc).__name__}: {exc}"}


def frozen_files() -> str:
    items = [
        "protocol.yaml", "knowledge.yaml", "judge/contract.yaml", "judge/rubrics.yaml",
        "assessment/c1.yaml", "assessment/c2.yaml", "assessment/c3.yaml", "assessment/c4.yaml",
    ]
    parts = ["# Frozen assessment and scoring definitions\n", "The following source files are reproduced verbatim from the active study package.\n"]
    for relative in items:
        content = (STUDY / relative).read_text(encoding="utf-8")
        parts.append(f"## `{STUDY.relative_to(ROOT).as_posix()}/{relative}`\n\n```yaml\n{content.rstrip()}\n```\n")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--test-output", type=Path, required=True)
    parser.add_argument("--test-command", required=True)
    args = parser.parse_args()

    export = load_json(LIVE / "session_export_partial.json")
    data = export["data"]
    failed = [call for call in data["llm_calls"] if call.get("purpose") == "JUDGE" and call.get("status") == "INVALID_OUTPUT"]
    if len(failed) != 5:
        raise RuntimeError(f"Expected five persisted invalid Judge calls; found {len(failed)}")
    first = next(call for call in failed if call.get("retry_number") == 0)
    body = json.loads(first["request_body_text"])
    comparison = load_json(LIVE / "judge_live_comparison_v2.json")
    gpt_results = [item for item in comparison["results"] if item.get("model") == "openai/gpt-5-mini"]

    out = args.output.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # Full ordered persisted messages, not reconstructed from source code.
    messages = body["messages"]
    prompt = ["# Persisted compiled Judge request", "", "Source call ID: " + first["id"], "", "## Ordered messages"]
    for number, message in enumerate(messages, 1):
        prompt.extend(["", f"### {number}. role: `{message['role']}`", "", message["content"]])
    (out / "JUDGE_PROMPT.txt").write_text("\n".join(prompt) + "\n", encoding="utf-8")
    dump_json(out / "JUDGE_SCHEMA.json", {"response_format": body["response_format"]})

    case_context = assessment_context(data, first["assessment_instance_id"])
    gemini_cases = []
    for call in sorted(failed, key=lambda item: item["retry_number"]):
        case = redact_session(call)
        case["provider_response_metadata"] = raw_choice_metadata(call)
        gemini_cases.append(case)
    gpt_cases = []
    for result in gpt_results:
        request = dict(body)
        request["model"] = result["model"]
        gpt_cases.append({
            "request": request,
            "result_metadata": {key: value for key, value in result.items() if key != "raw_response"},
            "raw_response_and_parsed_content": parse_raw_judgment(result["raw_response"]),
        })
    dump_json(out / "PREVIOUS_JUDGE_CASES.json", {
        "evidence_scope": "Persisted failed live Judge retry chain and the two persisted GPT-5 mini comparison records.",
        "source_export": str((LIVE / "session_export_partial.json").relative_to(ROOT).as_posix()),
        "failing_case_context": case_context,
        "gemini_invalid_output_calls": gemini_cases,
        "gpt_5_mini_comparison": {
            "comparison_metadata": {key: value for key, value in comparison.items() if key != "results"},
            "records": gpt_cases,
        },
    })

    settings_lines = (ROOT / "src/solo_harness/config.py").read_text(encoding="utf-8").splitlines()
    report = [
        "# Judge implementation extraction", "",
        "This report contains code references and source excerpts from the inspected working tree. It does not infer intended scientific outcomes.", "",
        "## Captured live-call configuration", "",
        f"- Provider: `{first['provider']}`", f"- Model: `{first['model']}`",
        f"- Generation parameters: `{json.dumps(first['generation_parameters'], ensure_ascii=False, sort_keys=True)}`",
        "- Request transport: persisted `request_body_text` and `request_payload` in `PREVIOUS_JUDGE_CASES.json`.", "",
        "## Call flow references", "",
        "- `src/solo_harness/web.py`: production runtime construction.",
        "- `src/solo_harness/runtime/ai.py`: prompt compilation, request preparation, provider response parsing, Pydantic validation, and Judge execution.",
        "- `src/solo_harness/runtime/engine.py`: deterministic rubric result and session/state application.",
        "- `src/solo_harness/config.py`: configuration fields and defaults.", "",
    ]
    for rel, start, end in [
        ("src/solo_harness/config.py", 1, len(settings_lines)),
        ("src/solo_harness/web.py", 1, 60),
        ("src/solo_harness/runtime/ai.py", 1, 235),
        ("src/solo_harness/runtime/ai.py", 237, 455),
        ("src/solo_harness/runtime/engine.py", 1, 245),
    ]:
        report.append(source_excerpt(rel, start, end))
    (out / "JUDGE_IMPLEMENTATION_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    rules = [
        "# Existing backend Judge and rubric decision rules", "",
        "The excerpts below are copied from the current source; line numbers are included in the excerpts.", "",
        source_excerpt("src/solo_harness/runtime/engine.py", 1, 245),
        source_excerpt("src/solo_harness/runtime/ai.py", 399, 520),
    ]
    (out / "JUDGE_RUBRIC_RULES.md").write_text("\n".join(rules), encoding="utf-8")
    (out / "ASSESSMENT_SCORING_CONTEXTS.md").write_text(frozen_files(), encoding="utf-8")

    test_output = args.test_output.read_text(encoding="utf-8")
    test_results = ["# Existing Judge-related test execution", "", "## Command", "", "```powershell", args.test_command, "```", "", "## Exact output", "", "```text", test_output.rstrip(), "```", ""]
    (out / "TEST_RESULTS.md").write_text("\n".join(test_results), encoding="utf-8")


if __name__ == "__main__":
    main()
