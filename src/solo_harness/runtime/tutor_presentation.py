"""Versioned learner-facing formatting guidance (NOT a pedagogy contract).

This text is appended to the persisted, fully compiled Tutor prompt. It does not
change the scientific source pack or assessment/Judge templates.
"""
TUTOR_PRESENTATION_VERSION = "tutor-markdown-v1"

TUTOR_PRESENTATION_GUIDANCE = """[LEARNER_MESSAGE_PRESENTATION: tutor-markdown-v1]
Only format `learner_message` using plain, human-readable Markdown. Keep `fidelity_note`
and `teaching_complete` in their existing JSON fields, and return the same wire schema.
- Use short, natural paragraphs separated by blank lines. Prefer clarity to length.
- When useful, add a short ### subheading for a concept, worked example, or comparison.
  Do not force headings into a one-sentence response.
- Use numbered steps ONLY if you are genuinely demonstrating a complete worked example.
  In Guided Questioning, preserve contingent prompting and do not reveal the solution.
- Use a small Markdown table ONLY when comparing explicitly available verified facts;
  this can help Contrasting Cases. Never invent missing rows, values, or premises.
- Put important bit strings and short calculations in inline code, e.g. `0101`.
- When asking the learner a question, give it its own final blockquote:
  > **Your turn**
  > [your actual learner-facing question]
- Do not output HTML, embedded images, links, or fenced JSON in `learner_message`.
- Do not write a recap, add new subject matter, disclose assessment material,
  change pedagogy, declare a SOLO pass, or claim an unverified numerical result.
- The message must still fit the existing 4000-character learner_message bound.
This is presentation guidance only. Scientific facts, treatment boundaries,
learner-contingent feedback, and completion logic take precedence.
[/LEARNER_MESSAGE_PRESENTATION]"""
