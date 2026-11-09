from alembic import command
from alembic.config import Config

from solo_harness.config import Settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import ActiveStudyVersion
from solo_harness.studies.activation import activate
from solo_harness.studies.catalog import StudyCatalog
from solo_harness.studies.loader import compile_scientific, load_scientific, source_bundle


def bootstrap(settings: Settings) -> StudyCatalog:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
    scientific = load_scientific(settings.study_dir)
    compiled = compile_scientific(scientific)
    bundle = source_bundle(scientific)
    factory = make_session_factory(settings.database_url)
    with factory() as db:
        existing = db.get(ActiveStudyVersion, compiled.study_id)
        if scientific.content_version == "v0.5.1":
            activate(db, compiled, bundle, make_active=False)
        elif existing is None or settings.activate_study_on_bootstrap:
            activate(db, compiled, bundle)
    return StudyCatalog()
