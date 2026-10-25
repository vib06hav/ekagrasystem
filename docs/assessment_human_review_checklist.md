# Generated assessment human-review checklist

Use this offline review alongside the deterministic `validate_generated_assessment` gate.

- Is the task factually answerable from the intended pilot knowledge?
- Does the task elicit the form's target SOLO evidence without revealing a key?
- Does the task contain semantic leakage not caught by the machine markers?
- Is it comparable in demand to the other forms in its assessment family?
- Does its hidden scoring context describe the same learner-visible task?

The automated gate does not establish factual answerability, semantic leakage,
form equivalence, comparable difficulty, or scientific validity. A passing gate
only means no implemented machine-checkable contradiction or explicit leakage
marker was found.
