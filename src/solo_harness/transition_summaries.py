"""Author-reviewed, versioned F1 v0.4 POST-ASSESSMENT transition summaries.

These pages are standardized *after* a passed assessment, never pre-assessment
teaching material and never generated from learner-specific chat or grades.
Scientific scope: v0.4 knowledge.yaml, transitions.yaml, and scientific invariants.
The application chooses by locked session transition, not by pedagogy or item.

Version updates to displayed instructional material are research-protocol changes.
Do not dynamically infer claims from a Tutor transcript or an LLM response.
"""
from __future__ import annotations

from typing import Any

TRANSITION_SUMMARY_VERSION = "f1-v04-transition-summary-v1"

_SUMMARIES: dict[str, dict[str, Any]] = {
    "C1": {
        "id": "C1", "from": "P", "to": "U",
        "title": "A shared rule makes parity useful",
        "subtitle": "The sender chooses a check bit, and the receiver tests the entire transmitted frame.",
        "points": [
            {"heading": "At the sender", "text": "For even parity, add a check bit that makes the total number of 1s in the complete frame even."},
            {"heading": "At the receiver", "text": "Check all transmitted bits, including the appended check bit, using the same agreed rule."},
            {"heading": "What failure tells us", "text": "A failed parity test indicates a violated check. By itself, it does not reveal the original data or which bit changed."},
        ],
        "example_title": "One complete sender-to-receiver example",
        "example_lede": "Assume the sender and receiver agree to use even parity.",
        "example_kind": "frame",
        "frame_rows": [
            {"label": "Data", "value": "010", "note": "One 1 — odd"},
            {"label": "Appended check bit", "value": "1", "note": "Makes the total even"},
            {"label": "Transmitted frame", "value": "0101", "note": "Two 1s — valid"},
            {"label": "Received after first-bit flip", "value": "1101", "note": "Three 1s — check fails"},
        ],
        "example_conclusion": "The receiver detects that the parity rule is broken; it cannot reconstruct the sent frame from this check alone.",
        "boundary_title": "Keep the distinction clear",
        "boundary": "Detecting a violated check is not the same as locating or correcting an error.",
        "next_preview": "Next, compare what different parity arrangements can and cannot tell you.",
        "science_refs": ("K1", "K2", "K3", "R1"),
    },
    "C2": {
        "id": "C2", "from": "U", "to": "M",
        "title": "Different checks, different capabilities",
        "subtitle": "One-dimensional parity and full two-dimensional parity provide distinct useful facts.",
        "points": [
            {"heading": "One-dimensional parity", "text": "For a valid complete frame, an odd number of transmitted-bit flips fails the single parity check; an even number passes."},
            {"heading": "Full two-dimensional parity", "text": "The transmitted grid has separate row and column checks, including check bits and a corner bit."},
            {"heading": "Location has a condition", "text": "Under the exactly-one-flip assumption, one failed row and one failed column meet at the flipped position. Do not generalize this guarantee to arbitrary multi-bit changes."},
        ],
        "example_title": "Side-by-side: what the checks report",
        "example_lede": "These are independent properties of the two arrangements, not a claim that one always solves every error.",
        "example_kind": "comparison",
        "comparison_headers": ("Feature", "One complete-frame check", "Full row-and-column checks"),
        "comparison_rows": [
            ("What is tested?", "One parity relation across the full frame", "A parity relation for each transmitted row and column"),
            ("Exactly one transmitted-bit flip", "Detected; location not established", "Detected and located at the failed row–column intersection"),
            ("Multiple flips", "Even counts can pass unnoticed", "Some patterns escape; unique location is not generally guaranteed"),
        ],
        "example_conclusion": "A passing test means the tested relations still hold. It does not prove that every transmitted bit is unchanged.",
        "boundary_title": "One caution",
        "boundary": "More check bits do not automatically mean that an arbitrary error is correctable or uniquely locatable.",
        "next_preview": "Next, connect a particular flip pattern to the exact checks it changes.",
        "science_refs": ("K4", "K5", "K6", "K7", "K8", "K9"),
    },
    "C3": {
        "id": "C3", "from": "M", "to": "R",
        "title": "Explain an outcome from the checks",
        "subtitle": "The key is the chain: enforced constraints → altered bits → failed tests → justified conclusion.",
        "points": [
            {"heading": "Start with the enforced relation", "text": "The sender constructs an even-parity row-and-column block, including its transmitted check cells."},
            {"heading": "Apply the change", "text": "A single flipped cell changes the parity of its own row and its own column; the remaining rows and columns keep their prior status."},
            {"heading": "Justify the inference", "text": "Exactly one failed row and one failed column locate a bit only when exactly one flip is assumed."},
        ],
        "example_title": "Trace a single-bit error through a 2D block",
        "example_lede": "Below is a received 4 × 5 transmitted block (3 × 4 data cells plus parity checks). Data cell R2 · C3 flipped from 0 to 1.",
        "example_kind": "grid",
        "grid_headers": ("C1", "C2", "C3", "C4", "Row check bit"),
        "grid_rows": [
            {"label": "R1", "values": ("1", "0", "1", "0", "0"), "status": "Pass", "failed": False},
            {"label": "R2", "values": ("0", "1", "1", "1", "0"), "status": "Fail", "failed": True},
            {"label": "R3", "values": ("1", "1", "0", "0", "0"), "status": "Pass", "failed": False},
            {"label": "Column check bits", "values": ("0", "0", "1", "1", "0"), "status": "Pass", "failed": False},
        ],
        "grid_column_results": ("Pass", "Pass", "Fail", "Pass", "Pass"),
        "grid_flip": (1, 2),
        "example_conclusion": "R2 and C3 fail; their intersection identifies the changed cell under the single-flip assumption.",
        "boundary_title": "Where that explanation stops",
        "boundary": "Not every multi-bit alteration is detectable or uniquely locatable. Four data flips at the corners of a 2 × 2 rectangle preserve every row and column parity check.",
        "next_preview": "Next, use this constraint-based reasoning for newly defined check groups.",
        "science_refs": ("K15", "K16", "R2", "R3", "R4", "R7", "R8"),
    },
    "C4": {
        "id": "C4", "from": "R", "to": "EA",
        "title": "Generalize beyond the familiar grid",
        "subtitle": "A check arrangement is defined by which bits each group actually tests—not by where the bits are drawn.",
        "points": [
            {"heading": "The general rule", "text": "Starting from a valid frame, a change is undetected if and only if every tested parity group contains an even number of flipped members."},
            {"heading": "Why the rule transfers", "text": "A flip toggles the parity of every group containing it. An even number of flips within a group leaves that group's parity unchanged."},
            {"heading": "What a new check can change", "text": "An additional genuinely independent group can detect a pattern that passed the original checks, but simply renaming or moving a check does not change its tested relation."},
        ],
        "example_title": "Apply the rule to unfamiliar check groups",
        "example_lede": "Two checks cover the indicated DATA positions; each also has its own parity bit. Only data positions are flipped in these examples.",
        "example_kind": "groups",
        "groups": (("G1", "{1, 2, 4}"), ("G2", "{2, 3, 5}")),
        "patterns": [
            {"flips": "{1, 4}", "g1": "2 (even)", "g2": "0 (even)", "outcome": "Undetected", "detected": False},
            {"flips": "{1, 2}", "g1": "2 (even)", "g2": "1 (odd)", "outcome": "Detected", "detected": True},
        ],
        "example_conclusion": "For flips {1, 4}, adding a check on group G3 = {1, 3} would create one flip in G3 and therefore detect that previously missed pattern.",
        "boundary_title": "The boundary of the claim",
        "boundary": "Always check the declared membership of every group. If check bits themselves may flip, include each check bit in the group that tests it.",
        "next_preview": "You've finished the four-transition learning sequence.",
        "science_refs": ("K17", "K18", "K19", "R9", "R10", "R11"),
    },
}


def get_transition_summary(transition_id: str) -> dict[str, Any] | None:
    """Provide a fresh copy so a caller cannot mutate the authored canon."""
    from copy import deepcopy

    authored = _SUMMARIES.get(transition_id)
    if authored is None:
        return None
    return {**deepcopy(authored), "version": TRANSITION_SUMMARY_VERSION}


def post_pass_transition_summary(*, f1_v04: bool, is_current: bool,
                                 phase: str, outcome: str | None,
                                 transition_id: str) -> dict[str, Any] | None:
    """Gate recap on an already persisted *passing* section outcome.

    Failed attempts can reach INTERVENTION_ACTIVE again; exhausted attempts can
    reach SECTION_COMPLETE with UNRESOLVED. Neither may see a success recap.
    """
    if not (f1_v04 and is_current and phase == "SECTION_COMPLETE" and outcome == "PASSED"):
        return None
    return get_transition_summary(transition_id)
