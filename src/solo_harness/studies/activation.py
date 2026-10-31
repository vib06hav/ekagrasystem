from sqlalchemy import select
from sqlalchemy.orm import Session

from solo_harness.db.models import ActiveStudyVersion, StudyVersion
from solo_harness.studies.canonicalization import COMPILER_CONTRACT_VERSION, CONTENT_CANONICALIZATION_VERSION, SNAPSHOT_SCHEMA_VERSION, content_identity, snapshot_identity
from solo_harness.studies.v04_types import CompiledStudy


def activate(db: Session, compiled: CompiledStudy, source_bundle: dict | None = None) -> StudyVersion:
    canonical, content_hash = content_identity(compiled.authored)
    snapshot = compiled.to_snapshot()
    snapshot_hash = snapshot_identity(content_hash, snapshot, COMPILER_CONTRACT_VERSION, SNAPSHOT_SCHEMA_VERSION)
    existing = db.scalar(select(StudyVersion).where(StudyVersion.snapshot_hash == snapshot_hash))
    if existing is None:
        conflict = db.scalar(select(StudyVersion).where(StudyVersion.study_id == compiled.study_id, StudyVersion.content_version == compiled.content_version, StudyVersion.content_hash != content_hash))
        if conflict:
            raise ValueError("content version collision: semantic content changed without a new content_version")
        existing = StudyVersion(study_id=compiled.study_id, content_version=compiled.content_version, study_schema_version=compiled.authored["manifest"]["study_schema_version"], content_canonicalization_version=CONTENT_CANONICALIZATION_VERSION, content_hash=content_hash, canonical_authored_definition=canonical, source_bundle=source_bundle or {"status": "NOT_CAPTURED"}, source_provenance=compiled.authored["manifest"].get("markdown_provenance", {}), compiler_contract_version=COMPILER_CONTRACT_VERSION, snapshot_schema_version=SNAPSHOT_SCHEMA_VERSION, snapshot_hash=snapshot_hash, compiled_snapshot=snapshot)
        db.add(existing); db.flush()
    pointer = db.get(ActiveStudyVersion, compiled.study_id)
    if pointer is None:
        db.add(ActiveStudyVersion(study_id=compiled.study_id, study_version_id=existing.id))
    else:
        pointer.study_version_id = existing.id
    db.commit()
    return existing
