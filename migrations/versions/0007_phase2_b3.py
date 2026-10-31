"""Persist immutable private B3 evaluation results."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007_phase2_b3"
down_revision = "0006_phase2_b2"
branch_labels = None
depends_on = None

def upgrade():
    if "phase2_evaluations" not in inspect(op.get_bind()).get_table_names():
        op.create_table("phase2_evaluations", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("assessment_response_id", sa.Uuid(), sa.ForeignKey("assessment_responses.id"), nullable=False, unique=True), sa.Column("status", sa.String(), nullable=False), sa.Column("mcq_results", sa.JSON()), sa.Column("mcq_score", sa.Integer()), sa.Column("subjective_score", sa.Integer()), sa.Column("judge_findings", sa.JSON()), sa.Column("judge_llm_call_id", sa.Uuid(), sa.ForeignKey("llm_calls.id")), sa.Column("evaluation_version", sa.String(), nullable=False), sa.Column("passed", sa.Boolean()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("finalized_at", sa.DateTime(timezone=True)))

def downgrade():
    if "phase2_evaluations" in inspect(op.get_bind()).get_table_names(): op.drop_table("phase2_evaluations")
