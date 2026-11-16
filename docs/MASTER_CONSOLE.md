# EkagraAI Master Testing Console (developer-only)

## Enable in an isolated local environment

Use a **disposable PostgreSQL database** with migrations and registered immutable `v0.5.5` study. Bind HTTP to localhost, not a public interface. Keep the participant deployment disabled for this test environment.

```dotenv
ENABLE_V051_INTERNAL_TESTING=true
ENABLE_MASTER_TEST_CONSOLE=true
V051_INTERNAL_TESTING_TOKEN=<strong-random-staff-token>
WEB_SESSION_SECRET=<independent-strong-random-cookie-secret>
V051_INTERNAL_CANDIDATE_VERSION=v0.5.5
```

`ENABLE_MASTER_TEST_CONSOLE` defaults to false. The console also requires the existing internal-testing switch, token, and a non-default cookie signing secret. Do not check real secret values into Git.

Open `http://localhost:8000/internal/master`, authenticate with the testing token, choose **section C1–C4**, **pedagogy P1/P2/P3/Random**, and **Teaching** or **Direct assessment**. Direct assessment can select Set A/B/C/Random. Launch opens the existing learner interface. The console provides recorder-readiness information and a per-session trace ZIP download. The last test session can be accessed again by opening `/internal/master` in the same authorized browser.

Each launch creates one `DEV-...` participant ID with synthetic age 20, gender `other`, and qualification `undergraduate`. Internal session/config/event markers distinguish these records from real research data; **exclude marked sessions from participant analysis**. Jumping to a later section initializes its starting SOLO state but does not claim prior sections passed. Direct assessment does not create teaching evidence, PAAS responses, or a fake assessment-build LLM call. Actual submission and Assessment Judge grading remain unchanged, as do normal retries.

Exports include session, attempts, instruction-progress ledger, Conversation Judge decisions, LLM calls, assessments and responses, UI events, protocol events, artifact manifest metadata and available session-local telemetry (up to 64 MiB). Files outside the session directory, including host capture-run media, are referenced by metadata rather than copied into the ZIP. Trace export is authorized only for synthetic Master Console sessions.

No scientific study content, assessments, normal participant enrollment or migrations are changed by this feature. Run targeted tests, the full regression suite, disposable PostgreSQL lifecycle checks and a real Docker/browser smoke test before enabling the console.
