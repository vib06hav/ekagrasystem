import hashlib
import json
from typing import Any


CONTENT_CANONICALIZATION_VERSION = "1"
COMPILER_CONTRACT_VERSION = "3.1"
SNAPSHOT_SCHEMA_VERSION = "3"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def content_identity(authored: dict[str, Any]) -> tuple[bytes, str]:
    payload = {"canonicalization_version": CONTENT_CANONICALIZATION_VERSION, "study": authored}
    data = canonical_bytes(payload)
    return data, sha256(data)


def snapshot_identity(content_hash: str, compiled: dict[str, Any], compiler_contract_version: str = COMPILER_CONTRACT_VERSION, snapshot_schema_version: str = SNAPSHOT_SCHEMA_VERSION) -> str:
    """Hash a snapshot using its own persisted contract identities."""
    return sha256(canonical_bytes({"content_hash": content_hash, "compiler_contract_version": compiler_contract_version, "snapshot_schema_version": snapshot_schema_version, "compiled": compiled}))
