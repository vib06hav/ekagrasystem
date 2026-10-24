"""Recorder identity and marker tests; no camera hardware required."""
import importlib.util
import json
import uuid
from pathlib import Path
import pytest


MODULE = Path(__file__).parents[1] / "tools" / "windows_capture" / "record.py"
spec = importlib.util.spec_from_file_location("windows_capture_record", MODULE)
record = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(record)


def test_record_does_not_accept_a_session_id():
    args = record.parser().parse_args(["record"])
    args.ffmpeg = "ffmpeg"
    assert not hasattr(args, "session_id")


DEVICE_OUTPUT = '''@device_pnp_camera [USB2.0 HD UVC WebCam] (video)
@device_sw_obs [OBS Virtual Camera] (none)
@device_cm_microphone [Microphone Array] (audio)
'''
MODE_OUTPUT = "[dshow @ 123]   pixel_format=mjpeg  min s=1280x720 fps=30 max s=1920x1080 fps=30\n"


def test_parse_dshow_sources_preserves_video_identity_and_excludes_obs_audio():
    assert record.parse_dshow_sources(DEVICE_OUTPUT) == [
        {"identifier": "@device_pnp_camera", "friendly_name": "USB2.0 HD UVC WebCam", "type": "video"},
        {"identifier": "@device_sw_obs", "friendly_name": "OBS Virtual Camera", "type": "none"},
        {"identifier": "@device_cm_microphone", "friendly_name": "Microphone Array", "type": "audio"},
    ]


def test_camera_configuration_selects_sole_device_and_best_native_mode(monkeypatch):
    args = record.parser().parse_args(["record"]); args.ffmpeg = "ffmpeg"
    monkeypatch.setattr(record, "list_video_sources", lambda _: ([{"identifier": "@device_pnp_camera", "friendly_name": "Integrated Camera", "type": "video"}], DEVICE_OUTPUT))
    monkeypatch.setattr(record, "probe_camera_modes", lambda *_: record.parse_camera_modes(MODE_OUTPUT))
    selected = record.configure_camera(args)
    assert selected["friendly_name"] == "Integrated Camera" and selected["source_identifier"] == "@device_pnp_camera"
    assert "video=Integrated Camera" in " ".join(record.webcam_command(args, Path("webcam.mkv")))


def test_camera_configuration_rejects_zero_or_multiple_devices(monkeypatch):
    args = record.parser().parse_args(["record"])
    monkeypatch.setattr(record, "list_video_sources", lambda _: ([], DEVICE_OUTPUT))
    try:
        record.configure_camera(args)
    except ValueError as exc:
        assert "found 0" in str(exc)
    else:
        raise AssertionError("zero devices must fail")
    monkeypatch.setattr(record, "list_video_sources", lambda _: ([{"identifier": "a", "friendly_name": "Camera A", "type": "video"}, {"identifier": "b", "friendly_name": "Camera B", "type": "video"}], DEVICE_OUTPUT))
    try:
        record.configure_camera(args)
    except ValueError as exc:
        assert "Camera A, Camera B" in str(exc)
    else:
        raise AssertionError("multiple devices must fail")


def test_explicit_camera_override_takes_precedence(monkeypatch):
    args = record.parser().parse_args(["record", "--webcam-device", "Debug Camera"]); args.ffmpeg = "ffmpeg"
    monkeypatch.setattr(record, "list_video_sources", lambda _: (_ for _ in ()).throw(AssertionError("must not enumerate override")))
    monkeypatch.setattr(record, "probe_camera_modes", lambda *_: [{"width": 640, "height": 480, "fps": 30.0}])
    assert record.configure_camera(args)["friendly_name"] == "Debug Camera"


def test_failed_detection_creates_no_active_marker(monkeypatch, tmp_path):
    args = record.parser().parse_args(["record", "--research-data", str(tmp_path)])
    args.ffmpeg = "ffmpeg"
    monkeypatch.setattr(record, "list_video_sources", lambda _: ([], DEVICE_OUTPUT))
    with pytest.raises(ValueError, match="found 0"):
        record.record(args)
    assert not (tmp_path / "active_capture.json").exists()


def test_active_marker_has_capture_identity_only(tmp_path):
    capture_run_id = uuid.uuid4()
    marker = record.write_active_marker(tmp_path, capture_run_id)
    payload = json.loads(marker.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["capture_run_id"] == str(capture_run_id)
    assert payload["status"] == "RECORDING"
    assert payload["capture_directory"] == f"capture-runs/{capture_run_id}"
    assert "session" not in json.dumps(payload).lower()
