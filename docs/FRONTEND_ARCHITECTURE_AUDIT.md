# Ekagra AI — Frontend Architecture Audit

| | |
|---|---|
| **Phase** | 1 of 8 — audit only. No application code, backend code, packages, or migrations were changed. |
| **Branch audited** | `feature/frontend-work` @ `5ead72a` (+ 4 uncommitted modified files, see §J.1) |
| **Source of truth** | The code as it runs today. Where documentation disagrees with code, the code wins and the disagreement is listed in §J.4. |
| **Method** | Full read of `web.py`, `templates/*`, `static/*`, `runtime/engine.py`, `runtime/ai.py`, `telemetry.py`, `db/models.py`, `config.py`, `main.py`, study validation/compiler, migrations, the study YAML, the e2e tests and the data-collection docs. Nothing was executed. |

---

## Executive summary

1. **There is no separate frontend.** The "frontend" is two server-rendered Jinja2 templates (`join.html`, `session.html`) plus one partial pair, hosted inside the FastAPI app, enhanced with HTMX (loaded from a CDN) and ~600 lines of vanilla JS/inline CSS. There is no SPA, bundler, `package.json`, component library, or client router.
2. **The participant journey is a protocol state machine, not a page flow.** What the participant sees is a projection (`ParticipantApplication.view()`) of `Session.phase` × `Attempt.status`. Every screen in the proposed journey that is not "tutor chat" or "open-text assessment" (consent, intro, objectives, What–Why–How, recap, NASA-TLX, MCQ, completion) **does not exist today and has no backend state to hang on.**
3. **The current experimental design conflicts with the new constraints.** Today pedagogy is chosen **per attempt, at random, without replacement**, and a *failed* assessment **switches the participant to a different pedagogy** (up to 3 attempts per transition). The new requirement ("participants may not change their assigned pedagogy", "controlled pseudo-randomized assignment", "12 conditions = 4 × 3") cannot be met by frontend work alone, and it contradicts a DB uniqueness constraint and a validated protocol enum. **This is the single biggest decision needed before Phase 2** (§E.3, §J.2).
4. **Telemetry is tightly coupled to template markup.** Specific `data-*` attributes, element IDs, form `hx-post` URLs and CSS class names are read by `participant_telemetry.js` / `participant_keyboard.js`, and event types/surfaces are server-side whitelists. Any template rewrite must preserve those hooks or the research record silently degrades.
5. **Most of the existing visual shell is reusable** (design tokens, dark mode, collapsible sidebar, chat composer, processing/retry/idempotency patterns). The big structural change is replacing "Section N → [chat → assessment]" with a multi-stage journey that has a *common* frame (intro/objectives/recap/TLX/MCQ/completion) around a *pedagogy-specific* teaching core.

---

## A. Existing architecture and technology stack

### A.1 Stack

| Layer | Technology | Where |
|---|---|---|
| Server / routing | FastAPI (`>=0.115`), single `APIRouter` | `src/solo_harness/web.py`, `main.py` |
| Rendering | Jinja2 server-side templates (`Jinja2Templates`) | `src/solo_harness/templates/` |
| Interactivity | **HTMX 2.0.4 from `https://unpkg.com/htmx.org@2.0.4`** (no SRI, no local copy) + hand-written vanilla JS | `session.html` lines 8, 255–309 |
| Styling | Hand-written CSS **inline in each template's `<style>`** (≈235 lines in `session.html`, ≈80 in `join.html`); CSS custom properties for tokens; light/dark via `prefers-color-scheme` **and** `data-theme` | templates |
| Theme | `static/theme.js` (localStorage `ekagra-theme`, try/catch-guarded) | `static/theme.js` |
| Telemetry (client) | Vendored rrweb 2.1.7 + `participant_telemetry.js` (rrweb + semantic UI events) + `participant_keyboard.js` (coarse keystroke dynamics) | `static/telemetry/`, `static/vendor/rrweb/2.1.7/` |
| Persistence | PostgreSQL via SQLAlchemy 2; Alembic migrations run **at app startup** (`bootstrap()`) | `db/`, `migrations/`, `bootstrap.py` |
| LLM | OpenAI-compatible HTTP client; Tutor / Assessment-generator / Judge roles; strict JSON-schema outputs | `runtime/ai.py` |
| Study content | Authored YAML → validated → compiled → hashed immutable `StudyVersion` | `studies/`, `studies/python_fibonacci_memoization/v0.1/` |
| Packaging | Docker + compose; Python 3.12 | `Dockerfile`, `compose.yaml` |
| Tests | pytest; Playwright e2e (`tests/e2e/test_participant_browser.py`); 65 test functions total | `tests/` |

There is **no** Node toolchain, TypeScript, Tailwind, component framework, icon library, or font loading (CSS names `Inter` but falls back to system fonts — no `@font-face`/Google Fonts).

### A.2 Architecture pattern

```
Browser ──HTMX form POST (+ idempotency_key)──▶ FastAPI route (web.py)
                                                   │ reserve LLMCall row (idempotent)
                                                   │ BackgroundTasks → run_operation()
                                                   ▼
                      AIExecutionRuntime ──▶ SessionRuntime (engine.py: state machine)
                                                   ▼
                                              PostgreSQL
Browser ◀── HTML fragment (#session-main) ◀── view() projection ◀──┘
        (polls GET /session/operation every 1 s while an LLM call is pending; 204 = no change)
```

Key properties that the redesign must respect:

