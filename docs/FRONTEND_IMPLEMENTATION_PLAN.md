# Ekagra AI — Frontend Implementation Plan (v2, frontend-only)

**Status:** plan only; no code written. Awaiting approval.
**Supersedes:** the backend-oriented recommendations in `FRONTEND_ARCHITECTURE_AUDIT.md` (§E.3, §H, §J.2 and the backend rows of §F). The audit's *findings* about the current code remain valid.

## 0. Ground rules

* **Final design (not revisited):** controlled, pseudo-randomized, within-participant. Every participant meets all three pedagogies across the four SOLO transitions, one pedagogy repeated (e.g. Socratic → Contrast → Worked → Socratic). The frontend must therefore render **any pedagogy in any section**.
* **Frontend only:** `templates/`, `static/`, CSS, client JS, and Playwright tests. No changes to `web.py` routes, `runtime/`, `db/`, migrations, `telemetry.py`, study YAML, assignment or evaluation logic.
* **Preserve:** the Jinja2 + HTMX model (single `#session-main` swap), existing styling tokens/dark mode, every telemetry hook in audit §C.5 (`data-*`, IDs, `hx-post` URLs, button/heading text asserted by Playwright), and the participant-safe projection.
* **Rule for anything needing the backend:** build the UI to the extent it can be built honestly, mark it in the Dependency Register (§4), do not fake persistence.

## 1. What the frontend can and cannot do today

| Feature | Frontend-only feasible? | Basis |
|---|---|---|
| Consent / onboarding UI | **Yes** (display + the existing `institutional_id` + `acknowledged` POST) | `/join` already accepts exactly these fields; extra fields are ignored by the server and not stored. |
| Course intro, objectives, What–Why–How framing | **Yes** (static template content, identical for all participants) | Pure content. |
| Five-level SOLO progress visualization | **Partly** | Section count/number are in `view` (`section_number`, `section_count`, `sections[].state`). Four sections map 1:1 to the four transitions in a fixed order, so "you are on step k→k+1 of 4" is derivable. The *attained* level is not exposed (it can stay unchanged after a failed attempt). |
| Socratic interface | **Yes** — it is the existing chat | Reuse `timeline` + `#tutor-composer`. |
| Contrasting Cases / Worked Examples interfaces | **Only generically** | The browser is never told which pedagogy is active (`view()` omits `pedagogy_id` by design). Tutor output is a single markdown text per turn. See D1. |
| Session recap | **Yes if static/generic**; conversation-specific recap needs data (D4) | |
| NASA-TLX UI | **UI yes; saving no** | No endpoint or table exists (D5). |
| MCQ UI | **UI yes; items, scoring, saving no** | No item source or endpoint exists (D6). |
| Completion & navigation | **Yes** (restyle terminal state, real debrief text from research team) | |
| Telemetry for new screens | **Only what DOM recording gives for free** | rrweb already records all DOM changes. New semantic event types/surfaces are rejected by the server whitelist (D7). |

## 2. Screen flow (client view) and where each screen lives

The server only knows: *join → sections 1–4 (tutor chat + assessment each) → finish*. New screens are attached around that without altering it:

```
Pre-session (before POST /join)         In-session (existing server state)            Post-session (after TERMINAL)
────────────────────────────────         ──────────────────────────────────            ──────────────────────────────
1 Welcome / purpose                      Section k (k=1..4):                           (blocked until backend, see D5/D6)
2 Course intro + objectives                 What–Why–How lesson frame (client)         Recap → NASA-TLX → MCQ → Complete
3 What–Why–How "how this works"             → teaching chat (pedagogy interface)
4 Consent + University ID  ──POST /join──▶  → assessment (existing open-text)
                                            → section complete → Next / Finish
```

Notes:
* Steps 1–3 are plain GET pages/partials (client-side stepping, e.g. `<details>`-free progressive disclosure or separate GET fragments) with no server state; refresh simply restarts them, which is harmless because no session exists yet.
* Step 4 is the **only** place data leaves the browser: it keeps `name="institutional_id"`, `name="acknowledged"`, label **University ID**, button **Continue** (Playwright).
* The existing `Next section` / `Finish study` buttons and their `hx-post` URLs stay.
* **Recap / TLX / MCQ placement is the one open design question** (§5, Q1): after `TERMINAL` the server accepts no more actions, and before `Finish study` there is no place to store answers. Until the backend supplies one, these three screens are built as complete, reviewable UI but gated behind a flag (default **off**), so production flow and tests are unaffected.

## 3. Incremental phases (each ends green on the existing Playwright suite)

