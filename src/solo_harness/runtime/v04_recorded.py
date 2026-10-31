"""Durable per-model-call bridge for the single v0.4 assessment lifecycle.

This is infrastructure for runtime/ai.py, NOT a new application or route.
Every writer/reviewer response gets its own LLMCall row and an exact redacted
provider request/response audit; accepted items are DB-checkpointed before the
next model call. Caller controls the outer AssessmentInstance state machine.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select

from solo_harness.db.models import AssessmentInstance, Attempt, Session, LLMCall
from solo_harness.runtime.ai import AIExecutionRuntime, PreparedLLMRequest, _decode
from solo_harness.runtime.v04_assessment import RecordedResult


class PersistedModelInvoker:
    """Scope to one current session/attempt/assessment, shared real/fake transport."""

    def __init__(self, db, ai: AIExecutionRuntime, session_id, assessment_id):
        self.db = db
        self.ai = ai
        self.session_id = session_id
        self.assessment_id = assessment_id

    async def __call__(self, role: str, messages: tuple, schema: type[BaseModel], audit: dict[str, Any]) -> RecordedResult:
        db = self.db
        session = db.scalar(select(Session).where(Session.id == self.session_id))
        if session is None or not session.current_attempt_id:
            raise ValueError("no active frozen-science session")
        attempt = db.get(Attempt, session.current_attempt_id)
        assessment = db.get(AssessmentInstance, self.assessment_id)
        if not attempt or not assessment or assessment.attempt_id != attempt.id or assessment.status != "GENERATING":
            raise ValueError("assessment generation is not active")
        expected_audit = {"v04": True, **audit}
        # Recovery re-enters the constructor after a process failure.  Reuse a
        # durable received/applied role output for this exact constructor step;
        # it is already an audited provider response and must never be sent again.
        prior = next((row for row in db.scalars(select(LLMCall).where(
            LLMCall.assessment_instance_id == assessment.id, LLMCall.purpose == role
        ).order_by(LLMCall.started_at.desc())).all()
            if (row.request_payload or {}).get("audit") == expected_audit and row.status in ("RECEIVED", "SUCCEEDED")), None)
        if prior is not None:
            if prior.status == "RECEIVED":
                await self.ai._finalize_received(db, prior.id)
                prior = db.get(LLMCall, prior.id)
            if prior.status == "SUCCEEDED" and prior.parsed_response is not None:
                return RecordedResult(call_id=str(prior.id), parsed=schema.model_validate(prior.parsed_response))
        call_id = self.ai._reserve(db, session, attempt, assessment, role, messages, schema,
                                   expected_audit)
        db.commit()  # The actual provider call must not begin before this durable audit row exists.
        call = db.get(LLMCall, call_id)
        request = self.ai._request(role, messages, call.model, schema, audit)
        prepared = PreparedLLMRequest(request, json.loads(call.request_body_text), call.request_body_text,
                                      {"Authorization": "Bearer [REDACTED]"})
        try:
            raw = await self.ai.client.send(prepared)
        except Exception as exc:
            # No provider response was persisted.  This is a transport failure
            # and a later build retry may safely issue a new request.
            call.status = "FAILED"
            call.error_class = "LLM_TRANSPORT_FAILURE"
            call.error_message = str(exc)[:4000]
            call.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise
        call.provider_request_id = raw.provider_request_id
        call.raw_response_text = raw.raw_response_text
        call.response_payload = raw.response_payload
        call.latency_ms = raw.latency_ms
        call.input_tokens = raw.usage.get("prompt_tokens")
        call.output_tokens = raw.usage.get("completion_tokens")
        call.total_tokens = raw.usage.get("total_tokens")
        call.status = "RECEIVED"
        db.commit()
        try:
            parsed = schema.model_validate(_decode(raw.structured_candidate or raw.raw_response_text))
        except Exception as exc:
            call.status = "INVALID_OUTPUT"
            call.error_class = "VALIDATION_FAILURE"
            call.error_message = str(exc)[:4000]
            call.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise
        try:
            call.parsed_response = parsed.model_dump(mode="json")
            call.status = "SUCCEEDED"
            call.completed_at = datetime.now(timezone.utc)
            db.commit()
            return RecordedResult(call_id=str(call.id), parsed=parsed)
        except Exception as exc:
            # A valid provider response was committed before local persistence
            # failed.  Preserve its RECEIVED state for constructor recovery.
            db.rollback()
            call=db.get(LLMCall,call_id)
            if call and call.status == "RECEIVED":
                call.error_class = "APPLICATION_FAILURE"
                call.error_message = str(exc)[:4000]
            db.commit()
            raise


class AssessmentCheckpoint:
    """Pre-freeze private recovery records; never exposed by public projection."""

    def __init__(self, db, assessment_id):
        self.db, self.assessment_id = db, assessment_id

    def completed(self) -> dict:
        item = self.db.get(AssessmentInstance, self.assessment_id)
        return dict((item.frozen_metadata_snapshot or {}).get("generation_checkpoints", {}))

    async def __call__(self, label: str, record: dict) -> None:
        assessment = self.db.scalar(select(AssessmentInstance).where(
            AssessmentInstance.id == self.assessment_id).with_for_update())
        if assessment is None or assessment.status != "GENERATING":
            raise ValueError("cannot checkpoint non-generating assessment")
        metadata = dict(assessment.frozen_metadata_snapshot or {})
        checkpoints = dict(metadata.get("generation_checkpoints", {}))
        if label in checkpoints:
            if checkpoints[label].get("instance_id") != record.get("instance_id"):
                raise ValueError("conflicting accepted-item checkpoint")
            return
        checkpoints[label] = record
        metadata["generation_checkpoints"] = checkpoints
        assessment.frozen_metadata_snapshot = metadata
        self.db.commit()
