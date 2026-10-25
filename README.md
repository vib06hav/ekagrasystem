# SOLO Harness — Fibonacci Memoization Study

SOLO Harness runs a single-participant learning study on recursive Fibonacci and memoization. It provides a FastAPI participant application, PostgreSQL persistence, an OpenAI-compatible LLM adapter, browser telemetry, optional Windows screen/webcam capture, and session export tools.

## Study activation

Bootstrap preserves an existing active study version by default. To activate a reviewed new authored pack such as `studies/python_fibonacci_memoization/v0.5`, point `STUDY_DIR` at that pack and explicitly set `ACTIVATE_STUDY_ON_BOOTSTRAP=true` for the activation run. Historical study versions are not rewritten.

## Run it with Docker (recommended)

### Prerequisites

- Docker Desktop with Docker Compose v2
- An OpenAI-compatible chat-completions endpoint and API key
- Windows only: PowerShell and a webcam if you will collect screen/webcam recordings

### 1. Clone and configure

```powershell
git clone https://github.com/vib06hav/ekagrasystem.git
cd ekagrasystem
```

Create a local `.env` file. It is intentionally ignored by Git.

```dotenv
# Required to use the live tutor and judge.
AICREDITS_BASE_URL=https://your-openai-compatible-provider/v1
AICREDITS_API_KEY=replace-with-your-secret
TUTOR_MODEL=your-tutor-model
JUDGE_MODEL=your-judge-model

# Optional defaults shown explicitly for clarity.
APP_PORT=8000
LLM_STRUCTURED_OUTPUT_MODE=provider_native_json_schema
REQUIRE_ACTIVE_CAPTURE=false
```

`AICREDITS_BASE_URL` must be the base URL before `/chat/completions`. Do not commit the `.env` file or any captured research data.

### 2. Start the complete application

```powershell
docker compose up -d --build --wait
```

This starts PostgreSQL and the web application. During app startup, the application automatically:

1. applies all Alembic migrations;
2. loads and validates `studies/python_fibonacci_memoization/v0.1`;
3. compiles the study content; and
4. activates the immutable study version in PostgreSQL.

Check that both services are healthy:

```powershell
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

The final command should return `status : ready`.

### 3. Run a participant session

Open <http://127.0.0.1:8000>. Enter a new institutional ID, acknowledge the study information, and complete the four sections in order. Each section includes a tutor interaction followed by an independent assessment.

Important operating rules:

- One installation supports one active participant at a time.
- An institutional ID is single-use.
- Completed sections are retained as read-only history.
- Restarting an already used participant session requires researcher intervention; do not ask the participant to re-enter.

### 4. Stop the application

```powershell
docker compose down
```

Use the following only when you deliberately want to remove the local PostgreSQL database as well:

```powershell
docker compose down -v
```

## Windows screen and webcam recording (optional)

Recordings run on the Windows host, outside Docker. The application never starts or stops capture itself.

1. Install the pinned FFmpeg runtime once:

   ```powershell
   powershell -ExecutionPolicy Bypass -File tools/windows_capture/bootstrap_ffmpeg.ps1
   ```

2. Confirm that the webcam and desktop capture are usable:

   ```powershell
   python tools/windows_capture/record.py preflight
   ```

   The tool requires exactly one DirectShow webcam unless you use `--no-webcam`.

3. Start Docker as above, then start recording before the participant begins:

   ```powershell
   python tools/windows_capture/record.py record
   ```

4. Open the participant application and run the study. Stop recording with `Ctrl+C` after the participant finishes.

Capture artifacts are written under `research-data/capture-runs/`. That directory, along with videos and telemetry exports, is ignored by Git. To require a live capture marker before allowing a participant session, set `REQUIRE_ACTIVE_CAPTURE=true` in `.env`.

For a screen-only dry run:

```powershell
python tools/windows_capture/record.py record --no-webcam
```

## Export or inspect a completed session

Run these commands in the running app container. Replace `<session-id>` with the UUID created for the participant session.

```powershell
docker compose exec app solo-harness inspect-session --session-id <session-id>
docker compose exec app solo-harness export-session --session-id <session-id> --output /app/exports/session.json
```

The export appears locally as `exports/session.json`. It references eligible capture manifests but never embeds video. Exports and research data may contain sensitive participant information and are ignored by Git.

## Local Python development (without Docker)

Use Python 3.12 or later and a PostgreSQL database. Docker is still the easiest way to run PostgreSQL locally.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

Create `.env` with the LLM settings shown above plus local database and study paths:

```dotenv
DATABASE_URL=postgresql+psycopg://solo_harness:change-me@127.0.0.1:5432/solo_harness
STUDY_DIR=studies/python_fibonacci_memoization/v0.1
AICREDITS_BASE_URL=https://your-openai-compatible-provider/v1
AICREDITS_API_KEY=replace-with-your-secret
TUTOR_MODEL=your-tutor-model
JUDGE_MODEL=your-judge-model
```

Start PostgreSQL only, then start the app. The app performs migrations and study activation during startup.

```powershell
docker compose up -d postgres --wait
python -m solo_harness
```

Useful study checks:

```powershell
solo-harness validate-study
solo-harness inspect-study
pytest
```

The browser suite requires a disposable PostgreSQL database and never targets the
collection database. Set `TEST_DATABASE_URL` to that isolated database, then run:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://solo_test:solo_test@127.0.0.1:55432/solo_test"
python -m pytest tests/e2e/test_participant_browser.py -q
```

The deterministic browser tests use scripted model responses and make no external
LLM calls. Chromium runs headless in the normal suite. The recorded validation
driver in `scripts/recorded_reconstruction_e2e.py` launches a visible Chromium
window and requires the real Windows capture preflight to pass.

## Project layout

- `src/solo_harness/` — FastAPI application, runtime, study compiler, database models, and telemetry.
- `studies/python_fibonacci_memoization/v0.1/` — executable study definition and its content.
- `migrations/` — Alembic database migrations.
- `tools/windows_capture/` — host-side recording tools.
- `docs/` — collection and recording specifications.
- `01_*.md` through `05_*.md` — human-readable research provenance; the YAML study files are the executable source of truth.

## Safety and data handling

The live database, browser telemetry, exports, screen recordings, webcam recordings, and provider traffic may contain sensitive data. Keep `.env`, `research-data/`, `exports/`, `artifacts/`, and Graphify outputs out of version control. Review `docs/COMPLETE_DATA_COLLECTION_SPECIFICATION.md` and `docs/research_recording.md` before collecting participant data.
