"""Pure, verified, move-scoped instructional context for the controlled C1 pilot.

This module does not advance moves or call an LLM. The immutable scientific
source and the 52-move contract remain the sole authority for teaching facts.
The C1.2--C1.4 execution overlay specifies delivery (not new curriculum).
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from solo_harness.studies.controlled_c1 import contract


class C1PromptContractError(ValueError):
    """Scientific case, source contract, or delivery overlay is inconsistent."""


_C11_MOVE_FACTS: dict[str, tuple[str, ...]] = {
    "C1.1-P1-M01": ("information_data", "bits"),
    "C1.1-P1-M02": ("rule", "primary_mapping", "primary_positions", "single_sequence"),
    "C1.1-P1-M03": ("primary_count", "count_purpose"),
    "C1.1-P1-M04": ("information_data", "bits", "ordered_representation", "rule"),
    "C1.1-P2-M01": ("information_data", "bits", "rule"),
    "C1.1-P2-M02": ("bits", "single_sequence"),
    "C1.1-P2-M03": ("rule", "primary_mapping", "primary_positions"),
    "C1.1-P2-M04": ("primary_mapping", "primary_count", "count_purpose"),
    "C1.1-P2-M05": ("information_data", "bits", "ordered_representation", "rule"),
    "C1.1-P3-M01": ("information_data", "bits", "rule", "single_sequence"),
    "C1.1-P3-M02": ("rule", "primary_mapping", "contrast_mapping", "changed_position"),
    "C1.1-P3-M03": ("primary_count", "contrast_count", "count_purpose"),
    "C1.1-P3-M04": ("information_data", "bits", "ordered_representation", "rule", "changed_position"),
}
_C11_GUIDED_BEFORE_REPLY: dict[str, tuple[str, ...]] = {
    "C1.1-P2-M02": ("bits",),
    "C1.1-P2-M03": ("rule",),
    "C1.1-P2-M04": ("primary_mapping",),
}
_C11_EXTRA_CRITICAL: dict[str, list[str]] = {
    "C1.1-P1-M04": ["States the Yes/No convention is illustrative, not universal."],
    "C1.1-P2-M04": ["If learner asks why we count ones, answers that the count will help check bits later; merely defining counting is insufficient."],
    "C1.1-P3-M01": ["Explicitly introduces information, data, 0/1 and the illustrative Yes=1, No=0 rule before or while making the one-bit/sequence contrast."],
    "C1.1-P3-M03": ["Ones counts are 2 for 110 and 1 for 100; do NOT compare these as 'total numerical values' or binary-number magnitudes."],
    "C1.1-P3-M04": ["Connects matched cases: same length and agreed rule, different answer at position 2; convention is illustrative."],
}


@lru_cache(maxsize=1)
def execution_overlay() -> dict:
    path = Path(__file__).resolve().parent.parent / "studies" / "controlled_c1_execution_overlay.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    base = contract()
    if data.get("overlay_id") != "EKAGRAAI_C1_EXECUTION_V1" or data.get("source_contract_id") != base["contract_id"]:
        raise C1PromptContractError("unexpected C1 delivery overlay identity")
    expected = {m["id"] for s, block in base["subsections"].items() if s != "C1.1"
                for moves in block["moves_by_pedagogy"].values() for m in moves}
    provided = set(data["moves"])
    if provided != expected:
        raise C1PromptContractError(f"C1 overlay mismatch, missing={sorted(expected - provided)}, extra={sorted(provided - expected)}")
    for move_id, spec in data["moves"].items():
        original = canonical_move(move_id)
        policy = original["learner_response_policy"]
        if policy == "guided":
            if not spec.get("guided_question") or "first_guided_fact_keys" not in spec:
                raise C1PromptContractError(f"guided question/initial facts missing: {move_id}")
        elif "guided_question" in spec:
            raise C1PromptContractError(f"non-guided move must not require an extra question: {move_id}")
        if not spec.get("focus") or not spec.get("verified_fact_keys") or not spec.get("critical_checks"):
            raise C1PromptContractError(f"incomplete execution specification: {move_id}")
    return data


def execution_overlay_hash() -> str:
    return hashlib.sha256(json.dumps(execution_overlay(), sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def canonical_move(move_id: str) -> dict:
    match = re.fullmatch(r"(C1\.[1-4])-(P[123])-M(\d\d)", move_id)
    if not match:
        raise C1PromptContractError(f"invalid controlled C1 move identifier: {move_id}")
    subsection, pedagogy, _ = match.groups()
    matches = [m for m in contract()["subsections"][subsection]["moves_by_pedagogy"][pedagogy]
               if m["id"] == move_id]
    if len(matches) != 1:
        raise C1PromptContractError(f"unknown controlled C1 move: {move_id}")
    return matches[0]


def validate_move(move: dict, index: int) -> tuple[str, str]:
    move_id = move.get("id", "")
    original = canonical_move(move_id)
    if move != original:
        raise C1PromptContractError(f"move content differs from the 52-move source contract: {move_id}")
    sub, pedagogy = move_id.split("-")[:2]
    moves = contract()["subsections"][sub]["moves_by_pedagogy"][pedagogy]
    if type(index) is not int or not (0 <= index < len(moves)) or moves[index]["id"] != move_id:
        raise C1PromptContractError("move index does not match authored order")
    return sub, pedagogy


def _assert_science_cases(subsection: str, f: dict) -> None:
    """Independent arithmetic/structural checks on locked examples; never fix them silently."""
    if subsection == "C1.1":
        for name in ("primary", "contrast"):
            a, b = f[f"{name}_answers"], f[f"{name}_bits"]
            if len(a) != len(b) or "".join(f["rule"][x] for x in a) != b or f["one_counts"][b] != b.count("1"):
                raise C1PromptContractError("incorrect C1.1 mapping or ones count")
        if len(f["positions"]) != len(f["primary_bits"]) or f["positions"] != list(range(1, len(f["positions"]) + 1)):
            raise C1PromptContractError("invalid C1.1 positions")
        if sum(a != b for a, b in zip(f["primary_bits"], f["contrast_bits"])) != 1:
            raise C1PromptContractError("C1.1 contrasting cases must differ at exactly one position")
    if subsection == "C1.2":
        before, after = f["sent"], f["corrupted_received"]
        differences = [i + 1 for i, (a, b) in enumerate(zip(before, after)) if a != b]
        if (len(before) != len(after) or f["intact_received"] != before
                or differences != [f["flip_position_1_based"]] or not differences
                or before[differences[0] - 1] + "_to_" + after[differences[0] - 1] != f["flip"]
                or f["receiver_has_original"] is not False):
            raise C1PromptContractError("invalid C1.2 verified transmission case")
    if subsection == "C1.3":
        if (f["checking_position"] != "p" or f["p_is_placeholder_only"] is not True
                or f["numeric_value_defined"] is not False or set(f["payload_bits"]) - set("01")):
            raise C1PromptContractError("C1.3 placeholder must be symbolic, never a determined value")
    if subsection == "C1.4":
        payload = f["payload_bits"]
        if (payload.count("1") != f["data_ones"]
                or f["even_frame"] != payload + f["even_parity_bit"]
                or f["odd_frame"] != payload + f["odd_parity_bit"]
                or f["even_frame"].count("1") != f["even_complete_ones"]
                or f["odd_frame"].count("1") != f["odd_complete_ones"]
                or f["even_complete_ones"] % 2 != 0 or f["odd_complete_ones"] % 2 != 1
                or f["even_pass_received"].count("1") % 2 != 0
                or f["even_fail_received"].count("1") % 2 != 1
                or f["odd_pass_received"].count("1") % 2 != 1):
            raise C1PromptContractError("invalid C1.4 full-frame parity cases")


def science_library(subsection: str) -> dict[str, str]:
    f = contract()["fixed_cases"][subsection]
    _assert_science_cases(subsection, f)
    if subsection == "C1.1":
        bits, contrast = f["primary_bits"], f["contrast_bits"]
        changed = [i + 1 for i, (a, b) in enumerate(zip(bits, contrast)) if a != b]
        return {
            "information_data": "information = meaningful content; data = representation used for communication",
            "bits": "one bit = one symbol, either 0 or 1",
            "ordered_representation": "bit positions preserve answer order; a multi-bit sequence can represent digital data",
            "rule": f"illustrative agreed convention, not universal: Yes={f['rule']['Yes']}, No={f['rule']['No']}",
            "single_sequence": f"single-bit example: {bits[0]}; ordered multi-bit example: {bits}",
            "primary_mapping": f"{', '.join(f['primary_answers'])} → {bits} under agreed convention",
            "primary_positions": f"sequence {bits} has positions {', '.join(map(str, f['positions']))} in order",
            "primary_count": f"{bits}: length {len(bits)}, count of 1s {f['one_counts'][bits]}",
            "contrast_mapping": f"{', '.join(f['contrast_answers'])} → {contrast} under SAME convention",
            "changed_position": f"matched examples both length {len(bits)}; different answer at position {changed[0]}; not evidence of a transmission error",
            "contrast_count": f"{contrast}: length {len(contrast)}, count of 1s {f['one_counts'][contrast]}",
            "count_purpose": "counting 1s is a simple prerequisite for later error-checking; not a measure of numerical magnitude",
        }
    if subsection == "C1.2":
        before, corrupted = f["sent"], f["corrupted_received"]
        p = f["flip_position_1_based"]
        return {
            "roles": "sender sends data through a channel/medium; receiver gets the transmitted sequence",
            "sent": f"sent bits: {before}",
            "intact_pair": f"intact: sent {before}, received {f['intact_received']} (same)",
            "corrupted": f"corrupted example: sent {before}, received {corrupted}",
            "changed_position": f"during transmission, bit at 1-based position {p} changed {before[p-1]} → {corrupted[p-1]}",
            "flip_directions": "transmission bit flip can change 0→1 or 1→0; no software-bug/lost-packet model here",
            "receiver_view": f"ordinary receiver sees the received bits {corrupted}, not a pristine sent copy",
            "instructor_view": f"instructor can compare sent {before} and received {corrupted}; real receiver normally cannot",
            "detection_need": "receiver without original needs extra way to detect possible corruption, not a direct comparison with pristine sent bits",
        }
    if subsection == "C1.3":
        payload = f["payload_bits"]
        return {
            "receiver_need": "receiver normally lacks original data, so a checking method is useful",
            "checking_purpose": "additional transmitted information can help check for possible corruption",
            "payload": f"original data payload is {payload}",
            "diagram_only": f"diagram shows {payload} | p; p is a placeholder, not a literal transmitted letter",
            "symbolic_p": f"{payload} | p denotes one extra CHECKING POSITION; p is symbolic placeholder, not a literal transmitted letter or determined 0/1",
            "redundancy": "redundancy = transmitted checking information outside the original payload",
            "parity_bit_intro": "parity bit is one extra 0/1 checking bit outside the original data; no actual bit value selected yet",
            "parity_definition": "parity bit = one extra 0/1 checking bit, whose value depends on the original data under an agreed rule",
            "data_dependence": "the parity bit is selected using the original payload and the shared checking convention",
            "nonarbitrary": "random choice of extra bit does not implement an agreed data-dependent check",
            "shared_rule": "sender and receiver must apply the SAME agreed checking convention",
        }
    if subsection == "C1.4":
        return {
            "payload_bits": f"same original payload: {f['payload_bits']}",
            "even_rule": "even parity: total 1s in COMPLETE transmitted/received frame INCLUDING parity bit must be even",
            "odd_rule": "odd parity: total 1s in COMPLETE transmitted/received frame INCLUDING parity bit must be odd",
            "payload_count": f"original payload {f['payload_bits']} has {f['data_ones']} ones",
            "even_sender": f"even: append {f['even_parity_bit']} to payload => {f['even_frame']}, total {f['even_complete_ones']} ones",
            "odd_sender": f"odd: append {f['odd_parity_bit']} to payload => {f['odd_frame']}, total {f['odd_complete_ones']} ones",
            "received_check_bits": f"full received frame for even-rule guided check: {f['even_fail_received']}",
            "even_receive_pass": f"even received {f['even_pass_received']}: full-frame ones {f['even_pass_received'].count('1')}, PASS",
            "even_receive_fail": f"even received {f['even_fail_received']}: full-frame ones {f['even_fail_received'].count('1')}, FAIL",
            "odd_receive_pass": f"odd received {f['odd_pass_received']}: full-frame ones {f['odd_pass_received'].count('1')}, PASS",
            "pass_meaning": "PASS only means agreed parity rule was satisfied; does NOT prove no corruption",
            "fail_meaning": "FAIL detects a parity-rule violation/possible corruption, not its exact location or correction",
            "three_actions": "detecting = noticing a violation; locating = finding where; correcting = recovering the right bit value; distinct operations",
        }
    raise C1PromptContractError(f"unsupported C1 subsection {subsection}")


def delivery_spec(move: dict) -> dict:
    sub = move["id"].split("-")[0]
    if sub == "C1.1":
        spec = move.get("delivery_controls")
        if not isinstance(spec, dict):
            raise C1PromptContractError("C1.1 authored delivery_controls missing")
        return {
            "focus": spec["focus"],
            "avoid": spec.get("avoid", ""),
            "guided_question": spec.get("guided_question"),
            "verified_fact_keys": list(_C11_MOVE_FACTS[move["id"]]),
            "first_guided_fact_keys": list(_C11_GUIDED_BEFORE_REPLY[move["id"]]) if move["id"] in _C11_GUIDED_BEFORE_REPLY else None,
            "target_words": spec.get("target_words", 32),
            "micro_move": spec.get("micro_move", False),
            "final_consolidation": spec.get("final_consolidation", False),
            "critical_checks": _C11_EXTRA_CRITICAL.get(move["id"], []),
        }
    result = dict(execution_overlay()["moves"][move["id"]])
    result["micro_move"] = False
    result["final_consolidation"] = int(move["id"][-2:]) == 5 if move["id"].split("-")[1] == "P2" else int(move["id"][-2:]) == 4
    return result


def selected_facts(move: dict, *, first_guided_turn: bool = False) -> dict[str, str]:
    spec = delivery_spec(move)
    keys = (spec["first_guided_fact_keys"] if first_guided_turn else spec["verified_fact_keys"])
    library = science_library(move["id"].split("-")[0])
    if keys is None:
        raise C1PromptContractError("missing first-guided fact set")
    missing = set(keys) - library.keys()
    if missing:
        raise C1PromptContractError(f"unknown scientific fact selector(s) {missing} for {move['id']}")
    return {key: library[key] for key in keys}


def previously_covered_topics(move: dict, index: int) -> list[str]:
    """Non-sentence labels of previous facts; no copyable transitions or full history."""
    sub, pedagogy = move["id"].split("-")[:2]
    earlier = contract()["subsections"][sub]["moves_by_pedagogy"][pedagogy][:index]
    if not earlier:
        return []
    # Labels only, never an authored command or a ready-to-copy learner sentence.
    return [key.replace("_", " ") for key in delivery_spec(earlier[-1])["verified_fact_keys"]]


def prior_facts_for_question(move: dict, index: int) -> dict[str, str]:
    sub, pedagogy = move["id"].split("-")[:2]
    prior_moves = contract()["subsections"][sub]["moves_by_pedagogy"][pedagogy][:index + 1]
    library = science_library(sub)
    keys = dict.fromkeys(key for m in prior_moves for key in delivery_spec(m)["verified_fact_keys"])
    return {key: library[key] for key in keys}


_POSITION_TERMS = ("leftmost", "rightmost", "place value", "position", "weight", "double", "doubling",
                   "shift", "binary number", "numerical value", "order")

def learner_science_guard(move: dict, learner_text: str) -> dict[str, str] | None:
    """Only exposed in response to learner speech, not during ordinary first-turn teaching."""
    sub = move["id"].split("-")[0]
    text = learner_text.strip().lower()
    if not text:
        return None
    if sub == "C1.1":
        if any(word in text for word in _POSITION_TERMS):
            return {
                "answer_order": "In the Yes/No example, bit positions mark which answers came first, second, third; they have no inherent numeric weights.",
                "binary_numeral_distinction": "If interpreted as a conventional binary NUMBER, place weights double right-to-left (1,2,4,...); this is a different use of bits.",
                "scope": "Answer this actual question briefly; no binary arithmetic lesson or unprompted numeric interpretation.",
            }
        if any(term in text for term in ("why count", "why do we count", "point of counting", "what's the point of", "why ones")):
            return {"count_purpose": "We count ones now because parity checking will later use how many ones are in a bit sequence. This does not compare numerical magnitude."}
    elif sub == "C1.2" and ("original" in text or "how know" in text):
        return {"receiver_perspective": "A receiver normally sees only the received sequence, not the clean original; the instructor shows both for illustration."}
    elif sub == "C1.3" and any(s in text for s in ("what is p", "value of p", "is p 0", "is p 1", "choose p", "calculate p")):
        return {"symbolic_p": "p is a placeholder for a bit position, not a transmitted letter; no 0/1 value has been chosen without specifying the checking rule."}
    elif sub == "C1.4" and any(s in text for s in ("prove", "guarantee", "always correct", "no error")):
        return {"pass_not_proof": "Parity PASS means the agreed parity count rule holds; it cannot prove the received message was unchanged."}
    return None


def current_move_dialogue(dialogue: list[dict], move_id: str) -> list[dict]:
    start = next((i for i, message in enumerate(dialogue) if message.get("role") == "TUTOR"
                  and (message.get("instructional_trace") or {}).get("pilot_move_id") == move_id), None)
    if start is None:
        return []
    return [{"id": m.get("id"), "role": m.get("role"), "content": m.get("content")}
            for m in dialogue[start:] if m.get("role") in ("TUTOR", "LEARNER")]


def latest_learner_text(scoped: list[dict]) -> str:
    return next((str(m.get("content") or "") for m in reversed(scoped) if m.get("role") == "LEARNER"), "")


def expressed_learner_questions(scoped: list[dict]) -> list[dict]:
    """Supply possible questions as evidence, not a deterministic resolution judgment."""
    candidates = []
    for item in scoped:
        if item["role"] != "LEARNER":
            continue
        text = str(item.get("content") or "").strip()
        low = text.lower()
        if ("?" in text or low.startswith(("why ", "what ", "how ", "can ", "could ", "is ",
                                        "i don't understand", "im confused", "i'm confused", "please explain"))):
            candidates.append({"message_id": item.get("id"), "text": text})
    return candidates


def prior_approved_messages(dialogue: list[dict], previous_evidence: dict) -> list[dict]:
    approved_ids = {str(i) for ids in previous_evidence.values() if isinstance(ids, list) for i in ids}
    return [{"id": m.get("id"), "move_id": (m.get("instructional_trace") or {}).get("pilot_move_id"),
             "content": m.get("content")}
            for m in dialogue if m.get("role") == "TUTOR" and str(m.get("id")) in approved_ids]


def conditional_prior_exchange(dialogue: list[dict], move: dict) -> list[dict]:
    """Minimal earlier guided exchange, only when a conditional repair needs evidence.

    C1.2 P2 M04 depends on whether the learner earlier assumed the receiver
    has pristine original data. An isolated M04 transcript would lose that.
    """
    if move["id"] != "C1.2-P2-M04":
        return []
    prior_id = "C1.2-P2-M03"
    start = next((i for i, m in enumerate(dialogue) if m.get("role") == "TUTOR"
                  and (m.get("instructional_trace") or {}).get("pilot_move_id") == prior_id), None)
    if start is None:
        return []
    exchange = []
    for m in dialogue[start:]:
        if m.get("role") == "TUTOR" and (m.get("instructional_trace") or {}).get("pilot_move_id") == move["id"]:
            break
        if m.get("role") in ("TUTOR", "LEARNER"):
            exchange.append({"id": m.get("id"), "role": m.get("role"), "content": m.get("content")})
    return exchange[-6:]