* **One swap target.** Almost every action returns the full `partials/session_main.html` and replaces `#session-main` (`hx-swap="outerHTML"`). The tutor send action is the one exception: it swaps only `#tutor-composer` (and re-targets to `#session-main` if the operation already finished).
* **`display: contents` trick.** `#session-main` is `display:contents`, so its children (`.section-nav`, `.panel`) participate directly in the `.shell` CSS grid defined in `session.html`. The sidebar nav is *inside* the swapped fragment.
* **Server is authoritative.** All state transitions are server-side; the browser never decides what comes next.
* **Idempotent LLM actions.** `begin`, `tutor-message`, `assessment-response`, `retry` carry a per-render `idempotency_key` (`IdempotencyRecord`, request-hash checked). `next` and `finish` do **not**.
* **Progressive-enhancement fallback.** If HTMX fails to load, an inline `fetch`-based fallback in `session.html` (lines 274–278) replicates submit + 1 s polling. This is the only thing that makes the app survive a CDN failure.
* **Single-participant process.** `ParticipantApplication.active_session_id` is an **in-memory attribute of the app process**. There is no cookie, token, or per-browser session; `/session` simply serves whichever session this process activated. README states "one installation supports one active participant at a time".

### A.3 Routing (complete)

| Method | Path | Purpose | Returns |
|---|---|---|---|
| GET | `/`, `/join` | Entry page | `join.html` |
| POST | `/join` (`institutional_id`, `acknowledged`) | Create session; 403 + error on failure | 303 → `/session` |
| POST | `/leave` | Deactivate in-memory session | 303 → `/join` |
| GET | `/session` | Full page for current section | `session.html` |
| GET | `/session/sections/{n}` | Review a completed section (read-only) or current one | `session.html` |
| GET | `/session/operation` | Poll; 204 while pending, else fragment | `session_main.html` / 204 |
| POST | `/session/actions/begin` | Start tutor conversation (LLM) | fragment |
| POST | `/session/actions/tutor-message` (`learner_text` ≤ 8000) | Learner turn (LLM) | `tutor_composer.html` or fragment |
| POST | `/session/actions/assessment-response` (`response_text` ≤ 12000) | Submit assessment (LLM Judge) | fragment |
| POST | `/session/actions/retry` | Re-reserve failed/stale LLM call | fragment |
| POST | `/session/actions/next` | `advance_section` | fragment |
| POST | `/session/actions/finish` | `finish_session` | fragment |
| POST | `/session/telemetry/rrweb` | rrweb batch → NDJSON file | JSON |
| POST | `/session/telemetry/keyboard` | keyboard dynamics → NDJSON file | JSON |
| POST | `/session/telemetry/ui-events` | semantic UI events → `participant_ui_events` | JSON |
| GET | `/health/live`, `/health/ready`, `/version` | ops | JSON |
| — | `/static/*` | `StaticFiles` mount | — |

No JSON data API exists for the participant UI. There is no authentication beyond the process-level active session.

---

## B. Existing frontend pages and their functionality

### B.1 `join.html` — study introduction + entry (`GET/POST /join`)

* Branding header (`E` mark, "Ekagra AI"), theme toggle.
* Static copy: title (`settings.participant_study_title`), "What to expect" (`settings.participant_intro_text`) with three hard-coded step cards (guided examples / think independently / assessments), "Your responses and interactions are recorded".
* **Consent/privacy panel is a labelled placeholder**: an amber "Draft — pending research-team approval" banner (hard-coded in the template) over `settings.participant_privacy_text` and `settings.participant_support_text`, whose defaults are literally "…will be provided here before participant deployment".
* Form: `institutional_id` (university roll number) + one checkbox `acknowledged` ("I have read the information above and am ready to begin"). No other fields.
* **What is recorded of the "consent":** only a boolean literal `study_information_acknowledged: True` inside the `PARTICIPANT_ENTERED` protocol event. The checkbox value is `required` but its value is not otherwise stored; there is no consent-version, no timestamp distinct from the event, no withdrawal option, no separate consent document hash.
* Failure paths: ID already used, no active study version, or (when `REQUIRE_ACTIVE_CAPTURE=true`) no fresh recorder marker → 403 with a generic message.

### B.2 `session.html` + `partials/session_main.html` + `partials/tutor_composer.html` — the whole in-study experience

`session.html` is the shell: sidebar (brand, collapse toggle, study title, section list, theme toggle, elapsed timer, "Exit study"), plus all CSS and three inline `<script>` blocks. `session_main.html` renders one of the following panel states, chosen by `view.phase` and flags:

| State (template branch) | Trigger | What the participant sees |
|---|---|---|
| **Completion** | `phase == TERMINAL` and current | "Study completed / Thank you / Your study responses have been saved", total/start/finish times, placeholder text "Debrief information and researcher support details will appear here." |
| **Review (read-only)** | viewing an earlier section | Timeline of that section's messages + "This completed section is available for review." |
| **Assessment preparing / saving** | `pending` and phase `ASSESSMENT_GENERATING` / `JUDGING` | Spinner card "Preparing your assessment" / "Saving your assessment", polling div |
| **Tutor pending** | `pending` during intervention | Timeline + composer replaced by "The study assistant is responding…" and polling div |
| **Retryable error** | last `LLMCall` FAILED / INVALID_OUTPUT / stale | "That step could not be completed" + Retry form |
| **Section complete** | `phase == SECTION_COMPLETE` | Timeline + "Next section" (or "Finish study" on the last) |
| **Intervention – begin** | `attempt_status == ASSIGNED` | "Select the button below to start the teaching conversation" + "Begin study" / "Begin teaching activity N" |
| **Intervention – chat** | `INTERVENTION_ACTIVE` | Timeline of tutor/learner messages + composer (`#tutor-composer`, textarea `#learner-text`, "Send") |
| **Assessment active** | `ASSESSMENT_ACTIVE` | Heading "Respond in your own words", LLM-generated prompt, textarea `#assessment-response`, "Submit assessment" |

### B.3 Sidebar / progress indicators (the only progress UI today)

* A list of "Section 1 … Section N" links (N = `len(protocol.transition_ids)` = 4) with states `completed` (✓) / `current` / `locked`; completed sections link to a read-only review; future sections are inert.
* Under the selected section: sub-bullets "Teaching activity k" (one per attempt, i.e. per pedagogy tried) and "Independent assessment".
* Elapsed-time clock (client-side, from `started_at`, stops at `ended_at`).
* No progress bar, no step count of a longer journey, no objective/level indicator, no notion of SOLO level or transition (deliberately hidden from the participant).

