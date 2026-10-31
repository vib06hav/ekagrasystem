from alembic import command
from alembic.config import Config

from solo_harness.config import Settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import ActiveStudyVersion
from solo_harness.studies.activation import activate
from solo_harness.studies.catalog import StudyCatalog
from solo_harness.studies.scientific_v04 import load_scientific_v04
from solo_harness.studies.v04_native_compiler import compile_v04


def bootstrap(settings: Settings) -> StudyCatalog:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
    if not (settings.study_dir / "08_SCIENTIFIC_YAML").is_dir():
        raise RuntimeError("only the authoritative F1 v0.4 scientific source may be activated")
    scientific = load_scientific_v04(settings.study_dir)
    compiled = compile_v04(scientific)
    bundle = {"schema_version": "v04.0", "files": {name: {"sha256": digest}
              for name, digest in scientific.source_hashes.items()}}
    factory = make_session_factory(settings.database_url)
    with factory() as db:
        existing = db.get(ActiveStudyVersion, compiled.study_id)
        if existing is None or settings.activate_study_on_bootstrap:
            activate(db, compiled, bundle)
    return StudyCatalog()
