# Study Terminology and Reconstruction Audit

**Audit date:** 2026-10-24  
**Scope:** current repository code, frozen study configuration, templates, PostgreSQL models, export logic, browser telemetry, Windows capture, tests, and one existing persisted session export  
**Behavior changed by this audit:** none

## Executive decision

The current dataset is strong enough to reconstruct the experimental condition, participant text, Tutor interaction, generated assessment, Judge operation, deterministic rubric decision, retries, and section progression. Those scientific facts are joined by stable UUIDs and supported by immutable rows and ordered protocol events.

It is not a perfect audiovisual replay system. Browser telemetry is best-effort; DOM render is not evidence of attention; the browser, server, recorder, and media timelines have no explicit synchronization calibration; and the current frontend does not correctly populate `teaching_activity_number` in semantic or keyboard telemetry. Technical abandonment also lacks a durable terminal classification. These weaknesses matter for fine-grained behavioral and cross-modal analysis, not for reconstructing the core protocol.

This audit treats [COMPLETE_DATA_COLLECTION_SPECIFICATION.md](COMPLETE_DATA_COLLECTION_SPECIFICATION.md) as the inventory and does not repeat its field catalogue. Claims below were checked against current code, especially `db/models.py`, `domain/enums.py`, `runtime/engine.py`, `runtime/ai.py`, `web.py`, the Jinja templates, both telemetry scripts, `telemetry.py`, `research_export.py`, `tools/windows_capture/record.py`, the authored study, and integration/E2E tests.

Two material documentation/runtime differences were found:

1. The authored protocol still says progression stops after three failures, while the current runtime records the section as scientifically `UNRESOLVED` and permits administrative continuation.
2. The existing data-collection specification names capture clocks as `wall_time_utc` and `monotonic_seconds` in places; current capture code and artifacts use `observed_at_utc` and `monotonic_ns`.

## 1. Plain-language study flow

The study has four participant-facing sections. Internally they are SOLO transitions C1-C4: P→U, U→M, M→R, and R→EA. A section may contain up to three teaching activities. Internally, each teaching activity is an `Attempt` using a different pedagogy and a fresh assessment form.

| Step | Participant-visible state | Backend and persisted evidence | Main times/artifacts |
|---|---|---|---|
| 1. Researcher prepares | Nothing yet | Researcher starts `record.py` when capture is required. It creates a `capture_run_id`, per-stream files, a recording manifest, and then `active_capture.json`. | Recorder UTC and monotonic stamps; FFmpeg logs/progress; MKV files |
| 2. Participant joins | Join form; University ID and acknowledgement | `ParticipantApplication.activate` validates the active marker only when `REQUIRE_ACTIVE_CAPTURE=true`; creates `Session`, first `Attempt`, `SESSION_CREATED`, `PEDAGOGY_SELECTED`, `ATTEMPT_CREATED`, then `PARTICIPANT_ENTERED`. | `Session.created_at`; protocol-event sequence; optional `Session.capture_run_id` |
| 3. Section 1 is ready | “Section 1”, “Teaching”, “Begin study” | Session is `ACTIVE / INTERVENTION_ACTIVE`; attempt is `ASSIGNED`. C1 and the selected pedagogy are already stored. | `Attempt.assigned_at`; selection event timestamp |
| 4. Participant begins | Study assistant processing, then opening Tutor message | A Tutor `LLMCall` is reserved before network work. First begin sets `Session.started_at`, `Attempt.intervention_started_at`, and emits `PARTICIPANT_BEGAN_STUDY`. Successful output creates a Tutor `Message` and `TUTOR_TURN_COMPLETED`. | LLM start/completion/latency; message time; UI processing/render events if delivered |
| 5. Tutor interaction | Tutor messages, “Your response”, Send, responding state | Every submitted learner text becomes a learner `Message`; the following Tutor request stores the ordered prompt and response. Tutor messages store instructional trace and link to their successful `LLMCall`. | Message sequence/time; LLM records; click/render/keyboard/rrweb evidence |
| 6. Teaching activity ends | “Preparing your assessment” | Tutor disposition `COMPLETE`, or reaching the turn budget, records `TUTOR_COMPLETE` or `BUDGET_EXHAUSTED`. Attempt becomes `ASSESSMENT_GENERATING`; a fresh `AssessmentInstance` is selected; `INTERVENTION_COMPLETED` and `ASSESSMENT_SELECTED` are emitted. | Intervention completion; selection audit; assessment-generation call |
| 7. Independent assessment | “Respond in your own words” | Successful assessment generation freezes `prompt_snapshot` and `hidden_scoring_context_snapshot`; assessment and attempt become `ACTIVE`; `ASSESSMENT_GENERATED` is emitted. | Generation call and render event/rrweb if present |
| 8. Participant submits | “Saving your assessment” | An immutable `AssessmentResponse` is inserted; assessment becomes `SUBMITTED`; attempt/session become `JUDGING`; `ASSESSMENT_SUBMITTED` is emitted; Judge call is reserved. | Response `submitted_at`; Judge start; submit click if delivered |
| 9. Judge and rules run | Processing, then either completion or another activity | Successful Judge output creates immutable `Judgment`; deterministic `RubricEvaluation` calculates pass/fail and reasons; assessment closes; `RUBRIC_EVALUATED` is emitted. | Judge raw/parsed output, evidence, evaluation, completion times |
| 10a. Pass | “Section completed” | Attempt `PASSED`; `SECTION_COMPLETED` has scientific outcome `PASSED`. Formal state advances only when the current state equals that transition's source state. | Evaluation plus section event |
| 10b. Fail with attempts left | “Begin teaching activity 2/3” | Attempt `FAILED`; runtime immediately creates another attempt in the same transition, selects an unused pedagogy, and writes a deterministic `LearnerHistorySnapshot`. | Previous evaluation; new selection/attempt events; history source IDs |
| 10c. Third failure | “Section completed” and Next | Last attempt `FAILED`; `outcome_details` records `PEDAGOGIES_EXHAUSTED_CONTINUE / UNRESOLVED`; `SECTION_CONTINUATION_ALLOWED` and `SECTION_COMPLETED` are emitted. Formal state does not advance. | Explicit scientific and administrative records |
| 11. Next section | “Next section”, then next Section | Explicit Next invokes `advance_section`, creates the next transition's first attempt, and emits `PARTICIPANT_ADVANCED_SECTION`. | New attempt and navigation event; optional click event |
| 12. Later pass after an unresolved prerequisite | “Section completed” | Rubric can pass locally, but formal state remains unchanged and evaluation adds `FORMAL_ADVANCEMENT_BLOCKED_BY_PRIOR_UNRESOLVED_SECTION`; section event says `formal_state_advanced=false`. | Evaluation is authoritative; UI does not expose this distinction |
| 13. Finish | “Finish study”, then “Thank you” | Only allowed after C4's completion gate. Session becomes `COMPLETED` only if no unresolved section exists; otherwise `UNRESOLVED`. Terminal reason is `COMPLETED_EA` or `COMPLETED_WITH_UNRESOLVED_SECTIONS`; `SESSION_COMPLETED` is emitted. | `ended_at`; terminal event; study-complete render if delivered |
| 14. Researcher stops and exports | Outside participant UI | Researcher stops recorder; streams exit, FFprobe metadata and hashes are written, manifest becomes `COMPLETED`. Session export takes a repeatable-read DB snapshot and indexes artifact manifests without embedding media/NDJSON. | Completed capture manifest/hash and versioned export hash |

