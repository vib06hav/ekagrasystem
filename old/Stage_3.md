# Stage 3 — Application, UI, Reliability, and Deployment Design

**Status:** Implementation design for human review  
**Scope:** Participant-facing web application, session entry, HTTP/HTMX flows, reliability, configuration, local deployment, operation, audit export, and final testing. No implementation is included.

---

## 1. Understanding of the approved Stage-1/2 system

Stage 3 exposes the approved data and runtime foundations without moving experimental logic into the browser or route handlers.

The fixed foundation is:

- The application is a Python 3.12+ FastAPI/PostgreSQL modular monolith.
- A reviewed and frozen operational YAML package is the executable source of truth for a StudyVersion. Markdown remains human-readable research/design provenance and is not read during participant execution.
- One immutable StudyVersion stores the authored `content_hash`, `compiler_contract_version`, compiled runtime snapshot, and `snapshot_hash`.
- A Session binds only to its immutable StudyVersion through `study_version_id`.
- PostgreSQL owns current participant state and durable research evidence.
- `SessionRuntime` is the application-level authority for participant commands and transaction boundaries.
- The browser renders `SessionRuntimeView`; it does not infer or advance protocol state.
- A pedagogy remains fixed for an Attempt.
- Intervention stages are authored guidance and progress trace unless a study explicitly requires stricter behavior.
- A fresh assessment is selected without using pedagogy identity.
- The Judge receives a narrow, blinded input and returns evidence; the deterministic rubric and Protocol Engine decide progression.
- Technical failure never becomes learner failure and does not consume another pedagogy.
- LLM calls follow `STARTED → RECEIVED → terminal status`, with persisted operations supporting recovery.
- Random selection uses a standard trustworthy selector and persists candidates, exclusions, selected ID, method, timestamp, and any optional deterministic test seed.
- Current rows are authoritative for execution; immutable evidence and protocol events provide reconstruction. The system is not event sourced.

The selected deployment remains exactly two services:

```text
browser
   │
   ▼
app: FastAPI + Jinja2 + HTMX + runtime
   │
   ▼
postgres

app ─────► configured external LLM provider
```

### 1.1 Small Stage-2 interface completion

Stage 2 defines how `TutorRuntime.prepare_opening()` creates the required opening Tutor turn, but its public `SessionRuntime` command list does not name the command used by a participant route to start an already-assigned Attempt.

Add one application-service command:

```text
SessionRuntime.start_current_attempt(
    session_id: UUID,
    idempotency_key: str
) -> TutorOperationResult
```

It may act only when the current Attempt is `ASSIGNED`, and it uses the existing opening-turn lifecycle, locking, LLMCall persistence, retry limits, and idempotency rules. This is an interface completion only. It adds no entity, protocol state, or experimental rule.

No other Stage-1 or Stage-2 change is required by this design.

---

## 2. Web application architecture

### 2.1 Web-layer structure

Extend the approved repository structure as follows:

```text
src/solo_harness/
├── main.py
├── bootstrap.py
├── config.py
├── cli/
│   ├── sessions.py
│   └── export.py
├── web/
│   ├── dependencies.py
│   ├── errors.py
│   ├── presenters.py
│   ├── security.py
│   ├── view_models.py
│   └── routers/
│       ├── health.py
│       ├── entry.py
│       └── participant.py
├── templates/
│   ├── base.html
│   ├── entry.html
│   ├── session.html
│   ├── error.html
│   └── partials/
│       ├── session_main.html
│       ├── intervention.html
│       ├── messages.html
│       ├── tutor_form.html
│       ├── pending.html
│       ├── assessment.html
│       ├── technical_hold.html
│       ├── continuation.html
│       ├── terminal.html
│       └── notice.html
└── static/
    ├── app.css
    └── app.js
```

This is one process and one deployable application. Routers, presenters, and templates are organizational boundaries, not independently deployed components.

### 2.2 Router responsibilities

| Router | Responsibility | May call `SessionRuntime`? |
|---|---|---|
| `health` | Liveness, readiness, and build metadata | No participant commands; readiness may use a read-only bootstrap/DB check |
| `entry` | Render code-entry page, validate opaque participant code, establish signed session cookie | Read-only session lookup only |
| `participant` | Render authoritative session state and accept participant actions | Yes, only through its public command/read interfaces |

Researcher session creation and export are CLI commands, not unauthenticated web routes.

### 2.3 Request boundary

The request flow is:

```text
HTTP request
    ↓
router: parse form, authenticate session cookie, verify CSRF
    ↓
SessionRuntime command or read
    ↓
SessionRuntimeView / typed command result
    ↓
presenter: choose participant-safe view model
    ↓
Jinja full page or HTMX fragment
```

Routes may:

- parse and size-limit participant text;
- validate the signed session cookie and CSRF token;
- pass an idempotency key to `SessionRuntime`;
- translate typed application errors into HTTP responses;
- render participant-safe views.

Routes must never:

- select pedagogy or assessment forms;
- compile Tutor or Judge prompts;
- call the LLM client directly;
- evaluate a rubric;
- decide whether a transition passed;
- mutate Session, Attempt, Assessment, or LLMCall rows directly;
- expose hidden scoring context, Judge evidence, raw provider payloads, or internal prompts;
- infer a new phase from browser-supplied fields.

### 2.4 Rendering boundary

`web/presenters.py` converts a `SessionRuntimeView` into a closed participant view model. Templates receive only display-safe fields. They do not receive ORM entities or the full compiled study.

The participant view model may contain:

- public session state label;
- learner-visible Tutor messages;
- current assessment prompt when active;
- whether a permitted action exists;
- pending-operation type and safe status;
- generic technical-hold information;
- transition/attempt progress labels suitable for participants;
- terminal outcome text.

It must not contain:

