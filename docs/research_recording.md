# Local research recording

PostgreSQL remains the scientific record. Browser replay data and Windows media remain files under `research-data/<session UUID>/`.

## Browser telemetry

The app serves local `@rrweb/record` 2.1.7 from `/static/vendor/rrweb/2.1.7/record.umd.min.cjs`; no rrweb CDN is used. Source: `https://github.com/rrweb-io/rrweb`, MIT. The vendored asset SHA-256 is `46d0efdc8cfc90ddf097d19e81ea050fb7cabbe3bb2074f19e08117bcb6e41f6`; its npm tarball SHA-256 is `d07955b789976c4dea6ae92debc46f3b0b80453e06b15d9a34ad802c38339409`, retrieved 2026-10-18.

`GHSA-xjgr-f74v-fx5m` affects the separate canvas-WebRTC recording plugin below 2.1.4. This application vendors only `@rrweb/record` 2.1.7 and enables neither that plugin nor canvas/cross-origin iframe recording.

rrweb uses `maskAllInputs: true`, `sampling.input: "all"`, `recordCanvas: false`, and `recordCrossOriginIframes: false`. Submitted response text remains in PostgreSQL but is not written plaintext to rrweb artifacts.

Each full session page creates a random browser run. Browser files are:

```text
research-data/<session UUID>/browser/manifest.json
research-data/<session UUID>/browser/rrweb/<browser run UUID>.ndjson
research-data/<session UUID>/browser/keyboard/<browser run UUID>.ndjson
```

Each rrweb line retains its original event plus browser UTC milliseconds, `performance.now()`, sequence, batch ID, and server receipt UTC. Semantic UI events are low-volume PostgreSQL rows. Their `*_RENDERED` time is emitted in `requestAnimationFrame` after relevant DOM insertion; it is not claimed to be eye-visible time.

No live merged timeline exists. Later reconstruction uses PostgreSQL UTC, semantic event times, rrweb UTC/performance clocks, and recording progress/media timestamps.

## Keyboard dynamics

`participant_keyboard.js` uses only native `keydown` and `keyup` listeners attached once to `#learner-text` and `#assessment-response`. It has no document-level listener, no institutional-ID listener, no OS hook, and no third-party dependency. HTMX replacements are reattached through the existing render lifecycle.

Each `keyboard-1.0` NDJSON event stores only: schema version, browser-run UUID, client sequence, `KEYDOWN`/`KEYUP`, press ID, client UTC milliseconds, `performance.now()`, time origin, participant-safe section/activity numbers, `TUTOR_RESPONSE` or `ASSESSMENT_RESPONSE`, coarse key class, repeat/composition and Ctrl/Alt/Shift/Meta flags, batch ID, and server receipt UTC. It never stores `KeyboardEvent.key`, `KeyboardEvent.code`, raw typed text, field values, selection, caret, or clipboard data. The server rejects top-level `key`, `code`, and `value` fields.

Key classes are `CHAR`, `DIGIT`, `SPACE`, `ENTER`, `BACKSPACE`, `DELETE`, `TAB`, `ARROW`, `MODIFIER`, `PUNCTUATION`, and `OTHER`. A locally held `event.code` map pairs a non-repeat keydown to its keyup; it is never serialized. Repeats reuse that press ID. A keyup with no observed non-repeat keydown is discarded, so the browser never invents a physical press.

## Windows capture

Install `ffmpeg` and `ffprobe` on the Windows host PATH. Before collection, enable Windows automatic time sync, click **Sync now**, and do not manually change the clock during capture.
Before collection, enable Windows automatic time sync, click **Sync now**, and do not manually change the clock during capture. Install the pinned project-local FFmpeg runtime once; no system PATH installation is used for collection.

```powershell
powershell -ExecutionPolicy Bypass -File tools/windows_capture/bootstrap_ffmpeg.ps1
python tools/windows_capture/record.py preflight
python tools/windows_capture/record.py probe-camera --webcam-device "Exact DirectShow camera name"
python tools/windows_capture/record.py record
```

The pinned runtime is BtbN GPL static `ffmpeg-n9.0.2-28-g669f5ab083-win64-gpl-9.0.zip` (SHA-256 `a38198cc130ed3fa02097d0baebcea9c1b8a9d9d3d1d8161d691d1f03709158b`). The tool uses `ffmpeg -sources dshow` for camera discovery, probes native modes, and selects the highest reported resolution at 15 FPS or higher, then highest FPS. If no camera—or unexpectedly more than one camera—is found, it stops and reports the devices rather than guessing. `--webcam-device`, `--ffmpeg`, and `--ffprobe` are explicit debugging overrides. Screen capture uses `gdigrab` at 30fps, `libx264`, CRF 18, and MKV. Do not upscale or interpolate. Stop with Ctrl+C.

```text
research-data/capture-runs/<capture_run_id>/capture_manifest.json
research-data/capture-runs/<capture_run_id>/capture_manifest.sha256
research-data/capture-runs/<capture_run_id>/webcam/webcam.mkv
research-data/capture-runs/<capture_run_id>/webcam/{capture_events.ndjson,ffmpeg_stderr.log,ffmpeg_stderr_timestamped.ndjson,ffprobe.json}
research-data/capture-runs/<capture_run_id>/screen/screen.mkv
research-data/capture-runs/<capture_run_id>/screen/{capture_events.ndjson,ffmpeg_stderr.log,ffmpeg_stderr_timestamped.ndjson,ffprobe.json}
```

MKV is used for crash tolerance. The manifest stores launch/start/first-progress/progress/stop/exit/ffprobe/hash observations with UTC and monotonic time, commands, selected settings, stderr paths, probe output, media size, and SHA-256. Webcam and screen remain independent files.

No capture is started or stopped by the participant app. No media enters PostgreSQL or session export. The export references only small manifests when present.
