"""participant-visible telemetry events

Revision ID: 0003_participant_ui_events
Revises: 0002_component_scoped_ai
"""
from alembic import op
from sqlalchemy import inspect

from solo_harness.db.models import ParticipantUIEvent

revision = "0003_participant_ui_events"
down_revision = "0002_component_scoped_ai"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    ParticipantUIEvent.__table__.create(bind=bind, checkfirst=True)
    op.execute("""CREATE OR REPLACE FUNCTION prevent_participant_ui_events_mutation() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'immutable table: participant_ui_events'; END; $$ LANGUAGE plpgsql""")
    op.execute("DROP TRIGGER IF EXISTS participant_ui_events_immutable ON participant_ui_events")
    op.execute("CREATE TRIGGER participant_ui_events_immutable BEFORE UPDATE OR DELETE ON participant_ui_events FOR EACH ROW EXECUTE FUNCTION prevent_participant_ui_events_mutation()")


def downgrade():
    bind = op.get_bind()
    if "participant_ui_events" in inspect(bind).get_table_names():
        ParticipantUIEvent.__table__.drop(bind=bind)