- pedagogy selection candidates or future assignment;
- hidden assessment context;
- Judge prompt, evidence, rubric internals, or confidence;
- future assessment forms;
- provider request/response data;
- secrets or operational stack details.

---

## 3. Session bootstrap

### 3.1 Researcher workflow

The POC uses a CLI rather than an administration dashboard:

```text
docker compose exec app \
  python -m solo_harness.cli.sessions create
```

The command:

1. Loads the active StudyVersion.
2. Creates a Session bound to that StudyVersion.
3. Generates an opaque, cryptographically random participant code.
4. Initializes the P/C1 Session and its first assigned Attempt through `SessionRuntime.initialize_session()`.
5. Prints the participant code and local application URL.

It does not call the Tutor provider. The participant explicitly begins the first Attempt from the browser.

The participant code is not a human identity. No name, email address, or other PII is required by the harness.

### 3.2 Participant entry

The participant opens `/join`, enters the opaque code, and submits it with `POST /join`.

On success, the application:

- resolves the unique Session by `participant_code`;
- creates a signed, HttpOnly, SameSite=Lax session cookie containing only the Session UUID and cookie issuance metadata;
- redirects to `/session`;
- does not include the participant code in subsequent URLs.

The cookie is an access mechanism, not runtime state. Deleting it does not affect the Session. Re-entering the participant code restores access from PostgreSQL.

Cookie properties:

```text
HttpOnly = true
SameSite = Lax
Secure = configurable; true whenever HTTPS is used
Path = /
Max-Age = configured infrastructure value
Signed = application secret with key rotation handled operationally
```

State-changing forms also carry a server-generated CSRF token bound to the signed session identity. The application rejects absent or invalid CSRF tokens before calling `SessionRuntime`.

### 3.3 Invalid, expired, and terminal access

- Unknown or malformed participant code: redisplay `/join` with a generic “code not recognized” message. Do not reveal whether a similarly shaped code exists.
- Expired or invalid cookie: clear it and redirect to `/join`. The participant may re-enter the code.
- Existing nonterminal Session: render its current authoritative state and permitted action.
- Terminal Session: render a read-only completion or unresolved page; no action form is present.
- Operator-aborted Session, if supported by the existing status vocabulary: render a generic closed-session message.

The POC does not add participant-code expiry or account lockout fields. Session access remains local and opaque; terminal state controls whether experimental actions remain possible.

---

## 4. Participant UI states

The browser owns no independent experiment state machine. Each page or fragment is selected from the current `SessionRuntimeView`.

| Backend condition | Participant sees | Permitted action |
|---|---|---|
| Current Attempt `ASSIGNED`; no opening operation | Short transition/attempt introduction and **Begin** button | Start current Attempt once |
| `INTERVENTION_ACTIVE`; no pending operation | Tutor message history and learner reply form | Submit one Tutor message |
| Tutor LLMCall `STARTED` or `RECEIVED` | Existing chat, disabled input, processing indicator | Refresh/poll only; resume appears only when recoverable |
| Intervention completed and assessment activated | Visually distinct assessment prompt and response form | Submit exactly one response |
| Assessment response committed; Judge pending | Submitted response confirmation and judging indicator | Refresh/poll only |
| Attempt `TECHNICAL_HOLD` in intervention | Existing chat and safe technical-failure notice | Explicit **Retry/Resume** action |
| Attempt `TECHNICAL_HOLD` in judging | Submitted assessment remains read-only and safe technical-failure notice | Explicit **Retry/Resume** action |
| Judgment routed to another Attempt | Brief “next learning attempt” continuation view; no pass/fail scoring detail | Begin the newly assigned Attempt |
| Judgment advances to next transition | Brief transition-continuation view | Begin the new transition’s assigned Attempt |
| Session `COMPLETED`, reason `COMPLETED_EA` | Completion page | None |
| Session `UNRESOLVED` | Neutral unresolved/end page | None |

### 4.1 Information shown during intervention

Show:

- learner-facing Tutor messages;
- participant’s own accepted messages;
- a plain transition progress indicator such as “Part 2 of 4” if approved for participant display;
- remaining interaction availability only if the study protocol intends participants to see it;
- pending or recovery status.

Do not show the pedagogy label by default. Treatment identity remains available to researchers in the database and export, but exposing it to participants is not required for operation and may influence behavior.

### 4.2 Assessment separation

Assessment uses a distinct visual container and explanatory text stating that tutoring is paused. The chat form is absent, not merely disabled. The assessment page contains only the frozen learner-facing prompt, one response field, and one submit action.

### 4.3 Outcome wording

Intermediate pass/fail, Judge evidence, observed SOLO labels, and the next selected pedagogy are not shown. The participant sees only operational continuation language. Terminal completion and unresolved wording must be approved by the researcher because it can affect participant interpretation.

---

## 5. HTTP / HTMX flow

All participant state-changing requests use form encoding, a CSRF token, and a server-rendered idempotency key. Text size limits are enforced before application-service invocation.

### 5.1 Route set