### Phase 2 — Foundation (zero visible/behaviour change)
* Move the ≈235 + ≈80 lines of inline CSS into `static/css/{tokens,base,components,join,session}.css`; de-duplicate the twin dark-mode blocks (keep both selectors `@media (prefers-color-scheme)` and `[data-theme=dark]`).
* Vendor HTMX 2.0.4 under `static/vendor/htmx/2.0.4/` (same pattern as rrweb) and reference it locally. *(Keeps the fallback fetch path untouched.)*
* Split `session_main.html` into stage partials with **byte-identical markup** for today's states; `session_main.html` becomes a dispatcher.
* Add component CSS only (progress stepper, content card, radio/likert/slider, callout) — unused until later phases.
* **Gate:** Playwright suite unchanged and passing; a scripted-run DOM diff of attributes in §C.5 shows no change.

### Phase 3 — Pre-session experience: onboarding, intro, objectives, W-W-H, consent
* Redesign `join.html` as a 4-step guided entry (stepper, back/continue, keyboard accessible, mobile-first).
* Content: welcome/purpose; course introduction and learning objectives (Fibonacci recursion → memoization, in learner language, no SOLO jargon, no pedagogy mention); W-W-H explanation of the lesson format; consent text. All copy supplied by the research team; placeholders clearly marked until then (the existing "Draft — pending approval" banner is retained until real text arrives).
* Final step is the existing form, unchanged field names/labels; the checkbox is split into clear consent statements **visually only** (the server accepts a single `acknowledged`; all statements must be checked client-side to enable submit, then one `acknowledged=yes` is posted).
* **Gate:** e2e join helper (`get_by_label("University ID")`, `acknowledged` checkbox, `Continue`) still passes; new e2e covers stepping and mobile layout.

### Phase 4 — In-session shell: progress and What–Why–How lesson frame
* Replace the "Section N" sidebar list with a **five-level SOLO path**: five nodes, four connecting segments (= the four sections), current segment highlighted, completed segments filled, using only `sections[].state`/`section_number`/`section_count`. Labels are participant-friendly level names supplied by the research team (open Q2). Link behaviour (review of completed sections via `/session/sections/{n}`) is kept; `.section-link`, `aria-current="step"`, `.nav-sub` hooks stay.
* Per section, show a W-W-H header card above the conversation: **What** (this step's target idea), **Why** (why it matters), **How** (how you'll work on it). Text comes from a static lookup keyed by `section_number` in the template — identical for every pedagogy, kept visually separate from the teaching area (satisfies "teaching separate from common intro/conclusion"). Placed outside the `.conversation` and without telemetry attributes, so no existing event changes.
* Add a section-closing "What you just practised" card on the existing `SECTION_COMPLETE` state, above the existing `Next section`/`Finish study` button (same `data-section-complete` element retained).
* **Gate:** existing e2e + new assertions that the header is identical across sections' pedagogies (see D1 for how this is tested).

### Phase 5 — Pedagogy interfaces (Socratic / Contrasting Cases / Worked Examples)
Constraint: the page is not told the pedagogy. Plan therefore has two tiers:

* **5a (no backend needed):** upgrade the shared tutor surface so all three pedagogies read well: safe Markdown + code-block rendering of tutor messages (sanitised, no raw `innerHTML` of LLM text), clearer tutor/learner bubbles, step-aware prompts in the composer placeholder ("Explain your thinking…"), keep `#tutor-composer`, `#learner-text`, `.message.learner`, `data-tutor-message-sequence`.
* **5b (needs D1):** pedagogy-specific layouts selected server-side from a participant-safe key: Socratic = conversational focus with a "your reasoning so far" rail; Contrasting Cases = side-by-side case cards with a compare/contrast prompt strip; Worked Examples = step-by-step solved example panel with "next step" reveal. Each is a CSS/partial variation on the same message stream and the same form/IDs. Without D1, 5b cannot be switched per participant and is **not started**.
* Never render pedagogy names, IDs or classes; a neutral key like `data-layout="a|b|c"` is the maximum (and must be agreed, since it is itself visible to the participant and recorded by rrweb).

