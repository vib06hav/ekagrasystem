"""Manual Windows webcam + screen capture. Run outside Docker with FFmpeg on PATH."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import re

SCHEMA_VERSION = "1.0"
TOOL_VERSION = "1.0"
PINNED_BUILD = "n9.0.2-28-g669f5ab083"
RUNTIME_DIR = Path(__file__).resolve().parents[1] / "runtime" / "ffmpeg" / PINNED_BUILD / "bin"


def stamp() -> dict[str, object]:
    return {"observed_at_utc": datetime.now(timezone.utc).isoformat(), "monotonic_ns": time.perf_counter_ns()}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command_version(executable: str) -> str:
    completed = subprocess.run([executable, "-version"], capture_output=True, text=True, check=False)
    return (completed.stdout or completed.stderr).splitlines()[0] if completed.returncode == 0 else f"UNAVAILABLE: {completed.stderr.strip()}"


def resolve_runtime(args) -> None:
    """Collection uses the pinned local runtime; overrides are explicit debugging only."""
    args.ffmpeg_override = bool(args.ffmpeg)
    args.ffprobe_override = bool(args.ffprobe)
    args.ffmpeg = args.ffmpeg or str(RUNTIME_DIR / "ffmpeg.exe")
    args.ffprobe = args.ffprobe or str(RUNTIME_DIR / "ffprobe.exe")
    if not Path(args.ffmpeg).is_file() or not Path(args.ffprobe).is_file():
        raise ValueError("Pinned FFmpeg runtime is not installed. Run: powershell -ExecutionPolicy Bypass -File tools/windows_capture/bootstrap_ffmpeg.ps1")
    version = command_version(args.ffmpeg)
    if PINNED_BUILD not in version:
        raise ValueError(f"Pinned FFmpeg build mismatch; expected {PINNED_BUILD}, got {version}")


def parse_dshow_sources(output: str) -> list[dict[str, str]]:
    """Narrow adapter for `ffmpeg -sources dshow`: identifier [friendly] (type)."""
    sources = []
    for line in output.splitlines():
        match = re.search(r"(@\S+)\s+\[([^]]+)\]\s+\(([^)]+)\)\s*$", line.strip())
        if match:
            sources.append({"identifier": match.group(1), "friendly_name": match.group(2), "type": match.group(3)})
    return sources


def list_video_sources(ffmpeg: str) -> tuple[list[dict[str, str]], str]:
    result = subprocess.run([ffmpeg, "-hide_banner", "-sources", "dshow"], capture_output=True, text=True, check=False)
    raw = (result.stdout or "") + "\n" + (result.stderr or "")
    if result.returncode:
        raise ValueError("FFmpeg DirectShow source discovery failed")
    return [source for source in parse_dshow_sources(raw) if source["type"] == "video"], raw


def parse_camera_modes(output: str) -> list[dict[str, object]]:
    modes = set()
    for width, height, fps in re.findall(r"(?:s=|size=)(\d+)x(\d+).*?(?:fps=|@\s*)([\d.]+)", output, re.I):
        modes.add((int(width), int(height), float(fps)))
    return [{"width": width, "height": height, "fps": fps} for width, height, fps in sorted(modes)]


def probe_camera_modes(ffmpeg: str, device: str) -> list[dict[str, object]]:
    result = subprocess.run([ffmpeg, "-hide_banner", "-list_options", "true", "-f", "dshow", "-i", f"video={device}"], capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        raise ValueError(f"could not probe camera {device!r}")
    modes = parse_camera_modes((result.stdout or "") + "\n" + (result.stderr or ""))
    if not modes:
        raise ValueError(f"FFmpeg reported no usable native modes for camera {device!r}")
    return modes


def choose_camera_mode(modes: list[dict[str, object]]) -> dict[str, object]:
    usable = [mode for mode in modes if float(mode["fps"]) >= 15]
    if not usable: raise ValueError("FFmpeg reported no usable camera mode at 15 FPS or higher")
    return max(usable, key=lambda mode: (int(mode["width"]) * int(mode["height"]), float(mode["fps"])))


def configure_camera(args) -> dict[str, object] | None:
    if getattr(args, "no_webcam", False):
        return None
    sources, raw_sources = list_video_sources(args.ffmpeg) if not args.webcam_device else ([{"identifier": "override", "friendly_name": args.webcam_device, "type": "video"}], "")
    if len(sources) != 1:
        found = ", ".join(source["friendly_name"] for source in sources) if sources else "none"
        raise ValueError(f"expected exactly one DirectShow video source; found {len(sources)}: {found}")
    source = sources[0]; device = source["friendly_name"]
    mode = choose_camera_mode(probe_camera_modes(args.ffmpeg, device))
    args.webcam_device = device
    args.webcam_size = f"{mode['width']}x{mode['height']}"
    args.webcam_fps = mode["fps"]
    return {"source_identifier": source["identifier"], "friendly_name": device, "resolution": args.webcam_size, "fps": args.webcam_fps, "raw_sources": raw_sources}


def null_probe(command: list[str]) -> dict:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return {"command": command, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def verify_readiness(args, camera: dict[str, object] | None) -> dict:
    if camera:
        camera_probe = null_probe([args.ffmpeg, "-hide_banner", "-f", "dshow", "-video_size", str(camera["resolution"]), "-framerate", str(camera["fps"]), "-i", f"video={camera['friendly_name']}", "-t", "1", "-f", "null", "NUL"])
        if camera_probe["returncode"]: raise ValueError("FFmpeg could not open the selected camera mode")
    else:
        camera_probe = None
    devices = null_probe([args.ffmpeg, "-hide_banner", "-devices"])
    if devices["returncode"] or "gdigrab" not in (devices["stdout"] + devices["stderr"]): raise ValueError("FFmpeg does not provide gdigrab input capture")
    screen_probe = null_probe([args.ffmpeg, "-hide_banner", "-f", "gdigrab", "-framerate", str(args.screen_fps), "-i", "desktop", "-t", "1", "-f", "null", "NUL"])
    if screen_probe["returncode"]: raise ValueError("FFmpeg could not open the desktop through gdigrab")
    return {"camera_open_probe": camera_probe, "screen_devices": devices, "screen_open_probe": screen_probe}


def webcam_command(args, output: Path) -> list[str]:
    if not args.webcam_device:
        raise ValueError("--webcam-device is required unless --no-webcam is used")
    return [args.ffmpeg, "-hide_banner", "-n", "-f", "dshow", "-video_size", args.webcam_size,
            "-framerate", str(args.webcam_fps), "-i", f"video={args.webcam_device}", "-c:v", args.encoder,
            "-preset", args.preset, "-crf", str(args.crf), "-progress", "pipe:1", "-nostats", str(output)]


def screen_command(args, output: Path) -> list[str]:
    if args.screen_backend != "gdigrab":
        raise ValueError("only verified default backend gdigrab is supported")
    return [args.ffmpeg, "-hide_banner", "-n", "-f", "gdigrab", "-framerate", str(args.screen_fps),
            "-i", "desktop", "-c:v", args.encoder, "-preset", args.preset, "-crf", str(args.crf),
            "-progress", "pipe:1", "-nostats", str(output)]


def ffprobe(args, media: Path, output: Path) -> dict:
    command = [args.ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(media)]
    started = stamp()
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output.write_text(completed.stdout, encoding="utf-8")
    return {"command": command, "started": started, "completed": stamp(), "returncode": completed.returncode,
            "path": str(output.name), "metadata": json.loads(completed.stdout) if completed.returncode == 0 else None,
            "stderr": completed.stderr}


class Stream:
    def __init__(self, name: str, directory: Path, command: list[str]):
        self.name, self.directory, self.command = name, directory, command
        self.events: list[dict] = []
        self.progress: list[dict] = []
        self.process: subprocess.Popen[str] | None = None
        self.stderr_path = directory / "ffmpeg_stderr.log"
        self.stderr_events_path = directory / "ffmpeg_stderr_timestamped.ndjson"
        self.capture_events_path = directory / "capture_events.ndjson"

    def event(self, event_type: str, **extra) -> None:
        row = {"event_type": event_type, **stamp(), **extra}
        self.events.append(row)
        with self.capture_events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def start(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self.event("LAUNCH_REQUESTED", command=self.command)
        self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.event("PROCESS_STARTED", pid=self.process.pid)
        threading.Thread(target=self._read_progress, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_progress(self) -> None:
        fields: dict[str, str] = {}
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            key, _, value = line.rstrip("\r\n").partition("=")
            if key:
                fields[key] = value
            if key == "progress":
                row = {"event_type": "FIRST_PROGRESS_OBSERVED" if not self.progress else "PROGRESS_OBSERVED", **stamp(), "raw_progress": fields}
                self.progress.append(row)
                self.event(row["event_type"], raw_progress=fields)
                fields = {}

    def _read_stderr(self) -> None:
        assert self.process and self.process.stderr
        with self.stderr_path.open("a", encoding="utf-8") as raw, self.stderr_events_path.open("a", encoding="utf-8") as timed:
            for line in self.process.stderr:
                raw.write(line); raw.flush()
                timed.write(json.dumps({**stamp(), "line": line.rstrip("\r\n")}) + "\n"); timed.flush()

    def stop(self) -> None:
        if not self.process:
            return
        self.event("STOP_REQUESTED")
        try:
            if self.process.poll() is None and self.process.stdin:
                try:
                    self.process.stdin.write("q\n"); self.process.stdin.flush()
                except OSError:
                    pass
            code = self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill(); code = self.process.wait()
        self.event("PROCESS_EXITED", returncode=code)


def write_manifest(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_active_marker(root: Path, capture_run_id: uuid.UUID) -> Path:
    path = root / "active_capture.json"
    document = {"schema_version": SCHEMA_VERSION, "capture_run_id": str(capture_run_id), "status": "RECORDING",
                "started_at_utc": datetime.now(timezone.utc).isoformat(), "host_pid": __import__("os").getpid(),
                "capture_directory": f"capture-runs/{capture_run_id}"}
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def record(args) -> int:
    camera = configure_camera(args)
    readiness = verify_readiness(args, camera)
    capture_run_id = uuid.uuid4()
    data_root = Path(args.research_data).resolve()
    root = data_root / "capture-runs" / str(capture_run_id)
    root.mkdir(parents=True, exist_ok=True)
    streams = []
    if not args.no_webcam:
        streams.append(Stream("webcam", root / "webcam", webcam_command(args, root / "webcam" / "webcam.mkv")))
    streams.append(Stream("screen", root / "screen", screen_command(args, root / "screen" / "screen.mkv")))
    manifest = {"schema_version": SCHEMA_VERSION, "status": "RECORDING", "capture_run_id": str(capture_run_id),
                "capture_tool_version": TOOL_VERSION, "operating_system": platform.platform(), "ffmpeg_version": command_version(args.ffmpeg),
                "ffprobe_version": command_version(args.ffprobe), "configuration": {"webcam_device": args.webcam_device,
                "webcam_size": args.webcam_size, "webcam_fps": args.webcam_fps, "webcam_selected_mode": camera, "screen_backend": args.screen_backend,
                "screen_fps": args.screen_fps, "encoder": args.encoder, "preset": args.preset, "crf": args.crf,
                "progress_cadence": "FFmpeg default progress emission", "mode_policy": "highest reported resolution at 15 FPS or higher, then highest FPS", "readiness": readiness}, "streams": {}}
    manifest_path = root / "capture_manifest.json"
    write_manifest(manifest_path, manifest)
    marker = None
    try:
        for stream in streams:
            stream.start()
            manifest["streams"][stream.name] = {"command": stream.command, "status": "RUNNING"}
        time.sleep(0.5)
        failed = [stream.name for stream in streams if stream.process and stream.process.poll() is not None]
        if failed:
            raise RuntimeError(f"capture startup failed: {', '.join(failed)}")
        write_manifest(manifest_path, manifest)
        marker = write_active_marker(data_root, capture_run_id)
    except Exception:
        for stream in streams:
            stream.stop()
        if marker:
            marker.unlink(missing_ok=True)
        raise
    print("Recording ready.")
    print(f"Webcam: {'disabled' if args.no_webcam else 'recording'}")
    print("Screen: recording")
    print(f"Capture run: {capture_run_id}")
    print("Participant may now begin. Press Ctrl+C after the participant finishes.")
    try:
        started = time.monotonic()
        while any(stream.process and stream.process.poll() is None for stream in streams):
            if args.max_seconds is not None and time.monotonic() - started >= args.max_seconds:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for stream in streams:
            stream.stop()
            media = stream.directory / ("webcam.mkv" if stream.name == "webcam" else "screen.mkv")
            probe = None
            if media.exists():
                stream.event("FFPROBE_STARTED")
                probe = ffprobe(args, media, stream.directory / "ffprobe.json")
                stream.event("FFPROBE_COMPLETED", returncode=probe["returncode"])
                stream.event("HASH_STARTED", path=media.name)
                digest = sha256(media)
                stream.event("HASH_COMPLETED", path=media.name, sha256=digest)
            manifest["streams"][stream.name] = {"command": stream.command, "status": "STOPPED", "events": stream.events,
                "progress_anchors": stream.progress, "stderr": "ffmpeg_stderr.log", "stderr_timestamped": "ffmpeg_stderr_timestamped.ndjson",
                "capture_events": "capture_events.ndjson", "media": media.name, "file_size": media.stat().st_size if media.exists() else None,
                "sha256": sha256(media) if media.exists() else None, "ffprobe": probe}
        manifest["status"] = "COMPLETED"
        write_manifest(manifest_path, manifest)
        (root / "capture_manifest.sha256").write_text(sha256(manifest_path) + "  capture_manifest.json\n", encoding="utf-8")
        try:
            if marker:
                marker.unlink()
        except FileNotFoundError:
            pass
    return 0


def preflight(args) -> int:
    camera = configure_camera(args)
    readiness = verify_readiness(args, camera)
    print(json.dumps({"ffmpeg_version": command_version(args.ffmpeg), "ffprobe_version": command_version(args.ffprobe),
                      "video_devices_detected": 0 if getattr(args, "no_webcam", False) else 1, "camera": camera, "screen_capture": "gdigrab", "screen_probe": "OK" if readiness else "FAILED", "active_capture": "none"}, indent=2))
    return 0


def probe_camera(args) -> int:
    if not args.webcam_device:
        raise ValueError("--webcam-device is required")
    return subprocess.run([args.ffmpeg, "-hide_banner", "-list_options", "true", "-f", "dshow", "-i", f"video={args.webcam_device}"], check=False).returncode


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ffmpeg"); p.add_argument("--ffprobe")
    sub = p.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight"); pre.add_argument("--webcam-device"); pre.add_argument("--screen-fps", type=int, default=30)
    probe = sub.add_parser("probe-camera"); probe.add_argument("--webcam-device", required=True)
    rec = sub.add_parser("record"); rec.add_argument("--research-data", default="research-data")
    rec.add_argument("--webcam-device"); rec.add_argument("--no-webcam", action="store_true"); rec.add_argument("--webcam-size")
    rec.add_argument("--max-seconds", type=float, help=argparse.SUPPRESS)
    rec.add_argument("--webcam-fps", type=float); rec.add_argument("--screen-backend", default="gdigrab", choices=["gdigrab"])
    rec.add_argument("--screen-fps", type=int, default=30); rec.add_argument("--encoder", default="libx264"); rec.add_argument("--preset", default="medium"); rec.add_argument("--crf", type=int, default=18)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        resolve_runtime(args)
        return preflight(args) if args.command == "preflight" else probe_camera(args) if args.command == "probe-camera" else record(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