If recording is disabled for development, the same study flow runs with `capture_run_id=null`. Browser telemetry remains independent of Windows video capture.

## 2. Complete terminology dictionary

| Term | Shown to participant? | Frontend meaning | Backend meaning | Database representation | Related IDs | Notes |
|---|---|---|---|---|---|---|
| Study | Yes | Entire learning experience | Frozen authored definition plus one participant execution | `StudyVersion`, `Session` | `study_version_id`, `session_id` | Avoid using “study” for one section |
| Session | Not as a label | One participant sitting | One protocol execution | `sessions` | `session_id` | Primary join key across DB/browser export |
| Section | Yes | One numbered unit, 1-4 | One configured SOLO transition | No Section table; derived from transition order | `transition_id` | Section 2 = C2 |
| Transition | No | Same unit as Section | Formal target movement | `Attempt.transition_id`, events, compiled snapshot | C1-C4 | Research term |
| C1/C2/C3/C4 | No | Section 1/2/3/4 | P→U, U→M, M→R, R→EA | Frozen protocol and row strings | `transition_id` | Stable backend identifiers |
| SOLO state | No | Hidden learner-model state | P, U, M, R, EA classification | Session, attempt, judgment, evaluation state fields | state ID | Judge observation and formal state are distinct |
| Formal state | No | None | Deterministically maintained protocol state | `Session.formal_state_id`; before/after fields | state ID | Does not advance after a prior unresolved gap |
| Teaching activity | Yes | One Tutor conversation plus its assessment path | One pedagogical attempt | `Attempt` | `attempt_id`, sequence | Activity 1/2/3 equals `sequence_in_transition` |
| Attempt | No | Teaching activity | One pedagogy intervention, assessment, judgment | `attempts` | `attempt_id` | Not an individual chat turn |
| Intervention | No | Tutor conversation portion | Instruction before assessment | Attempt status/timestamps/messages | `attempt_id` | Ends before assessment generation |
| Pedagogy | No | Hidden teaching approach | P1 Worked Example, P2 Guided Questioning, P3 Contrasting Case | `Attempt.pedagogy_id`; selection event | pedagogy ID | Random without replacement within transition |
| Study assistant | Yes | Conversational instructor | Tutor role | Tutor `Message`; Tutor `LLMCall` | message/call IDs | Preferred participant term |
| Tutor | No | Study assistant | Prompt/compiler/model operation role | `Message.role=TUTOR`, `LLMCall.purpose=TUTOR` | call/message IDs | “Tutor” also names the intervention subsystem |
| Tutor turn | Not literally | One assistant reply | One successful Tutor call plus Tutor message | linked `LLMCall` and `Message` | `llm_call_id` | Failed calls create no Tutor message |
| Learner response | “Your response” | Text typed in Tutor composer | Learner chat message | `Message.role=LEARNER` | message/attempt IDs | Distinct from assessment response |
| Message | No | Tutor or learner chat bubble | Ordered intervention utterance | `messages`, unique attempt+sequence | message/attempt/call IDs | Assessment text is not a Message |
| Assessment | Yes | Independent question/answer stage | Generated instance for one attempt | Instance + response + Judge chain | assessment ID | Broad term; qualify when precision matters |
| Assessment instance | No | The displayed assessment occurrence | Selected form plus generated/frozen prompt and status | `assessment_instances` | instance/attempt IDs | Exactly one per attempt |
| Assessment family | No | None | Form pool for a transition | Instance and snapshot | family ID | Configuration concept |
| Assessment form | No | Hidden template/source form | Random unused blueprint | `assessment_form_id`, blueprint/selection audit | form ID | Generated wording is `prompt_snapshot` |
| Assessment response | Not as noun | Text submitted on assessment screen | Immutable independent answer | `assessment_responses` | response/instance/action IDs | Exactly one per instance |
| Judge | No | Hidden evaluation operation | LLM constrained to assessment/scoring inputs | `LLMCall.purpose=JUDGE` | call ID | Deliberately blind to Tutor/pedagogy/history |
| Judgment | No | None | Validated Judge observation | `judgments` | judgment/response/call IDs | Model output, not final pass rule |
| Rubric evaluation | No | None | Deterministic decision over judgment evidence | `rubric_evaluations` | evaluation/judgment/attempt IDs | Authoritative pass/fail evidence |
| Pass | Not explicitly; completion shown | Section gate completed | Rubric passed for attempt | `Attempt.passed=true/status=PASSED`; evaluation/event | attempt ID | Local pass may not advance formal state after an unresolved prior section |
| Fail | No | Another activity may appear | Rubric failed | `passed=false/status=FAILED` plus reasons | attempt ID | Not a technical error |
| Unresolved | No | Section still appears complete and allows Next | Three pedagogies exhausted without pass | outcome details and continuation/completion events | attempt/transition IDs | Scientific result, not UI failure |
| Section completed | Yes | Navigation gate is open | Pass or exhausted/unresolved transition | `Session.phase=SECTION_COMPLETE`; event | transition/attempt IDs | Does not always mean passed |
| Teaching activity completed | Timeline marker | Intervention ended and assessment completed | Attempt reached closed assessment/judgment | attempt and closed assessment | attempt ID | UI timeline label is broader than `INTERVENTION_COMPLETED` |
| Tutor complete | No | Tutor elected to end teaching | Model disposition `COMPLETE` | `Attempt.completion_reason=TUTOR_COMPLETE` | attempt/call IDs | Not scientific pass |
| Budget exhausted | No | Tutor turn limit reached | Runtime forced intervention end | `completion_reason=BUDGET_EXHAUSTED` | attempt ID | Not failure by itself |
| Pedagogies exhausted | No | Section completion gate | Maximum distinct pedagogies failed | `PEDAGOGIES_EXHAUSTED_CONTINUE` | attempt/transition IDs | Administrative decision |
| Scientific outcome | No | None | `PASSED`, `UNRESOLVED`, or final completed/unresolved result | event payload/outcome details | transition/session | Must be separated from navigation |
| Administrative continuation | No | Next remains available | Continue after unresolved section | `SECTION_CONTINUATION_ALLOWED` | transition/attempt | Formal state stays behind |
| Processing | Accessible label/visual state | Waiting; input disabled | Latest LLM call `STARTED`/`RECEIVED`, non-stale | LLM call plus optional UI events | call ID | “Responding”, “Preparing”, or “Saving” by phase |
| Retry | Yes | Repeat failed model step | New call in same retry group | `retry_group_id`, `retry_number`, statuses | old/new call IDs | Tutor/assessment manual; Judge also gets one automatic retry in current code |
| Generation error | Yes | “That step could not be completed” | Latest relevant call failed, invalid, or stale | LLM error fields plus UI event | call ID | Technical error, not learner fail |
| Browser run | No | One loaded page context | Telemetry namespace created on script load | manifest/NDJSON and UI event field | `browser_run_id` | Reload normally creates a new run |
| Capture run | No | One recorder invocation | One screen stream and optional webcam stream | filesystem manifest; session nullable link | `capture_run_id` | Not a DB entity/FK target |
| LLM call | No | One processing operation/retry | Persisted request/response attempt | `llm_calls` | call/retry group IDs | Reserved before network transmission |
| Protocol event | No | None | Ordered scientific/runtime milestone | `protocol_events` | event ID, sequence, correlation | Total order only within a session's event stream |
| UI event | No | Click or DOM-render signal | Best-effort semantic observation | `participant_ui_events` | event/run/session IDs | Render does not prove seeing/reading |
| rrweb event | No | Browser DOM/input/scroll/pointer replay datum | Best-effort file-only event | per-run NDJSON | session/run/sequence | Inputs and learner bubbles are masked |
| Keyboard event | No | Coarse timing from two response fields | Paired key class/timing signal | per-run keyboard NDJSON | run/press/sequence | Never stores raw key/code/value |
| Read-only review | Yes | Reopen a completed section timeline | Rendering selection only; no protocol phase change | Derived view | transition/session | Assessment remains hidden; timeline remains stored |
| Terminal | “Thank you” | Study UI complete | Session phase after Finish | `phase=TERMINAL` | session ID | Status can be `COMPLETED` or `UNRESOLVED` |

