import argparse
import json
import uuid
from pathlib import Path
from sqlalchemy import select
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.studies.catalog import StudyCatalog
from solo_harness.studies.compiler import compile_study
from solo_harness.studies.loader import load
from solo_harness.studies.validation import validate
from solo_harness.studies.canonicalization import content_identity, snapshot_identity
from solo_harness.research_export import inspect_session, write_session_export

def main():
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-study"); sub.add_parser("inspect-study")
    inspect = sub.add_parser("inspect-session"); inspect.add_argument("--session-id", required=True)
    export = sub.add_parser("export-session"); export.add_argument("--session-id", required=True); export.add_argument("--output", required=True); export.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(); settings = get_settings()
    if args.command == "validate-study":
        study = load(settings.study_dir); validate(study); print("study valid")
    elif args.command == "inspect-study":
        study = load(settings.study_dir); validate(study)
        compiled = compile_study(study); _, content_hash = content_identity(compiled.authored)
        print(json.dumps({"study_id": compiled.study_id, "content_hash": content_hash, "snapshot_hash": snapshot_identity(content_hash, compiled.to_snapshot())}, sort_keys=True))
    elif args.command == "inspect-session":
        print(json.dumps(inspect_session(settings.database_url, uuid.UUID(args.session_id)), indent=2, sort_keys=True))
    else:
        document = write_session_export(settings.database_url, uuid.UUID(args.session_id), Path(args.output), overwrite=args.overwrite, research_data_root=settings.research_data_dir)
        print(json.dumps({"output": str(Path(args.output).resolve()), "data_sha256": document["data_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
