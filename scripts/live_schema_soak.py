"""Real-provider schema-conformance soak test without mutating study state."""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import uuid

from sqlalchemy import select

from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance, AssessmentResponse, LLMCall, Session, StudyVersion
from solo_harness.runtime.ai import (
    AssessmentGenerationOutput,
    CanonicalMessage,
    JudgeOutput,
    LLMRequest,
    OpenAICompatibleClient,
    PromptCompiler,
    TutorTurnOutput,
    _decode_json_text,
)
from solo_harness.studies.catalog import StudyCatalog


MODELS = {
    "TUTOR": TutorTurnOutput,
    "ASSESSMENT": AssessmentGenerationOutput,
    "JUDGE": JudgeOutput,
}


async def main():
    settings = get_settings()
    repetitions = int(os.getenv("LIVE_SCHEMA_SOAK_REPETITIONS", "5"))
    roles = tuple(item.strip().upper() for item in os.getenv("LIVE_SCHEMA_SOAK_ROLES", "TUTOR,JUDGE").split(","))
    factory = make_session_factory(settings.database_url)
    client = OpenAICompatibleClient(settings)
    samples = {}
    with factory() as db:
        for role in roles:
            call = db.scalar(
                select(LLMCall)
                .where(LLMCall.purpose == role, LLMCall.status == "SUCCEEDED")
                .order_by(LLMCall.started_at.desc())
            )
            if call is None:
                raise RuntimeError(f"no successful persisted {role} call is available as a soak fixture")
            messages = tuple(CanonicalMessage.model_validate(item) for item in call.request_payload["messages"])
            audit = call.request_payload.get("audit_context", {})
            if role == "JUDGE":
                assessment = db.get(AssessmentInstance, call.assessment_instance_id)
                response = db.scalar(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id == assessment.id))
                session = db.get(Session, call.session_id)
                version = db.get(StudyVersion, session.study_version_id)
                study = StudyCatalog().load(db, session.study_version_id)
                envelope = PromptCompiler().compile_judge(version, study, assessment, response)
                messages = envelope.ordered_messages
                audit = envelope.audit_context
            samples[role] = {
                "model": call.model,
                "messages": messages,
                "audit": audit,
            }

    results = []
    for role in roles:
        output_model = MODELS[role]
        sample = samples[role]
        tutorish = role in ("TUTOR", "ASSESSMENT")
        parameters = {
            "temperature": settings.tutor_temperature if tutorish else settings.judge_temperature,
            "max_tokens": settings.tutor_max_output_tokens if tutorish else settings.judge_max_output_tokens,
        }
        if settings.llm_reasoning_effort:
            parameters["reasoning_effort"] = settings.llm_reasoning_effort
        for sequence in range(1, repetitions + 1):
            raw = None
            request = LLMRequest(
                role,
                uuid.uuid4(),
                uuid.uuid4(),
                0,
                settings.llm_provider,
                sample["model"],
                sample["messages"],
                output_model.__name__,
                "1.0",
                output_model.model_json_schema(),
                parameters,
                settings.llm_request_timeout_seconds,
                sample["audit"],
            )
            try:
                raw = await client.send(client.prepare(request))
                parsed = output_model.model_validate(_decode_json_text(raw.structured_candidate))
                result = {"role": role, "sequence": sequence, "valid": True, "latency_ms": raw.latency_ms}
                if role == "JUDGE":
                    result.update({"correctness": parsed.correctness, "observed_solo_state_id": parsed.observed_solo_state_id})
            except Exception as exc:
                result = {"role": role, "sequence": sequence, "valid": False, "error": f"{type(exc).__name__}: {exc}"}
                if raw is not None:
                    result.update({"finish_reason": raw.finish_reason, "raw_chars": len(raw.raw_response_text), "usage": raw.usage})
            results.append(result)
            print(json.dumps(result), flush=True)

    summary = {}
    for role in roles:
        role_results = [item for item in results if item["role"] == role]
        latencies = [item["latency_ms"] for item in role_results if item["valid"]]
        summary[role] = {
            "calls": len(role_results),
            "valid": sum(item["valid"] for item in role_results),
            "invalid": sum(not item["valid"] for item in role_results),
            "average_latency_ms": round(statistics.mean(latencies)) if latencies else None,
            "maximum_latency_ms": max(latencies) if latencies else None,
        }
    print(json.dumps({"summary": summary}), flush=True)
    if any(not item["valid"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
