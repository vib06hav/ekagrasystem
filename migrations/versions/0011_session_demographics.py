"""Store optional participant demographics on the research session.

Nullable columns preserve every pre-existing session and internal test session.
"""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa

revision = "0011_session_demographics"
down_revision = "0010_v051_conversation_judge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {row["name"] for row in inspect(op.get_bind()).get_columns("sessions")}
    for name, column_type in (
        ("age", sa.Integer()),
        ("gender", sa.String(length=16)),
        ("educational_qualification", sa.String(length=32)),
    ):
        if name not in columns:
            op.add_column("sessions", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    columns = {row["name"] for row in inspect(op.get_bind()).get_columns("sessions")}
    for name in ("educational_qualification", "gender", "age"):
        if name in columns:
            op.drop_column("sessions", name)