## 3. Frontend-to-backend state mapping

| What participant sees | `session.phase` | Attempt status | Assessment status | Pending LLM purpose | Expected UI | Scientific meaning |
|---|---|---|---|---|---|---|
| Begin study | `INTERVENTION_ACTIVE` | `ASSIGNED` | none | none | Section 1; Begin study | First attempt selected, no exposure yet |
| Begin teaching activity N | `INTERVENTION_ACTIVE` | `ASSIGNED` | none | none | Later attempt; Begin teaching activity N | Prior attempt failed; new pedagogy assigned |
| Tutor conversation | `INTERVENTION_ACTIVE` | `INTERVENTION_ACTIVE` | none | none | Timeline, text area, Send | Intervention exposure active |
| Study assistant is responding | `INTERVENTION_ACTIVE` | active | none | `TUTOR` (`STARTED`/`RECEIVED`) | Timeline plus disabled composer | Model operation pending |
| Preparing your assessment | `ASSESSMENT_GENERATING` | `ASSESSMENT_GENERATING` | `GENERATING` | `ASSESSMENT` | Input disabled; poll | Teaching ended; independent item being generated |
| Assessment screen | `ASSESSMENT_ACTIVE` | `ASSESSMENT_ACTIVE` | `ACTIVE` | none | Prompt, response box, Submit | Assessment available, not yet submitted |
| Saving your assessment | `JUDGING` | `JUDGING` | `SUBMITTED` | `JUDGE` | Input disabled; poll | Response persisted, evaluation pending |
| Generation error / Retry | Usually same phase as failed operation | Same as phase | none/`GENERATING`/`SUBMITTED` | latest is failed/invalid/stale, not pending | Saved-work message and Retry | Technical failure only |
| Section completed | `SECTION_COMPLETE` | `PASSED`, or final `FAILED` after exhaustion | `CLOSED` | none | Timeline; Next/Finish | Either pass or scientifically unresolved—UI alone cannot distinguish |
| Completed-section review | Current session phase is unchanged | Historical final attempt | Historical `CLOSED` | none | Read-only timeline | Navigation/view state, not protocol transition |
| Study complete | `TERMINAL` | Final attempt completed | final `CLOSED` | none | Thank you and elapsed time | Session status/terminal reason determines completed vs unresolved |
| Refresh this page to continue | An unexpected/unrendered combination | varies | varies | none | Fallback | No scientific meaning; diagnostic UI fallback |

Declared but not assigned by the current runtime: attempt `INTERVENTION_COMPLETE`, `ASSESSMENT_SUBMITTED`, and `TECHNICAL_HOLD`; session `ABORTED`. `TRANSITION_READY` exists only during in-transaction session construction before the first attempt changes phase. Analysts must not infer missing records merely because these enum values exist.

## 4. Reconstructing one complete transition

For generic transition Cx, the causal chain is reconstructable as follows:

| Arrow / fact | Persisted proof | Strength |
|---|---|---|
| Session → Attempt 1 | `Attempt.session_id`; `ATTEMPT_CREATED` | Exact |
| Attempt → selected pedagogy | `Attempt.pedagogy_id`; `PEDAGOGY_SELECTED` candidates/exclusions/method/selection | Exact and redundant |
| Begin → first Tutor request | `PARTICIPANT_BEGAN_STUDY`; Tutor `LLMCall.started_at`; attempt start | Exact accepted operation; physical click only if UI event arrives |
| Tutor request → Tutor message | `Message.llm_call_id` to successful call; message sequence | Exact |
| Tutor message → learner response → following Tutor request | Ordered `Message.sequence_no`; learner text; next call ordered messages include recent dialogue | Exact within attempt |
| Intervention → completion | Attempt reason/time and `INTERVENTION_COMPLETED` | Exact |
| Completion → assessment selection | Assessment's attempt FK; `ASSESSMENT_SELECTED`; selection audit | Exact |
| Selected form → generated prompt | `generation_llm_call_id`; generation parsed output; frozen prompt/hidden context | Exact for successful generation |
| Prompt → participant assessment response | Instance-response FK; response text/time/action ID | Exact accepted response; display/attention not guaranteed |
| Response → Judge operation | Judge call's assessment/attempt IDs; ordered user message contains response | Exact |
| Judge output → Judgment | unique `Judgment.llm_call_id` and response ID | Exact |
| Judgment → deterministic rubric result | unique evaluation/judgment and attempt IDs; frozen rule/input/reasons | Exact |
| Evaluation → next attempt or section gate | `RUBRIC_EVALUATED`, then ordered `PEDAGOGY_SELECTED/ATTEMPT_CREATED` or `SECTION_COMPLETED` | Exact |

