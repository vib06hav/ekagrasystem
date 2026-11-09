"""Persist v0.5.1 Conversation Judge decisions independently of assessment judging."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "0010_v051_conversation_judge"
down_revision = "0009_v051_subsection_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "conversation_judge_decisions" in inspect(bind).get_table_names():
        return
    op.create_table(
        "conversation_judge_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attempts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subsection_progress_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subsection_progress.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("llm_call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("llm_calls.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("latest_learner_message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="RESTRICT")),
        sa.Column("action", sa.String(), nullable=False), sa.Column("confidence", sa.String(), nullable=False), sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("application_status", sa.String(), nullable=False), sa.Column("application_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("applied_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_conversation_judge_decisions_attempt", "conversation_judge_decisions", ["attempt_id", "created_at"])


def downgrade():
    if "conversation_judge_decisions" in inspect(op.get_bind()).get_table_names():
        op.drop_index("ix_conversation_judge_decisions_attempt", table_name="conversation_judge_decisions")
        op.drop_table("conversation_judge_decisions")
