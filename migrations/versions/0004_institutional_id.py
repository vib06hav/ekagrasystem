"""Name the direct participant identifier accurately."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_institutional_id"
down_revision = "0003_participant_ui_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0001 bootstraps clean databases from current metadata. Rename only when
    # upgrading an older database that still has the legacy column.
    columns = {item["name"] for item in inspect(op.get_bind()).get_columns("sessions")}
    if "participant_code" in columns and "institutional_id" not in columns:
        op.alter_column("sessions", "participant_code", new_column_name="institutional_id", existing_type=sa.String(), existing_nullable=True)


def downgrade() -> None:
    columns = {item["name"] for item in inspect(op.get_bind()).get_columns("sessions")}
    if "institutional_id" in columns and "participant_code" not in columns:
        op.alter_column("sessions", "institutional_id", new_column_name="participant_code", existing_type=sa.String(), existing_nullable=True)