| Method and route | Important input | Idempotency | Backend call | Response | Allowed state |
|---|---|---|---|---|---|
| `GET /` | None | N/A | None | Redirect to `/session` if cookie is valid; otherwise `/join` | Any |
| `GET /join` | None | N/A | None | Full entry page | No valid cookie required |
| `POST /join` | `participant_code`, CSRF for anonymous entry form | Not required; read-only lookup | Session access lookup | `303` to `/session` and signed cookie, or entry page with safe error | Existing Session |
| `POST /leave` | CSRF | Repeat-safe | None | Clear cookie and `303` to `/join` | Any authenticated Session |
| `GET /session` | Signed cookie | N/A | `get_runtime_state` | Full `session.html` page | Any accessible Session |
| `GET /session/state` | Signed cookie | N/A | `get_runtime_state` | `partials/session_main.html` | Any accessible Session |
| `POST /session/actions/start` | CSRF, `idempotency_key` | Required | `start_current_attempt` | Updated `session_main` fragment | Current Attempt `ASSIGNED` |
| `POST /session/actions/tutor-message` | CSRF, `idempotency_key`, `learner_text` | Required | `submit_tutor_message` | Updated `session_main` fragment | `INTERVENTION_ACTIVE`, no pending call, budget remains |
| `POST /session/actions/assessment-response` | CSRF, `idempotency_key`, `response_text` | Required | `submit_assessment_response` | Updated `session_main` fragment | `ASSESSMENT_ACTIVE` |
| `GET /session/operation` | Signed cookie | N/A | `get_runtime_state` | Pending/current-state fragment | Pending, judging, or technical hold; harmless elsewhere |
| `POST /session/actions/resume` | CSRF, `idempotency_key` | Required | `resume_pending_operation` | Updated `session_main` fragment | Recoverable stale/received/held operation |
| `GET /session/terminal` | Signed cookie | N/A | `get_runtime_state` | Full terminal page or redirect to `/session` if nonterminal | Terminal only |
| `GET /health/live` | None | N/A | Process check | Small JSON, `200` | Always after process starts |
| `GET /health/ready` | None | N/A | Read-only readiness check | Small JSON, `200` or `503` | Ready only after bootstrap succeeds |
| `GET /version` | None | N/A | None | Build/version JSON | Any |

### 5.2 Full-page and fragment rules

- Normal browser navigation returns a full page.
- Requests with `HX-Request: true` return only `#session-main` or the narrowest useful partial.
- Every action response is rendered from a fresh post-command state read. The route does not construct a predicted next state.
- Successful POST actions return `200` fragments for HTMX. Non-HTMX form submissions use `303 See Other` to `/session` to avoid resubmission on refresh.
- Participant input errors return `422` with the same action partial and preserved safe input where appropriate.
- Stale phase, different-key duplicate, or concurrency conflict returns `409` with the authoritative `session_main` fragment.
- A tiny global HTMX handler permits safe `409` fragments to replace `#session-main`; no client state is introduced.
- Unexpected errors return a generic `500` page or fragment with a correlation ID.

### 5.3 Idempotency-key rendering

Each enabled action form receives a new UUID idempotency key from the server. The key remains unchanged in that rendered form. Double click, browser retry, or back-button resubmission therefore reaches the same backend idempotency record.

A fresh authoritative render may issue a new key. If the prior logical action is still pending or already consumed the phase, Stage-2 locking and uniqueness rules remain authoritative.

### 5.4 Pending-operation reads

`GET /session/operation` is read-only. It reports state but never retries an LLM call, performs validation, or advances protocol. Recovery always requires `POST /session/actions/resume`.

---

## 6. Jinja / HTMX structure

### 6.1 Templates

| Template | Purpose |
|---|---|
| `base.html` | Document shell, accessibility landmarks, CSS/HTMX assets, correlation-safe error area |
| `entry.html` | Participant code form |
| `session.html` | Full participant page containing `#session-main` |
| `error.html` | Generic full-page error without internals |
| `partials/session_main.html` | Authoritative phase switch; includes exactly one state partial |
| `partials/intervention.html` | Chat layout and allowed action |
| `partials/messages.html` | Ordered accepted learner/Tutor messages |
| `partials/tutor_form.html` | Learner response form with CSRF and idempotency key |
| `partials/pending.html` | Processing status and polling trigger |
| `partials/assessment.html` | Frozen assessment prompt and submission form |
| `partials/technical_hold.html` | Safe recovery explanation and resume form |
| `partials/continuation.html` | Next-attempt or next-transition message and Begin action |
| `partials/terminal.html` | Completed/unresolved read-only result |
| `partials/notice.html` | Validation, stale-state, and duplicate-action notices |

### 6.2 Fragment replacement

The stable replacement boundary is:

```html
<main id="session-main">...</main>
```

Tutor and assessment POSTs replace `#session-main` because a command may legitimately change phases. Pending polling also replaces this boundary, allowing the server to switch from pending to chat, assessment, continuation, hold, or terminal without client-side routing logic.

Message-only partial replacement is optional for normal chat responses, but the implementation should prefer the single `session-main` boundary until a measured UX need justifies finer updates.

### 6.3 Minimal JavaScript

Use HTMX plus a small `app.js` only for:

- accepting known `409` authoritative-state fragments for swapping;
- moving focus to a new notice or first enabled control after a swap;
- optional confirmation before leaving an assessment with unsent local text.

Do not store phase, attempt, messages, assessment, or pending-operation state in JavaScript or browser storage.

### 6.4 Accessibility and rendering safety

- Use semantic form labels, headings, landmarks, and an `aria-live="polite"` pending/status region.
- Preserve keyboard focus after HTMX swaps.
- Render Tutor Markdown through a strict allowlist sanitizer before persistence or display, or render it as escaped plain text for the initial POC.
- Always escape participant text. Never mark learner or provider content safe directly.
- Assessment code blocks use escaped text; hidden scoring context is never present in template input.

---

## 7. Long-running LLM operation UX

### 7.1 Primary pattern

Tutor and Judge commands remain synchronous from the participant's perspective, while the provider adapter performs asynchronous network I/O:

1. The participant submits a form.
2. HTMX disables that form and displays an in-place processing indicator.
3. The route calls the corresponding `SessionRuntime` command.
4. The runtime commits the `STARTED` reservation before awaiting the provider request; no database transaction remains open during that wait.
5. If the request completes normally, the route returns the newly rendered authoritative state.

Use `hx-disabled-elt` and `hx-indicator`; do not depend on custom JavaScript flags to prevent duplicates.

### 7.2 Refresh and disconnect

