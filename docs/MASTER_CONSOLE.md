# EkagraAI Master Testing Console

The Master Testing Console is a local-development tool. It is available without
a separate login only when the application starts with:

```dotenv
APP_ENV=development
```

In every other environment, `/internal/master`, launch requests, and trace
exports return `404`. The existing token-protected `/internal/v051` pilot route
remains separate and unchanged.

## Start the portable development stack

```powershell
docker compose -f compose.dev.yaml up --build -d --wait
```

Open <http://127.0.0.1:18080/internal/master>. The Docker development stack is
bound to localhost, uses its own PostgreSQL database and research-data volume,
activates v0.5 C1–C4, and disables the active-capture admission gate.

The Console creates synthetic `DEV-...` sessions with synthetic demographics.
Choose C1–C4, P1/P2/P3/Random, and either teaching or direct assessment. Direct
assessment can select fixed Set A/B/C/Random and uses the authentic fixed
assessment, submission, Judge, retry, and progression code without fabricating
teaching or PAAS records.

Trace downloads are available only for marked synthetic Console sessions. Their
exports include the session ledger, attempts, subsection progress, Conversation
Judge decisions, assessment records, UI/protocol events, and session-local
telemetry up to the documented size limit.

No live LLM provider is configured by default. Add provider values to `dev.env`
only when intentionally testing paid Tutor or Judge calls.
