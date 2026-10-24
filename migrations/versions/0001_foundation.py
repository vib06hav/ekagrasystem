"""Version 0 foundation schema."""
from alembic import op
from solo_harness.db.base import Base
import solo_harness.db.models  # noqa: F401

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    for table in ("study_versions", "messages", "assessment_responses", "protocol_events", "learner_history_snapshots", "judgments", "rubric_evaluations"):
        op.execute(f"CREATE OR REPLACE FUNCTION prevent_{table}_mutation() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'immutable table: {table}'; END; $$ LANGUAGE plpgsql")
        op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION prevent_{table}_mutation()")

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