If the participant refreshes or the connection drops:

- accepted input and the LLM operation reservation already in PostgreSQL remain authoritative;
- reopening `/session` shows the pending state;
- the browser begins read-only polling of `/session/operation` every two seconds while a fresh operation is pending;
- polling stops as soon as the returned fragment no longer contains a polling trigger.

The state read does not launch work. If the original request is still executing, its commit becomes visible on a later poll. If the process was interrupted, the stale/recovery rules apply.

### 7.3 Recovery states

- Fresh `STARTED`: show “Still processing”; continue bounded polling.
- `RECEIVED`: show “Response received; finishing processing” and an explicit Resume button if no active request is finalizing it.
- Stale `STARTED`: show recoverable technical interruption and a Resume button.
- `TECHNICAL_HOLD` with retry allowance: show a Resume button.
- Exhausted retry allowance: show a neutral “staff assistance is required” state; do not invite repeated provider calls.

The Resume form has its own idempotency key. Repeated resume clicks return the same operation/result.

### 7.4 Polling limits

Polling is limited to the current participant page and uses a modest fixed interval. It is not a job runner. After an infrastructure-configured maximum display period, the UI replaces continuous polling with an explicit Refresh button while preserving the same backend operation.

No WebSocket, server-sent event, worker, or message broker is needed for the POC.

---

## 8. Idempotency, refresh, back button, and recovery behavior

| Situation | Required behavior |
|---|---|
| Double Tutor submit | Same form key and request returns the existing operation/result; no second learner Message or Tutor call |
| Different Tutor form/key while call pending | `409 OPERATION_IN_PROGRESS`; authoritative pending fragment replaces stale UI |
| Double assessment submit | Same key returns original acceptance/result; different key reports already submitted; never creates a second response or Judge call |
| Browser reload | `GET /session` rereads PostgreSQL and renders current phase; it never repeats the previous POST |
| Reopen same session | Signed cookie or re-entered participant code resolves the same Session and current state |
| Browser back | Old form may display from browser cache, but its idempotency key and backend phase checks prevent another logical action; response replaces it with current state |
| Two tabs | Both share the Session; Session row locking, pending-call constraints, and idempotency allow one valid mutation. The losing tab receives current state |
| Network fails after form submission | Participant reloads. If reservation/commit exists, pending or completed state is shown; if no commit exists, the original form may be safely submitted again with the same key |
| Provider completes after browser disconnect | Server finalization commits normally if the request continues; later state reads show the result |
| Process dies after raw receipt | `RECEIVED` response is validated from storage on explicit resume without another provider call |
| Process dies before raw receipt commit | After stale threshold, resume may create a bounded retry in the same retry group; only one domain result may commit |
| Application restarts | Existing sessions and operations are discovered from PostgreSQL; no automatic protocol advancement occurs during startup |

The application should send `Cache-Control: no-store` on participant pages and fragments. This reduces stale browser rendering but does not replace server-side phase and idempotency checks.

---

## 9. Error UX

### 9.1 Error classes

| Error class | HTTP/UI behavior | Protocol effect |
|---|---|---|
| Missing/too-long/invalid participant text | `422`, inline form message | None |
| Invalid participant code or cookie | Generic join error or redirect | None |
| Stale page/phase | `409`, replace with authoritative state and short notice | None |
| Duplicate same-key action | Return original result/state with informational notice | None |
| Duplicate different-key assessment | `409`, show already submitted/current judging state | None |
| Tutor provider/validation failure | Technical-hold fragment with retry/resume when allowed | Same Attempt and pedagogy retained |
| Judge provider/validation failure | Technical-hold fragment; submitted response remains visible/read-only | No learner failure or progression |
| Provider unavailable | Safe technical message; retry according to Stage 2 | No learner failure |
| Protocol invariant violation | Generic participant message plus high-severity log/correlation ID | Freeze affected action; no improvisation |
| Database/internal error | Generic retry-later page/fragment and correlation ID | Transaction rollback; no partial state |
| Invalid study or migration at startup | App not ready and process exits nonzero | No participant traffic accepted |

### 9.2 Participant-action versus technical failure

Participant-action errors use concrete language such as “Please enter a response” or “This assessment was already submitted.” Technical failures use neutral language such as “The system could not finish this step. Your progress has been saved.”

Do not imply that a technical error was caused by the learner, and do not display provider status codes, exception messages, retry counts that reveal internals, raw model output, prompt text, Judge evidence, scoring criteria, database details, or secrets.

### 9.3 Correlation IDs

Every request receives a correlation ID. Unexpected-error pages show only that ID and a short instruction for contacting the researcher. Logs and protocol/LLM records carry the same ID where applicable.

---

## 10. Environment and configuration

Environment configuration is infrastructure/runtime configuration only. Transition order, pedagogy behavior, attempts, assessment behavior, rubric rules, and intervention budgets remain in the frozen operational study.

### 10.1 Proposed `.env.example` surface

```dotenv
# PostgreSQL
POSTGRES_DB=solo_harness
POSTGRES_USER=solo_harness
POSTGRES_PASSWORD=change-me
DATABASE_URL=postgresql+psycopg://solo_harness:change-me@postgres:5432/solo_harness

# Study activation
STUDY_DIR=/app/studies/python_fibonacci_memoization/v0.1

# AICredits.in provider
LLM_PROVIDER=aicredits_openai_compatible
AICREDITS_BASE_URL=
AICREDITS_API_KEY=
LLM_STRUCTURED_OUTPUT_MODE=provider_native_json_schema
TUTOR_MODEL=
JUDGE_MODEL=
TUTOR_TEMPERATURE=0.2
JUDGE_TEMPERATURE=0
REPAIR_TEMPERATURE=0
TUTOR_MAX_OUTPUT_TOKENS=2000
JUDGE_MAX_OUTPUT_TOKENS=2500
LLM_CONNECT_TIMEOUT_SECONDS=10
LLM_REQUEST_TIMEOUT_SECONDS=120
LLM_STALE_GRACE_SECONDS=30

# Web application
APP_HOST=0.0.0.0
APP_PORT=8000
APP_BUILD_ID=dev
LOG_LEVEL=INFO
SESSION_COOKIE_SECRET=
SESSION_COOKIE_MAX_AGE_SECONDS=43200
SESSION_COOKIE_SECURE=false
```

