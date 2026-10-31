# Illustrative independent generated-case examples (NOT runtime bank)

Every example in `verified_examples.json` was actually calculated by the reference oracle during package generation. These exact values are **fixtures for verification**, not an authorized or preferred question instance. The first four examples demonstrate same broad sender-parity class with different lengths, data patterns, conventions and true parity bits. The grouped and 2D examples demonstrate changing syndromes. The LLM is not asked to reproduce these strings.

| Fixture | Scenario | Verified result |
|---|---|---|
| 1 | sender_parity | `check=1, frame=010111` |
| 2 | sender_parity | `check=0, frame=1001000` |
| 3 | sender_parity | `check=0, frame=110100` |
| 4 | sender_parity | `check=0, frame=0011100` |
| 5 | full2d_single | `{'failing_rows': (0,), 'failing_cols': (1,), 'passes': False}` |
| 6 | full2d_rectangle | `{'failing_rows': (), 'failing_cols': (), 'passes': True}` |
| 7 | full2d_single | `{'failing_rows': (0,), 'failing_cols': (1,), 'passes': False}` |
| 8 | full2d_rectangle | `{'failing_rows': (), 'failing_cols': (), 'passes': True}` |
| 9 | grouped_evasion | `{'failed_groups': (), 'passes': True}` |
| 10 | grouped_evasion | `{'failed_groups': (0, 1), 'passes': False}` |
| 11 | grouped_evasion | `{'failed_groups': (), 'passes': True}` |

**Important:** A model rendering different prose for the same fixed fixture does not prove genuinely varied question generation. Docker/live-provider tests must vary the underlying case parameters and option position too.
