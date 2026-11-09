"""Capture admission contracts — no camera, Docker, or PostgreSQL required."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
import json
import uuid

from solo_harness.capture_gate import inspect_active_capture
from solo_harness.web import ParticipantApplication


def make_ready(tmp_path: Path, *, webcam=True, heartbeat=None):
    run_id = uuid.uuid4()
    root = tmp_path / "capture-runs" / str(run_id)
    root.mkdir(parents=True)
    manifest = {
        "capture_run_id": str(run_id), "status": "RECORDING",
        "streams": {"screen": {"status": "RUNNING"}},
    }
    if webcam:
        manifest["streams"]["webcam"] = {"status": "RUNNING"}
    (root / "capture_manifest.json").write_text(json.dumps(manifest))
    marker = {
        "schema_version": "1.0", "capture_run_id": str(run_id),
        "status": "RECORDING", "capture_directory": f"capture-runs/{run_id}",
        "started_at_utc": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        "heartbeat_at_utc": (heartbeat or datetime.now(timezone.utc)).isoformat(),
    }
    (tmp_path / "active_capture.json").write_text(json.dumps(marker))
    return run_id, marker, manifest


def test_recorded_mode_requires_both_streams(tmp_path):
    run_id, marker, manifest = make_ready(tmp_path, webcam=False)
    assert inspect_active_capture(tmp_path)[0] is None
    assert inspect_active_capture(tmp_path)[1] == "required_stream_not_running"
    assert inspect_active_capture(tmp_path, required_streams="screen")[0] == run_id


def test_live_heartbeat_allows_recorder_started_more_than_five_minutes_ago(tmp_path):
    run_id, _, _ = make_ready(tmp_path)
    assert inspect_active_capture(tmp_path)[0] == run_id


def test_stopped_or_stale_recorder_cannot_admit(tmp_path):
    _, marker, _ = make_ready(tmp_path, heartbeat=datetime.now(timezone.utc) - timedelta(seconds=35))
    assert inspect_active_capture(tmp_path)[1] == "stale_recorder_heartbeat"
    marker["heartbeat_at_utc"] = datetime.now(timezone.utc).isoformat()
    marker["status"] = "COMPLETED"
    (tmp_path / "active_capture.json").write_text(json.dumps(marker))
    assert inspect_active_capture(tmp_path)[1] == "marker_not_recording"


def test_forged_or_invalid_path_and_manifest_rejected(tmp_path):
    run_id, marker, manifest = make_ready(tmp_path)
    marker["capture_directory"] = "../outside"
    (tmp_path / "active_capture.json").write_text(json.dumps(marker))
    assert inspect_active_capture(tmp_path)[1] == "invalid_capture_directory"
    marker["capture_directory"] = f"capture-runs/{run_id}"
    (tmp_path / "active_capture.json").write_text(json.dumps(marker))
    manifest["status"] = "COMPLETED"
    (tmp_path / "capture-runs" / str(run_id) / "capture_manifest.json").write_text(json.dumps(manifest))
    assert inspect_active_capture(tmp_path)[1] == "manifest_not_recording"


def test_legacy_marker_without_heartbeat_fails_closed(tmp_path):
    _, marker, _ = make_ready(tmp_path)
    marker.pop("heartbeat_at_utc")
    (tmp_path / "active_capture.json").write_text(json.dumps(marker))
    assert inspect_active_capture(tmp_path)[1] == "missing_recorder_heartbeat"


def test_development_flag_does_not_bypass_capture_requirement(tmp_path):
    application = ParticipantApplication.__new__(ParticipantApplication)
    application.settings = SimpleNamespace(
        require_active_capture=True,
        enable_f1_v04_development=True,
        research_data_dir=tmp_path,
        required_capture_streams="screen_and_webcam",
        active_capture_max_age_seconds=15,
    )
    db = MagicMock()
    db.scalar.return_value = None
    application.factory = MagicMock()
    application.factory.return_value.__enter__.return_value = db
    application.execution = MagicMock()
    assert application.activate("test-participant") is None
    application.execution.runtime.create_session.assert_not_called()


def test_recorder_id_cannot_be_reused(tmp_path):
    make_ready(tmp_path)
    application = ParticipantApplication.__new__(ParticipantApplication)
    application.settings = SimpleNamespace(
        research_data_dir=tmp_path, required_capture_streams="screen_and_webcam",
        active_capture_max_age_seconds=15,
    )
    db = MagicMock()
    db.scalar.return_value = uuid.uuid4()
    assert application._active_capture_run_id(db) is None


def setup_activation_application(tmp_path, *, capture_required):
    application = ParticipantApplication.__new__(ParticipantApplication)
    application.settings = SimpleNamespace(
        require_active_capture=capture_required, enable_f1_v04_development=True,
        research_data_dir=tmp_path, required_capture_streams="screen_and_webcam",
        active_capture_max_age_seconds=15, app_build_id="test",
    )
    application.factory = MagicMock()
    db = application.factory.return_value.__enter__.return_value
    active = SimpleNamespace(study_version_id=uuid.uuid4())
    db.scalar.side_effect = ([None, None, active] if capture_required else [None, active])
    application.execution = MagicMock()
    application.execution.runtime.catalog.load.return_value = SimpleNamespace(authored={"v04": True})
    application.execution.runtime.create_session.return_value = SimpleNamespace(
        id=uuid.uuid4(), current_attempt_id=uuid.uuid4(),
    )
    return application, db


def test_recorded_development_admits_with_valid_capture_and_snapshots_policy(tmp_path):
    run_id, _, _ = make_ready(tmp_path)
    application, db = setup_activation_application(tmp_path, capture_required=True)
    assert application.activate("recorded-test") is not None
    kwargs = application.execution.runtime.create_session.call_args.kwargs
    assert kwargs["capture_run_id"] == run_id
    assert kwargs["runtime_config"]["capture_required_at_join"] is True
    assert kwargs["runtime_config"]["capture_required_streams"] == "screen_and_webcam"
    db.commit.assert_called_once()


def test_optional_capture_dev_mode_works_without_marker(tmp_path):
    application, db = setup_activation_application(tmp_path, capture_required=False)
    assert application.activate("no-camera-test") is not None
    kwargs = application.execution.runtime.create_session.call_args.kwargs
    assert kwargs["capture_run_id"] is None
    assert kwargs["runtime_config"]["capture_required_at_join"] is False
    db.commit.assert_called_once()
