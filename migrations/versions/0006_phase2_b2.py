"""Persist frozen Phase 2 B1 packages and structured B2 responses.

Revision ID: 0006_phase2_b2
Revises: 0005_capture_run_id
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_phase2_b2"
down_revision = "0005_capture_run_id"
branch_labels = None
depends_on = None


def _add(table, column):
    if column.name not in {item["name"] for item in inspect(op.get_bind()).get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    _add("assessment_instances", sa.Column("frozen_public_snapshot", sa.JSON(), nullable=True))
    _add("assessment_instances", sa.Column("frozen_private_snapshot", sa.JSON(), nullable=True))
    _add("assessment_instances", sa.Column("frozen_package_fingerprint", sa.String(length=64), nullable=True))
    _add("assessment_instances", sa.Column("frozen_schema_version", sa.String(), nullable=True))
    _add("assessment_instances", sa.Column("frozen_metadata_snapshot", sa.JSON(), nullable=True))
    _add("assessment_instances", sa.Column("delivery_status", sa.String(), nullable=True))
    _add("assessment_instances", sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True))
    _add("assessment_responses", sa.Column("structured_response", sa.JSON(), nullable=True))
    _add("assessment_responses", sa.Column("response_schema_version", sa.String(), nullable=True))


def downgrade() -> None:
    for table, name in (("assessment_responses", "response_schema_version"), ("assessment_responses", "structured_response"),
                        ("assessment_instances", "frozen_at"), ("assessment_instances", "delivery_status"),
                        ("assessment_instances", "frozen_metadata_snapshot"), ("assessment_instances", "frozen_schema_version"),
                        ("assessment_instances", "frozen_package_fingerprint"), ("assessment_instances", "frozen_private_snapshot"),
                        ("assessment_instances", "frozen_public_snapshot")):
        if name in {item["name"] for item in inspect(op.get_bind()).get_columns(table)}:
            op.drop_column(table, name)
