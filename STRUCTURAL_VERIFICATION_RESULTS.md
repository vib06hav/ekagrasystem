# F1 v0.4 structural verification results

Run date: 2026-10-31. All records below use the existing FastAPI/Jinja,
PostgreSQL, and `AIExecutionRuntime` application. Development mode remained
enabled; no research participant capture was enabled.

| # | Scenario | Result | Actual evidence |
|---:|---|---|---|
| 1 | Real Tutor message and authorized completion/advance | PASS | `task7_real_provider_session_trace.json`: one persisted Tutor message; Tutor did not self-complete, so the explicitly development-gated advance was recorded. |
| 2 | 3 MCQs plus 1 subjective item | PASS | `task7_real_provider_session_trace.json`: `mcqs: 3`, `subjective: true`. |
| 3 | Writer and Semantic Reviewer records | PASS | Same trace: four `ASSESSMENT_WRITER` and four `SEMANTIC_REVIEW` calls, all `SUCCEEDED`. |
| 4 | Freeze, private keys, and learner-visible package | PASS | Same trace: frozen fingerprint, three private MCQ keys, closed immutable package. `public_projection` was used by the production submission path. |
| 5 | Submission and real blind Judge | PASS | Same trace: one response, one real `JUDGE` call, one evaluation. |
| 6 | Deterministic scoring and progression | PASS | Same trace: MCQ 3/3 plus Judge subjective score 0/2 yielded a persisted failed attempt and next intervention attempt; no formal-state advance. |
| 7 | Interrupted assessment-generation recovery | PASS | `tutor_assessment_recovery_trace.json`: atomic reservation, orphan reconciliation, one retained checkpoint, and no duplicate freeze build. |
| 8 | Saved-response recovery for all four roles | PASS | `received_role_dispatch_trace.json`: Tutor, Writer, Reviewer, and Judge each finalized `SUCCEEDED`; zero provider sends. |
| 9 | Review hold, exhaustion, and authorized technical recovery | PASS | `judge_hold_retry_trace.json`: one response/evaluation after linked Judge retry. `technical_hold_trace.json`: persisted hold requeued to one linked final evaluation. |
| 10 | Three genuine failed attempts to UNRESOLVED terminal state | PASS | `unresolved_termination_trace.json`: sequences `[1,2,3]`, C1 `UNRESOLVED`, unchanged formal state, terminal `UNRESOLVED`. |
| 11 | No formal SOLO jump after unresolved prerequisite | PASS | `formal_advancement_gate_trace.json`: C2 assessment passed but formal state remained P; repeated finalization retained one evaluation. |
| 12 | Two independent browser sessions | PASS | `task7_browser_isolation_trace.json`: distinct session IDs, both pages rendered, no cross-session identifier leakage. |
| 13 | Repeated/concurrent requests do not duplicate records | PASS | `task6_http_race_trace.json`: concurrent HTTP posts returned 200 and 409 with one Tutor call. `task6_concurrency_recovery_trace.json` records separate PostgreSQL Tutor and Judge races. |
| 14 | Actual Docker restart and committed-state recovery | PASS | `task7_restart_recovery_trace.json`: after `app` restart, committed call `32610733-4ed4-41fe-8102-b7f41643e81b` recovered to `SUCCEEDED`, created one message, and retained no provider request ID. `/health/live` returned 200. |
| 15 | Full real-provider C1–C4 transition progression | NOT EXECUTED | C1 completed through a real provider session. C2–C4 end-to-end provider assessments were not run in this structural pass; no learner outcome was fabricated to claim them. The configured supported mappings remain C1-A1-Q2, C2-A1-Q2, C3-A1-Q2, C4-A1-Q3. |

## Fault-injection details

- `task6_concurrency_recovery_trace.json`: an injected local failure after a
  Tutor provider response was persisted left the call `RECEIVED` with
  `APPLICATION_FAILURE`. Re-applying that exact response produced one message,
  one assessment reservation, and zero provider sends.
- `task7_real_provider_session_trace.json`: fresh real provider path contained
  Tutor, build, Writer, Reviewer, and Judge operations. The development advance
  was used only after the real Tutor response did not mark instruction complete.
- `tutor_assessment_recovery_trace.json`: repeated startup reconciliation did
  not create an additional assessment-build operation.

No scientific YAML, authored prompts, typed policy rules, or grading contracts
were changed during this verification task.