There is no single global sequence number spanning every table. Rows created in one transaction can share a database timestamp. Causality is nevertheless established by UUID links, unique constraints, per-attempt message sequences, retry numbers, and the per-session protocol-event sequence. The exact micro-order of unrelated writes inside a transaction is not scientifically meaningful and cannot always be recovered from timestamps alone.

## 5. Multiple-attempt reconstruction

- Ordering is exact from `(session_id, transition_id, sequence_in_transition)` and corroborated by `assigned_at` and protocol-event order.
- Assignment is exact from `Attempt.pedagogy_id`; the selection event also preserves eligible, excluded, selected, method, and selection timestamp.
- Unused pedagogies are reconstructable from earlier attempts and from each selection audit. The DB uniqueness constraint forbids reuse in a transition.
- Assessment choice is exact from the instance and its selection audit. A session-wide uniqueness constraint prevents form reuse.
- Attempts 2 and 3 have a deterministic `LearnerHistorySnapshot` with target/source attempt IDs and the exact structured summary supplied to the later Tutor compiler. The later `LLMCall` stores the actual request, so exposure is directly verifiable.
- Failure is exact in `Attempt`, `RubricEvaluation`, reasons, and `RUBRIC_EVALUATED`.
- Pass is exact in those same sources plus `SECTION_COMPLETED`.
- Third-failure exhaustion is explicit in `Attempt.outcome_details`, `SECTION_CONTINUATION_ALLOWED`, and `SECTION_COMPLETED(scientific_outcome=UNRESOLVED)`.
- Administrative continuation is explicit in the continuation event and later `PARTICIPANT_ADVANCED_SECTION`.

Therefore “Attempt 1 failed → Attempt 2 was created because of that failure → a different pedagogy and new assessment were used → result” is reconstructable without runtime memory. One nuance is not recoverable as an RNG replay: `SystemRandom` has no persisted seed. That is not a scientific gap because the complete candidate set, exclusions, method, selected result, and time are stored; the realized randomization is auditable even though it cannot be regenerated bit-for-bit.

## 6. Participant-response reconstruction

### Tutor interaction

| Required fact | Join | Result |
|---|---|---|
| Learner text, sequence, attempt, transition, server time | Message → Attempt | Unambiguous |
| Preceding/following Tutor message | Same attempt, `sequence_no` | Unambiguous when present; no following message if operation failed/abandoned |
| Tutor LLM operation | Tutor message's `llm_call_id`; following request also embeds ordered dialogue | Unambiguous for successful reply |
| Pedagogy and instructional move | Attempt pedagogy; Tutor message instructional trace; call audit context | Unambiguous |
| Model latency | Linked call `latency_ms` | Exact provider-request measurement for successful HTTP response; absent on provider exception |
| Frontend submit | UI event matched by session/run/time and server-resolved attempt | Best-effort, not guaranteed; accepted learner Message is authoritative |

### Assessment

Instance, form, blueprint, generated prompt, hidden scoring context, response, Judge prompt/request, raw and parsed Judge output, Judgment evidence, and deterministic evaluation all have direct joins. The chain is:

`Attempt.id → AssessmentInstance.attempt_id → AssessmentResponse.assessment_instance_id → Judgment.assessment_response_id → RubricEvaluation.judgment_id`, with the generation and Judge call IDs supplying model provenance.

The assessment response's `client_action_id` proves idempotent acceptance identity, not click time. The click event is optional corroboration. The Judge prompt is exact in its call record and intentionally excludes pedagogy, Tutor dialogue, prior failure, and learner history.

## 7. LLM reconstruction

| Item | Classification | Reason |
|---|---|---|
| Configured provider/model identifier | EXACTLY RECONSTRUCTABLE | Stored per call; does not prove an immutable provider-side weight revision |
| Generation parameters | EXACTLY RECONSTRUCTABLE | Stored JSON and exact request body |
| Canonical prompt and ordered messages | EXACTLY RECONSTRUCTABLE | Canonical text plus ordered request payload |
| Participant content sent | EXACTLY RECONSTRUCTABLE | Present in ordered messages/body |
| Output schema | EXACTLY RECONSTRUCTABLE | Stored in request payload with schema name/hash |
| HTTP request body | EXACTLY RECONSTRUCTABLE | `request_body_text`; secrets are intentionally absent/redacted |
| Raw successful provider response | EXACTLY RECONSTRUCTABLE | Raw text and payload stored |
| Parsed/validated output | EXACTLY RECONSTRUCTABLE | `parsed_response` on success |
| Token usage | PARTIALLY RECONSTRUCTABLE | Exact if provider supplied it; nullable/provider-defined |
| Provider request ID | PARTIALLY RECONSTRUCTABLE | Stored if response header supplied it |
| Start/completion | EXACTLY RECONSTRUCTABLE | Application persistence instants |
| Network/model latency | PARTIALLY RECONSTRUCTABLE | `latency_ms` covers client send-to-response on successful HTTP response; provider exceptions have no latency; queue/persistence/render time is separate |
| Retry relationship/order | EXACTLY RECONSTRUCTABLE | Shared `retry_group_id` and unique `retry_number` |
| Validation/provider error state | PARTIALLY RECONSTRUCTABLE | Status/class/message are stored; HTTP error response body/headers and failed-request latency are not retained |
| Provider finish reason/refusal | PARTIALLY RECONSTRUCTABLE | Usually remains inside raw/response payload; not normalized into columns |

Tutor, Assessment Generator, and Judge use the same durable call envelope. Assessment/Judge joins are direct; Tutor joins are direct for produced Tutor messages and by attempt/time for failed calls. A `STARTED` call proves reservation, not that bytes reached the provider. `RECEIVED` proves a provider response was persisted before parsing. On restart, current code marks stranded `STARTED` calls `PROCESS_INTERRUPTED` and resumes `RECEIVED` calls.

## 8. Participant UI reconstruction

| Phenomenon | Classification | Evidence and boundary |
|---|---|---|
| Section rendered | EXACT EVENT if delivered | Semantic render event; not proof of visibility/attention |
| Teaching activity rendered | EXACT EVENT if delivered | Event exists, but current activity number is normally null; latest attempt is resolved on server receipt |
| Tutor message rendered | EXACT EVENT if delivered | Payload has message sequence; attempt resolution can be wrong if a delayed batch arrives after a new attempt |
| Learner submitted | EXACT accepted action in DB; click NOT GUARANTEED | Message is authoritative; click is best-effort |
| Processing shown/hidden | EXACT EVENT if delivered | Semantic DOM state transition; rrweb can corroborate |
| Assessment rendered/submitted | Render/click NOT GUARANTEED; accepted response HIGH | DB proves submission, not rendering or reading |
| Error/Retry appeared | EXACT EVENT if delivered | LLM failure proves backend cause; UI render optional |
| Section completed appeared | EXACT EVENT if delivered | Backend event proves gate, not participant exposure |
| Next/Finish clicked | EXACT EVENT if delivered | Resulting protocol state proves accepted action, not physical click time |
| Scroll behavior | DERIVABLE from complete rrweb | No semantic scroll table; missing rrweb means unavailable |
| Browser reloads | DERIVABLE | New browser run/rrweb full snapshot; hard close with no delivered batch may leave only partial evidence |