### B.4 What the participant never sees (by design — must remain so)

`view()` is documented as "participant-safe … no research-only fields". It does **not** expose `pedagogy_id`, SOLO state, transition ID, rubric, judge output, attempt pass/fail, or hidden scoring context. The tutor prompt contract also forbids naming pedagogy IDs. The e2e test asserts hidden strings are absent from rendered HTML. **Any new screen must keep this projection discipline.**

---

## C. Existing backend integrations

### C.1 Request/response contract (as implemented)

All participant UI → server traffic is `application/x-www-form-urlencoded` (HTMX default) except telemetry (JSON). Responses are **HTML fragments**, not JSON.

| Action | Form fields | Server effect (engine) |
|---|---|---|
| `begin` | `idempotency_key` | `reserve_tutor(opening)` → sets attempt `INTERVENTION_ACTIVE`, sets `session.started_at` (first time), emits `PARTICIPANT_BEGAN_STUDY` |
| `tutor-message` | `learner_text`, `idempotency_key` | stores `Message(role=LEARNER)` + reserves Tutor call; on `COMPLETE`/turn budget → `complete_intervention` → auto-selects a random unseen assessment form → auto-chains an **ASSESSMENT-generation** LLM call → phase `ASSESSMENT_ACTIVE` |
| `assessment-response` | `response_text`, `idempotency_key` | `submit_assessment` + Judge call → `apply_judgment` → deterministic `RubricEvaluator` → pass: `SECTION_COMPLETE`; fail: new attempt with another pedagogy, or `SECTION_COMPLETE` (UNRESOLVED) after 3 |
| `retry` | `idempotency_key` | re-reserves latest failed/stale `LLMCall` |
| `next` | — | `advance_section` → creates attempt for next transition |
| `finish` | — | `finish_session` → `TERMINAL`, status `COMPLETED`/`UNRESOLVED` |

LLM execution is asynchronous (FastAPI `BackgroundTasks`); the UI learns the outcome only by polling `/session/operation`. Judge failures auto-retry once server-side; Tutor/Assessment failures surface the Retry card.

### C.2 Session management

* Created in `ParticipantApplication.activate()` from `institutional_id` (unique column). Binds to the *latest* `ActiveStudyVersion`, optionally a fresh `capture_run_id`.
* "Logged-in" state = `application.active_session_id` in process memory. **Server restart ⇒ participant cannot resume** (`/session` redirects to `/join`; the ID is single-use ⇒ "requires researcher intervention", per README).
* `lock_version` column exists on `Session` but is not used by the participant path; concurrency control is a `SELECT … FOR UPDATE` inside `reserve_idempotent`.

### C.3 Experimental assignment logic (must not be broken)

All in `runtime/engine.py`:

* `RandomSelector` wraps `secrets.SystemRandom().choice`; `SelectionDecision` records `eligible_candidate_ids`, `excluded_candidate_ids`, `selected_id`, `selection_method`, `selected_at`, optional seed.
* `SessionRuntime._create_attempt` picks a pedagogy from `protocol.pedagogy_ids` **minus those already used in that transition** and persists a `PEDAGOGY_SELECTED` + `ATTEMPT_CREATED` event pair per attempt.
* `complete_intervention` picks a random **unseen assessment form** (4 per transition) per attempt — pedagogy-independent.
* `apply_judgment`: pass ⇒ advance; fail ⇒ another attempt with another unused pedagogy (max 3) ⇒ else `UNRESOLVED` + continue.
* `HistoryBuilder` → `LearnerHistorySnapshot` feeds prior-attempt summaries to later Tutor attempts (Judge stays blind to pedagogy).
* Protocol (`protocol.yaml`) is validated by a Pydantic model with `pedagogy_strategy: Literal["random_without_replacement"]` and `assessment_strategy: Literal["random_unseen"]`; `validate()` hard-requires exactly 14 KC / 12 relations / 10 misconceptions / **5 SOLO states / 4 transitions / 3 pedagogies / 12 cells / 4 assessment forms per family**.
* DB: `Attempt` has `UniqueConstraint(session_id, transition_id, pedagogy_id)` — **the same pedagogy cannot be used twice in the same transition.**

### C.4 Telemetry and data collection (must not be broken)

| Channel | Client | Server | Storage |
|---|---|---|---|
| rrweb DOM replay (`maskAllInputs`, mask `.message.learner`) | `participant_telemetry.js` | `append_rrweb_batch` | NDJSON files `research-data/<session>/browser/rrweb/` |
| Semantic UI events | `participant_telemetry.js` (`enqueueUi`) | `record_ui_events` → whitelist `UI_EVENT_TYPES` (18) and `SURFACES` (9), `teaching_activity_number` ∈ 1..3, `section_number` ≤ #transitions | `participant_ui_events` (immutable) |
| Keyboard dynamics (key *class* only) | `participant_keyboard.js` (attached to `#learner-text`, `#assessment-response` only) | `append_keyboard_batch` (strict field set, 4 KB cap) | NDJSON `…/browser/keyboard/` |
| Protocol events | server | `SessionRuntime._event` | `protocol_events` (immutable) |
| Full LLM audit | server | `LLMCall` (prompt, raw response, tokens, latency) | `llm_calls` |
| Screen/webcam | host tool `tools/windows_capture/record.py` (outside the app) | marker `active_capture.json` | `research-data/capture-runs/` |
| Export | CLI | `research_export.py` lists tables **explicitly** | JSON |

Several tables are protected by `BEFORE UPDATE OR DELETE` triggers (`messages`, `assessment_responses`, `protocol_events`, `judgments`, `rubric_evaluations`, `learner_history_snapshots`, `study_versions`, `participant_ui_events`) — new response tables for TLX/MCQ should follow the same pattern.

### C.5 Telemetry coupling inventory (the "do not rename" list)

The following front-end identifiers are **read by telemetry JS or asserted by e2e tests**. Renaming or restructuring them without updating both sides will silently lose research data or fail tests:

