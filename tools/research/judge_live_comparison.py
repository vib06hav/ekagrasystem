"""Compare live Judge schema compliance using one frozen persisted request."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics
import time
from pathlib import Path

import httpx

from solo_harness.config import get_settings
from solo_harness.runtime.ai import JudgeOutput, _decode_json_text


def agreement(value: JudgeOutput) -> dict[str, bool]:
    criteria = {item.criterion_id: item.status for item in value.criterion_evidence}
    misconceptions = {item.misconception_id: item.status for item in value.misconception_evidence}
    return {
        "correctness_allows_pass": value.correctness in {"CORRECT", "MINOR_ERROR"},
        "solo_at_least_u": value.observed_solo_state_id in {"U", "M", "R", "EA"},
        "required_c1_a1_evidence": all(criteria.get(key) == "DEMONSTRATED" for key in ("C1-E1", "C1-E2")),
        "m1_not_detected": misconceptions.get("M1") == "NOT_DETECTED",
    }


async def one_call(client: httpx.AsyncClient, url: str, headers: dict[str, str], body: dict, model: str) -> dict:
    request = {**body, "model": model}
    started = time.perf_counter()
    result = {"model": model}
    try:
        response = await client.post(url, headers=headers, json=request)
        latency_ms = round((time.perf_counter() - started) * 1000)
        payload = response.json()
        choice = (payload.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or choice.get("text") or ""
        result.update({
            "http_status": response.status_code,
            "provider_request_id": response.headers.get("x-request-id") or response.headers.get("request-id"),
            "finish_reason": choice.get("finish_reason"),
            "native_finish_reason": choice.get("native_finish_reason"),
            "latency_ms": latency_ms,
            "usage": payload.get("usage"),
            "cost": payload.get("cost") or (payload.get("usage") or {}).get("cost"),
            "content_chars": len(text),
            "raw_response": response.text,
        })
        parsed = JudgeOutput.model_validate(_decode_json_text(text))
        result.update({"schema_valid": True, "judgment": parsed.model_dump(mode="json"), "rubric_agreement": agreement(parsed)})
    except Exception as exc:
        result.update({"schema_valid": False, "error": f"{type(exc).__name__}: {exc}", "latency_ms": result.get("latency_ms", round((time.perf_counter() - started) * 1000))})
    return result


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strong-model", default="openai/gpt-5-mini")
    parser.add_argument("--repetitions", type=int, default=2)
    args = parser.parse_args()
    if args.repetitions < 1 or args.repetitions > 3:
        raise ValueError("repetitions must be between 1 and 3")

    document = json.loads(args.export.read_text(encoding="utf-8"))["data"]
    source = next(
        call for call in document["llm_calls"]
        if call["purpose"] == "JUDGE" and call["status"] == "INVALID_OUTPUT" and call["retry_number"] == 0
    )
    body = json.loads(source["request_body_text"])
    settings = get_settings()
    if not settings.aicredits_base_url or not settings.aicredits_api_key:
        raise RuntimeError("AICredits configuration is incomplete")
    current_model = source["model"]
    url = f"{settings.aicredits_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.aicredits_api_key.get_secret_value()}", "Content-Type": "application/json"}

    results = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(settings.llm_request_timeout_seconds, connect=settings.llm_connect_timeout_seconds)) as client:
        for model in (current_model, args.strong_model):
            for _ in range(args.repetitions):
                results.append(await one_call(client, url, headers, body, model))

    summary = {}
    for model in (current_model, args.strong_model):
        rows = [item for item in results if item["model"] == model]
        valid = [item for item in rows if item.get("schema_valid")]
        summary[model] = {
            "calls": len(rows),
            "schema_valid": len(valid),
            "schema_valid_rate": len(valid) / len(rows),
            "median_latency_ms": statistics.median(item["latency_ms"] for item in rows),
            "median_content_chars": statistics.median(item.get("content_chars", 0) for item in rows),
            "rubric_agreement": sum(all((item.get("rubric_agreement") or {}).values()) for item in valid),
            "cost_available": any(item.get("cost") is not None for item in rows),
        }
    output = {
        "source_call_id": source["id"],
        "source_request_sha256": hashlib.sha256(source["request_body_text"].encode()).hexdigest(),
        "frozen_request_preserved_except_model": True,
        "current_model": current_model,
        "strong_model": args.strong_model,
        "results": results,
        "summary": summary,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
