from alembic import command
from alembic.config import Config
from sqlalchemy import text

from solo_harness.config import Settings
from solo_harness.db.engine import make_session_factory
from solo_harness.studies.activation import activate
from solo_harness.studies.catalog import StudyCatalog
from solo_harness.studies.compiler import compile_study
from solo_harness.studies.loader import load
from solo_harness.studies.validation import validate


def bootstrap(settings: Settings) -> StudyCatalog:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
    study = load(settings.study_dir)
    validate(study)
    compiled = compile_study(study)
    factory = make_session_factory(settings.database_url)
    with factory() as db:
        activate(db, compiled)
    return StudyCatalog()
