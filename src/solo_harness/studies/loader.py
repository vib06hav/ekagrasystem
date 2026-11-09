"""Version-aware study source loading and compilation entry points."""
from pathlib import Path

from solo_harness.studies.scientific_v04 import load_scientific_v04
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v04_native_compiler import compile_v04
from solo_harness.studies.v051_native_compiler import compile_v051


def load_scientific(root: Path):
    version = root.name
    if version == "v0.4":
        return load_scientific_v04(root)
    if version == "v0.5":
        return load_scientific_v051(root)
    raise ValueError(f"unsupported study source version directory: {version}")


def compile_scientific(scientific):
    return compile_v051(scientific) if scientific.content_version == "v0.5" else compile_v04(scientific)


def source_bundle(scientific) -> dict:
    return {"schema_version": scientific.content_version, "files": {name: {"sha256": digest} for name, digest in scientific.source_hashes.items()}}
