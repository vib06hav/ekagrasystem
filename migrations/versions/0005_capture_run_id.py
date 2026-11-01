"""Bind a scientific session to at most one capture run."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0005_capture_run_id"
down_revision = "0004_institutional_id"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 0001 builds the schema from the current models, so a fresh database already has this column.
    if "capture_run_id" in {c["name"] for c in inspect(op.get_bind()).get_columns("sessions")}:
        return
    op.add_column("sessions", sa.Column("capture_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_unique_constraint("uq_sessions_capture_run_id", "sessions", ["capture_run_id"])

def downgrade() -> None:
    op.drop_constraint("uq_sessions_capture_run_id", "sessions", type_="unique")
    op.drop_column("sessions", "capture_run_id")
