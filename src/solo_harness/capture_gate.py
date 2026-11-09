"""Filesystem handoff from the independent host recorder to session admission.

This validates *admission-time* recording readiness. It does not replace the
recording manifest or claim that frames remain available throughout a session.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

CaptureStreams = Literal["screen", "screen_and_webcam"]


def inspect_active_capture(
    research_data_dir: Path,
    *,
    required_streams: CaptureStreams = "screen_and_webcam",
    heartbeat_max_age_seconds: int = 15,
    now: datetime | None = None,
) -> tuple[uuid.UUID | None, str]:
    """Return a capture UUID only for a fresh, correctly configured recorder.

    Caller must separately enforce one participant session per capture run.
    The marker is written and refreshed atomically by the Windows host recorder.
    """
    reference = now or datetime.now(timezone.utc)
    try:
        payload = json.loads((research_data_dir / "active_capture.json").read_text(encoding="utf-8"))
        if payload.get("schema_version") != "1.0" or payload.get("status") != "RECORDING":
            return None, "marker_not_recording"
        run_id = uuid.UUID(str(payload["capture_run_id"]))
        directory_name = Path(str(payload["capture_directory"]))
        if directory_name.is_absolute() or directory_name != Path("capture-runs") / str(run_id):
            return None, "invalid_capture_directory"

        raw_heartbeat = payload.get("heartbeat_at_utc")
        if not raw_heartbeat:
            return None, "missing_recorder_heartbeat"
        heartbeat = datetime.fromisoformat(str(raw_heartbeat).replace("Z", "+00:00"))
        if heartbeat.tzinfo is None:
            return None, "invalid_recorder_heartbeat"
        difference = reference - heartbeat.astimezone(timezone.utc)
        if difference > timedelta(seconds=heartbeat_max_age_seconds) or difference < timedelta(seconds=-5):
            return None, "stale_recorder_heartbeat"

        directory = research_data_dir / directory_name
        if not directory.is_dir():
            return None, "missing_capture_directory"
        manifest = json.loads((directory / "capture_manifest.json").read_text(encoding="utf-8"))
        if manifest.get("capture_run_id") != str(run_id) or manifest.get("status") != "RECORDING":
            return None, "manifest_not_recording"
        streams = manifest.get("streams")
        if not isinstance(streams, dict):
            return None, "missing_streams"
        names = ("screen", "webcam") if required_streams == "screen_and_webcam" else ("screen",)
        if any(not isinstance(streams.get(name), dict) or streams[name].get("status") != "RUNNING" for name in names):
            return None, "required_stream_not_running"
        return run_id, "ready"
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None, "invalid_capture_marker_or_manifest"
