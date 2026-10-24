import json
import sys
import uuid
from pathlib import Path

import pytest

from solo_harness.telemetry import KEYBOARD_SCHEMA_VERSION, TELEMETRY_SCHEMA_VERSION, append_keyboard_batch, append_rrweb_batch, ensure_browser_manifest

sys.path.insert(0, str(Path(__file__).parents[1] / "tools" / "windows_capture"))
from record import screen_command, sha256, webcam_command  # noqa: E402


def test_rrweb_batch_is_file_only_and_idempotent(tmp_path):
    session_id, run_id, batch_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    metadata = {"browser_run_id": str(run_id), "page_path": "/session", "telemetry_schema_version": TELEMETRY_SCHEMA_VERSION}
    ensure_browser_manifest(tmp_path, session_id, run_id, metadata)
    body = {"browser_run_id": str(run_id), "batch_id": str(batch_id), "events": [{
        "telemetry_schema_version": TELEMETRY_SCHEMA_VERSION, "browser_run_id": str(run_id), "sequence": 1,
        "client_emit_utc_ms": 1_700_000_000_000, "client_performance_ms": 12.5, "rrweb_event": {"type": 2, "timestamp": 1_700_000_000_000},
    }]}
    assert append_rrweb_batch(tmp_path, session_id, body)["accepted"]
    assert append_rrweb_batch(tmp_path, session_id, body)["duplicate"]
    data = (tmp_path / str(session_id) / "browser" / "rrweb" / f"{run_id}.ndjson").read_text(encoding="utf-8")
    assert data.count("\n") == 1 and "server_received_at_utc" in data


def test_rrweb_batch_rejects_invalid_wrapper(tmp_path):
    with pytest.raises(ValueError):
        append_rrweb_batch(tmp_path, uuid.uuid4(), {"browser_run_id": str(uuid.uuid4()), "batch_id": str(uuid.uuid4()), "events": [{}]})


def test_keyboard_batch_is_coarse_file_only_and_idempotent(tmp_path):
    session_id, run_id, batch_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    ensure_browser_manifest(tmp_path, session_id, run_id, {"browser_run_id": str(run_id)})
    event = {
        "telemetry_schema_version": KEYBOARD_SCHEMA_VERSION, "browser_run_id": str(run_id), "client_sequence": 1,
        "event_type": "KEYDOWN", "press_id": 1, "client_event_at_utc_ms": 1_700_000_000_000,
        "client_performance_ms": 12.5, "performance_time_origin_ms": 1_700_000_000_000,
        "section_number": 1, "teaching_activity_number": 1, "surface": "TUTOR_RESPONSE", "key_class": "CHAR",
        "flags": {"repeat": False, "is_composing": False, "ctrl": False, "alt": False, "shift": False, "meta": False},
    }
    body = {"browser_run_id": str(run_id), "batch_id": str(batch_id), "events": [event]}
    assert append_keyboard_batch(tmp_path, session_id, body)["accepted"]
    assert append_keyboard_batch(tmp_path, session_id, body)["duplicate"]
    stored = (tmp_path / str(session_id) / "browser" / "keyboard" / f"{run_id}.ndjson").read_text(encoding="utf-8")
    assert '"key_class":"CHAR"' in stored and '"key"' not in stored and '"code"' not in stored
    manifest = json.loads((tmp_path / str(session_id) / "browser" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["runs"][0]["keyboard"]["event_count"] == 1


def test_keyboard_batch_refuses_raw_key_fields(tmp_path):
    event = {
        "telemetry_schema_version": KEYBOARD_SCHEMA_VERSION, "browser_run_id": str(uuid.uuid4()), "client_sequence": 1,
        "event_type": "KEYDOWN", "press_id": 1, "client_event_at_utc_ms": 1, "client_performance_ms": 1,
        "performance_time_origin_ms": 1, "surface": "TUTOR_RESPONSE", "key_class": "CHAR", "key": "x",
        "flags": {"repeat": False, "is_composing": False, "ctrl": False, "alt": False, "shift": False, "meta": False},
    }
    with pytest.raises(ValueError):
        append_keyboard_batch(tmp_path, uuid.uuid4(), {"browser_run_id": event["browser_run_id"], "batch_id": str(uuid.uuid4()), "events": [event]})


def test_windows_capture_command_and_hash(tmp_path):
    class Args:
        ffmpeg = "ffmpeg"; webcam_device = "Camera"; webcam_size = "1280x720"; webcam_fps = 30
        encoder = "libx264"; preset = "medium"; crf = 18; screen_backend = "gdigrab"; screen_fps = 30
    assert "video=Camera" in webcam_command(Args(), tmp_path / "webcam.mkv")
    assert "gdigrab" in screen_command(Args(), tmp_path / "screen.mkv")
    path = tmp_path / "data"; path.write_text("x", encoding="utf-8")
    assert sha256(path) == "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"
