"""Bind a scientific session to at most one capture run."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "0005_capture_run_id"
down_revision = "0004_institutional_id"
branch_labels = None
depends_on = None

def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns("sessions")}
    if "capture_run_id" not in columns:
        op.add_column("sessions", sa.Column("capture_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    constraints = {item["name"] for item in inspect(op.get_bind()).get_unique_constraints("sessions")}
    if "uq_sessions_capture_run_id" not in constraints:
        op.create_unique_constraint("uq_sessions_capture_run_id", "sessions", ["capture_run_id"])

def downgrade() -> None:
    inspector = inspect(op.get_bind())
    constraints = {item["name"] for item in inspector.get_unique_constraints("sessions")}
    if "uq_sessions_capture_run_id" in constraints:
        op.drop_constraint("uq_sessions_capture_run_id", "sessions", type_="unique")
    columns = {item["name"] for item in inspect(op.get_bind()).get_columns("sessions")}
    if "capture_run_id" in columns:
        op.drop_column("sessions", "capture_run_id")
