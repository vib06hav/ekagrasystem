# Fibonacci POC Study Definition

**Status:** Human-readable research provenance for operational content v0.4  
**Domain:** Python Programming  
**Topic:** Recursive Fibonacci with Memoization  
**SOLO pathway:** P → U → M → R → EA  
**Transitions:** C1 P→U, C2 U→M, C3 M→R, C4 R→EA  
**Pedagogies:** Worked-Example Instruction, Guided Questioning, Contrasting-Case Instruction

This directory is the concrete study-content instantiation of the conceptual specification developed for the AI harness.

## Run the participant application

```powershell
docker compose up -d --build --wait
Start the recorder first, then open `/join`; the participant enters their University ID and the application creates and binds the session UUID server-side.
```

Run `python tools/windows_capture/record.py record`, then open `http://127.0.0.1:8000`, enter `u20240132`, acknowledge the study information, and continue. The recorder automatically detects the one DirectShow webcam and stops rather than guessing if zero or multiple cameras are found. One installation hosts one active participant at a time. University IDs are single-use; an application restart requires researcher intervention, not participant re-entry.

The participant surface contains four sections. Each section preserves its teaching conversation, switches to a separate independent-assessment screen, records completion markers, and requires an explicit Next or Finish action. Completed sections remain available as read-only history. The elapsed clock begins with the first Begin action.

The five Markdown packs are human-readable research provenance. The reviewed normalized YAML under `studies/python_fibonacci_memoization/v0.1` is the executable source of truth for the frozen study version; participant execution never synchronizes or sends these Markdown documents to a model.

## Files

- `01_Knowledge_Pack.md` — bounded conceptual frontier, prerequisites, knowledge components, relations, misconceptions, SOLO states, and transition definitions.
- `02_Intervention_Pack.md` — the three pedagogy-family contracts plus all 12 transition × pedagogy intervention cells.
- `03_Assessment_Pack.md` — four transition-specific assessment families with four fresh forms each (16 total).
- `04_Judge_Rubric_Pack.md` — generic Judge contract plus C1–C4 evidence/correctness rubrics.
- `05_Protocol_Config.md` — lightweight POC sequencing/randomization/stop behavior.

## Core dependency rule

```text
Knowledge Pack
    │
    ├──► Intervention Pack
    ├──► Assessment Pack
    └──► Judge Pack

Protocol Config
    └──► controls runtime sequencing only
```

The Knowledge Pack is the semantic source of truth. Other packs reference its concepts; they do not redefine them.

## POC-specific operating assumptions

- One topic only.
- Three pedagogies are sampled without replacement at each transition.
- Every intervention is followed by a fresh independent assessment.
- Maximum of three intervention attempts per transition.
- No renewed pedagogy cycle after all three pedagogies fail.
- Four assessment blueprints exist per transition; each selected blueprint generates and freezes one fresh assessment instance.
- Later Tutor attempts receive structured prior-attempt history.
- Judge input is blind to pedagogy and prior Tutor history.
- Formal progression advances one transition at a time even if a response appears above target.
- No reward model is used during the POC runtime.
- No tabulation/bottom-up dynamic programming is introduced.

## Important status note

This package is an authored research instrument draft. It is detailed enough to implement and pilot, but it should still receive human review for:

- content validity;
- transition validity;
- treatment fidelity;
- assessment equivalence;
- rubric clarity;
- and pilot difficulty.

No claim is made here that the items are already psychometrically calibrated.
