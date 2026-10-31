from sqlalchemy.orm import Session
from solo_harness.db.models import ActiveStudyVersion, StudyVersion
from solo_harness.studies.canonicalization import snapshot_identity
from solo_harness.studies.v04_types import CompiledStudy


class StudyCatalog:
    def __init__(self): self._cache: dict[str, CompiledStudy] = {}
    def load(self, db: Session, study_version_id) -> CompiledStudy:
        key = str(study_version_id)
        if key not in self._cache:
            version = db.get(StudyVersion, study_version_id)
            if version is None: raise KeyError("unknown StudyVersion")
            if snapshot_identity(version.content_hash, version.compiled_snapshot, version.compiler_contract_version, version.snapshot_schema_version) != version.snapshot_hash: raise ValueError("compiled snapshot hash mismatch")
            self._cache[key] = CompiledStudy.from_snapshot(version.compiled_snapshot)
        return self._cache[key]
    def active(self, db: Session, study_id: str) -> CompiledStudy:
        pointer = db.get(ActiveStudyVersion, study_id)
        if pointer is None: raise KeyError("no active StudyVersion")
        return self.load(db, pointer.study_version_id)
