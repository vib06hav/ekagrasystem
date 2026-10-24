"""Component-scoped provider-neutral AI execution.

Protocol decisions remain in ``SessionRuntime``. This module resolves only the
study components needed by one model operation and persists every call before
network work begins.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from solo_harness.config import Settings
from solo_harness.db.models import (AssessmentInstance, AssessmentResponse, Attempt,
    LLMCall, LearnerHistorySnapshot, Message, Session, StudyVersion)
from solo_harness.runtime.engine import JudgeObservation, SessionRuntime


class CanonicalMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    role: Literal["system", "user", "assistant"]
    content: str


class PromptEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    prompt_contract_version: Literal["2.0"] = "2.0"
    logical_role: Literal["TUTOR", "ASSESSMENT", "JUDGE"]
    operation_id: uuid.UUID
    study_version_id: uuid.UUID
    content_hash: str
    compiler_contract_version: str
    snapshot_hash: str
    ordered_messages: tuple[CanonicalMessage, ...]
    response_schema_name: str
    response_schema_version: str = "1.0"
    response_json_schema: dict[str, Any]
    audit_context: dict[str, Any]
    canonical_prompt_text: str
    prompt_hash: str


class TutorTurnOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["1.0"]
    learner_message: str = Field(min_length=1, max_length=2500)
    disposition: Literal["CONTINUE", "COMPLETE"]
    current_move_id: str
    next_move_id: str | None
    progress_summary: str = Field(min_length=1, max_length=800)


class AssessmentGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["1.0"]
    learner_prompt: str = Field(min_length=40, max_length=4000)
    hidden_scoring_context: str = Field(min_length=20, max_length=3000)


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    excerpt: str = Field(min_length=1, max_length=300)


class EvidenceBase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["DEMONSTRATED", "PARTIAL", "NOT_DEMONSTRATED", "CONTRADICTED", "NOT_EVALUABLE"]
    citations: list[Citation] = Field(max_length=1)
    concise_summary: str = Field(max_length=300)


class CriterionEvidence(EvidenceBase): criterion_id: str


class MisconceptionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    misconception_id: str
    status: Literal["NOT_DETECTED", "POSSIBLE", "DETECTED"]
    citations: list[Citation] = Field(max_length=1)
    concise_summary: str = Field(max_length=300)


class JudgeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["1.0"]
    not_gradable_reason: Literal["EMPTY_OR_NO_MEANINGFUL_RESPONSE", "OFF_TOPIC", "UNINTERPRETABLE", "INSUFFICIENT_TO_EVALUATE"] | None
    correctness: Literal["CORRECT", "MINOR_ERROR", "MATERIALLY_INCORRECT", "NOT_GRADABLE"]
    observed_solo_state_id: str | None
    criterion_evidence: list[CriterionEvidence]
    misconception_evidence: list[MisconceptionEvidence]
    confidence: float | None = Field(ge=0, le=1)
    ambiguity_summary: str | None = Field(max_length=500)
    overall_evidence_summary: str = Field(min_length=1, max_length=700)

    @field_validator("correctness", mode="before")
    @classmethod
    def normalize_provider_synonyms(cls, value):
        return {"PARTIAL": "MINOR_ERROR", "NOT_DEMONSTRATED": "MATERIALLY_INCORRECT", "CONTRADICTED": "MATERIALLY_INCORRECT"}.get(value, value)

    @model_validator(mode="after")
    def validate_gradability_fields(self):
        if self.correctness == "NOT_GRADABLE":
            if self.not_gradable_reason is None:
                self.not_gradable_reason = "INSUFFICIENT_TO_EVALUATE"
            self.observed_solo_state_id = None
        else:
            if self.observed_solo_state_id is None:
                raise ValueError("gradable judgments require an observed SOLO state")
            self.not_gradable_reason = None
        return self

    @property
    def gradable(self) -> bool:
        return self.correctness != "NOT_GRADABLE"


@dataclass(frozen=True)
class LLMRequest:
    logical_role: str; operation_id: uuid.UUID; retry_group_id: uuid.UUID; retry_number: int
    provider: str; model: str; messages: tuple[CanonicalMessage, ...]; response_schema_name: str
    response_schema_version: str; response_json_schema: dict[str, Any]; generation_parameters: dict[str, Any]
    timeout_seconds: int; audit_context: dict[str, Any]


@dataclass(frozen=True)
class PreparedLLMRequest:
    request: LLMRequest; body: dict[str, Any]; body_text: str; redacted_headers: dict[str, str]


@dataclass(frozen=True)
class RawLLMResponse:
    provider_request_id: str | None; status_code: int; raw_response_text: str; response_payload: dict[str, Any] | None
    structured_candidate: object | str | None; finish_reason: str | None; refusal: bool; usage: dict[str, int | None]; latency_ms: int


class LLMClient(Protocol):
    def prepare(self, request: LLMRequest) -> PreparedLLMRequest: ...
    async def send(self, prepared: PreparedLLMRequest) -> RawLLMResponse: ...


class ProviderError(RuntimeError):
    def __init__(self, error_class: str, message: str, retryable: bool):
        super().__init__(message); self.error_class = error_class; self.retryable = retryable


class OpenAICompatibleClient:
    def __init__(self, settings: Settings):
        self.base_url = (settings.aicredits_base_url or "").rstrip("/")
        self.api_key = settings.aicredits_api_key.get_secret_value() if settings.aicredits_api_key else ""
        self.structured_output_mode = settings.llm_structured_output_mode
        self.timeout = httpx.Timeout(settings.llm_request_timeout_seconds, connect=settings.llm_connect_timeout_seconds)

    def prepare(self, request: LLMRequest) -> PreparedLLMRequest:
        if not self.base_url or not self.api_key:
            raise ProviderError("CONFIGURATION_ERROR", "AICredits configuration is incomplete", False)
        body = {"model": request.model, "messages": [m.model_dump() for m in request.messages], **request.generation_parameters}
        if self.structured_output_mode == "provider_native_json_schema":
            _validate_openai_strict_schema(request.response_json_schema)
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": request.response_schema_name, "strict": True, "schema": request.response_json_schema}}
        return PreparedLLMRequest(request, body, json.dumps(body, sort_keys=True, separators=(",", ":")), {"Authorization": "Bearer [REDACTED]", "Content-Type": "application/json"})

    async def send(self, prepared: PreparedLLMRequest) -> RawLLMResponse:
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, json=prepared.body)
        except httpx.TimeoutException as exc: raise ProviderError("TIMEOUT", str(exc), True) from exc
        except httpx.ConnectError as exc: raise ProviderError("CONNECTION_ERROR", str(exc), True) from exc
        latency = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 500: raise ProviderError("PROVIDER_5XX", f"HTTP {response.status_code}", True)
        if response.status_code == 429: raise ProviderError("RATE_LIMIT", "HTTP 429", True)
        if response.status_code in (401, 403): raise ProviderError("AUTHENTICATION_ERROR", f"HTTP {response.status_code}", False)
        if response.status_code >= 400: raise ProviderError("BAD_REQUEST", f"HTTP {response.status_code}", False)
        try: payload = response.json()
        except ValueError: payload = None
        choice = ((payload or {}).get("choices") or [{}])[0]; message = choice.get("message") or {}
        return RawLLMResponse(response.headers.get("x-request-id") or response.headers.get("request-id"), response.status_code, response.text, payload, _provider_content_candidate(payload), choice.get("finish_reason"), bool(message.get("refusal")), (payload or {}).get("usage") or {}, latency)


def _validate_openai_strict_schema(schema: dict[str, Any]) -> None:
    """Fail locally when a generated schema cannot be used in strict mode."""
    def walk(node, path):
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            properties = node.get("properties", {})
            if node.get("additionalProperties") is not False:
                raise ProviderError("CONFIGURATION_ERROR", f"strict schema object at {path} must forbid additional properties", False)
            if set(node.get("required", [])) != set(properties):
                raise ProviderError("CONFIGURATION_ERROR", f"strict schema object at {path} must require every property", False)
            for key, value in properties.items():
                walk(value, f"{path}.{key}")
        if node.get("type") == "array":
            walk(node.get("items"), f"{path}[]")
        for key in ("anyOf", "oneOf", "allOf"):
            for index, value in enumerate(node.get(key, [])):
                walk(value, f"{path}.{key}[{index}]")

    walk(schema, "$")
    for name, definition in schema.get("$defs", {}).items():
        walk(definition, f"$defs.{name}")


def _provider_content_candidate(payload):
    choice = ((payload or {}).get("choices") or [{}])[0]; content = (choice.get("message") or {}).get("content")
    if isinstance(content, str): return content
    if isinstance(content, list):
        parts = [x["text"] for x in content if isinstance(x, dict) and isinstance(x.get("text"), str)]
        if parts: return "".join(parts)
    return choice.get("text") if isinstance(choice.get("text"), str) else content


def _decode_json_text(value):
    if not isinstance(value, str): return value
    text = value.strip().lstrip("\ufeff")
    if text.startswith("```"):
        text = text[text.find("\n") + 1:]
        if text.rstrip().endswith("```"): text = text.rstrip()[:-3].rstrip()
    start = text.find("{")
    if start < 0: raise ValueError("provider output contains no JSON object")
    try: return json.JSONDecoder().raw_decode(text[start:])[0]
    except json.JSONDecodeError as exc: raise ValueError(f"provider output contains invalid JSON: {exc.msg}") from exc


class ComponentResolver:
    """Resolve whitelisted prompt-sized components from one frozen snapshot."""
    @staticmethod
    def _index(items): return {x["id"]: x for x in items}

    def tutor(self, study, cell, current_move_id):
        move = study.intervention_moves[current_move_id]
        knowledge = study.authored["knowledge"]
        kc, rel, mis = self._index(knowledge["knowledge_components"]), self._index(knowledge["relations"]), self._index(knowledge["misconceptions"])
        return {"recipe": study.tutor_prompt_recipes[cell["pedagogy_id"]], "move": move,
            "move_index": [{"id": mid, "title": study.intervention_moves[mid]["title"], "purpose": study.intervention_moves[mid]["purpose"][:180]} for mid in cell["move_ids"]],
            "knowledge_components": [kc[x] for x in move["kc_ids"]], "relations": [rel[x] for x in move["relation_ids"]],
            "misconceptions": [mis[x] for x in move["misconception_ids"]]}

    def assessment(self, study, blueprint):
        k = study.authored["knowledge"]; kc, rel = self._index(k["knowledge_components"]), self._index(k["relations"])
        rubric = study.rubrics[blueprint["id"].split("-")[0]]; evidence = self._index(rubric["evidence_criteria"])
        return {"blueprint": blueprint, "knowledge_components": [kc[x] for x in blueprint["target_kc_ids"]],
            "relations": [rel[x] for x in blueprint["target_relation_ids"]], "evidence": [evidence[x] for x in blueprint["target_evidence_ids"]]}

    def judge(self, study, assessment):
        bp = assessment.blueprint_snapshot; k = study.authored["knowledge"]
        kc, rel, mis = self._index(k["knowledge_components"]), self._index(k["relations"]), self._index(k["misconceptions"])
        rubric = study.rubrics[assessment.transition_id]; evidence = self._index(rubric["evidence_criteria"])
        return {"rubric": {"id": rubric["id"], "target_state_id": rubric["target_state_id"], "evidence_ids": bp["target_evidence_ids"], "blocking_misconception_ids": bp["relevant_misconception_ids"], "success_rule": rubric["success_rule"]},
            "knowledge_components": [kc[x] for x in bp["target_kc_ids"]], "relations": [rel[x] for x in bp["target_relation_ids"]],
            "evidence": [evidence[x] for x in bp["target_evidence_ids"]], "misconceptions": [mis[x] for x in bp["relevant_misconception_ids"]]}


class PromptCompiler:
    MAX_TUTOR_CHARS = 14000; MAX_ASSESSMENT_CHARS = 14000; MAX_JUDGE_CHARS = 18000
    def __init__(self, resolver=None): self.resolver = resolver or ComponentResolver()

    def _envelope(self, role, version, messages, output_model, audit):
        schema = output_model.model_json_schema(); canonical = "\n\n".join(f"[{m.role.upper()}]\n{m.content}" for m in messages)
        limit = {"TUTOR": self.MAX_TUTOR_CHARS, "ASSESSMENT": self.MAX_ASSESSMENT_CHARS, "JUDGE": self.MAX_JUDGE_CHARS}[role]
        if len(canonical) > limit: raise ValueError(f"{role} prompt exceeds {limit} character audit limit")
        digest = hashlib.sha256(json.dumps({"messages": [m.model_dump() for m in messages], "schema": schema}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return PromptEnvelope(logical_role=role, operation_id=uuid.uuid4(), study_version_id=version.id, content_hash=version.content_hash, compiler_contract_version=version.compiler_contract_version, snapshot_hash=version.snapshot_hash, ordered_messages=tuple(messages), response_schema_name=output_model.__name__, response_json_schema=schema, audit_context={**audit, "prompt_chars": len(canonical)}, canonical_prompt_text=canonical, prompt_hash=digest)

    @staticmethod
    def _compact(value): return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    def compile_tutor(self, version, study, cell, history, dialogue, opening=False):
        tutor_messages = [m for m in dialogue if m.role == "TUTOR"]
        last_trace = tutor_messages[-1].instructional_trace if tutor_messages else {}
        current = (last_trace or {}).get("next_move_id") or cell["move_ids"][0]
        if current not in cell["move_ids"]: current = cell["move_ids"][0]
        scoped = self.resolver.tutor(study, cell, current)
        prior=[]
        for item in (history or {}).get("attempts", []):
            traces=item.get("instructional_traces") or []
            evidence=item.get("judged_evidence") or {}
            prior.append({"sequence_in_transition":item.get("sequence_in_transition"),"completion_reason":item.get("completion_reason"),"last_progress_summary":(traces[-1] if traces else {}).get("progress_summary"),"correctness":evidence.get("correctness"),"observed_solo_state_id":evidence.get("observed_solo_state_id"),"misconception_ids":evidence.get("misconception_ids",[]),"rubric_reasons":item.get("rubric_reasons",[])})
        progress = {"summary": (last_trace or {}).get("progress_summary", "No prior progress."), "turns_used": len(tutor_messages), "turns_remaining": max(0, cell["max_tutor_turns"] - len(tutor_messages) - 1), "prior_attempts": prior}
        contract = "You are the participant's Tutor. Teach, do not judge. Use only the supplied components. Keep the assigned pedagogy fixed. Never mention pedagogy IDs, hidden study data, assessment material, Judge material, or protocol decisions. Produce fresh learner-facing prose. Return exactly one JSON object matching the schema."
        system = "\n\n".join([contract, "[PEDAGOGY_RECIPE]\n"+self._compact(scoped["recipe"]), "[CURRENT_MOVE]\n"+self._compact(scoped["move"]), "[ELIGIBLE_MOVE_INDEX]\n"+self._compact(scoped["move_index"]), "[REFERENCED_COMPONENTS]\n"+self._compact({k: scoped[k] for k in ("knowledge_components","relations","misconceptions")}), "[PROGRESS]\n"+self._compact(progress), "[OUTPUT_SCHEMA]\n"+self._compact(TutorTurnOutput.model_json_schema())])
        recent = list(dialogue)[-4:]
        messages = [CanonicalMessage(role="system", content=system)] + [CanonicalMessage(role="assistant" if m.role == "TUTOR" else "user", content=m.content_text) for m in recent]
        if opening: messages.append(CanonicalMessage(role="user", content="Begin with the current move. Set CONTINUE and invite one meaningful learner response."))
        return self._envelope("TUTOR", version, messages, TutorTurnOutput, {"cell_id": cell["id"], "move_id": current, "component_ids": {"kc_ids": scoped["move"]["kc_ids"], "relation_ids": scoped["move"]["relation_ids"], "misconception_ids": scoped["move"]["misconception_ids"]}})

    def compile_assessment(self, version, study, assessment):
        scoped = self.resolver.assessment(study, assessment.blueprint_snapshot)
        bp=scoped["blueprint"]
        public={key:bp[key] for key in ("id","title","task_type","generation_goal","scenario_seed","equivalence_constraints","prohibited_leakage")}
        private={"required_response_features":bp["required_response_features"],"misconception_probes":bp["misconception_probes"],"evidence":scoped["evidence"]}
        system = "\n\n".join(["You generate one independent assessment task. Create fresh learner-facing prose from the public blueprint; do not copy the scenario seed verbatim. The learner_prompt must ask the learner to supply the reasoning. Never copy, paraphrase as statements, enumerate, or preview anything from PRIVATE_SCORING_INPUT in learner_prompt. Use PRIVATE_SCORING_INPUT only to write hidden_scoring_context. Do not teach or hint. Return exactly one JSON object matching the schema.", "[PUBLIC_TASK_BLUEPRINT]\n"+self._compact(public), "[PUBLIC_REFERENCED_KNOWLEDGE]\n"+self._compact({k: scoped[k] for k in ("knowledge_components","relations")}), "[PRIVATE_SCORING_INPUT_NEVER_SHOW_TO_LEARNER]\n"+self._compact(private), "[OUTPUT_SCHEMA]\n"+self._compact(AssessmentGenerationOutput.model_json_schema())])
        return self._envelope("ASSESSMENT", version, [CanonicalMessage(role="system", content=system)], AssessmentGenerationOutput, {"assessment_instance_id": str(assessment.id), "blueprint_id": assessment.assessment_form_id, "component_ids": assessment.resolved_component_ids})

    def compile_judge(self, version, study, assessment, response):
        scoped = self.resolver.judge(study, assessment)
        required=scoped["rubric"]
        output_rules={"correctness_allowed":["CORRECT","MINOR_ERROR","MATERIALLY_INCORRECT","NOT_GRADABLE"],"observed_solo_state_id_allowed":["P","U","M","R","EA"],"criterion_ids_exactly_once_when_gradable":required["evidence_ids"],"misconception_ids_exactly_once_when_gradable":required["blocking_misconception_ids"],"use_status_not_omission_for_absent_evidence":True}
        system = "\n\n".join(["You are the independent Judge. Evaluate only the frozen task and learner response. Do not teach or decide progression. Set correctness to NOT_GRADABLE only when the response cannot be evaluated; otherwise set not_gradable_reason to null and provide an observed_solo_state_id. Keep every concise_summary to one short sentence. Use at most one short citation per evidence object; every citation must be an exact contiguous excerpt copied from the response without changing words or punctuation. Use an empty citations array when no grounded excerpt applies. The observed_solo_state_id must agree with the evidence statuses you assign. Return exactly one criterion_evidence object for every required criterion ID and one misconception_evidence object for every required misconception ID; use NOT_DEMONSTRATED or NOT_DETECTED rather than omitting an object. Mark a misconception DETECTED only when the learner endorses it as true; if the learner explicitly rejects or corrects it, mark it NOT_DETECTED. Return exactly one JSON object matching the schema, with no aliases or additional keys.", "[FROZEN_TASK]\n"+assessment.prompt_snapshot, "[HIDDEN_SCORING_CONTEXT]\n"+assessment.hidden_scoring_context_snapshot, "[SCOPED_EVALUATION_COMPONENTS]\n"+self._compact(scoped), "[OUTPUT_RULES]\n"+self._compact(output_rules), "[OUTPUT_SCHEMA]\n"+self._compact(JudgeOutput.model_json_schema())])
        return self._envelope("JUDGE", version, [CanonicalMessage(role="system", content=system), CanonicalMessage(role="user", content=response.response_text)], JudgeOutput, {"assessment_instance_id": str(assessment.id), "component_ids": assessment.resolved_component_ids})


class AIExecutionRuntime:
    def __init__(self, runtime: SessionRuntime, client: LLMClient, settings: Settings, compiler=None):
        self.runtime, self.client, self.settings, self.compiler = runtime, client, settings, compiler or PromptCompiler()

    def _request(self, envelope, role, group, number):
        tutorish = role in ("TUTOR", "ASSESSMENT")
        parameters={"temperature": self.settings.tutor_temperature if tutorish else self.settings.judge_temperature, "max_tokens": self.settings.tutor_max_output_tokens if tutorish else self.settings.judge_max_output_tokens}
        if self.settings.llm_reasoning_effort: parameters["reasoning_effort"]=self.settings.llm_reasoning_effort
        return LLMRequest(role, envelope.operation_id, group, number, self.settings.llm_provider, self.settings.tutor_model if tutorish else self.settings.judge_model, envelope.ordered_messages, envelope.response_schema_name, envelope.response_schema_version, envelope.response_json_schema, parameters, self.settings.llm_request_timeout_seconds, envelope.audit_context)

    def _reserve(self, db, session, attempt, assessment, envelope, role, group=None, number=0):
        group = group or uuid.uuid4(); prepared = self.client.prepare(self._request(envelope, role, group, number))
        call = LLMCall(session_id=session.id, attempt_id=attempt.id if attempt else None, assessment_instance_id=assessment.id if assessment else None, purpose=role, status="STARTED", retry_group_id=group, retry_number=number, provider=self.settings.llm_provider, model=prepared.request.model, generation_parameters=prepared.request.generation_parameters, compiled_prompt_text=envelope.canonical_prompt_text, request_payload={"messages":[m.model_dump() for m in envelope.ordered_messages],"response_schema":envelope.response_json_schema,"response_schema_name":envelope.response_schema_name,"prompt_hash":envelope.prompt_hash,"audit_context":envelope.audit_context,"redacted_headers":prepared.redacted_headers}, request_body_text=prepared.body_text)
        db.add(call); db.flush(); self.runtime._event(db, session, "LLM_CALL_STARTED", {"role":role,"call_id":str(call.id)}, attempt.id if attempt else None); return call.id

    def _prepared(self, call):
        messages=tuple(CanonicalMessage.model_validate(x) for x in call.request_payload["messages"])
        req=LLMRequest(call.purpose,uuid.uuid4(),call.retry_group_id,call.retry_number,call.provider,call.model,messages,call.request_payload["response_schema_name"],"1.0",call.request_payload["response_schema"],call.generation_parameters,self.settings.llm_request_timeout_seconds,call.request_payload.get("audit_context",{}))
        return self.client.prepare(req)

    async def _receive(self, db, call):
        try: raw=await self.client.send(self._prepared(call))
        except ProviderError as exc:
            call.status="FAILED"; call.error_class=exc.error_class; call.error_message=str(exc)[:4000]; call.completed_at=datetime.now(timezone.utc); db.commit(); return False
        call.status="RECEIVED"; call.provider_request_id=raw.provider_request_id; call.raw_response_text=raw.raw_response_text; call.response_payload=raw.response_payload; call.input_tokens=raw.usage.get("prompt_tokens") or raw.usage.get("input_tokens"); call.output_tokens=raw.usage.get("completion_tokens") or raw.usage.get("output_tokens"); call.total_tokens=raw.usage.get("total_tokens"); call.latency_ms=raw.latency_ms; db.commit(); return True

    @staticmethod
    def _candidate(call): return _provider_content_candidate(call.response_payload) if call.response_payload else call.raw_response_text

    def _invalidate(self, db, call, exc):
        call.status="INVALID_OUTPUT"; call.error_class="INVALID_OUTPUT"; call.error_message=str(exc)[:4000]; call.completed_at=datetime.now(timezone.utc); db.commit()

    def reserve_tutor(self, db, session_id, learner_text=None, commit=True):
        session=db.get(Session,session_id); attempt=db.get(Attempt,session.current_attempt_id)
        if session.phase!="INTERVENTION_ACTIVE" or db.scalar(select(LLMCall.id).where(LLMCall.session_id==session.id,LLMCall.status.in_(["STARTED","RECEIVED"]))): raise ValueError("Tutor operation is unavailable")
        if learner_text is not None:
            if not learner_text.strip(): raise ValueError("learner response is empty")
            seq=(db.scalar(select(Message.sequence_no).where(Message.attempt_id==attempt.id).order_by(Message.sequence_no.desc())) or 0)+1
            db.add(Message(attempt_id=attempt.id,sequence_no=seq,role="LEARNER",content_text=learner_text.strip(),content_format="plain",material_ids=[],exposed_kc_ids=[],exposed_relation_ids=[])); db.flush()
        if attempt.status=="ASSIGNED":
            now = datetime.now(timezone.utc)
            attempt.status="INTERVENTION_ACTIVE"; attempt.intervention_started_at=now
            if session.started_at is None:
                session.started_at = now
                self.runtime._event(db,session,"PARTICIPANT_BEGAN_STUDY",{"started_at":now.isoformat()},attempt.id)
        study=self.runtime._compiled(db,session); cell=study.cells[f"{attempt.transition_id}:{attempt.pedagogy_id}"]
        history=db.scalar(select(LearnerHistorySnapshot).where(LearnerHistorySnapshot.target_attempt_id==attempt.id)); dialogue=db.scalars(select(Message).where(Message.attempt_id==attempt.id).order_by(Message.sequence_no)).all(); version=db.get(StudyVersion,session.study_version_id)
        call_id = self._reserve(db,session,attempt,None,self.compiler.compile_tutor(version,study,cell,history.summary if history else None,dialogue,learner_text is None),"TUTOR")
        if commit: db.commit()
        return call_id

    def reserve_assessment(self, db, session_id, assessment_id=None, commit=True):
        session=db.get(Session,session_id); attempt=db.get(Attempt,session.current_attempt_id); assessment=db.get(AssessmentInstance,assessment_id) if assessment_id else db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id==attempt.id))
        if session.phase!="ASSESSMENT_GENERATING" or assessment.status!="GENERATING": raise ValueError("assessment generation is unavailable")
        study=self.runtime._compiled(db,session); version=db.get(StudyVersion,session.study_version_id)
        call_id=self._reserve(db,session,attempt,assessment,self.compiler.compile_assessment(version,study,assessment),"ASSESSMENT"); assessment.generation_llm_call_id=call_id
        if commit: db.commit()
        return call_id

    def reserve_judge(self, db, session_id, response_text, client_action_id=None, commit=True):
        response=self.runtime.submit_assessment(db,session_id,response_text,client_action_id,commit=False); session=db.get(Session,session_id); attempt=db.get(Attempt,session.current_attempt_id); assessment=db.get(AssessmentInstance,response.assessment_instance_id); study=self.runtime._compiled(db,session); version=db.get(StudyVersion,session.study_version_id)
        call_id = self._reserve(db,session,attempt,assessment,self.compiler.compile_judge(version,study,assessment,response),"JUDGE")
        if commit: db.commit()
        return call_id

    def _retry_call(self, db, call, commit=True):
        session=db.get(Session,call.session_id); attempt=db.get(Attempt,call.attempt_id); assessment=db.get(AssessmentInstance,call.assessment_instance_id) if call.assessment_instance_id else None
        version=db.get(StudyVersion,session.study_version_id); messages=tuple(CanonicalMessage.model_validate(x) for x in call.request_payload["messages"]); model={"TUTOR":TutorTurnOutput,"ASSESSMENT":AssessmentGenerationOutput,"JUDGE":JudgeOutput}[call.purpose]
        envelope=self.compiler._envelope(call.purpose,version,list(messages),model,call.request_payload.get("audit_context",{}))
        new_id=self._reserve(db,session,attempt,assessment,envelope,call.purpose,call.retry_group_id,call.retry_number+1)
        if call.purpose=="ASSESSMENT": assessment.generation_llm_call_id=new_id
        if commit: db.commit()
        return new_id

    def reserve_manual_retry(self, db, session_id, commit=True):
        call=db.scalar(select(LLMCall).where(LLMCall.session_id==session_id,LLMCall.status.in_(["STARTED","RECEIVED","FAILED","INVALID_OUTPUT"])).order_by(LLMCall.started_at.desc()))
        if not call: raise ValueError("no retryable operation")
        if call.status=="RECEIVED": return call.id
        if call.status=="STARTED":
            cutoff=timedelta(seconds=self.settings.llm_request_timeout_seconds+self.settings.llm_stale_grace_seconds)
            if datetime.now(timezone.utc)-call.started_at < cutoff: raise ValueError("operation is still running")
            call.status="FAILED"; call.error_class="PROCESS_INTERRUPTED"; call.error_message="Operation did not complete before process restart."; call.completed_at=datetime.now(timezone.utc)
        return self._retry_call(db,call,commit=commit)

    async def execute(self, db, call_id):
        call=db.get(LLMCall,call_id)
        if not call or call.status not in ("STARTED","RECEIVED"): return
        if call.status=="STARTED" and not await self._receive(db,call):
            if call.purpose=="JUDGE" and call.retry_number==0: return await self.execute(db,self._retry_call(db,call))
            return
        call=db.get(LLMCall,call_id); session=db.get(Session,call.session_id); attempt=db.get(Attempt,call.attempt_id); study=self.runtime._compiled(db,session)
        try:
            if call.purpose=="TUTOR":
                output=TutorTurnOutput.model_validate(_decode_json_text(self._candidate(call))); cell=study.cells[f"{attempt.transition_id}:{attempt.pedagogy_id}"]
                if output.current_move_id not in cell["move_ids"] or (output.next_move_id and output.next_move_id not in cell["move_ids"]): raise ValueError("Tutor returned a move outside the assigned cell")
                if output.disposition=="COMPLETE" and not db.scalar(select(Message.id).where(Message.attempt_id==attempt.id,Message.role=="LEARNER").limit(1)): raise ValueError("opening turn cannot complete")
                call.parsed_response=output.model_dump(mode="json"); call.status="SUCCEEDED"; call.completed_at=datetime.now(timezone.utc)
                seq=(db.scalar(select(Message.sequence_no).where(Message.attempt_id==attempt.id).order_by(Message.sequence_no.desc())) or 0)+1
                trace={"current_move_id":output.current_move_id,"next_move_id":output.next_move_id,"progress_summary":output.progress_summary}
                db.add(Message(attempt_id=attempt.id,sequence_no=seq,role="TUTOR",content_text=output.learner_message,content_format="markdown",llm_call_id=call.id,instructional_trace=trace,material_ids=[],exposed_kc_ids=[],exposed_relation_ids=[])); db.flush()
                count=len(db.scalars(select(Message.id).where(Message.attempt_id==attempt.id,Message.role=="TUTOR")).all()); done=output.disposition=="COMPLETE" or count>=cell["max_tutor_turns"]
                self.runtime._event(db,session,"TUTOR_TURN_COMPLETED",{"disposition":"COMPLETE" if done else "CONTINUE","move_id":output.current_move_id},attempt.id)
                if done:
                    assessment=self.runtime.complete_intervention(db,session.id,"TUTOR_COMPLETE" if output.disposition=="COMPLETE" else "BUDGET_EXHAUSTED",commit=False)
                    return await self.execute(db,self.reserve_assessment(db,session.id,assessment.id,commit=True))
                db.commit()
            elif call.purpose=="ASSESSMENT":
                output=AssessmentGenerationOutput.model_validate(_decode_json_text(self._candidate(call))); assessment=db.get(AssessmentInstance,call.assessment_instance_id)
                lowered=output.learner_prompt.lower()
                normalized=lambda text: " ".join(re.findall(r"[a-z0-9]+", text.lower()))
                leaked_feature=any(len(normalized(feature).split())>=4 and normalized(feature) in normalized(output.learner_prompt) for feature in assessment.blueprint_snapshot["required_response_features"])
                if leaked_feature or any(marker in lowered for marker in ("expected answer", "expected relationship", "answer key", "scoring criteria", "required features", "specifically address")):
                    raise ValueError("generated learner prompt leaks hidden answer or scoring material")
                call.parsed_response=output.model_dump(mode="json"); call.status="SUCCEEDED"; call.completed_at=datetime.now(timezone.utc); assessment.prompt_snapshot=output.learner_prompt; assessment.hidden_scoring_context_snapshot=output.hidden_scoring_context; assessment.generation_llm_call_id=call.id; assessment.status="ACTIVE"; attempt.status="ASSESSMENT_ACTIVE"; session.phase="ASSESSMENT_ACTIVE"; self.runtime._event(db,session,"ASSESSMENT_GENERATED",{"assessment_id":str(assessment.id),"call_id":str(call.id)},attempt.id); db.commit()
            else:
                assessment=db.get(AssessmentInstance,call.assessment_instance_id); response=db.scalar(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id==assessment.id)); output=JudgeOutput.model_validate(_decode_json_text(self._candidate(call))); scoped=self.compiler.resolver.judge(study,assessment); rubric=scoped["rubric"]
                allowed_states=set(study.knowledge_slices[attempt.transition_id]["transition"]["state_order"])
                if output.observed_solo_state_id and output.observed_solo_state_id not in allowed_states: raise ValueError("Judge returned an unknown SOLO state")
                criterion={x.criterion_id for x in output.criterion_evidence}; misconceptions={x.misconception_id for x in output.misconception_evidence}
                if output.gradable and criterion!=set(rubric["evidence_ids"]): raise ValueError("Judge criterion evidence is incomplete")
                if output.gradable and misconceptions!=set(rubric["blocking_misconception_ids"]): raise ValueError("Judge misconception evidence is incomplete")
                normalize_excerpt=lambda value: " ".join(unicodedata.normalize("NFKC",value).split())
                normalized_response=normalize_excerpt(response.response_text)
                for evidence in (*output.criterion_evidence,*output.misconception_evidence):
                    if any(normalize_excerpt(c.excerpt) not in normalized_response for c in evidence.citations): raise ValueError("Judge citation is not grounded")
                demonstrated=tuple(x.criterion_id for x in output.criterion_evidence if x.status=="DEMONSTRATED"); detected=tuple(x.misconception_id for x in output.misconception_evidence if x.status=="DETECTED")
                transition=study.knowledge_slices[attempt.transition_id]["transition"]
                call.parsed_response=output.model_dump(mode="json"); call.status="SUCCEEDED"; call.completed_at=datetime.now(timezone.utc); db.flush()
                observation=JudgeObservation(output.gradable,output.correctness,output.observed_solo_state_id,demonstrated,detected)
                self.runtime.apply_judgment(db,session.id,observation,call.id,output.model_dump(mode="json"))
        except (ValidationError,ValueError,json.JSONDecodeError) as exc:
            self._invalidate(db,call,exc)
            if call.purpose=="JUDGE" and call.retry_number==0: return await self.execute(db,self._retry_call(db,call))