### 10.2 Responsibilities and validation

- `DATABASE_URL`: app-to-PostgreSQL connection; reject non-PostgreSQL URLs.
- `STUDY_DIR`: one mounted operational YAML version to validate and activate at boot.
- AICredits variables: adapter endpoint, credential, and capability, never study semantics. The OpenAI-compatible adapter path is used when supported; any provider-specific difference remains inside that adapter.
- Model/generation variables: role-specific effective settings, copied without secrets into Session runtime snapshots and LLMCall records.
- Timeout/stale values: infrastructure recovery timing; require positive bounded values and ensure stale threshold is greater than provider timeout.
- `APP_BUILD_ID`: immutable image/commit identifier copied to each Session.
- Cookie settings: browser access protection only.

Startup fails clearly for absent required secrets, invalid URLs, empty model IDs, malformed numeric settings, an unsafe default cookie secret, or contradictory timeout values. Secret values are represented with `SecretStr`-equivalent handling and never included in settings dumps.

Provider connectivity is not checked as a readiness prerequisite. Configuration shape is validated, but network/provider failure is discovered and persisted at call time.

---

## 11. Docker Compose and container design

### 11.1 Services

| Service | Responsibility |
|---|---|
| `app` | Bootstrap, migrations, study validation/activation, FastAPI, templates/static assets, all Stage-2 runtime logic, CLI session/export commands |
| `postgres` | Durable relational state and audit evidence |

### 11.2 Networking and ports

- `app` listens on container port 8000 and is published as `127.0.0.1:${APP_PORT:-8000}:8000` by default.
- `postgres` is reachable as `postgres:5432` on the private Compose network.
- PostgreSQL need not be published to the host. Researchers can use `docker compose exec postgres psql` or the app export CLI.
- The app makes outbound HTTPS requests to the configured AICredits endpoint through asynchronous provider I/O.

Binding the app to loopback matches the local POC boundary. LAN exposure requires an explicit Compose override and corresponding secure-cookie/TLS review.

### 11.3 Volumes and mounts

```text
postgres volume:
  pgdata → /var/lib/postgresql/data

app bind mount:
  selected operational study directory → /app/studies/...:ro

optional export bind mount:
  ./exports → /app/exports
```

Application code, templates, migrations, and static assets are built into the image for pilot use. They are not host-mounted in the pilot Compose configuration.

### 11.4 Environment loading

Compose loads `.env` for local substitution and passes an explicit allowlist of variables to each service. PostgreSQL receives only its database variables. The app receives `DATABASE_URL`, study path, provider/model settings, web settings, and build ID.

No secret is baked into the image or stored in operational YAML.

### 11.5 Health and dependency behavior

- PostgreSQL healthcheck uses `pg_isready` with the configured database/user.
- `app` depends on PostgreSQL being healthy, then performs its own bounded connection retry because Compose dependency order is not a transaction guarantee.
- App liveness checks `/health/live`.
- App readiness checks `/health/ready` and succeeds only after migration, study activation, and catalog construction.
- Readiness does not call the LLM provider.

### 11.6 Migration and application command

The app container has one entrypoint that:

1. Loads and validates infrastructure settings.
2. Waits for PostgreSQL within a bounded timeout.
3. Runs the approved bootstrap under the PostgreSQL advisory lock.
4. Starts one Uvicorn process only after bootstrap succeeds.

Multiple Uvicorn workers are unnecessary for the local POC. One process uses asynchronous provider I/O, so a slow AICredits request does not block polling or state reads; database correctness still protects concurrent browser requests.

### 11.7 Restart policy

- `postgres`: `unless-stopped`.
- `app`: `on-failure:3` for transient boot failures without hiding a persistent invalid study or migration loop.

For development, an override may disable restarts and mount source code, but that is not the pilot configuration.

---

## 12. Startup and shutdown lifecycle

### 12.1 Fresh start

```text
docker compose up
    ↓
PostgreSQL initializes persistent volume
    ↓
PostgreSQL healthcheck passes
    ↓
app validates environment configuration
    ↓
app connects and obtains advisory bootstrap lock
    ↓
Alembic revision checked and upgraded to one known head
    ↓
operational YAML loaded from read-only mount
    ↓
local and cross-pack validation
    ↓
canonical authored content → content_hash
    ↓
compile snapshot using compiler_contract_version
    ↓
compiled snapshot → snapshot_hash
    ↓
immutable StudyVersion inserted/reused and activated
    ↓
StudyCatalog constructed and existing snapshot compatibility checked
    ↓
FastAPI begins serving; readiness becomes 200
```

The operational YAML may be activated despite descriptive “draft” wording in Markdown. Runtime validity and any external research/pilot approval remain separate concerns.

### 12.2 Failure behavior

- Invalid environment: exit nonzero before DB mutation when possible.
- PostgreSQL unavailable beyond the bounded wait: exit nonzero.
- Database revision ahead/divergent or migration failure: exit nonzero and remain unready.
- Invalid study: print a concise validation summary, log full structured diagnostics, do not partially activate, and exit nonzero.
- Content-version collision: refuse activation and exit nonzero.
- Unsupported snapshot reader for a nonterminal Session: exit nonzero rather than reinterpret that Session.
- Provider unavailable: do not block boot; fail the later call into the Stage-2 technical-recovery path.

