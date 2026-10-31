import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from solo_harness.db.base import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class StudyVersion(Base):
    __tablename__ = "study_versions"
    id: Mapped[uuid.UUID] = uuid_pk()
    study_id: Mapped[str] = mapped_column(String, nullable=False)
    content_version: Mapped[str] = mapped_column(String, nullable=False)
    study_schema_version: Mapped[str] = mapped_column(String, nullable=False)
    content_canonicalization_version: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_authored_definition: Mapped[bytes] = mapped_column(nullable=False)
    source_bundle: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    compiler_contract_version: Mapped[str] = mapped_column(String, nullable=False)
    snapshot_schema_version: Mapped[str] = mapped_column(String, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    compiled_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (
        UniqueConstraint("study_id", "content_version", "compiler_contract_version", "snapshot_schema_version"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("snapshot_hash ~ '^[0-9a-f]{64}$'"),
        Index("ix_study_versions_study_content", "study_id", "content_hash"),
    )


class ActiveStudyVersion(Base):
    __tablename__ = "active_study_versions"
    study_id: Mapped[str] = mapped_column(String, primary_key=True)
    study_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("study_versions.id", ondelete="RESTRICT"), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    activated_by: Mapped[str | None] = mapped_column(String)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = uuid_pk()
    institutional_id: Mapped[str | None] = mapped_column(String, unique=True)
    capture_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)
    study_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("study_versions.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    phase: Mapped[str] = mapped_column(String, nullable=False)
    formal_state_id: Mapped[str] = mapped_column(String, nullable=False)
    current_transition_id: Mapped[str | None] = mapped_column(String)
    current_attempt_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("attempts.id", ondelete="RESTRICT", use_alter=True, name="fk_sessions_current_attempt"))
    current_attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    terminal_reason: Mapped[str | None] = mapped_column(String)
    lock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_event_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    application_build_id: Mapped[str] = mapped_column(String, nullable=False)
    runtime_config_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False)
    transition_id: Mapped[str] = mapped_column(String, nullable=False)
    sequence_in_transition: Mapped[int] = mapped_column(Integer, nullable=False)
    pedagogy_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    formal_state_before_id: Mapped[str] = mapped_column(String, nullable=False)
    formal_state_after_id: Mapped[str | None] = mapped_column(String)
    completion_reason: Mapped[str | None] = mapped_column(String)
    passed: Mapped[bool | None] = mapped_column(Boolean)
    outcome_details: Mapped[dict | None] = mapped_column(JSON)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    intervention_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    intervention_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("session_id", "transition_id", "sequence_in_transition"), UniqueConstraint("session_id", "transition_id", "pedagogy_id"))


class LearnerHistorySnapshot(Base):
    __tablename__ = "learner_history_snapshots"
    id: Mapped[uuid.UUID] = uuid_pk(); session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    target_attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("attempts.id"), nullable=False, unique=True)
    transition_id: Mapped[str] = mapped_column(String, nullable=False); source_attempt_ids: Mapped[list[str]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False); generation_method: Mapped[str] = mapped_column(String, nullable=False)
    llm_call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True)); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[uuid.UUID] = uuid_pk(); attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("attempts.id"), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False); role: Mapped[str] = mapped_column(String, nullable=False); content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_format: Mapped[str] = mapped_column(String, nullable=False, default="markdown"); llm_call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    instructional_trace: Mapped[dict | None] = mapped_column(JSON); material_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    exposed_kc_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list); exposed_relation_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("attempt_id", "sequence_no"),)


class AssessmentInstance(Base):
    __tablename__ = "assessment_instances"
    id: Mapped[uuid.UUID] = uuid_pk(); session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("attempts.id"), nullable=False); transition_id: Mapped[str] = mapped_column(String, nullable=False)
    assessment_family_id: Mapped[str] = mapped_column(String, nullable=False); assessment_form_id: Mapped[str] = mapped_column(String, nullable=False); status: Mapped[str] = mapped_column(String, nullable=False)
    candidate_form_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False); selection_method: Mapped[str] = mapped_column(String, nullable=False); selection_audit: Mapped[dict] = mapped_column(JSON, nullable=False)
    blueprint_snapshot: Mapped[dict | None] = mapped_column(JSON)
    resolved_component_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    generation_llm_call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    prompt_snapshot: Mapped[str | None] = mapped_column(Text); hidden_scoring_context_snapshot: Mapped[str | None] = mapped_column(Text)
    # v0.4 keeps the complete package immutable on the server and exposes only
    # frozen_public_snapshot to the participant view.
    frozen_public_snapshot: Mapped[dict | None] = mapped_column(JSON)
    frozen_private_snapshot: Mapped[dict | None] = mapped_column(JSON)
    frozen_package_fingerprint: Mapped[str | None] = mapped_column(String(64))
    frozen_schema_version: Mapped[str | None] = mapped_column(String)
    frozen_metadata_snapshot: Mapped[dict | None] = mapped_column(JSON)
    delivery_status: Mapped[str | None] = mapped_column(String)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False); submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True)); closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("attempt_id"), UniqueConstraint("session_id", "assessment_form_id"))


class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"
    id: Mapped[uuid.UUID] = uuid_pk(); assessment_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_instances.id"), nullable=False, unique=True)
    response_text: Mapped[str] = mapped_column(Text, nullable=False); response_format: Mapped[str] = mapped_column(String, nullable=False); submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False); client_action_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    structured_response: Mapped[dict | None] = mapped_column(JSON)
    response_schema_version: Mapped[str | None] = mapped_column(String)


