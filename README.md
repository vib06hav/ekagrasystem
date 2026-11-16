# EkagraAI — Unified C1–C4 Study

EkagraAI is a PostgreSQL-backed learning study for error detection and parity.
The active v0.5 study contains four sections (C1–C4), fixed assessment banks,
Tutor/Judge execution, PAAS, progression, demographics, trace exports, and the
developer-only Master Testing Console.

## Local Docker development

The recommended development workflow needs only Docker Desktop with Compose v2.
It does not use a locally installed Python or PostgreSQL service, the existing
collection database, or `compose.yaml`.

Optional: copy [`dev.env.example`](dev.env.example) to `dev.env` and replace the
local development password and session secret. The defaults are sufficient for
a localhost-only development installation.

```powershell
Copy-Item dev.env.example dev.env
docker compose --env-file dev.env -f compose.dev.yaml up --build -d --wait
```

Without a `dev.env` file, run:

```powershell
docker compose -f compose.dev.yaml up --build -d --wait
```

Open the application at <http://127.0.0.1:18080> and the Master Testing Console
directly at <http://127.0.0.1:18080/internal/master>.

The development stack explicitly uses `APP_ENV=development`, the unified v0.5
study, and `REQUIRE_ACTIVE_CAPTURE=false`. The console requires no token in this
local-only stack. Docker binds both the app and development PostgreSQL port to
`127.0.0.1`, so it is not exposed to the network.

### Useful commands

```powershell
# Inspect services and follow application logs.
docker compose -f compose.dev.yaml ps
docker compose -f compose.dev.yaml logs -f app

# Stop the development stack while retaining its isolated dev database.
docker compose -f compose.dev.yaml down

# Deliberately reset development-only data and volumes.
docker compose -f compose.dev.yaml down -v
```

The development database and research-data volume are named independently from
the existing collection stack. `down -v` affects only the `ekagra-dev` project
when using the commands above.

## Master Testing Console

`/internal/master` is available only when `APP_ENV=development`. In production,
the page, launch route, and trace route return `404`.

The Console creates clearly marked synthetic `DEV-...` sessions with synthetic
demographics. It can start C1–C4 with P1/P2/P3/Random pedagogy, or directly
open fixed assessment Set A/B/C/Random. It uses the real fixed-assessment,
submission, Judge, retry, progression, visual, and trace-export paths without
claiming that a participant consented or that capture requirements were met.

Direct assessment can be explored without a live LLM provider. Teaching and
Judge execution call the configured provider only when those actions are taken.
Set the optional `EKAGRA_DEV_AICREDITS_*`, `EKAGRA_DEV_TUTOR_MODEL`, and
`EKAGRA_DEV_JUDGE_MODEL` variables in `dev.env` only when intentionally testing
with a paid provider.

## Docker test suite

Run the complete deterministic suite, including PostgreSQL integration tests,
inside Docker:

```powershell
docker compose -p ekagra-test -f compose.dev.yaml --profile test up -d --wait test_db
docker compose -p ekagra-test -f compose.dev.yaml --profile test run --build --rm --no-deps test
docker compose -p ekagra-test -f compose.dev.yaml --profile test down -v --remove-orphans
```

The test service uses its own PostgreSQL container with a temporary in-memory
data directory. It receives `EKAGRA_STAGE3_DATABASE_URL` internally, so the
PostgreSQL lifecycle tests run rather than skip. It never connects to the
development or participant database.

## Runtime configuration

[`.env.example`](.env.example) documents deployment configuration for the
ordinary application. Keep actual `.env` files out of Git. The development stack
intentionally uses its own `EKAGRA_DEV_*` variables rather than reading the
repository `.env`, preventing collection credentials and research settings from
leaking into local development.

The older [`compose.yaml`](compose.yaml) remains the existing collection-oriented
stack. Use [`compose.dev.yaml`](compose.dev.yaml) for local development and
testing.

## Research integrity

Development and test records are isolated from collection data by database,
Docker project, and research-data volume. Synthetic Console records are marked
in their session configuration and must be excluded from participant analysis.
Historical `StudyVersion` identities are preserved; migrations add schema only
and do not rewrite study/session identities.