### 12.3 Graceful shutdown

On SIGTERM/SIGINT:

1. Stop accepting new requests.
2. Allow in-flight HTTP requests a bounded grace period.
3. Dispose database connections.
4. Exit.

The application does not attempt to fabricate terminal LLMCall results during shutdown. A persisted `STARTED` call that does not finish becomes recoverable after its stale threshold. A committed `RECEIVED` call remains available for validation on resume.

### 12.4 Restart with existing sessions

Startup does not automatically call providers or advance Sessions. It validates that every nonterminal Session’s StudyVersion snapshot is readable. Participant reads show current state, and explicit Resume handles incomplete operations according to Stage 2.

---

## 13. Logging and observability

### 13.1 Log format

Write structured JSON logs to stdout/stderr. Compose is the initial log collector.

Common fields:

```text
timestamp
level
event
app_build_id
correlation_id
session_id when relevant
attempt_id when relevant
operation_id / llm_call_id when relevant
error_class when relevant
duration_ms when relevant
```

### 13.2 Required operational events

Log:

- application start, settings validation success, and shutdown;
- database connection and migration revision/result;
- study validation, content hash, compiler contract, snapshot hash, reuse/insertion, and activation;
- Session creation, entry, phase changes, and terminal status;
- LLM logical operation start/final status and provider request ID where available;
- provider timeout/rate-limit/5xx/authentication failures;
- structured-output validation and repair outcome;
- technical hold and recovery;
- protocol invariant violation;
- database connectivity, transaction, and constraint failures;
- audit export start/result.

### 13.3 Redaction and data minimization

Do not log:

- API keys, authorization headers, cookie values, CSRF tokens, or participant codes;
- full prompts or raw provider responses already persisted in `llm_calls`;
- full learner messages or assessment responses;
- hidden assessment scoring context;
- unnecessary PII;
- database URLs containing credentials.

Logs may include stable internal UUIDs because they are needed for diagnosis, but participant codes are never used as log identifiers.

### 13.4 Minimal metrics

No separate metrics service is required. Logs and database queries should make it possible to determine call latency, failure class, retry count, held Sessions, and readiness. Research facts remain in normalized records/events, not reconstructed from application logs.

---

## 14. Research audit and export

### 14.1 Inspection mechanisms

The POC provides:

- direct SQL through `docker compose exec postgres psql` for authorized local researchers;
- a read-only CLI summary command;
- a read-only full Session export command.

No web dashboard or participant-accessible research endpoint is required.

Suggested commands:

```text
python -m solo_harness.cli.sessions inspect --session-id <uuid>
python -m solo_harness.cli.export session --session-id <uuid> --output /app/exports/<uuid>.json
```

### 14.2 Export format

Use one versioned UTF-8 JSON document per Session. Arrays are ordered by their persisted sequence/timestamp keys. The CLI writes atomically to a new file, never mutates database evidence, and prints the file SHA-256.

Top-level shape:

```text
export_schema_version
exported_at
application_build_id
study_version:
    study_version_id
    study_id
    content_version
    content_hash
    compiler_contract_version
    snapshot_schema_version
    snapshot_hash
session
attempts
messages
learner_history_snapshots
assessment_instances
assessment_responses
llm_calls
judgments
rubric_evaluations
protocol_events
idempotency_summary
```

The full research export includes exact learner responses, exact compiled requests, raw provider responses, parsed outputs, and hidden scoring snapshots because it is an authorized local research artifact. It must be written only to an explicitly chosen local path and handled as sensitive research data.

The export allows reconstruction of:

- Session progression and terminal reason;
- pedagogy order and eligible/excluded candidates;
- assessment forms used and candidate pools;
- exact learner inputs;
- Tutor/Judge calls, retries, and failures;
- accepted Tutor traces and judgments;
- deterministic rubric inputs/results;
- protocol events;
- content, compiler, snapshot, configuration, model, and application provenance.

### 14.3 Export consistency

The exporter runs in a read-only repeatable-read transaction or exports from a terminal Session. It records the database event sequence observed. This prevents a mixed view if an active Session changes during export.

---

## 15. Testing strategy

### 15.1 Unit tests

Retain the Stage-1/2 unit suites and add tests for:

- participant-safe presenter mappings for every Session phase/status;
- hidden-field exclusion from all participant view models;
- cookie signing/expiry and CSRF verification;
- route input size/empty-value validation;
- full-page versus HTMX response selection;
- error-to-partial mapping;
- export schema and stable ordering.

### 15.2 Route and template tests

Using FastAPI’s ASGI test client and fake `SessionRuntime`:

- valid and invalid code entry;
- cookie creation, clearing, expiry, and unauthorized redirect;
- full `/session` page for every participant state;
- HTMX fragments contain one `#session-main` root;
- exactly one permitted action is rendered for each state;
- Tutor form absent during assessment;
- assessment form absent after submission;
- hidden scoring/Judge/provider fields never appear in HTML;
- `Cache-Control: no-store` on participant state;
- expected `422`, `409`, `500`, liveness, and readiness behavior.

### 15.3 Idempotency, refresh, and recovery tests

Against PostgreSQL and fake delayed providers:

- double-click Tutor form creates one learner Message and one logical operation;
- same idempotency key/same body returns original result;
- same key/different body conflicts;
- different key while Tutor pending does not create another call;
- double assessment submission creates one response and one Judge operation;
- reload during `STARTED` renders pending and does not call provider;
- `RECEIVED` resumes parsing without provider call;
- stale `STARTED` resumes inside the same retry group;
- two concurrent tabs produce one valid state mutation;
- back-button resubmission returns current authoritative state;
- disconnect after reservation preserves recoverability;
- disconnect after provider completion exposes committed result on refresh.

### 15.4 PostgreSQL integration tests

