import importlib.util
import json
import uuid
from pathlib import Path


MODULE = Path(__file__).parents[1] / "tools/research/reconstruct_session.py"
spec = importlib.util.spec_from_file_location("reconstruct_session", MODULE)
reconstruct = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(reconstruct)


def minimal_export(session_id, capture_run_id=None):
    return {
        "session_id": str(session_id),
        "data": {
            "session": {"id": str(session_id), "capture_run_id": str(capture_run_id) if capture_run_id else None, "status": "ACTIVE", "created_at": "2026-10-24T10:00:00+05:30", "started_at": None, "ended_at": None},
            "study_version": {"compiled_snapshot": {"protocol": {"transition_ids": ["C1", "C2", "C3", "C4"]}}},
            "attempts": [], "protocol_events": [], "messages": [], "assessment_instances": [],
            "assessment_responses": [], "llm_calls": [], "rubric_evaluations": [], "participant_ui_events": [],
        },
    }


def test_timestamp_normalization_preserves_instant():
    assert reconstruct.compact_time(reconstruct.utc("2026-10-24T10:00:00+05:30")) == "2026-10-24T04:30:00Z"


def test_incomplete_session_is_warning_not_corruption(tmp_path):
    session_id = uuid.uuid4()
    result = reconstruct.Reconstruction(minimal_export(session_id), tmp_path)
    result.run()
    assert not result.errors
    assert "Browser manifest is absent" in result.warnings
    assert "Session has no capture_run_id" in result.warnings


def test_capture_integrity_uses_real_hashes_over_fixture_bytes(tmp_path):
    session_id, capture_id = uuid.uuid4(), uuid.uuid4()
    base = tmp_path / "capture-runs" / str(capture_id)
    streams = {}
    for name in ("screen", "webcam"):
        directory = base / name; directory.mkdir(parents=True)
        media = directory / f"{name}.mkv"; media.write_bytes((name + "-fixture-not-real-media").encode())
        events = directory / "capture_events.ndjson"
        events.write_text(json.dumps({"event_type": "PROCESS_EXITED", "observed_at_utc": "2026-10-24T04:31:00Z", "monotonic_ns": 10}) + "\n")
        streams[name] = {
            "media": media.name, "sha256": reconstruct.sha256(media), "capture_events": events.name,
            "ffprobe": {"metadata": {"format": {"duration": "1.0"}, "streams": [{"codec_type": "video", "codec_name": "fixture", "width": 1, "height": 1, "avg_frame_rate": "1/1"}]}},
        }
    manifest = base / "capture_manifest.json"
    manifest.write_text(json.dumps({"capture_run_id": str(capture_id), "status": "COMPLETED", "streams": streams}))
    (base / "capture_manifest.sha256").write_text(f"{reconstruct.sha256(manifest)}  capture_manifest.json\n")
    result = reconstruct.Reconstruction(minimal_export(session_id, capture_id), tmp_path)
    result.run()
    assert not result.errors
    relevant = [(name, status) for name, status, _detail in result.checks if "capture" in name or "media" in name or "FFprobe" in name]
    assert relevant and all(status == "PASS" for _name, status in relevant)
