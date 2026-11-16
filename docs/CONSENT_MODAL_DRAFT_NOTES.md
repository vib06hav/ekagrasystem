# Consent modal: items needing research-team approval

The participant-facing consent text in `src/solo_harness/templates/join.html` is a DRAFT. It must not be used with participants until the items below are supplied and approved. Facts were checked against `docs/COMPLETE_DATA_COLLECTION_SPECIFICATION.md` and `web.py`.

## Needs approval / missing
1. Retention period, backup and encryption/access policy (spec Appendix F: "NOT DETERMINED").
2. Who can access the data; confidentiality terms.
3. Voluntary-participation statement and withdrawal procedure, including what happens to collected data (spec section 14: no withdrawal workflow is implemented).
4. Researcher contact details and ethics/institutional approval reference.
5. Whether screen/webcam recording is used (only when `REQUIRE_ACTIVE_CAPTURE` is enabled); the modal currently says "some sessions may".
6. Age, gender and educational qualification are collected with participant ID and stored on the session. Obtain research-team approval for these fields and their retention/use before participant testing. The form accepts ages 5–120; confirm age eligibility and any required safeguards for minors. Do not confuse educational qualification with semester.
7. AI service provider: participant text is sent to an OpenAI-compatible provider; the provider's own retention/logging is outside this codebase. Name the provider if required.
8. Whether University ID is the participant ID or will be replaced by an anonymous ID.
9. The "DRAFT" banner stays until approval; remove it in the template at that point.