| Identifier | Used by |
|---|---|
| `#session-main` | telemetry root, swap target, clock sync, scroll restore |
| `[data-section-number]`, `[data-teaching-activity-number]`, `[data-telemetry-mode]` | UI-event context → `participant_ui_events.section_number / teaching_activity_number` |
| `[data-processing-kind]` | `PROCESSING_SHOWN/HIDDEN` |
| `[data-tutor-message-sequence]` | `TUTOR_MESSAGE_RENDERED` |
| `[data-telemetry-surface="assessment"]` | `ASSESSMENT_RENDERED` |
| `[data-assessment-completed-marker]`, `[data-generation-error]`, `[data-section-complete]`, `[data-completed-section-review]`, `[data-study-complete]` | corresponding `*_RENDERED` events |
| form `hx-post` values (`/session/actions/begin|tutor-message|assessment-response|retry|next|finish`) | click → event map in `clickEvent()` |
| `#learner-text`, `#assessment-response` | keyboard capture + surface classification (`learner-text` ⇒ `TUTOR_RESPONSE`, else `ASSESSMENT_RESPONSE`) |
| `#tutor-composer`, `.conversation`, `.message.learner` | pending UX, scroll preservation, rrweb text masking |
| Visible text used by Playwright: button names `Continue`, `Begin`, `Send`, `Retry`, `Submit assessment`, `Next section`, `Finish study`; label `University ID`; label `Your response`; headings `Respond in your own words`, `That step could not be completed`, `Thank you`, `Section N`; text `Section completed` | `tests/e2e/test_participant_browser.py` |

---

## D. Existing reusable components

There are no component files; "components" are Jinja macros/partials and CSS class patterns. Reuse assessment:

| Component | Location | Reuse for | Notes |
|---|---|---|---|
| Design tokens (`--ink --muted --faint --line --soft --accent --ring`, indigo accent for nav) | top of each `<style>` | Everything | **Duplicated** across the two templates and again for dark mode (two near-identical dark blocks per file: `@media` and `[data-theme=dark]`). Extract once. |
| Theme toggle | `static/theme.js` + markup | All pages | Solid; already guarded for blocked storage. |
| Sidebar shell + collapse/mobile drawer | `session.html` grid CSS + script | Journey stepper host | Good responsive behaviour (≤900px drawer). Its content must change from "Section N" to journey stages. |
| `section_nav` macro | `session_main.html` | Becomes journey stepper | Needs a richer item model (stage groups, SOLO transition sub-steps). |
| `timeline` macro / `.message` bubbles | `session_main.html` | Teaching-core chat (Socratic; reused for Contrasting/Worked-example Q&A) | Has `data-tutor-message-sequence` hooks. |
| Chat composer + optimistic bubble + local "processing" + draft recovery | `tutor_composer.html` + JS (`enterTutorPending`, `recoverTutorPending`) | Any free-text turn | Mature failure handling; keep. |
| Processing card + 1 s poll (`data-operation-poll`, 204 semantics) | `session_main.html`, `/session/operation` | Any LLM-backed step | Reuse as-is for Tutor/Assessment/Judge; not needed for deterministic steps (TLX/MCQ). |
| Retry card | `session_main.html` | LLM steps | Keep. |
| `.action-card`, `.begin-state`, `.panel`, `.panel-head`, `.phase-badge`, `.completion-grid` | CSS | Intro, objectives, recap, completion cards | Generic enough; need a content-card variant. |
| Idempotency-key hidden input + `reserve_idempotent` | `web.py` | Any non-idempotent submit (TLX, MCQ, consent) | Server helper is LLM-shaped (`result_object_type="LLMCall"`); needs generalising for non-LLM actions. |
| Double-submit guard (capture-phase `submit` listener) + `htmx:responseError` recovery | `session.html` | All forms | Reuse. |
| Elapsed-time clock | `session.html` | Header/footer | Starts at first "Begin"; semantics will change with an earlier consent/onboarding phase (§E). |
| Telemetry JS (render observer, click map, keyboard attach via `onRender`) | `static/telemetry/` | All new screens | Extensible via `ParticipantTelemetry.onRender` and the `events` map, but event/surface names are server-whitelisted. |
| Form styling (`textarea`, `.consent`, `input`) | `join.html`, `session.html` | Onboarding, TLX sliders, MCQ radios | **No radio/slider/likert/progress-bar styles exist.** |
| Markdown rendering | — | — | **None.** Tutor messages are stored as `content_format="markdown"` but rendered as plain text with `white-space:pre-wrap`. Worked examples with code will need a safe renderer (§G). |

---

## E. Gap analysis against the proposed learning experience

### E.1 Journey step vs. current implementation

Legend: **R** retain · **M** modify · **N** new.

| # | Proposed step | Exists today? | Status | Notes |
|---|---|---|---|---|
| 1 | Participant onboarding & consent | Partial: `join.html` (placeholder consent, one checkbox, ID) | **M + N** | Needs real consent copy (research-team text), versioned consent record, maybe demographics/prior-knowledge capture (only if the protocol requires it — **not currently collected anywhere**). ID entry and single-use enforcement: **R**. |
| 2 | Course introduction & learning objectives | No. Only generic "What to expect" prose on `/join`. No objectives exist in study YAML (`in_scope` lists exist in `knowledge.yaml` but are research-facing). | **N** | Static, common to all conditions. |
| 3 | What–Why–How structure | No such concept. Closest: authored `move_ids` sequence + tutor recipe per pedagogy (`role_instruction`, `move_generation_instruction`, `learner_check_instruction`). | **N** (content + UI) | Must be defined as *common frame* vs. *pedagogy-specific core* (see E.2). |
| 4 | Five SOLO levels / four transitions | Backend: **yes** (states P,U,M,R,EA; transitions C1–C4; validated). UI: shown only as anonymous "Section 1–4". | **M** | Frontend needs only participant-safe labels (e.g. "Level 1→2"), never raw state IDs unless the researchers explicitly want SOLO named to learners. |
| 5 | Three pedagogies | Backend: **yes** (P1 Worked-Example, P2 Guided Questioning, P3 Contrasting-Case) – delivered 100 % by LLM chat. UI: one generic chat surface. | **M** | Naming mismatch: proposal says "Socratic Questioning"; code says "Guided Questioning" (P2). Rendering surfaces for Contrasting Cases (side-by-side) and Worked Examples (code blocks) don't exist. |
| 6 | Session recap | No | **N** | Needs a content source (see E.2) and a place in the state machine. |
| 7 | NASA-TLX workload assessment | No (grep: zero occurrences in `src/`, `studies/`, `tests/`, `migrations/`, `docs/`) | **N** | 6 subscales (+ optionally pairwise weights). New table(s), form UI, telemetry. |
| 8 | MCQ assessment | No. Assessments are **LLM-generated open-text** prompts judged by an LLM; no item bank, no options, no scoring. | **N** | See E.4 — unclear whether MCQ replaces or supplements the per-transition open assessment. |
| 9 | Session completion & progression | Partial: `TERMINAL` page with durations and placeholder debrief; `Next section` / `Finish study`. | **M** | Debrief text is a placeholder. Progression semantics change if pedagogy is fixed (E.3). |

