"""Persist v0.5.1 subsection delivery state.

Revision ID: 0009_v051_subsection_lifecycle
Revises: 0008_paas_mental_effort
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "0009_v051_subsection_lifecycle"
down_revision = "0008_paas_mental_effort"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "subsection_progress" in inspect(bind).get_table_names():
        return
    op.create_table(
        "subsection_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attempts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subsection_id", sa.String(), nullable=False),
        sa.Column("order_in_attempt", sa.Integer(), nullable=False),
        sa.Column("pedagogy_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("required_move_ids", sa.JSON(), nullable=False),
        sa.Column("required_content_ids", sa.JSON(), nullable=False),
        sa.Column("move_evidence", sa.JSON(), nullable=False),
        sa.Column("content_evidence", sa.JSON(), nullable=False),
        sa.Column("clarification_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("instructional_state", sa.JSON(), nullable=False),
        sa.Column("delivery_exception", sa.JSON()),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("core_delivered_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("attempt_id", "subsection_id"),
        sa.UniqueConstraint("attempt_id", "order_in_attempt"),
    )
    op.create_index("ix_subsection_progress_attempt_status", "subsection_progress", ["attempt_id", "status"])


def downgrade():
    bind = op.get_bind()
    if "subsection_progress" in inspect(bind).get_table_names():
        op.drop_index("ix_subsection_progress_attempt_status", table_name="subsection_progress")
        op.drop_table("subsection_progress")
