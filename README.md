# EkagraAI — C1–C4 Study

EkagraAI is the unified C1–C4 error-detection and parity study. It includes
guided Tutor/Judge teaching, PAAS, fixed assessments, section progression,
demographic storage, trace exports, and a development-only Master Testing
Console.

You normally use one of two modes:

- **Development** — safe local testing with an isolated Docker database,
  optional capture gating, and the Master Console.
- **Participant collection** — the real study, with its separate database,
  capture gate, and no Master Console.

Docker Desktop is the only required local dependency for both modes.

## Development: run locally

Use this mode for coding, QA, synthetic participants, and the Master Console.
It does **not** use the participant database or research-data directory.

1. Create your private development configuration:

   ```powershell
   Copy-Item dev.env.example dev.env
   ```

2. Open `dev.env` and, if you want live Tutor/Judge conversations, fill in
   your provider values:

   ```env
   EKAGRA_DEV_AICREDITS_BASE_URL=https://your-provider/v1
   EKAGRA_DEV_AICREDITS_API_KEY=your-api-key
   EKAGRA_DEV_TUTOR_MODEL=your-tutor-model
   EKAGRA_DEV_JUDGE_MODEL=your-judge-model
   ```

   Leave those values blank when you do not want to make paid LLM calls.
   The Console and fixed assessments still start; Tutor/Judge conversation
   requires these four values.

3. Start Ekagra:

   ```powershell
   docker compose --env-file dev.env -f compose.dev.yaml up --build -d --wait
   ```

4. Open one of these local URLs:

   - Master Console: <http://127.0.0.1:18080/internal/master>
   - Participant-style enrollment: <http://127.0.0.1:18080/join>

   The Console is direct access in development—there is no token login.
   Capture is disabled by default.

Stop development while keeping its local database:

```powershell
docker compose --env-file dev.env -f compose.dev.yaml down
```

Delete **only development** data and start over:

```powershell
docker compose --env-file dev.env -f compose.dev.yaml down -v
```

### Test screen and webcam capture in development

Development uses the same capture admission gate as participant collection when
you opt in, but stores all media and manifests in the ignored local folder
`local-artifacts/ekagra-dev/`. It never uses participant data.

1. In `dev.env`, set:

   ```env
   EKAGRA_DEV_REQUIRE_ACTIVE_CAPTURE=true
   EKAGRA_DEV_REQUIRED_CAPTURE_STREAMS=screen_and_webcam
   EKAGRA_DEV_ACTIVE_CAPTURE_MAX_AGE_SECONDS=15
   ```

2. Restart the development stack:

   ```powershell
   docker compose --env-file dev.env -f compose.dev.yaml up --build -d --wait
   ```

3. In another PowerShell window, install the pinned FFmpeg runtime once if
   needed, then start the host recorder:

   ```powershell
   powershell -ExecutionPolicy Bypass -File tools/windows_capture/bootstrap_ffmpeg.ps1
   python tools/windows_capture/record.py preflight
   python tools/windows_capture/record.py record --research-data local-artifacts/ekagra-dev
   ```

4. Test participant admission at <http://127.0.0.1:18080/join> with a fresh
   participant ID. With the recorder stopped, enrollment must fail. With both
   streams recording, it must succeed and the session receives a capture-run
   ID. Use `/join`, not the Master Console: synthetic Console sessions bypass
   capture by design.

Stop the recorder with `Ctrl+C` when finished. Use a new recorder run and a
new participant ID for every capture-test session.

## Participant collection: run the real study

Use this mode only for the normal participant/research environment. Do not use
the development Compose file or its database.

1. Create the private collection configuration:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Edit `.env`. Set matching PostgreSQL values, a strong session secret, and
   the live Tutor/Judge provider configuration:

   ```env
   APP_ENV=production

   POSTGRES_DB=ekagra
   POSTGRES_USER=ekagra_app
   POSTGRES_PASSWORD=choose-a-long-password
   DATABASE_URL=postgresql+psycopg://ekagra_app:choose-a-long-password@postgres:5432/ekagra

   WEB_SESSION_SECRET=use-a-long-random-secret

   AICREDITS_BASE_URL=https://your-provider/v1
   AICREDITS_API_KEY=your-api-key
   TUTOR_MODEL=your-tutor-model
   JUDGE_MODEL=your-judge-model

   REQUIRE_ACTIVE_CAPTURE=true
   REQUIRED_CAPTURE_STREAMS=screen_and_webcam
   ```

   `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `DATABASE_URL`
   must describe the same database. Docker creates that database on its first
   start. In `DATABASE_URL`, `postgres` is the Docker database service name.

3. Start the collection stack:

   ```powershell
   docker compose up --build -d --wait
   ```

4. Direct participants to:

   <http://127.0.0.1:8000/join>

   Start the host screen/webcam recorder before enrollment. Docker runs the
   application and database, but the recorder must run on the capture computer
   because it accesses its physical screen and camera:

   ```powershell
   python tools/windows_capture/record.py preflight
   python tools/windows_capture/record.py record
   ```

In participant mode, `/internal/master` is unavailable and returns `404`.

## Run the full test suite in Docker

This uses a disposable PostgreSQL database and does not need local Python or
PostgreSQL:

```powershell
docker compose -p ekagra-test -f compose.dev.yaml --profile test up -d --wait test_db
docker compose -p ekagra-test -f compose.dev.yaml --profile test run --build --rm --no-deps test
docker compose -p ekagra-test -f compose.dev.yaml --profile test down -v --remove-orphans
```

## Keep secrets private

Never commit or share `.env` or `dev.env`. They are intentionally ignored by
Git. Commit only `.env.example` and `dev.env.example`; every developer creates
their own local configuration and credentials.

Development, test, and participant data remain isolated by Docker project,
database, and storage volume. Synthetic Master Console sessions are marked as
development data and must never be treated as participant records.
