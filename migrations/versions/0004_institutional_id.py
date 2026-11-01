"""Name the direct participant identifier accurately."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_institutional_id"
down_revision = "0003_participant_ui_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0001 builds the schema from the current models, so a fresh database already has the new name.
    if "participant_code" not in {c["name"] for c in inspect(op.get_bind()).get_columns("sessions")}:
        return
    op.alter_column("sessions", "participant_code", new_column_name="institutional_id", existing_type=sa.String(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("sessions", "institutional_id", new_column_name="participant_code", existing_type=sa.String(), existing_nullable=True)