The semantic recorder's `seen` set suppresses repeated render events with the same key in one browser run. Processing shown/hidden can repeat. HTMX may show an optimistic learner bubble and processing state before the server accepts an action; rrweb can capture that transient display, whereas the DB distinguishes accepted state.

**Current linkage defect:** `participant_telemetry.js` and `participant_keyboard.js` read `teaching_activity_number` from the element carrying `data-section-number`. The template puts `data-teaching-activity-number` on child composer/marker elements. Consequently the event context normally records the activity as null. The semantic script does locate a child activity for its internal deduplication key, but does not copy that number into the stored event. Server-side “latest attempt for section at receipt time” linkage usually compensates, but is not safe under delayed delivery across an attempt boundary.

## 9. Keyboard reconstruction

Directly stored per accepted event:

- `KEYDOWN`/`KEYUP`, run and client sequence, paired `press_id`;
- client wall-clock milliseconds, monotonic `performance.now`, and `performance.timeOrigin`;
- section, normally-null activity number, and Tutor/assessment surface;
- key class: CHAR, DIGIT, SPACE, ENTER, BACKSPACE, DELETE, TAB, ARROW, MODIFIER, PUNCTUATION, or OTHER;
- repeat/composition and modifier flags; batch/server receipt metadata.

Derivable later, within a browser run:

- dwell duration from paired down/up;
- inter-key flight time, pauses, bursts, typing onset/offset, deletion frequency, modifier use, coarse class sequences, and timing relative to browser events;
- approximate attempt linkage from section, surface, rrweb/UI state, and time. Exact attempt linkage is not guaranteed until the activity-number defect is fixed.

Not reconstructable:

- exact characters, words, raw keys/codes, textarea value from keyboard data, caret/selection state, semantic edit operations, clipboard contents/actions, mouse-driven edits, IME content, or keyboard activity outside the two response fields.

Repeat keydowns reuse a press ID; keyup without a locally observed initial keydown is discarded. Missing/pagehide batches can create incomplete pairs. These privacy constraints are appropriate; exact response text already exists in the authoritative DB and should not be duplicated into keystroke telemetry.

## 10. rrweb reconstruction

With complete batches and the pinned compatible player, rrweb can reconstruct DOM snapshots/mutations, scrolls, pointer and click activity, layout as represented by captured DOM/CSS state, processing elements, message appearance, HTMX navigation mutations, and much visible participant-facing text.

It intentionally cannot provide:

- typed input values (`maskAllInputs=true`);
- learner chat-bubble text (`maskTextSelector='.message.learner'`);
- canvas pixels (`recordCanvas=false`);
- cross-origin iframe contents (`recordCrossOriginIframes=false`);
- browser chrome, other applications, or physical gaze/attention.

Thus, when no batches are missing, replay is generally sufficient to visually recreate the web application's DOM experience, but not necessarily the exact rasterized screen or every private text value. The screen video is the raster source. rrweb event timestamps originate in the browser event, while wrapper emit time, monotonic time, sequence, batch receipt, and run metadata assist ordering.

Completeness is not presently cryptographically or numerically asserted: the browser manifest has run metadata and keyboard counts, but no rrweb event/batch count, terminal sequence, per-file hash, or “run closed cleanly” marker. NDJSON batch-marker files help deduplicate received batches but cannot prove unreceived batches never existed.

## 11. Video reconstruction

For each enabled stream, current capture artifacts provide:

- `LAUNCH_REQUESTED` and exact FFmpeg command;
- `PROCESS_STARTED` and PID;
- `FIRST_PROGRESS_OBSERVED` then `PROGRESS_OBSERVED` with FFmpeg raw progress and recorder `observed_at_utc`/`monotonic_ns`;
- timestamped FFmpeg stderr plus raw stderr;
- `STOP_REQUESTED` and `PROCESS_EXITED` return code;
- FFprobe start/completion, output JSON, streams/format, duration, resolution, frame rates, codec, and other reported metadata;
- media size and SHA-256; manifest hash.

The screen stream is mandatory in `record`; webcam is optional via `--no-webcam`. No audio input is configured. `active_capture.json.started_at_utc` is the marker creation time after streams have remained alive for 0.5 seconds, not the first captured frame. Stream process start and first progress are better anchors. The webcam and screen start independently and can have different durations.

Exact mapping of browser event X to video frame Y is **not currently established**. Maximum defensible alignment is approximate:

1. map FFmpeg `out_time`/frame progress to recorder observation UTC/monotonic anchors;
2. map browser `Date.now` events to UTC, preferably checking browser/server receipt offsets;
3. if browser and recorder share a correctly synchronized host clock, estimate the media timestamp/frame and visually validate against a known UI change.

Uncertainty includes browser/recorder clock offset, encoding/buffering, progress cadence, capture startup, frame drops, and lack of a shared synchronization flash/event. The manifest proves file integrity and recording process chronology, not exact exposure of a particular browser event at a particular frame.

## 12. Cross-source timeline reconstruction

| Source | Clock/order fields | What the clock means |
|---|---|---|
| Session/attempt/message/assessment/judgment DB | timezone-aware server/app timestamps | Authoritative persisted lifecycle times; no stored NTP/clock-health evidence |
| Protocol events | `sequence_no`, `occurred_at` | Exact event order per session; same transaction may share time |
| UI events | browser `client_event_at`, `client_performance_ms`, `performance_time_origin_ms`; server receipt | Client occurrence and within-run monotonic order plus delivery observation |
| rrweb | rrweb timestamp; wrapper emit UTC/performance; sequence; server receipt | Replay event time/order within run; best-effort delivery |
| Keyboard | event UTC/performance/origin; client sequence; server receipt | High-resolution relative timing within run |
| LLM calls | start/completion; successful-response `latency_ms` | Application reservation/completion and HTTP response latency |
| Recorder | `observed_at_utc`, `monotonic_ns` | Host observation and stable within-process ordering |
| FFmpeg media | PTS/time base; progress frame/out-time; FFprobe duration/rate | Stream-local media timeline |

A timeline such as “Tutor rendered → learner starts typing → submit → processing shown → LLM completes → Tutor rendered” can be built. Confidence is high for causal order and DB/LLM times; high for relative keyboard/UI timing within one intact browser run; medium across browser and server clocks; low-to-medium for browser-to-video frame alignment.

