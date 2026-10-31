"""Create an honest v0.4 deployment evidence ZIP from source and PostgreSQL."""
from __future__ import annotations
import hashlib, json, os, shutil
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts"/"EKAGRAAI_F1_V04_EVIDENCE"
SOURCE=ROOT/"studies"/"networks_error_detection_parity_f1"/"v0.4"
ACTIVE=["src/solo_harness/runtime/ai.py","src/solo_harness/runtime/v04_native.py","src/solo_harness/runtime/v04_execution.py","src/solo_harness/runtime/v04_persistence.py","src/solo_harness/studies/scientific_v04.py","src/solo_harness/studies/scientific_v04_policy.py","src/solo_harness/studies/v04_native_compiler.py","src/solo_harness/bootstrap.py","src/solo_harness/web.py","compose.yaml","Dockerfile","tests/test_v04_native.py"]

def write(name,value):
    path=OUT/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(value,encoding="utf-8")
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    files=[ROOT/x for x in ACTIVE if (ROOT/x).is_file()]
    for path in files:
        target=OUT/"deployed_source"/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
    shutil.copytree(SOURCE,OUT/"authoritative_f1_v04_source")
    write("source_sha256.json",json.dumps({str(x.relative_to(ROOT)):sha(x) for x in files},indent=2))
    write("cleanup_manifest.json",json.dumps({"removed_runtime_modules":["phase2_assessment.py","phase2_evaluation.py","phase2_persistence.py","scientific_v03_dev.py","v04_adapter.py"],"removed_generic_study_modules":["compiler.py","loader.py","validation.py","authored/models.py"],"active_study":"networks_error_detection_parity_f1/v0.4","database_history_preserved":True},indent=2))
    prompts={p.name:p.read_text(encoding="utf-8") for p in sorted((SOURCE/"07_PROMPT_CONTRACTS").glob("*.md"))}
    write("compiled_scientific_prompt_contracts.json",json.dumps(prompts,indent=2))
    database_url=os.environ.get("DATABASE_URL")
    if database_url:
        engine=create_engine(database_url)
        with engine.connect() as db:
            rows=[dict(x._mapping) for x in db.execute(text("select purpose,status,provider,model,compiled_prompt_text,raw_response_text,parsed_response from llm_calls order by started_at"))]
            sessions=[dict(x._mapping) for x in db.execute(text("select id,status,phase,formal_state_id,started_at,ended_at from sessions order by started_at"))]
        write("postgres_llm_calls.json",json.dumps(rows,default=str,indent=2)); write("postgres_sessions.json",json.dumps(sessions,default=str,indent=2))
    write("evidence_status.md","""# F1 v0.4 evidence status

This package contains the deployed v0.4 source, all authoritative scientific inputs, active route/runtime sources, cleanup manifest, hashes, and PostgreSQL records available at export time.

It deliberately does **not** claim a controlled or real-provider assessment result unless matching persisted `llm_calls` are present in `postgres_llm_calls.json`. A missing call is an unmet execution step, not a learner failure or simulated proof.
""")
    archive=shutil.make_archive(str(OUT),"zip",OUT.parent,OUT.name); print(archive)
if __name__=="__main__": main()
