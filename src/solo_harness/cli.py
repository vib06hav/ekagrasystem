import argparse
import json
import uuid
from pathlib import Path
from sqlalchemy import select
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.studies.catalog import StudyCatalog
from solo_harness.studies.activation import activate
from solo_harness.studies.loader import compile_scientific, load_scientific, source_bundle
from solo_harness.studies.canonicalization import content_identity, snapshot_identity
from solo_harness.research_export import inspect_session, write_session_export

def main():
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-study"); sub.add_parser("inspect-study"); sub.add_parser("register-study")
    inspect = sub.add_parser("inspect-session"); inspect.add_argument("--session-id", required=True)
    export = sub.add_parser("export-session"); export.add_argument("--session-id", required=True); export.add_argument("--output", required=True); export.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(); settings = get_settings()
    if args.command == "validate-study":
        load_scientific(settings.study_dir); print("study valid")
    elif args.command == "inspect-study":
        compiled = compile_scientific(load_scientific(settings.study_dir)); _, content_hash = content_identity(compiled.authored)
        print(json.dumps({"study_id": compiled.study_id, "content_hash": content_hash, "snapshot_hash": snapshot_identity(content_hash, compiled.to_snapshot())}, sort_keys=True))
    elif args.command == "register-study":
        scientific = load_scientific(settings.study_dir); compiled = compile_scientific(scientific)
        with make_session_factory(settings.database_url)() as db:
            candidate = bool(compiled.authored.get("v051", {}).get("candidate_only"))
            version = activate(db, compiled, source_bundle(scientific), make_active=not candidate)
        print(json.dumps({"study_version_id": str(version.id), "study_id": version.study_id, "content_version": version.content_version, "active": not candidate}, sort_keys=True))
    elif args.command == "inspect-session":
        print(json.dumps(inspect_session(settings.database_url, uuid.UUID(args.session_id)), indent=2, sort_keys=True))
    else:
        document = write_session_export(settings.database_url, uuid.UUID(args.session_id), Path(args.output), overwrite=args.overwrite, research_data_root=settings.research_data_dir)
        print(json.dumps({"output": str(Path(args.output).resolve()), "data_sha256": document["data_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