`performance.timeOrigin + performance.now()` supplies a second browser wall-time estimate and protects within-run intervals from wall-clock adjustments. It does not calibrate the browser against the server or recorder. `server_received_at - client_event_at` mixes clock offset, batching (up to the five-second interval), network, and server processing, so it is not a pure latency measurement. Reloads require separate per-run origins; UTC can merge runs only subject to clock accuracy.

## 13. Reconstruction confidence matrix

| Phenomenon | Source(s) | Reconstructable? | Confidence | Limitation |
|---|---|---|---|---|
| Session creation/start/end | Session, events | Yes | HIGH | Start means first intervention, not join |
| Section/transition | Snapshot, attempt, events | Yes | HIGH | “Section” is derived terminology |
| Attempt/order | Attempt, events | Yes | HIGH | None material |
| Assigned pedagogy | Attempt, selection event | Yes | HIGH | RNG stream itself not replayable |
| Tutor/learner messages | Messages | Yes | HIGH | Server persistence time, not reading time |
| Tutor prompt/output | LLM call, linked message | Yes | HIGH | Provider-side hidden processing unavailable |
| Assessment prompt/response | Instance/response | Yes | HIGH | Display/attention separate |
| Judge output/SOLO observation | Call/Judgment | Yes | HIGH | Model observation is not ground truth |
| Rubric/pass/fail | Evaluation/attempt/events | Yes | HIGH | UI “complete” does not reveal pass vs unresolved |
| Unresolved continuation | Outcome details/events | Yes | HIGH | Authored narrative is inconsistent |
| Click timing | UI events/rrweb | Best effort | MEDIUM | Delivery loss; client clock |
| Render timing | UI events/rrweb | Best effort | MEDIUM | DOM, not attention; deduplication |
| Typing dynamics | Keyboard | Yes within run | MEDIUM | Missing batches/pairs; activity number defect |
| Scroll behavior | rrweb | If intact | MEDIUM | No completeness assertion |
| Browser reload | Manifest/runs/rrweb | Usually | MEDIUM | Abrupt loss can obscure boundary |
| Screen state | Screen MKV | If associated/intact | HIGH visually | Browser window may be obscured; no exact event-frame map |
| Webcam state | Webcam MKV | If enabled/intact | HIGH visually | Optional; no gaze inference automatically |
| LLM latency | LLM call | Successful response only | HIGH/MEDIUM | Missing for provider exceptions; not end-to-end UI latency |
| Provider errors | Call status/class/message | Partly | MEDIUM | Error body/headers/latency omitted |
| Technical vs learner failure | Calls vs evaluations | Usually | MEDIUM | Abandoned/aborted sessions lack durable terminal reason |
| Video/browser alignment | Multiple clocks/progress | Approximate | LOW | No clock calibration/shared anchor |

## 14. Redundant evidence

| Fact | Primary evidence | Secondary evidence | Tertiary evidence |
|---|---|---|---|
| Session created | Session row | `SESSION_CREATED` | export inclusion |
| Pedagogy assigned | Attempt | selection event | LLM audit context/prompt |
| Learner Tutor submission | Learner Message | submit UI event | rrweb/screen/keyboard cessation |
| Tutor reply | Tutor Message | successful call/parsed output | protocol/UI render/rrweb/screen |
| Intervention ended | Attempt completion fields | `INTERVENTION_COMPLETED` | assessment instance/call |
| Assessment selected/generated | Assessment instance | selection/generated events | generation call |
| Assessment submitted | AssessmentResponse | instance status/time and event | click/rrweb/screen |
| Judge completed | successful call | Judgment | Evaluation/event/UI transition |
| Pass/fail | RubricEvaluation | Attempt status/pass | rubric event/section progression |
| Unresolved | outcome details | continuation event | section event/final session status |
| Section navigation | participant-advanced event | next attempt | UI click/rrweb/screen |
| Recording integrity | media SHA in manifest | standalone manifest SHA | FFprobe/logs/file size |

## 15. Single points of failure

- `StudyVersion.compiled_snapshot` is the authoritative interpretation of IDs and rules. Source files alone may later change; preserving the snapshot is essential.
- `Attempt.pedagogy_id` is primary, but selection events and prompts redundantly recover it. Loss of all three would destroy condition assignment.
- `RubricEvaluation` is the only complete deterministic decision object. Attempt/event pass flags survive its loss, but frozen rules, exact inputs, and reasons do not.
- Exact accepted participant text depends on `Message` and `AssessmentResponse`. Masked rrweb/keyboard cannot restore it; screen video might expose it but is not a safe canonical substitute.
- Without UI events, accepted action ordering and protocol remain strong; click/render timing weakens.
- Without rrweb, semantic UI states remain, but scroll/pointer/DOM replay is lost.
- Without keyboard NDJSON, typing dynamics cannot be recovered from DB, rrweb (masked input), or video reliably.
- Without the capture manifest but with MKV, FFprobe can recover media properties and file hashing can be redone; process/readiness commands, UTC/monotonic anchors, device identity, progress evidence, and original hash attestation are lost.
- A new `browser_run_id` on reload is joinable by session and UTC, but there is no parent/previous-run ID or explicit reload reason.
- Capture association depends on `Session.capture_run_id`. A loose capture directory cannot be assigned to a participant with certainty after the active marker and DB/export link are lost.
- The export indexes manifests but does not copy or hash every referenced browser/media artifact. Preservation must include the artifact tree, not just export JSON.

## 16. Missing-data audit

| Missing field/data | Why it matters | Can existing data derive it? | Recommendation |
|---|---|---|---|
| Correct attempt/activity number in UI and keyboard events | Attempt-specific exposure and typing comparisons can be misjoined after retries | Often inferable from server receipt/time/rrweb; not guaranteed | **CRITICAL BEFORE COLLECTION** if behavioral analysis is planned; small correctness fix |
| Durable termination/abandonment reason, including technical vs participant/researcher stop | Attrition/exclusion analysis and failure denominators | Partly from last phase/calls/`PARTICIPANT_EXITED`; not definitive | **CRITICAL BEFORE COLLECTION** |
| Reconciled protocol rule for third failure | Scientific interpretation and preregistration conflict with implementation | Runtime behavior is clear; intended design is not | **CRITICAL BEFORE COLLECTION** as a governance/config decision |
| Browser-recorder synchronization anchor or measured clock offset | Frame-level screen/webcam-to-action analysis | Approximate only | **CRITICAL** only if exact cross-modal timing is a planned endpoint; otherwise **USEFUL BUT OPTIONAL** |
| rrweb expected/final sequence, event count, file hash, clean-close marker | Detect missing/truncated replay | Batch markers show received data only | **USEFUL BUT OPTIONAL** |
| Failed HTTP response body/status/request ID and failure latency | Diagnose/model reliability analyses | Error class/message only; status sometimes encoded in message | **USEFUL BUT OPTIONAL**; avoid secrets |
| Explicit accepted action timestamps for Next/Finish | Separate server acceptance from optional client click | Protocol event time is the accepted result | **NOT NEEDED**; event is sufficient |
| Exact intervention exposure/reading time | Strong claims about attention/dose | Approximate from render/action/typing; never actual reading | **NOT NEEDED** unless study claims require gaze/attention |
| Exact current screen state continuously | Millisecond replay | rrweb/video approximate/visual | **NOT NEEDED** for core science |
| Idle periods | Behavioral pacing | Derivable within intact UI/keyboard/rrweb runs | **NOT NEEDED** as a new field |
| Scroll position | Reading/navigation studies | rrweb derives it when complete | **NOT NEEDED** as duplicate telemetry |
| Typing onset | Response-process analysis | First keyboard event derives it | **NOT NEEDED** as a new field after fixing attempt context |
| Raw keys/clipboard/caret | Detailed editing reconstruction | Intentionally unavailable | **NOT NEEDED**; privacy cost outweighs value |
| Audio | Verbalization/environment study | Not available | **NOT NEEDED** unless a separate approved research question requires it |

