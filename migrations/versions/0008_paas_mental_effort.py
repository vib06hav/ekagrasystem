"""Add a once-per-attempt versioned Paas mental-effort response.

Revision ID: 0008_paas_mental_effort
Revises: 0007_phase2_b3
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0008_paas_mental_effort"
down_revision = "0007_phase2_b3"
branch_labels = None
depends_on = None


def upgrade():
    if "paas_responses" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "paas_responses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), sa.ForeignKey("attempts.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("transition_id", sa.String(), nullable=False),
        sa.Column("pedagogy_id", sa.String(), nullable=False),
        sa.Column("completion_reason", sa.String(), nullable=False),
        sa.Column("instrument_id", sa.String(), nullable=False),
        sa.Column("instrument_version", sa.String(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("question_snapshot", sa.Text(), nullable=False),
        sa.Column("anchors_snapshot", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("rating BETWEEN 1 AND 9", name="ck_paas_rating_1_9"),
    )
    op.create_index("ix_paas_responses_session_id", "paas_responses", ["session_id"])


def downgrade():
    if "paas_responses" in inspect(op.get_bind()).get_table_names():
        op.drop_index("ix_paas_responses_session_id", table_name="paas_responses")
        op.drop_table("paas_responses")
