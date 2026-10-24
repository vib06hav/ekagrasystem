"""Name the direct participant identifier accurately."""
from alembic import op
import sqlalchemy as sa

revision = "0004_institutional_id"
down_revision = "0003_participant_ui_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("sessions", "participant_code", new_column_name="institutional_id", existing_type=sa.String(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("sessions", "institutional_id", new_column_name="participant_code", existing_type=sa.String(), existing_nullable=True)