## 17. Terminology consistency audit

| Current term | Where used | Actual concept | Recommended canonical term | Frontend change? | Backend change? |
|---|---|---|---|---|---|
| Section | Templates/UI | SOLO transition | Participant: Section; research: SOLO transition | No | No |
| Teaching activity | UI/telemetry | Pedagogical attempt | Teaching activity / pedagogical attempt | No | No |
| Attempt | DB/runtime | Whole pedagogy+assessment cycle | Pedagogical attempt | N/A | No |
| Study assistant | UI | Tutor model role | Study assistant (Tutor) | No | No |
| Response | Both forms | Either chat Message or assessment response | Qualify as Tutor response or assessment response | Label context is adequate | Use precise entity names in docs |
| Assessment | UI/code | Stage, instance, form, or prompt | Independent assessment; instance/form when technical | No | No |
| Completed | UI | Gate opened by pass **or unresolved exhaustion** | Section complete (navigation gate) | Consider neutral explanatory copy only after governance review | No rename |
| Passed | Runtime | Rubric success for attempt | Rubric pass | Do not expose unless intended | No |
| Unresolved | Runtime/research docs | No transition pass after all pedagogies | Scientifically unresolved | Optional debrief decision | No |
| Tutor complete | Runtime | Model ended intervention | Tutor-ended intervention | No | No |
| Budget exhausted | Runtime | Turn cap ended intervention | Tutor-turn budget exhausted | No | No |
| Generation error | Telemetry/UI | Any retryable model step failure | Model-operation error | Existing participant copy is better | No |
| `COMPLETED_WITH_UNRESOLVED_SECTIONS` | Runtime | Participant reached end but scientific chain unresolved | Session finished; scientific status unresolved | UI may remain neutral | No |
| Authored “stop progression” | protocol YAML | Conflicts with current administrative continuation | Resolve to one authoritative policy | Depends on decision | Config/docs or runtime must align |
| Capture clock field names | existing specification | Current `observed_at_utc`/`monotonic_ns` | Use current exact names | N/A | No |

## 18. Canonical vocabulary

| Participant-facing | Research/thesis term | Backend identifier/entity |
|---|---|---|
| Study | Participant session under a frozen study version | `Session`, `StudyVersion` |
| Section N | SOLO transition Cn | `transition_id` |
| Teaching activity N | Pedagogical attempt N within transition | `Attempt.sequence_in_transition` |
| Study assistant | Tutor model role | `TUTOR` Message/LLM purpose |
| Your response (teaching) | Learner Tutor response | learner `Message` |
| Independent assessment | Attempt-specific assessment instance | `AssessmentInstance` |
| Your response (assessment) | Independent assessment response | `AssessmentResponse` |
| Responding/Preparing/Saving | Pending model operation | `LLMCall` + session phase |
| Retry | Model-operation retry | retry group/number |
| Section completed | Section navigation gate | `SECTION_COMPLETE`; inspect outcome separately |
| — | Assigned pedagogical condition | `pedagogy_id` |
| — | Judge observation | `Judgment` |
| — | Deterministic rubric decision | `RubricEvaluation` |
| — | Formal SOLO state | `Session.formal_state_id` |
| — | Scientific section outcome | event payload: PASSED/UNRESOLVED |
| — | Administrative continuation | `SECTION_CONTINUATION_ALLOWED` |
| — | Browser recording context | `browser_run_id` |
| — | Host audiovisual recording invocation | `capture_run_id` |

For figures and thesis prose, use “Section 2 (SOLO transition C2)” on first mention and “Teaching activity 2 (the second pedagogical attempt)” on first mention. Never equate “section completed” with “passed” without inspecting the scientific outcome.

## 19. Persisted-session reconstruction

### Evidence used

The existing ignored export `exports/live-e2e-u2026live02.json` was read without querying or mutating the database. It is export schema 1.0, application build `dev`, study content v0.4/snapshot schema 3, session `0abb67d7-ca29-4484-948d-c98dc5a25758`. It predates the current export schema 1.1 and has no UI events, capture association, or artifact index. It is therefore a useful “DB-only reconstruction under missing optional streams” case, but not a golden fixture for the exact current build. Docker was unavailable during this audit, so no new integration session was generated.

### Reconstruction using persisted artifacts only

1. Session was created at `2026-10-01T23:25:57.972231+00:00`, first intervention began at `23:26:01.903674`, and the session ended at `23:44:40.691979`.
2. C1 attempt 1 used P1 and assessment form C1-A4. Fifteen messages and eight successful Tutor operations were recorded. Teaching ended by `BUDGET_EXHAUSTED`. Four Judge operations occurred (three invalid, one successful). The rubric passed and formal state moved P→U.
3. C2 attempt 1 used P1/form C2-A3, ended `TUTOR_COMPLETE`, and failed. Two Tutor retries and four invalid Judge attempts before a successful Judge are visible.
4. C2 attempt 2 used a fresh pedagogy P3/form C2-A4, had deterministic history from one source attempt, exhausted the Tutor budget, and failed.
5. C2 attempt 3 used the remaining pedagogy P2/form C2-A1, had history from two source attempts, and failed after budget exhaustion. The stored result records pedagogies exhausted, scientific `UNRESOLVED`, and administrative continuation. Formal state remained U.
6. The participant advanced to C3. Attempt 1 used P2/form C3-A2 and locally passed. Because the session formal state was still U rather than C3's required M, the evaluation retained U and marked formal advancement blocked by the prior unresolved section.
7. C4 attempt 1 used P1/form C4-A2 and failed. C4 attempt 2 used P3/form C4-A1, incorporated one prior C4 attempt in its deterministic history, and locally passed; formal state still could not advance through the missing chain.
8. The session ended `UNRESOLVED / COMPLETED_WITH_UNRESOLVED_SECTIONS`, with 7 attempts, 101 messages, 7 assessment instances/responses/judgments/evaluations, 101 LLM-call records, and 219 ordered protocol events.
9. LLM evidence includes 54 successful Tutor calls, 15 invalid Tutor outputs, 7 provider-failed Tutor calls, 7 successful assessment-generation calls, 7 successful Judge calls, and 11 invalid Judge outputs. Retry groups/numbers make each sequence reconstructable.