### Phase 6 — Recap, NASA-TLX, MCQ, completion (UI complete, flag-gated where data is missing)
* **Recap:** static summary of the four steps' learning objectives (reusing Phase 4 content) with visual path; no conversation data.
* **NASA-TLX:** six subscales (Mental, Physical, Temporal, Performance, Effort, Frustration) as accessible 0–100 sliders with numeric readout and keyboard control; optional second step for the 15 pairwise weights if the team wants the weighted version (Q3). Posting target: none yet (D5).
* **MCQ:** reusable item renderer (radio group, one-per-view, progress bar, confirm-before-submit, no correctness feedback), driven by a data structure the page receives (D6); no keys on the client, ever.
* **Completion:** restyle `TERMINAL` panel keeping `data-study-complete`, `Thank you` heading, `data-duration`; replace the debrief placeholder with team-approved text; add "what happens next" and researcher contact.
* Flag: a Jinja condition on a **config-free** constant in the template (e.g. `{% set show_post_session = false %}`) so no `Settings`/backend change is needed. Default off.

### Phase 7 — Accessibility, responsive and visual polish
* WCAG 2.2 AA pass (focus order in stepper, `aria-live` for processing, contrast in both themes, reduced motion already supported), 320–1440 px layouts, print-safe debrief.
* Visual consistency review in light/dark.

### Phase 8 — Test and documentation hardening
* Extend Playwright: pre-session stepper, consent gating, progress path states, markdown rendering safety (XSS payload in a fake tutor reply), theme persistence, mobile drawer, post-session screens when flag on.
* Keep every existing assertion; add a "telemetry hooks present" test asserting the §C.5 selectors exist on every stage that previously had them.
* Update README (frontend section) only; data-spec doc untouched except a note listing new screens that are not instrumented.

## 4. Backend Dependency Register (documented only — nothing to be implemented by this work)

| ID | Needed by | Missing capability today | Frontend behaviour until provided |
|---|---|---|---|
| D1 | Phase 5b | `view()` does not expose the active attempt's pedagogy (or a neutral layout key). Needed to choose Socratic / Contrast / Worked layout and to verify "one repeated pedagogy" rendering. | Generic upgraded chat (5a) for all. |
| D2 | Phase 4 accuracy | Attained SOLO level / formal state not in `view()`. | Show *progress along the four steps*, not attained level. |
| D3 | Phase 3 | Consent is stored only as `study_information_acknowledged: true` in an event; no consent version/text hash, no per-statement record, no demographics/prior-knowledge fields. | Single `acknowledged` posted; extra statements enforced client-side only (not recorded). |
| D4 | Recap | No endpoint/data giving per-participant summary of what was covered. | Static recap. |
| D5 | NASA-TLX | No route, table or event for questionnaire responses. | UI built, flag off, nothing submitted. |
| D6 | MCQ | No item bank, route, scoring or storage; no leakage controls equivalent to open-text path. | Renderer built against a sample structure, flag off. |
| D7 | All new screens | `UI_EVENT_TYPES`/`SURFACES` whitelist rejects new semantic events; `teaching_activity_number` capped 1..3. | No new semantic events; rrweb DOM recording continues; screens carry no new `data-*` event hooks. |
| D8 | Post-session screens | After `TERMINAL` no further participant actions are accepted; no stage between last assessment and finish. | Post-session screens unreachable in production (flag off). |
| D9 | Restart safety | Active session is process memory (`active_session_id`); a restart loses the participant. | Out of scope; noted as an operational risk. |
| D10 | Fixed schedule display | Schedule of pedagogies (e.g. P1,P2,P3,P2) is chosen per attempt at runtime; frontend cannot know future sections' pedagogy. | Nothing about future sections shown. |

## 5. Questions I need answered before coding (the plan assumes the stated defaults)

1. **Post-session screens (recap, TLX, MCQ):** build them flag-off now (default), or do you want me to hold Phase 6 until the backend dependency D5/D6/D8 is scheduled by whoever owns it?
2. **SOLO naming:** may participants see level names? Proposed neutral labels for the five levels (e.g. "Starting out → Single idea → Several ideas → Connected → Extended") require professor sign-off; default is numbered levels 1–5.
3. **TLX variant:** raw six-item (default) or weighted with pairwise comparisons?
4. **Copy:** who supplies consent, objectives, W-W-H and debrief text? Default: I draft plain placeholders clearly marked "DRAFT" and you replace them.
5. **Phase 5b:** do you want the neutral layout key (D1) raised to the backend owner, or should Phase 5 stop at 5a for now?

## 6. Risks specific to this scope

* Static W-W-H/objective text cannot be made pedagogy-specific without D1 — intentionally common, which also protects the separation requirement.
* Anything not in the server whitelist is unmeasured; the research team should know the new screens will have no semantic UI events (D7).
* Client-side consent statements are not auditable (D3).
* Changing markup in `session_main.html` is the main regression surface; Phase 2's byte-identical split and the DOM attribute diff are the guard.
* Markdown rendering must be sanitised; raw LLM text must never reach `innerHTML`.