Use real PostgreSQL, migrations from zero, and transaction/concurrency tests for:

- StudyVersion immutability and Session binding;
- row locks, uniqueness constraints, and idempotency records;
- current-state mutation plus event append atomicity;
- LLMCall lifecycle and retry lineage;
- assessment freshness and one-response constraint;
- Judge/rubric/progression atomic finalization;
- read-only repeatable export consistency.

SQLite is not an acceptable substitute for these tests.

### 15.5 Mocked end-to-end success flow

One automated test runs through the HTTP surface with fixed fake selectors and scripted fake Tutor/Judge outputs:

```text
researcher creates Session
→ participant joins
→ begin C1 Attempt
→ intervention chat completes
→ fresh C1 assessment submitted
→ Judge evidence accepted
→ deterministic C1 pass
→ begin C2
→ C2 pass
→ begin C3
→ C3 pass
→ begin C4
→ C4 pass
→ COMPLETED_EA terminal page
```

The test asserts study binding, treatment assignment, assessment freshness, Judge blindness, exact request/response persistence, deterministic progression, event ordering, refresh safety, and final export completeness.

### 15.6 Required failure flows

- One assessment failure creates the next same-transition Attempt with a different pedagogy and structured history; the later Attempt succeeds.
- Three valid failures use each pedagogy once and end `UNRESOLVED_<transition>` with no fourth Attempt.
- Tutor technical failure enters hold, retains the same Attempt/pedagogy and learner message, and resumes successfully.
- Judge technical failure retains the exact AssessmentResponse, creates no learner failure, and resumes successfully.
- Invalid Tutor/Judge output exercises one repair and bounded terminal technical hold.
- Provider timeout plus process interruption exercises stale recovery without duplicate domain results.

### 15.7 Docker and real-provider smoke tests

Fresh-machine/clean-volume smoke test:

1. Build images.
2. Start the two-service Compose stack.
3. Verify migration from zero and readiness.
4. Create a Session through the CLI.
5. Complete a short fake-provider path.
6. Restart the app and verify Session resume.
7. Export the Session and validate its schema/hash.

Real-provider smoke tests are separately marked, require explicit credentials, use a dedicated nonresearch Session, and are excluded from the normal test suite. They verify provider connectivity, structured-output mode, persistence, and one Tutor/Judge round trip without being a CI prerequisite.

---

## 16. Recommended implementation order

1. **Repository and configuration scaffold**  
   Create packaging, typed infrastructure settings, structured logging, and test layout.

2. **Compose and PostgreSQL connectivity**  
   Build the two services, healthchecks, persistent volume, and clean startup path.

3. **Stage-1 schema and migrations**  
   Implement the reviewed SQLAlchemy models, constraints, triggers, Alembic history, and bootstrap lock.

4. **Operational study transcription**  
   Produce and human-review the YAML package, including explicit runtime budgets, without making Markdown a runtime dependency.

5. **Study loader/compiler/version activation**  
   Implement validation, separate content/snapshot identities, embedded compiled snapshot, catalog, and startup activation.

6. **Protocol core with fake selectors/models**  
   Implement Session/Attempt progression, standard random selection with audit records, assessment freshness, deterministic rubric evaluation, and history.

7. **LLM persistence and adapter**  
   Implement provider-neutral request preparation, `STARTED → RECEIVED → terminal`, retries/repair, and fake client.

8. **Tutor and Judge runtime**  
   Implement prompt compilation, fidelity/blindness boundaries, structured validation, technical hold, and resume.

9. **Application-facing SessionRuntime commands**  
   Complete participant commands including `start_current_attempt`, state views, idempotency, and transaction orchestration.

10. **Participant web shell**  
    Implement entry cookie/CSRF handling, routes, presenters, Jinja templates, HTMX fragments, polling, and error UX.

11. **Research CLI and export**  
    Add Session creation/inspection and versioned JSON export.

12. **Integration and mocked E2E tests**  
    Cover success, retries, three-failure unresolved, concurrency, refresh, restart, and exports.

13. **Fresh Compose and real-provider smoke tests**  
    Validate the pilot image/configuration, freeze the application build and model settings, and rehearse recovery/export procedures.

Each step should leave the preceding layer testable. The protocol and full participant lifecycle must work with fake LLMs before real-provider behavior is introduced.

---

## 17. Final POC acceptance criteria

- [ ] A clean machine can run the two-service stack with `docker compose up`.
- [ ] PostgreSQL reaches healthy state; migrations reach exactly one expected head.
- [ ] Invalid configuration, migration state, or operational study prevents readiness with a clear diagnostic.
- [ ] Reviewed operational YAML validates, compiles, freezes, and activates without depending on Markdown at runtime.
- [ ] `content_hash`, `compiler_contract_version`, and `snapshot_hash` are stored distinctly in the immutable StudyVersion.
- [ ] Every Session remains bound only to its original `study_version_id` and resumes after app restart.
- [ ] Researcher CLI creates a minimal opaque participant code without collecting PII.
- [ ] Signed-cookie entry, CSRF protection, refresh, reopening, back navigation, and two-tab conflicts behave safely.
- [ ] Pedagogy selection uses a trustworthy standard random mechanism, never repeats within a transition, and preserves its complete audit record.
- [ ] The assigned pedagogy remains fixed and prohibited/out-of-scope material is rejected.
- [ ] Intervention stages remain guidance/trace unless the study explicitly requires strict sequencing.
- [ ] Every completed intervention receives one fresh, pedagogy-blind assessment.
- [ ] Tutor interaction is unavailable during assessment.
- [ ] Exact assessment response is committed once.
- [ ] Judge input is structurally blind to pedagogy, Tutor dialogue, and prior failures.
- [ ] Exact Tutor/Judge request bodies and raw responses are preserved with model/provider parameters and call lifecycle.
- [ ] Deterministic rubric evaluation alone produces pass/fail and Protocol Engine alone advances/retries/stops.
- [ ] Success advances exactly one transition; three failures end unresolved without a renewed cycle.
- [ ] Technical failure never becomes learner failure, never consumes a new pedagogy, and can resume from persisted state.
- [ ] `RECEIVED` operations can finalize without another provider call; stale `STARTED` operations follow bounded recovery.
- [ ] Participant HTML exposes no hidden assessment context, Judge evidence, internal prompts, raw provider output, secrets, or stack traces.
- [ ] Database evidence and protocol events reconstruct the complete Session.
- [ ] Versioned JSON export contains progression, selections, responses, calls, judgments, deterministic results, events, and study/runtime provenance.
- [ ] Full mocked C1→C4→EA E2E passes.
- [ ] Failure-then-success, three-failure unresolved, Tutor recovery, and Judge recovery E2E paths pass.
- [ ] A separately invoked real-provider smoke test succeeds with the frozen pilot configuration.
- [ ] Researcher-approved participant wording, intervention budgets, model IDs, generation parameters, and pilot study version are frozen before enrollment.