### Comparison and ambiguities

The reconstructed path satisfies current relational/runtime invariants: no repeated pedagogy within a transition, no repeated assessment form, later-attempt history source counts are correct, third failure emits unresolved continuation, later local passes cannot bridge a missing formal prerequisite, and final status remains unresolved. The current deterministic integration tests explicitly verify the first five of those behaviors; the current E2E passing test verifies the all-pass alternative through C1-C4.

What cannot be recovered from this export is equally clear:

- no optional UI, rrweb, keyboard, screen, or webcam evidence is associated;
- physical clicks, rendered states, typing, scroll, and attention cannot be reconstructed;
- no independent “known execution log” accompanies this old live E2E export, so comparison is against stored invariants/current tests rather than hidden runtime memory;
- the `dev` build identifier is not a source commit, so exact historical code provenance is weaker than the frozen study provenance;
- timestamps are UTC in this schema-1.0 export, while current schema 1.1 declares research-timezone transformation behavior.

This case demonstrates the central conclusion: the scientific protocol is reconstructable even when all optional observational streams are absent, but behavior and audiovisual experience are not.

### Reconstruction script decision

No script was added in this pass. A read-only script would be useful, but the semantics for cross-source clock fusion, delayed UI-event attempt linkage, export-version differences, and missing artifact completeness markers remain intentionally classified rather than normalized. Encoding those as if exact would create false confidence. A later script should consume an export plus artifact root—not default to a live mutable DB—and label every item as direct, derived, or inferred.

## 20. Recommendations before real collection

### Must Fix Before Real Collection

1. **Resolve the third-failure policy.** Make the authored protocol, researcher documentation/preregistration, and current `UNRESOLVED` administrative-continuation runtime agree. The runtime is internally consistent, but scientific intent cannot remain contradictory.
2. **Persist the actual teaching activity number in semantic and keyboard telemetry** if attempt-specific behavioral analysis is in scope. Read it from the located child activity/composer (or expose it once on the section root), and add a browser test asserting a non-null activity on attempts 2/3.
3. **Add a durable terminal/withdrawal/technical-abort classification.** A participant who closes the browser or a study stopped for technical reasons must be distinguishable from an active/incomplete session and a scientific failure. Use the existing `ABORTED`/terminal vocabulary only after defining its allowed reasons and workflow.
4. **If video/browser frame alignment is a preregistered outcome, add and validate a shared synchronization anchor before collection.** If video is only qualitative/contextual evidence, document approximate alignment and do not add complexity.

Operationally, real collection should also use a source-identifying `APP_BUILD_ID`, retain export plus complete artifact tree, verify hashes, and set `REQUIRE_ACTIVE_CAPTURE=true` only when capture is actually required. Development may safely keep it false and use `--no-webcam`; screen capture remains mandatory when the recorder itself is run.

### Recommended improvements

- Add rrweb received event/batch counts, last sequence, file hash, and clean-close status to the browser manifest.
- Correct the capture clock names in the existing data-collection specification.
- Persist normalized HTTP status/finish/refusal and failure latency where available, without retaining secrets.
- Add a versioned, read-only reconstruction tool after the linkage policy is settled; have it report missing files and sequence gaps rather than silently infer them.
- Add a current-schema deterministic export fixture covering fail→retry→unresolved→administrative continuation, so reconstruction can be regression-tested without Docker or a live provider.

### Already sufficient — do not add more data

- Do not collect raw keystrokes, clipboard contents, caret state, or duplicate typed text. Current coarse dynamics plus authoritative response text are enough and materially safer.
- Do not expose or duplicate hidden scoring context, pedagogy, Judge output, or formal state in participant UI telemetry.
- Do not add another pass/fail event stream: evaluation, attempt, and protocol event already provide redundancy.
- Do not store video blobs in PostgreSQL. The capture ID, manifests, hashes, and governed artifact storage are the appropriate separation.
- Do not add gaze/attention claims from render events. If actual attention is not a research question, DOM/rrweb/screen evidence is sufficient.

# Is the Current Dataset Sufficient for Scientific Reconstruction?

| Area | Decision | Why |
|---|---|---|
| A. Scientific/protocol reconstruction | **SUFFICIENT WITH LIMITATIONS** | Conditions, attempts, randomization result, assessment, judgment, deterministic progression, unresolved continuation, and frozen study are strong. The authored/runtime third-failure policy must be reconciled before interpreting future data. |
| B. Participant-response reconstruction | **SUFFICIENT** | Tutor and assessment text, sequence, context, and model/evaluation joins are direct and immutable. UI click evidence is not required to establish accepted responses. |
| C. LLM-operation reconstruction | **SUFFICIENT WITH LIMITATIONS** | Exact requests, successful raw/parsed responses, parameters, models, retry chains, usage, and successful latency are stored. Provider-side revision and detailed failure response/latency are incomplete. |
| D. Browser-behavior reconstruction | **SUFFICIENT WITH LIMITATIONS** | Semantic events plus rrweb support defensible render/click/scroll/reload analysis when delivered, but collection is best-effort, completeness is not proven, activity context is currently defective, and render is not attention. |
| E. Typing-dynamics reconstruction | **SUFFICIENT WITH LIMITATIONS** | Dwell/flight/pause/burst/deletion/modifier measures are available without raw text. Exact attempt assignment is not guaranteed until activity context is fixed; missing batches/pairs must be screened. |
| F. Screen/video reconstruction | **SUFFICIENT WITH LIMITATIONS** | Intact associated media, logs, FFprobe data, progress anchors, and hashes reconstruct each recording well. Webcam is optional, audio absent, and capture association must be preserved. |
| G. Cross-modal timing reconstruction | **INSUFFICIENT** for exact frame/event claims; **sufficient with limitations** for coarse chronology | Within-source timing is good, but there is no explicit browser/server/recorder clock calibration or shared media synchronization event. Approximate and visually validated alignment is possible. |

Against the intended standard—not perfect millisecond replay, but defensible reconstruction of experimental condition, learner actions, instruction, assessment, model behavior, progression, timing, and available behavioral evidence—the core dataset is fit after the genuinely critical consistency/linkage issues above are resolved. More invasive telemetry would add privacy and operational risk without improving the central scientific record.