### E.2 "Keep the teaching pedagogy separate from the common introduction and conclusion"

Currently there is **no such separation**: the Tutor LLM authors the *opening* turn too (`reserve_tutor(opening=True)` → "Begin with the current move…"), so any "introduction" text would be pedagogy-flavoured and LLM-variable. To satisfy the constraint:

* The **common frame** (intro, objectives, What/Why framing, recap, conclusion) should be **static, authored, identical for all 12 conditions**, rendered by the frontend from versioned content — not generated by the Tutor.
* The **pedagogy core** is the only part that varies by condition and stays LLM-driven within existing cells/moves.
* Today's authored schema (`StrictModel`, `extra="forbid"`) has no field for common-frame content. Putting it in YAML means a new `content_hash` → new `StudyVersion` (the system is built for that), but needs backend model + validator changes (§H). Putting it in templates avoids backend work but loses versioning/hash provenance, which is bad for a research record. **Recommendation: author it in study YAML.**
* Risk of **contamination**: a "Why/How" in the common frame that resembles a worked example would leak the Worked-Example treatment into the Socratic and Contrasting arms. Content review is needed (research task, not code).
* Recap: if the recap is LLM-generated it is pedagogy-dependent (it would summarise *that* conversation). A deterministic, authored, condition-independent recap preserves the separation; a conversation-aware recap needs an explicit research decision.

### E.3 Experimental-design conflicts (blocking — needs research-team decision)

| Proposed constraint | Current behaviour | Conflict |
|---|---|---|
| "Do not allow participants to change their assigned pedagogy" | A failed assessment *automatically assigns a different pedagogy* for the same transition; progression is **mastery-gated**. | **Direct conflict.** There is no "fixed pedagogy" mode. |
| "Controlled pseudo-randomized participant assignment" | Uniform `SystemRandom` choice per attempt; no blocking, stratification, seed, or ledger of group sizes. | No balancing mechanism; unequal arms are likely at small N. |
| "Twelve experimental conditions (4 × 3)" | 12 = 4 transitions × 3 pedagogies = the **content cells** (`C1-P1 … C4-P3`), validated as such. A *participant* is never assigned to a condition; the cells are visited stochastically. | The word "condition" is ambiguous (see below). |
| "Preserve the existing research methodology" | The adaptive retry-with-new-pedagogy loop **is** the existing methodology (`protocol.yaml`: "If failure and an unused pedagogy remains … select another unused pedagogy"). | Preserving it and fixing pedagogy are mutually exclusive unless the two protocols coexist as versions. |
| (implicit) | `UniqueConstraint(session_id, transition_id, pedagogy_id)` + `_create_attempt` excluding used pedagogies. | A fixed pedagogy plus any retry in the same transition violates the constraint. |

**Interpretations the research team must pick between** (this audit cannot choose; the choice determines Phases 3–8):

1. **Between-subjects pedagogy, 3 arms** — each participant gets one pedagogy for all four transitions; "12 conditions" = the 4×3 content matrix. *(Closest to "do not allow participants to change their pedagogy"; lowest engine change.)*
2. **Per-transition pedagogy assignment** — each participant gets a pre-assigned pedagogy *per transition* (3⁴ = 81 sequences, or a Latin-square subset), fixed up front.
3. **Participant assigned to exactly one of the 12 cells** — each participant studies a single transition with a single pedagogy (12 between-subject groups).

And independently: **what happens on a failed assessment?** (a) proceed anyway/record outcome (no remediation), (b) repeat same pedagogy (needs constraint change), (c) keep today's switch loop for a separate protocol version.

### E.4 Assessment gap

Current per-transition assessment = LLM-generated open-text task → LLM Judge → deterministic rubric → gates progression and drives `formal_state_id`. The proposal lists "MCQ assessment" with no stated relationship. Options (needs decision): (i) MCQ is an **additional** end-of-session test, leaving the Judge pipeline as-is; (ii) MCQ **replaces** the Judge pipeline (large backend change, loses SOLO-state evidence); (iii) MCQ per transition alongside the open-text. No MCQ items, options, answer keys, scoring, or leakage controls exist (the open-text path has leakage checks in `ai.py` that MCQ would need an equivalent for). **Recommendation: (i) or (iii), never (ii), to preserve SOLO-based outcome measurement.**

### E.5 Other gaps