---

## 18. Implementation decisions made

| Decision | Rationale | Alternatives considered | Consequence |
|---|---|---|---|
| Keep one FastAPI/Jinja2/HTMX modular monolith | Matches the local POC and approved runtime boundary | SPA plus API; separate frontend | One deployable image and server-owned state |
| Use researcher CLI for Session creation and audit export | Avoids unauthenticated admin routes and an unnecessary dashboard | Research web console; direct SQL only | Researchers use local container commands |
| Use opaque participant code only for entry, then a signed HttpOnly cookie | Keeps identity minimal and codes out of normal URLs | Code on every URL; account authentication | Cookie secret becomes required infrastructure configuration |
| Add CSRF protection to cookie-authenticated forms | Protects localhost state-changing routes from cross-site submissions | SameSite cookie alone | Every POST form carries a server-bound token |
| Render one authoritative `#session-main` fragment | Any command can change phase; one boundary keeps HTMX logic simple | Fine-grained client orchestration; full reload after every action | Some responses replace more HTML than strictly necessary |
| Use synchronous HTMX POST plus asynchronous provider I/O and read-only polling | Preserves Stage-2 execution model without a queue or blocked event loop | WebSockets; background workers; manual refresh only | Browser disconnect recovery depends on persisted operation state |
| Require explicit POST for stale/held resume | A GET must not call a provider or mutate experiment state | Auto-resume during polling | Participant may need one Retry/Resume click |
| Use server-rendered UUID idempotency keys | Handles double click, retry, and back-button replay without client state | JavaScript-generated keys; no keys | Each action form is a single logical command |
| Return authoritative state on stale/concurrent action | Lets all tabs converge on PostgreSQL state | Display only an error and require reload | A small HTMX 409 swap handler is needed |
| Hide pedagogy and intermediate Judge/pass-fail details from participant UI | They are unnecessary for the task and may influence behavior | Display full progress/audit data | Researchers use database/export for experimental detail |
| Do not require provider health at startup | Provider outages must not prevent inspection/resume of local state | Provider readiness probe | First provider action may enter technical hold |
| Build code/templates into the pilot image and mount study read-only | Makes the pilot artifact reproducible while protecting study files | Bind-mount whole repository | Code changes require image rebuild |
| Run one Uvicorn process with asynchronous provider I/O | Sufficient for a local POC while keeping state reads responsive during AICredits calls | Multiple workers | Provider adapter must not use blocking network I/O on the event loop |
| Use structured stdout logs and database audit records | Minimal operations with research truth in PostgreSQL | External observability stack | Operational diagnosis uses Compose logs and SQL |
| Export one versioned JSON document plus SHA-256 | Preserves nested evidence and provenance with minimal tooling | Dashboard; CSV bundle; database dump | Researchers may derive tabular files downstream |
| Add `SessionRuntime.start_current_attempt` | Provides the missing web command for required opening Tutor turns | Trigger opening implicitly on GET; call TutorRuntime from route | Opening remains explicit, idempotent, and inside SessionRuntime |

---

## 19. Ambiguities / questions requiring approval

1. **Participant-facing outcome wording**

   Approve the exact language for next attempt, next transition, successful completion, and unresolved termination. Recommendation: keep it neutral and avoid showing treatment identity or detailed scoring.

2. **Participant progress visibility**

   Decide whether participants may see “transition 2 of 4,” attempt count, or remaining Tutor turns. Recommendation: show coarse transition progress only if it does not conflict with the research protocol; do not show remaining pedagogy alternatives.

3. **Intervention budgets**

   Exact positive Tutor-turn limits, and any elapsed-time limits, must be present in operational YAML before that StudyVersion is frozen. They are study-config decisions, not approval-state gates or environment defaults.

4. **Model and generation settings**

   Tutor/Judge model IDs, structured-output capability, temperatures, output-token limits, and timeouts must be selected and frozen for the pilot runtime configuration.

5. **Cookie security for the pilot network**

   The default design binds to loopback and permits `Secure=false` for local HTTP. If participants connect over a LAN, approve HTTPS termination and require secure cookies before enrollment.

6. **Research export retention and access**

   Define who may run full exports, where sensitive exports are stored, how long they are retained, and whether participant codes must be omitted or pseudonymized further.

7. **Exhausted technical recovery**

   Stage 2 retains the Session in technical hold when retry allowance is exhausted. Approve the operator procedure: inspect, correct infrastructure, then invoke an explicitly authorized resume, or close the Session as a technical termination without recording learner failure.

8. **Participant-code usability**

   Recommendation: use a high-entropy copy/paste code. If manual entry is required, approve a shorter formatted code and the associated local guessing risk rather than adding user accounts.