class V04Evaluation(Base):
    """One private immutable F1 v0.4 result per frozen learner response."""
    __tablename__ = "phase2_evaluations"
    id: Mapped[uuid.UUID] = uuid_pk(); assessment_response_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_responses.id"), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String, nullable=False); mcq_results: Mapped[dict | None] = mapped_column(JSON); mcq_score: Mapped[int | None] = mapped_column(Integer)
    subjective_score: Mapped[int | None] = mapped_column(Integer); judge_findings: Mapped[dict | None] = mapped_column(JSON); judge_llm_call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("llm_calls.id"))
    evaluation_version: Mapped[str] = mapped_column(String, nullable=False); passed: Mapped[bool | None] = mapped_column(Boolean); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False); finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LLMCall(Base):
    __tablename__ = "llm_calls"
    id: Mapped[uuid.UUID] = uuid_pk(); session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("attempts.id")); assessment_instance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_instances.id"))
    purpose: Mapped[str] = mapped_column(String, nullable=False); status: Mapped[str] = mapped_column(String, nullable=False); retry_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False); retry_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False); model: Mapped[str] = mapped_column(String, nullable=False); provider_request_id: Mapped[str | None] = mapped_column(String)
    generation_parameters: Mapped[dict] = mapped_column(JSON, nullable=False); compiled_prompt_text: Mapped[str | None] = mapped_column(Text); request_payload: Mapped[dict] = mapped_column(JSON, nullable=False); request_body_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response_text: Mapped[str | None] = mapped_column(Text); response_payload: Mapped[dict | None] = mapped_column(JSON); parsed_response: Mapped[dict | None] = mapped_column(JSON); error_class: Mapped[str | None] = mapped_column(String); error_message: Mapped[str | None] = mapped_column(Text)
    input_tokens: Mapped[int | None] = mapped_column(Integer); output_tokens: Mapped[int | None] = mapped_column(Integer); total_tokens: Mapped[int | None] = mapped_column(Integer); latency_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False); completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("retry_group_id", "retry_number"),)


class Judgment(Base):
    __tablename__ = "judgments"
    id: Mapped[uuid.UUID] = uuid_pk(); assessment_response_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_responses.id"), nullable=False, unique=True); llm_call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("llm_calls.id"), nullable=False, unique=True)
    rubric_id: Mapped[str] = mapped_column(String, nullable=False); gradable: Mapped[bool] = mapped_column(Boolean, nullable=False); correctness: Mapped[str] = mapped_column(String, nullable=False); observed_solo_state_id: Mapped[str | None] = mapped_column(String)
    kc_evidence: Mapped[dict] = mapped_column(JSON, nullable=False); relation_evidence: Mapped[dict] = mapped_column(JSON, nullable=False); misconception_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False); evidence_summary: Mapped[dict] = mapped_column(JSON, nullable=False); confidence: Mapped[float | None] = mapped_column(); ambiguity: Mapped[dict | None] = mapped_column(JSON); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RubricEvaluation(Base):
    __tablename__ = "rubric_evaluations"
    id: Mapped[uuid.UUID] = uuid_pk(); judgment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("judgments.id"), nullable=False, unique=True); attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("attempts.id"), nullable=False, unique=True)
    transition_id: Mapped[str] = mapped_column(String, nullable=False); rubric_id: Mapped[str] = mapped_column(String, nullable=False); rule_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False); input_evidence_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False); passed: Mapped[bool] = mapped_column(Boolean, nullable=False); decision_reasons: Mapped[dict] = mapped_column(JSON, nullable=False); formal_state_before_id: Mapped[str] = mapped_column(String, nullable=False); formal_state_after_id: Mapped[str] = mapped_column(String, nullable=False); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ProtocolEvent(Base):
    __tablename__ = "protocol_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True); session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False); sequence_no: Mapped[int] = mapped_column(Integer, nullable=False); event_type: Mapped[str] = mapped_column(String, nullable=False); event_version: Mapped[int] = mapped_column(Integer, nullable=False); attempt_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True)); actor: Mapped[str] = mapped_column(String, nullable=False); correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False); payload: Mapped[dict] = mapped_column(JSON, nullable=False); occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint("session_id", "sequence_no"),)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    id: Mapped[uuid.UUID] = uuid_pk(); session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False); action_type: Mapped[str] = mapped_column(String, nullable=False); idempotency_key: Mapped[str] = mapped_column(String, nullable=False); request_hash: Mapped[str] = mapped_column(String(64), nullable=False); result_object_type: Mapped[str | None] = mapped_column(String); result_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True)); response_snapshot: Mapped[dict | None] = mapped_column(JSON); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False); expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("session_id", "action_type", "idempotency_key"),)


class ParticipantUIEvent(Base):
    __tablename__ = "participant_ui_events"
    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("attempts.id"))
    assessment_instance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_instances.id"))
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    client_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    client_performance_ms: Mapped[float] = mapped_column(Float, nullable=False)
    performance_time_origin_ms: Mapped[float] = mapped_column(Float, nullable=False)
    browser_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    client_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    section_number: Mapped[int | None] = mapped_column(Integer)
    teaching_activity_number: Mapped[int | None] = mapped_column(Integer)
    surface: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    server_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (UniqueConstraint("session_id", "browser_run_id", "client_sequence"),)