* **Persistent participant state across page loads:** no cookie/token — journey stages before/after the study (consent, TLX, MCQ) will be lost on server restart unless stage state is DB-backed (it should be).
* **Browser back/refresh behaviour** for non-LLM steps (TLX, MCQ): need server-side "answered once" enforcement; the current pattern relies on `phase` guards.
* **Time semantics:** `session.started_at` is set on the first "Begin". With consent/intro earlier, "elapsed" and "total time" definitions in completion UI and the export need an explicit decision (don't silently move `started_at`).
* **Accessibility:** radios/sliders for TLX/MCQ need keyboard + screen-reader support; current CSS has good `:focus-visible` handling to extend.
* **Font:** `Inter` is requested but never loaded (system fallback) — cosmetic only.

---

## F. File-by-file modification plan

> Frontend files first; **(B)** marks a file that is backend and therefore needs your approval per the constraints. Nothing below has been done.

### F.1 Existing files

| File | Action | Detail | Risk |
|---|---|---|---|
| `src/solo_harness/templates/join.html` | **Modify** | Split concerns: keep ID entry; replace placeholder consent block with real, versioned consent copy (content from research team); keep `name="institutional_id"`, `name="acknowledged"`, `Continue`, `University ID` (e2e). Extract CSS to shared file. May become step 1 of onboarding. | Med — tests + consent text approvals |
| `src/solo_harness/templates/session.html` | **Modify (heavy)** | Extract ≈235 lines of CSS and 3 inline scripts into `static/`. Keep shell grid and all telemetry hooks. Replace "Section N" nav with a journey stepper. Vendor HTMX locally (replace unpkg). | **High** — highest blast radius; protected by e2e |
| `src/solo_harness/templates/partials/session_main.html` | **Modify (heavy)** | Today a single `if/elif` ladder on `view.phase`. Refactor into a stage dispatcher that `{% include %}`s one partial per stage; keep the existing branches (teaching/assessment/review/pending/retry/complete) as partials unchanged in markup. | **High** |
| `src/solo_harness/templates/partials/tutor_composer.html` | **Retain** | Keep ID/labels exactly. | Low |
| `src/solo_harness/static/theme.js` | **Retain** | | — |
| `src/solo_harness/static/telemetry/participant_telemetry.js` | **Modify (additive only)** | Add render observers + click-map entries for new stages. **Has uncommitted changes (§J.1).** Must not change existing event semantics. | Med |
| `src/solo_harness/static/telemetry/participant_keyboard.js` | **Modify (small)** | Attach to new free-text fields only if the research design wants keystroke data there; surface mapping is by `id === 'learner-text'` — extend deliberately. Never attach to ID/consent fields (documented guarantee). | Med (privacy) |
| `src/solo_harness/web.py` **(B)** | **Modify** | New stage routes, view-model projection for new stages, generalised idempotency for non-LLM actions, and a participant-safe journey model. `view()` must keep omitting pedagogy/state/transition IDs. | **High** |
| `src/solo_harness/runtime/engine.py` **(B)** | **Modify** | New phases and transitions in the session state machine; assignment service for fixed pedagogy (§E.3); `_create_attempt` selection. Must keep `PEDAGOGY_SELECTED` event shape (research export / analysis depends on it). | **High** |
| `src/solo_harness/db/models.py` + `migrations/versions/*` **(B)** | **Modify** | New tables (§H). Note `0001_foundation` calls `Base.metadata.create_all` ⇒ new models appear in fresh DBs at 0001; later migrations must be guarded with `checkfirst`/inspect (exactly the problem the uncommitted 0004/0005 edits fix). | **High** |
| `src/solo_harness/telemetry.py` **(B)** | **Modify** | Extend `UI_EVENT_TYPES`, `SURFACES`; relax `teaching_activity_number ≤ 3` and `section_number` assumptions for non-section stages. | Med |
| `src/solo_harness/config.py` **(B)** | **Modify** | Move/replace `participant_*_text` defaults; add content/consent version settings. | Low |
| `src/solo_harness/research_export.py` **(B)** | **Modify** | Add new tables to the explicit export lists. | Med — silent data omission if forgotten |
| `src/solo_harness/studies/authored/models.py`, `validation.py`, `compiler.py`, study YAML **(B)** | **Modify** | Add common-frame content + MCQ items + protocol assignment mode. `validate()` has hard-coded cardinalities; adding new authored sections requires new checks. Changes `content_hash` ⇒ new `StudyVersion` (intended). | **High** |
| `tests/e2e/test_participant_browser.py` | **Modify** | Journey is longer; update expectations deliberately (don't weaken hidden-leak & telemetry-masking assertions). **Has uncommitted changes.** | Med |
| `docs/COMPLETE_DATA_COLLECTION_SPECIFICATION.md`, `README.md` | **Modify** | Document new data and flow at the end. | Low |
| `01_…05_*.md`, `old/*` | **Do not touch** | Research provenance. | — |

### F.2 New files (proposed; none created)

See §G.

---

## G. New components required

### G.1 Frontend (templates / CSS / JS)

| Component | Purpose |
|---|---|
| `static/css/tokens.css`, `base.css`, `components.css` | Single copy of tokens (light/dark), shell grid, buttons, cards, forms. Removes ~300 duplicated lines. |
| `static/vendor/htmx/2.0.4/htmx.min.js` (+ licence) | Eliminate runtime CDN dependency (offline lab machines; unpinned integrity; breaks reproducibility). Mirrors how rrweb is already vendored. |
| `partials/journey_nav.html` | Stage stepper (common stages + 4 SOLO transitions), participant-safe labels, locked/current/done. |
| `partials/stage_consent.html`, `stage_course_intro.html`, `stage_objectives.html` | Common frame, static content. |
| `partials/stage_wwh.html` | What–Why–How presentation scaffold shared by all conditions. |
| `partials/teach_socratic.html`, `teach_contrast.html`, `teach_worked_example.html` | Pedagogy-specific *presentation* around the shared chat component (e.g. side-by-side case cards for Contrasting; code-block layout for Worked Example). Selected server-side by the assigned pedagogy; **never exposing its name** to the participant. |
| `partials/stage_recap.html` | Common recap. |
| `partials/stage_tlx.html` + `static/js/likert.js` | NASA-TLX 6 subscales (0–100 sliders or 21-tick scale), optional weighting; accessible inputs. |
| `partials/stage_mcq.html` | MCQ item renderer (radio group, one-at-a-time or paged, review/confirm). |
| `partials/stage_complete.html` | Replace placeholder debrief. |
| `static/js/markdown.js` (or server-side sanitised render) | Safe Markdown/code rendering for tutor messages and worked examples (none exists). Must be XSS-safe; messages are LLM output. |
| Telemetry additions | New render markers + click-map entries (`data-stage`, etc.) following the existing `data-*` convention. |

### G.2 Cross-cutting

* Progress component driven by a **server-supplied** `journey` list (don't compute progress in JS).
* A reusable "non-LLM submit" form pattern (idempotency key + double-submit guard + server rejection UI) distinct from the LLM pending/poll pattern.

---

## H. Backend dependencies

Everything here is outside the frontend and needs explicit approval before implementation.

| # | Dependency | Why | Notes |
|---|---|---|---|
| H1 | **Condition assignment ledger** (new table, e.g. `condition_assignments`: session, condition id, method, block id, seed/RNG audit, timestamp) + allocation service | "Controlled pseudo-randomized" (block/stratified), auditable, balanced | Must be concurrency-safe and recorded as a protocol event. Replaces per-attempt random pedagogy selection in whichever interpretation is chosen (E.3). |
| H2 | **Fixed-pedagogy attempt creation** | Cannot change pedagogy | Relax/replace `UniqueConstraint(session_id, transition_id, pedagogy_id)` and the exclusion logic if retries are allowed; or remove retry/remediation loop for the new protocol version. `protocol.yaml` enum values need extending (`pedagogy_strategy`, `max_attempts_per_transition`). |
| H3 | **Protocol versioning** | "Preserve the existing research methodology" | Keep v0.x adaptive protocol runnable; ship the new design as a **new study/content version**, not an in-place edit, so previously collected data remains interpretable. |
| H4 | **Session stage model** | New pre/post-teaching stages | Add to `SessionPhase` (the column is a free `String`, no DB enum/CHECK → no schema change needed for new values, but all `view()` branches and `SessionPhase` tests need updating). New protocol events (`CONSENT_RECORDED`, `STAGE_ENTERED/COMPLETED`, …). |
| H5 | **Consent record** | Auditable consent | Store consent version + text hash + timestamp; today only a boolean inside an event payload. |
| H6 | **NASA-TLX tables + endpoint** | Persist 6 ratings (+ weights), per-session (and per-transition if repeated) | Immutable-table trigger pattern; link to `attempt_id`/stage; telemetry events. |
| H7 | **MCQ item bank + response tables + scoring** | Items, options, key (hidden from client), per-item response/latency | Keys must never be sent to the browser; `view()` must project question text/options only. Add to study YAML + validator + export. |
| H8 | **Common-frame / recap content in study YAML** | Versioned, hashed, condition-independent content | New authored models (`extra="forbid"` today), compiler, validator; updates cardinality checks. |
| H9 | **Generalised idempotency** | TLX/MCQ/consent submits | `reserve_idempotent` currently stores `result_object_type="LLMCall"`. |
| H10 | **Telemetry whitelists** | New event types/surfaces; activity-number bounds | `telemetry.py` constants. |
| H11 | **Export + data-spec doc** | New tables must reach analysts | `research_export.py` lists tables explicitly. |
| H12 | **Durable participant session** (recommended) | Resume after restart/refresh across a longer journey | Replace in-memory `active_session_id` with a signed session cookie bound to the session row; keep single-use ID rule. Needs a decision about multi-participant concurrency. |
| H13 | **Participant-safe API contract for recap/hints** | If recap is conversation-aware | Only if the research team chooses that (E.2). |

---

## I. Implementation sequence for the remaining seven phases

> Gate: **no phase starts without your approval.** Phase 2 cannot finalise until the §J.2 decisions are made, because they decide whether Phases 3–7 are mostly frontend or mostly engine work.

| Phase | Scope | Backend? | Exit criteria |
|---|---|---|---|
| **2 — Frontend foundation** | Vendor HTMX locally; extract CSS/JS into `static/`; introduce stage-dispatcher in `session_main.html` that renders **today's exact markup** for today's phases; no behaviour change. | No | Existing e2e suite passes unmodified; telemetry diff is empty; visual regression is zero. |
| **3 — Design decisions → protocol & data model** | Resolve §J.2; new study/content version; assignment ledger; consent record; stage model; migrations (guarded). | **Yes** | Unit/integration tests for assignment balance, immutability, export; old protocol still loads. |
| **4 — Onboarding, consent, course intro, objectives** | `join` redesign + consent flow + intro/objectives stages + journey nav. | Light | New e2e: join → consent → intro → first teaching stage; refresh-safe. |
| **5 — Teaching core (What–Why–How × 3 pedagogies × 4 transitions)** | Shared W-W-H frame; per-pedagogy presentation partials; markdown/code rendering; SOLO-transition progress UI (participant-safe). | Medium | Pedagogy never shown to participant; no change possible via UI/URL; e2e per pedagogy using fake LLM client. |
| **6 — Recap + NASA-TLX** | Recap stage; TLX form, persistence, telemetry. | Yes (TLX tables) | TLX values persisted once, immutable, exported. |
| **7 — MCQ assessment** | Item renderer, scoring, hidden keys, telemetry, export. | Yes | Keys absent from HTML (extend leak test); idempotent submit. |
| **8 — Completion, progression, hardening** | Completion/debrief page, progression rules per decision, telemetry/keyboard review, a11y pass, docs (`COMPLETE_DATA_COLLECTION_SPECIFICATION.md`), full e2e and `scripts/live_participant_e2e.py` update. | Light | Full journey e2e on 12 condition paths; data-spec updated. |

---

## J. Risks and recommendations

### J.1 Working-tree state (before any implementation)

Four files have **uncommitted modifications** on `feature/frontend-work`:

* `src/solo_harness/static/telemetry/participant_telemetry.js` — new size-bounded rrweb flush (`RR_FLUSH_CHARS`, `flushOnHide`). A telemetry-integrity fix.
* `tests/e2e/test_participant_browser.py` — new test `test_rrweb_events_survive_navigation_before_periodic_flush`.
* `migrations/versions/0004_institutional_id.py`, `0005_capture_run_id.py` — idempotency guards so fresh DBs (whose `0001` already `create_all`s the current models) don't fail.

**Recommendation:** commit these as a separate change (or confirm they are intentionally in flight) *before* Phase 2 so frontend refactors are diffed against a clean baseline and the telemetry fix isn't mixed with UI work. I did not touch them.

### J.2 Decisions required from the research team (blocking)

1. Which assignment interpretation applies — **E.3 (1) / (2) / (3)**? *(My recommendation: (1) between-subjects, 3 pedagogy arms balanced by permuted blocks, with the existing 4×3 cell matrix as the content grid. It is the only reading that makes "cannot change pedagogy" and "controlled assignment" simple and auditable. If the team intends "12 conditions" to be 12 participant groups, (3) applies and the validator's cell logic still works.)*
2. Behaviour on failed transition assessment under fixed pedagogy: proceed, repeat same pedagogy, or none (E.3).
3. Is the existing adaptive protocol retired or retained as a separate version (H3)? *(Recommend retain as v-prior; ship new as new version.)*
4. MCQ relationship to the Judge pipeline (E.4). *(Recommend additive.)*
5. Is the recap static or conversation-aware (E.2)? *(Recommend static for isolation of the pedagogy variable.)*
6. Are SOLO level names shown to participants? Currently they are hidden; showing them could itself be a treatment cue.
7. TLX variant: raw (6 items) vs weighted (15 pairwise comparisons); once at end or per transition?
8. Final consent / debrief / privacy text and its owner (currently labelled "Draft — pending research-team approval").
9. Name alignment: "Socratic Questioning" (proposal) vs "Guided Questioning" (code/YAML P2). Participant-facing text will not name pedagogies, so this is mainly for docs/analysis.

### J.3 Technical risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | Fixed-pedagogy requirement conflicts with adaptive retry, DB unique constraint, validated protocol literals | **High** | Version the protocol; decide before Phase 3 (J.2). |
| R2 | **Telemetry silently degrades** if `data-*`/IDs/hx-post/labels change | **High** | Freeze the coupling list (§C.5); add a test that asserts every expected UI event type is emitted per stage; diff `participant_ui_events` for a scripted session before/after Phase 2. |
| R3 | Process-level `active_session_id`: restart or second browser loses/hijacks the session; longer journey increases exposure | **High** | H12 durable cookie bound to session row; at minimum, DB-backed stage resume. |
| R4 | HTMX from unpkg (no pin integrity, needs internet) | Med | Vendor locally (Phase 2). Fallback fetch path currently masks failures — keep it tested. |
| R5 | Extending `UI_EVENT_TYPES`/`SURFACES` is server-side; frontend-only work cannot emit new event types | Med | Plan telemetry changes with backend in Phase 3. |
| R6 | `0001` runs `create_all` from live models → every new model auto-creates in fresh DBs and breaks later `create_table` migrations | Med | Use inspect/`checkfirst` guards (precedent in the uncommitted 0004/0005 edits); test migrations from an empty DB and from a 0005 DB. |
| R7 | Pedagogy leakage through the common frame or recap | Med | Author as static condition-independent content; research-team content review; automated test that common-frame HTML is byte-identical across conditions. |
| R8 | Participant can infer/alter condition via URL (`/session/sections/{n}`) or inspect HTML | Med | Server-chooses template; no condition/pedagogy in URLs, class names, `data-*`, or JS; extend the existing "hidden string not in HTML" test. |
| R9 | MCQ keys or TLX logic exposed client-side | Med | Keys server-side only; project question + options only. |
| R10 | LLM markdown rendered unsafely (stored as `markdown` but shown raw today) | Med | Server-side sanitised render or vetted client lib; never `innerHTML` raw LLM text. |
| R11 | `validate()` hard-codes cardinalities; `extra="forbid"` models reject new YAML keys | Low–Med | Plan schema/validator changes together with content. |
| R12 | `view()` runs many queries per request and is also called each poll second | Low | Acceptable for single-participant use; avoid adding per-poll N+1 queries in new stages. |
| R13 | Non-LLM submits (`next`, `finish`) lack idempotency keys; replays after back/refresh possible | Low–Med | Server-side phase guards exist; add keys for TLX/MCQ/consent. |
| R14 | Elapsed/`started_at` semantics change with earlier stages | Low | Keep `started_at` meaning unchanged or add distinct stage timestamps; update spec. |

### J.4 Documentation vs. code discrepancies noticed

* `docs/COMPLETE_DATA_COLLECTION_SPECIFICATION.md` states the implemented study is content version **v0.4** while the directory is `v0.1` (the version is `content_version` inside `study.yaml`; directory name is not the version). Not a bug, but easy to misread.
* README and UI describe "tutor interaction followed by an independent assessment" per section; code additionally runs up to three such attempts per section with different pedagogies (the UI shows them as "Teaching activity 1–3").
* The `join.html` consent area is explicitly placeholder text; `config.py` defaults for privacy/support are placeholders.
* The telemetry file header says "intentionally captures no custom keyboard telemetry" while a separate keyboard script exists — accurate (separation of concerns), but easy to misread.
* Product name "Ekagra AI" appears only in UI chrome; package/app title is "SOLO Harness".

### J.5 Recommendations (summary)

1. Commit or stash the four in-flight files; start Phase 2 from a clean tree.
2. Get the §J.2 decisions in writing **first**; they determine ~70 % of the remaining scope.
3. Treat the new design as a **new study/protocol version**; keep the existing adaptive protocol intact and runnable.
4. Do Phase 2 as a pure no-behaviour-change refactor protected by the existing e2e suite and a before/after `participant_ui_events` diff.
5. Author all common-frame content, MCQ items and recap in versioned study YAML, not in templates.
6. Make participant state durable and server-owned before lengthening the journey.
7. Keep the participant projection rule: *the browser never receives pedagogy, SOLO state, transition ID, rubric, or answer keys.*

---

*End of audit. No implementation has been started; awaiting your review and approval.*
