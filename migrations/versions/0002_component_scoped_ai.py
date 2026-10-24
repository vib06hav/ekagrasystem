"""component-scoped AI operations and generated assessments

Revision ID: 0002_component_scoped_ai
Revises: 0001_foundation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_component_scoped_ai"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    # 0001 intentionally bootstraps from current metadata. IF NOT EXISTS keeps
    # a clean install valid while still upgrading databases created by the
    # original Version-0 metadata.
    op.execute("ALTER TABLE assessment_instances ADD COLUMN IF NOT EXISTS blueprint_snapshot JSON")
    op.execute("ALTER TABLE assessment_instances ADD COLUMN IF NOT EXISTS resolved_component_ids JSON NOT NULL DEFAULT '{}'::json")
    op.execute("ALTER TABLE assessment_instances ADD COLUMN IF NOT EXISTS generation_llm_call_id UUID")
    op.alter_column("assessment_instances", "prompt_snapshot", existing_type=sa.Text(), nullable=True)
    op.alter_column("assessment_instances", "hidden_scoring_context_snapshot", existing_type=sa.Text(), nullable=True)


def downgrade():
    op.execute("UPDATE assessment_instances SET prompt_snapshot = '' WHERE prompt_snapshot IS NULL")
    op.execute("UPDATE assessment_instances SET hidden_scoring_context_snapshot = '' WHERE hidden_scoring_context_snapshot IS NULL")
    op.alter_column("assessment_instances", "hidden_scoring_context_snapshot", existing_type=sa.Text(), nullable=False)
    op.alter_column("assessment_instances", "prompt_snapshot", existing_type=sa.Text(), nullable=False)
    op.drop_column("assessment_instances", "generation_llm_call_id")
    op.drop_column("assessment_instances", "resolved_component_ids")
    op.drop_column("assessment_instances", "blueprint_snapshot")
