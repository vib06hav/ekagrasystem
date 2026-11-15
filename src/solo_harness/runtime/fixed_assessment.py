"""Verified fixed assessment forms for all four course sections.

All assessment content is embedded in the immutable compiled study snapshot.
This module never reads a mutable bank from disk during a participant attempt.
"""
from __future__ import annotations

import hashlib
import json
import re  # CHANGED
import secrets
from typing import Any


class FixedAssessmentError(ValueError):
    pass


def _check(ok: bool, message: str) -> None:
    if not ok:
        raise FixedAssessmentError(message)


def _compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def validate_c1_bank(bank: dict) -> None:
    """Reject malformed answer keys or objectively incorrect numerical facts at source load."""
    _check(isinstance(bank, dict) and bank.get("schema_version") == "ekagra.c1.fixed_assessment_bank.v2", "wrong fixed C1 bank schema")
    _check(bank.get("transition_id") == "C1" and bank.get("study_id") == "EkagraAI", "wrong fixed C1 study")
    sets = bank.get("sets")
    _check(isinstance(sets, dict) and set(sets) == {"A", "B", "C"}, "fixed C1 requires exactly A/B/C")
    expected_roles = ("transmission_error_recognition", "checking_information_purpose", "sender_parity_application")
    seen_subjective = set()
    for set_id, record in sets.items():
        _check(record.get("set_id") == f"C1-SET-{set_id}", "incorrect C1 set ID")
        public, private = record.get("public", {}), record.get("private", {})
        mcqs, answers = public.get("mcqs", []), private.get("mcqs", [])
        _check(len(mcqs) == len(answers) == 3, "C1 needs 3 public/private MCQs")
        for n, (mcq, answer) in enumerate(zip(mcqs, answers)):
            expected_id = f"MCQ{n+1}"
            _check(mcq.get("id") == answer.get("id") == expected_id, "incorrect MCQ order or ID")
            _check(answer.get("role") == expected_roles[n], "incorrect fixed C1 MCQ role")
            _check(isinstance(mcq.get("stem"), str) and bool(mcq["stem"].strip()), "empty MCQ stem")
            options = mcq.get("options", [])
            _check(len(options) == 4 and [o.get("id") for o in options] == list("ABCD"), "four labeled options required")
            _check(all(isinstance(o.get("text"), str) and o["text"].strip() for o in options), "empty option")
            _check(len({o["text"].strip() for o in options}) == 4, "duplicate option text")
            correct = answer.get("correct_option_id")
            _check(correct in "ABCD" and next(o["text"] for o in options if o["id"] == correct) == answer.get("correct_answer"), "incorrect answer-key text")
            oracle = answer.get("oracle", {})
            if n == 0:
                sent, received = oracle.get("sent"), oracle.get("received")
                _check(isinstance(sent, str) and isinstance(received, str) and len(sent) == len(received) == 5 and set(sent+received) <= {"0", "1"}, "invalid transmission bit strings")
                changed = [i+1 for i, (a,b) in enumerate(zip(sent,received)) if a != b]
                _check(changed == oracle.get("changed_positions_1_based") and len(changed) == 1, "wrong error position")
                i = changed[0]-1
                _check(oracle.get("change") == f"{sent[i]}_to_{received[i]}", "wrong flip direction")
                _check(f"Position {changed[0]} changed from {sent[i]} to {received[i]}." == answer["correct_answer"], "incorrect transmission key")
            elif n == 2:
                payload, convention = oracle.get("payload"), oracle.get("convention")
                _check(isinstance(payload,str) and len(payload)==5 and set(payload) <= {"0","1"} and convention in {"even","odd"}, "invalid sender parity case")
                checking_bit = str((payload.count("1") % 2) ^ (convention == "odd"))
                frame = payload + checking_bit
                _check(oracle.get("payload_ones") == payload.count("1") and oracle.get("correct_check_bit") == checking_bit and oracle.get("complete_frame") == frame and oracle.get("complete_ones") == frame.count("1"), "incorrect sender parity oracle")
        subject = public.get("subjective", {})
        resolved = private.get("subjective_resolved", {})
        contract, case = resolved.get("contract", {}), resolved.get("case", {})
        _check(subject.get("id") == "SUB1" and isinstance(subject.get("prompt"),str) and subject["prompt"].strip(), "missing subjective question")
        _check(contract.get("type") == "SUBJECTIVE" and contract.get("transition_id") == "C1" and contract.get("assessment_mode") == "fixed_c1_receiver_only", "invalid subjective grading contract")
        _check(set(contract.get("score_anchor",{})) == {"0","1","2"}, "incomplete subjective 0/1/2 rubric")
        _check(all(isinstance(contract["score_anchor"][x], str) and contract["score_anchor"][x].strip() for x in ("0","1","2")), "blank subjective score anchor")
        frame, convention = case.get("complete_received_frame"), case.get("convention")
        _check(isinstance(frame,str) and len(frame)==6 and set(frame)<={"0","1"} and convention in {"even","odd"}, "invalid receiver case")
        result = "PASS" if (frame.count("1") % 2 == (convention == "odd")) else "FAIL"
        _check(case.get("received_frame_ones") == frame.count("1") and case.get("receiver_check_result") == result and case.get("parity_bit_position_1_based") == 6, "wrong receiver answer oracle")
        _check(case.get("receiver_has_pristine_original") is False, "receiver must not be given pristine original")
        _check(frame in subject["prompt"] and convention in subject["prompt"] and "pass or fail" in subject["prompt"].lower(), "subjective question does not match oracle")
        _check(frame not in seen_subjective, "duplicate subjective numerical case")
        seen_subjective.add(frame)
    _check([sets[s]["private"]["subjective_resolved"]["case"]["receiver_check_result"] for s in "ABC"] == ["FAIL","PASS","FAIL"], "C1 fixed bank must contain PASS and FAIL subjective examples")



# CHANGED: C2/C3 numeric verification derives expected row/column results from
# actual bit strings, rather than trusting the bank's own claimed checks.
def _grid(value, label: str) -> list[str]:
    _check(isinstance(value, list) and len(value) == 3 and all(
        isinstance(row, str) and len(row) == 4 and set(row) <= {"0", "1"} for row in value
    ), f"invalid 3x4 grid: {label}")
    return value


def _check_results(grid: list[str]) -> tuple[dict, dict]:
    return ({f"R{r+1}": "PASS" if row.count("1") % 2 == 0 else "FAIL"
             for r, row in enumerate(grid)},
            {f"C{c+1}": "PASS" if sum(int(row[c]) for row in grid) % 2 == 0 else "FAIL"
             for c in range(4)})


def _flip_grid(start: list[str], positions: list[str]) -> tuple[list[str], dict]:
    _check(isinstance(positions, list) and bool(positions)
           and len(set(positions)) == len(positions), "invalid duplicate/empty flipped positions")
    rows = [list(row) for row in start]
    flips_per_group = {**{f"R{r}": 0 for r in range(1, 4)},
                       **{f"C{c}": 0 for c in range(1, 5)}}
    for position in positions:
        match = re.fullmatch(r"R([1-3])C([1-4])", position) if isinstance(position, str) else None
        _check(match is not None, f"invalid cell position: {position}")
        r, c = map(int, match.groups())
        rows[r-1][c-1] = "1" if rows[r-1][c-1] == "0" else "0"
        flips_per_group[f"R{r}"] += 1
        flips_per_group[f"C{c}"] += 1
    return ["".join(row) for row in rows], flips_per_group


def _verify_grid_history(original, received, flipped, oracle: dict, label: str) -> None:
    original, received = _grid(original, label + ": original"), _grid(received, label + ": received")
    _check(all(outcome == "PASS" for outcomes in _check_results(original) for outcome in outcomes.values()),
           f"{label}: original not a complete valid even-parity grid")
    observed, counts = _flip_grid(original, flipped)
    _check(received == observed, f"{label}: wrong received grid for flipped positions")
    rows, cols = _check_results(received)
    if "row_results" in oracle:
        _check(oracle["row_results"] == rows, f"{label}: wrong row results")
    if "column_results" in oracle:
        _check(oracle["column_results"] == cols, f"{label}: wrong column results")
    if "failed_rows" in oracle:
        _check(oracle["failed_rows"] == [k for k, v in rows.items() if v == "FAIL"],
               f"{label}: wrong failed rows")
    if "failed_columns" in oracle:
        _check(oracle["failed_columns"] == [k for k, v in cols.items() if v == "FAIL"],
               f"{label}: wrong failed columns")
    if "failed_groups" in oracle:
        _check(set(oracle["failed_groups"]) == {k for result in (rows, cols) for k, v in result.items() if v == "FAIL"},
               f"{label}: wrong failed groups")
    if "flips_per_group" in oracle:
        _check(oracle["flips_per_group"] == counts, f"{label}: wrong per-group flip counts")
    if "all_seven_groups" in oracle:
        _check(oracle["all_seven_groups"] == "PASS" and all(v == "PASS" for result in (rows, cols) for v in result.values()),
               f"{label}: incorrectly claims all checks pass")


def _verify_receiver_grid(received, oracle: dict, label: str) -> None:
    rows, cols = _check_results(_grid(received, label))
    _check(set(oracle.get("failed_groups", [])) == {k for result in (rows, cols) for k, v in result.items() if v == "FAIL"},
           f"{label}: incorrect receiver check results")


def _verify_non_c1_case(section: str, set_id: str, slot: int, question: dict, answer: dict) -> None:
    oracle = answer.get("oracle")
    _check(isinstance(oracle, dict), f"{section} {set_id} MCQ{slot}: missing oracle")
    label = f"{section} {set_id} MCQ{slot}"
    if section == "C2":
        if slot == 1:
            payload, sent, received = oracle.get("payload"), oracle.get("valid_complete_frame"), oracle.get("received_frame")
            _check(isinstance(payload, str) and len(payload) == 5 and set(payload) <= {"0", "1"}
                   and oracle.get("parity_convention") == "even", label + ": invalid single parity case")
            _check(sent == payload + str(payload.count("1") % 2) and sent.count("1") % 2 == 0,
                   label + ": invalid transmitted frame")
            positions = oracle.get("flipped_positions_1_based", [])
            _check(len(positions) == 2 and len(set(positions)) == 2 and all(isinstance(pos, int) and 1 <= pos <= 6 for pos in positions),
                   label + ": expected two distinct transmitted-bit flips")
            flipped = list(sent)
            for pos in positions:
                flipped[pos-1] = "1" if flipped[pos-1] == "0" else "0"
            _check("".join(flipped) == received and received.count("1") % 2 == 0
                   and oracle.get("valid_frame_ones") == sent.count("1")
                   and oracle.get("received_ones") == received.count("1")
                   and oracle.get("result") == "PASS", label + ": wrong two-flip parity result")
            _check(all(str(pos) in question["stem"] for pos in positions), label + ": stem/positions mismatch")
        elif slot == 2:
            _check(question.get("grid") == oracle.get("received_grid"), label + ": invisible/mismatched public grid")
            _verify_grid_history(oracle["valid_grid"], oracle["received_grid"], [oracle["flipped_position"]], oracle, label)
        else:
            flipped = oracle["flipped_positions"]
            _check(len(flipped) == 2 and flipped[0][:2] == flipped[1][:2], label + ": not a same-row pair")
            _check(all(position in question["stem"] for position in flipped), label + ": stem/positions mismatch")
            _verify_grid_history(oracle["valid_grid"], oracle["received_grid"], flipped, oracle, label)
    else:  # C3
        if slot == 1:
            _check(question.get("grid") == oracle.get("valid_grid"), label + ": missing/mismatched valid grid")
            flipped = oracle["flipped_positions"]
            _check(len(flipped) == 2 and all(position in question["stem"] for position in flipped),
                   label + ": stem/positions mismatch")
            _verify_grid_history(oracle["valid_grid"], oracle["received_grid"], flipped, oracle, label)
        elif slot == 2:
            _check(question.get("grid") == oracle.get("received_grid"), label + ": missing/mismatched received grid")
            _verify_receiver_grid(oracle["received_grid"], oracle, label)
            _check(oracle.get("receiver_has_original") is False and oracle.get("both_histories_give_same_received_grid_and_checks") is True,
                   label + ": receiver/history boundary")
            for name, count in (("one_flip_history", 1), ("three_flip_history", 3)):
                history = oracle[name]
                _check(len(history["flipped_positions"]) == count, label + ": invalid history size")
                _verify_grid_history(history["original_for_instructor"], oracle["received_grid"], history["flipped_positions"], {}, label + name)
            failed = set(oracle["failed_groups"])
            candidate = oracle["single_error_candidate"]
            _check(failed == {candidate[:2], "C" + candidate.split("C")[1]}, label + ": wrong intersection candidate")
            candidate_repaired, _ = _flip_grid(oracle["received_grid"], [candidate])
            _check(all(v == "PASS" for result in _check_results(candidate_repaired) for v in result.values()),
                   label + ": correction does not restore valid checking results")
        else:
            _check(question.get("grid") == oracle.get("valid_grid"), label + ": missing/mismatched valid grid")
            flipped = oracle["flipped_positions"]
            _check(len(flipped) == 4 and all(position in question["stem"] for position in flipped),
                   label + ": four-corner stem mismatch")
            _verify_grid_history(oracle["valid_grid"], oracle["received_grid"], flipped, oracle, label)


def _verify_subjective_case(section: str, set_id: str, prompt: str, resolved: dict) -> None:
    case, contract = resolved.get("case", {}), resolved.get("contract", {})
    label = f"{section} {set_id} SUB1"
    _check(contract.get("assessment_mode") == f"fixed_{section.lower()}_" + (
        "multistructural_patterns" if section == "C2" else "relational_causal"), label + ": wrong grading contract mode")
    _check(contract.get("type") == "SUBJECTIVE" and contract.get("transition_id") == section,
           label + ": incorrect subjective contract")
    _check(set(contract.get("score_anchor", {})) == {"0", "1", "2"}, label + ": incomplete rubric")
    _check(all(isinstance(s, str) and s.strip() for s in contract["score_anchor"].values()), label + ": blank rubric")
    _check(case.get("parity_convention") == "even" and case.get("scenario_kind"), label + ": missing verified parity facts")
    if section == "C2":
        original = case["valid_complete_grid"]
        _grid(original, label + " original")
        _check(all(out == "PASS" for results in _check_results(original) for out in results.values()),
               label + ": invalid original grid")
        for row in original:
            _check(" ".join(row) in prompt, label + ": original grid is not shown")
        _check(set(case["cases"]) == {"same_row", "same_column", "different_rows_columns"}, label + ": incomplete pattern coverage")
        for kind, record in case["cases"].items():
            flipped = record["flipped_positions"]
            _check(len(flipped) == 2 and all(pos in prompt for pos in flipped), label + ": subjective positions omitted")
            _verify_grid_history(original, record["received_grid"], flipped, record, label + " " + kind)
    else:
        original, received, flipped = (case["valid_original_grid_for_instructor_explanation"],
                                       case["received_grid"], case["flipped_positions"])
        _check(len(flipped) == 3 and all(pos in prompt for pos in flipped), label + ": subjective positions omitted")
        for row in received:
            _check(" ".join(row) in prompt, label + ": subjective received grid not shown")
        _verify_grid_history(original, received, flipped, case, label)
        _check(case.get("receiver_has_original") is False, label + ": receiver original assumed available")
        candidate = case["single_error_candidate_cell"]
        flipped_received, _ = _flip_grid(received, [candidate])
        _check(flipped_received == case.get("grid_after_assumed_single_error_correction"),
               label + ": wrong hypothetical correction grid")
        _check(all(out == "PASS" for results in _check_results(flipped_received) for out in results.values()),
               label + ": hypothetical correction checks do not pass")
        diffs = [f"R{r+1}C{c+1}" for r in range(3) for c in range(4)
                 if flipped_received[r][c] != original[r][c]]
        _check(diffs == case.get("cells_where_corrected_grid_still_differs_from_original"),
               label + ": wrong comparison with actual original")


# CHANGED: Independent numerical validator for generalized, non-grid C4 parity.
# Uses actual position membership and bit values, never the author-provided verdicts.
def _c4_arrangement(arr: dict, label: str) -> tuple[list[str], str, dict]:
    _check(isinstance(arr, dict), label + ": missing arrangement")
    pos, sent, groups = arr.get("positions"), arr.get("sent_sequence"), arr.get("groups")
    _check(isinstance(pos, list) and len(pos) in (7, 8) and
           all(isinstance(p, str) and re.fullmatch(r"[A-Z][1-9][0-9]*", p) for p in pos) and
           len(set(pos)) == len(pos), label + ": invalid position labels")
    _check(isinstance(sent, str) and len(sent) == len(pos) and set(sent) <= {"0", "1"},
           label + ": invalid complete sent sequence")
    _check(isinstance(groups, dict) and len(groups) in (2, 3) and
           all(isinstance(g, str) and isinstance(members, list) and len(members) >= 2 and
               len(set(members)) == len(members) and set(members) <= set(pos)
               for g, members in groups.items()), label + ": invalid groups")
    _check(all(sum(int(sent[pos.index(member)]) for member in members) % 2 == 0
               for members in groups.values()), label + ": sent sequence violates a group")
    return pos, sent, groups


def _c4_flip(pos: list[str], sent: str, flips: list[str], groups: dict, label: str) -> tuple[str, dict, dict]:
    _check(isinstance(flips, list) and bool(flips) and len(flips) == len(set(flips)) and
           set(flips) <= set(pos), label + ": invalid flipped positions")
    received = list(sent)
    for member in flips:
        index = pos.index(member)
        received[index] = "0" if received[index] == "1" else "1"
    counts = {name: sum(member in members for member in flips)
              for name, members in groups.items()}
    results = {name: "FAIL" if count % 2 else "PASS" for name, count in counts.items()}
    return "".join(received), counts, results


def validate_c4_bank(bank: dict) -> None:
    """Verify each C4 A/B/C form, all answer keys, and the added-rule oracles."""
    _check(isinstance(bank, dict) and bank.get("schema_version") == "ekagra.c4.fixed_assessment_bank.v1"
           and bank.get("study_id") == "EkagraAI" and bank.get("transition_id") == "C4",
           "C4: wrong bank schema/study/transition")
    sets = bank.get("sets")
    _check(isinstance(sets, dict) and set(sets) == {"A", "B", "C"}, "C4: exactly A/B/C required")
    roles = ("group_membership_overlap_effect", "general_non_detection_condition_application",
             "added_rule_evaluation_against_specified_pattern")
    for set_id, record in sets.items():
        label = f"C4 set {set_id}"
        _check(record.get("set_id") == f"C4-SET-{set_id}", label + ": wrong set ID")
        public, private = record.get("public", {}), record.get("private", {})
        _check(isinstance(public.get("notation"), str) and bool(public["notation"].strip()),
               label + ": missing notation")
        mcqs, answers = public.get("mcqs", []), private.get("mcqs", [])
        _check(len(mcqs) == len(answers) == 3, label + ": expected three MCQs")
        for n, (question, answer) in enumerate(zip(mcqs, answers), 1):
            name = f"{label} MCQ{n}"
            _check(question.get("id") == answer.get("id") == f"MCQ{n}" and
                   answer.get("role") == roles[n-1], name + ": incorrect question ID/role")
            _check(isinstance(question.get("stem"), str) and question["stem"].strip(),
                   name + ": empty stem")
            opts = question.get("options", [])
            _check(len(opts) == 4 and [o.get("id") for o in opts] == list("ABCD") and
                   all(isinstance(o.get("text"), str) and o["text"].strip() for o in opts) and
                   len({o["text"] for o in opts}) == 4, name + ": incorrect MCQ options")
            key = answer.get("correct_option_id")
            _check(key in list("ABCD") and answer.get("correct_answer") ==
                   next(o["text"] for o in opts if o["id"] == key), name + ": answer key/text mismatch")
            oracle = answer.get("oracle", {})
            arr = question.get("arrangement")
            pos, sent, groups = _c4_arrangement(arr, name)
            _check(arr.get("label") == f"Arrangement {1 if n <= 2 else 2}", name + ": arrangement label mismatch")
            _check(oracle.get("sent_sequence") == sent and oracle.get("groups") == groups,
                   name + ": private facts differ from public arrangement")
            flips = oracle.get("flipped_positions")
            _check(all(p in question["stem"] for p in flips), name + ": flip positions missing in stem")
            received, counts, results = _c4_flip(pos, sent, flips, groups, name)
            _check(oracle.get("received_sequence") == received, name + ": wrong received sequence")
            if n in (1, 2):
                _check(oracle.get("flips_per_group") == counts and oracle.get("group_results") == results and
                       sorted(oracle.get("failed_groups", [])) == sorted(g for g, v in results.items() if v == "FAIL"),
                       name + ": incorrect flip counts or check results")
                _check((n == 1 and sum(v == "FAIL" for v in results.values()) == 2) or
                       (n == 2 and len(flips) == 3 and set(counts.values()) == {2}
                        and not any(v == "FAIL" for v in results.values())),
                       name + ": wrong C4 item role/outcome")
            else:
                _check(oracle.get("original_flips_per_group") == counts and
                       all(v == "PASS" for v in results.values()),
                       name + ": target must be missed by existing checks")
                candidates = oracle.get("candidate_groups", [])
                _check(len(candidates) == 4 and [x.get("option") for x in candidates] == list("ABCD"),
                       name + ": expected four added-rule candidates")
                failing = []
                for candidate in candidates:
                    members = candidate.get("group", [])
                    _check(isinstance(members, list) and len(set(members)) == len(members)
                           and members.count("R") == 1 and set(members) <= set(pos) | {"R"},
                           name + ": invalid candidate group")
                    c = sum(member in members for member in flips)
                    verdict = "FAIL" if c % 2 else "PASS"
                    _check(candidate.get("flipped_inside") == c and
                           candidate.get("new_group_result_on_target") == verdict,
                           name + ": incorrect candidate verification")
                    opt = next(o for o in opts if o["id"] == candidate["option"])
                    _check("{" + ", ".join(members) + "}" in opt["text"],
                           name + ": option group does not match key")
                    if verdict == "FAIL": failing.append(candidate["option"])
                _check(failing == [key], name + ": missing/ambiguous correct added-rule option")
        # Subjective: exact public situation and private per-pattern oracles must agree.
        subj = public.get("subjective", {})
        resolved = private.get("subjective_resolved", {})
        contract, case = resolved.get("contract", {}), resolved.get("case", {})
        name = label + " SUB1"
        _check(subj.get("id") == "SUB1" and isinstance(subj.get("prompt"), str)
               and subj["prompt"].strip(), name + ": missing prompt")
        _check(contract.get("type") == "SUBJECTIVE" and contract.get("transition_id") == "C4"
               and contract.get("assessment_mode") == "fixed_c4_extended_abstract" and
               set(contract.get("score_anchor", {})) == {"0", "1", "2"} and
               all(isinstance(v, str) and v.strip() for v in contract["score_anchor"].values()),
               name + ": invalid 0/1/2 subjective grading rubric")
        arr = subj.get("arrangement")
        pos, sent, groups = _c4_arrangement(arr, name)
        _check(arr.get("label") == "Arrangement 3" and
               pos == case.get("positions_in_order") and sent == case.get("sent_sequence") and
               groups == case.get("groups"), name + ": public/private arrangement mismatch")
        _check(sent in subj["prompt"] and all("{" + ", ".join(members) + "}" in subj["prompt"]
               for members in groups.values()), name + ": public prompt differs from group science")
        patterns = case.get("patterns", {})
        _check(set(patterns) == {"Pattern 1", "Pattern 2", "Pattern 3"},
               name + ": requires all three patterns")
        added = case.get("added_rule", {})
        members = added.get("members", [])
        _check(added.get("group") == "H4" and added.get("checking_bit") == "R" and
               isinstance(members, list) and len(set(members)) == len(members)
               and members.count("R") == 1 and set(members) <= set(pos) | {"R"} and
               "{" + ", ".join(members) + "}" in subj["prompt"],
               name + ": invalid or undisplayed added rule")
        expected_r = str(sum(int(sent[pos.index(m)]) for m in members if m != "R") % 2)
        _check(str(added.get("R_value_in_sent_sequence")) == expected_r and
               added.get("sent_sequence_with_R") == sent + expected_r and
               added.get("overhead_extra_transmitted_bits") == 1,
               name + ": incorrect added checking bit")
        for kind, pattern in patterns.items():
            flips = pattern.get("flipped_positions", [])
            _check(all(member in subj["prompt"] for member in flips),
                   name + ": subjective flip missing from prompt")
            received, counts, results = _c4_flip(pos, sent, flips, groups, name + " " + kind)
            detected = any(v == "FAIL" for v in results.values())
            _check(pattern.get("received_sequence") == received and
                   pattern.get("flips_per_group") == counts and
                   pattern.get("group_results") == results and
                   sorted(pattern.get("failed_groups", [])) == sorted(k for k, v in results.items() if v == "FAIL") and
                   pattern.get("detected") is detected and pattern.get("total_flips") == len(flips),
                   name + " " + kind + ": incorrect verified pattern facts")
            extra_count = sum(member in members for member in flips)
            _check(added.get("flips_inside_H4_by_pattern", {}).get(kind) == extra_count,
                   name + " " + kind + ": incorrect H4 flip count")
            if kind != "Pattern 1":
                expected_with = results | {"H4": "FAIL" if extra_count % 2 else "PASS"}
                _check(pattern.get("with_H4_results") == expected_with,
                       name + " " + kind + ": incorrect added-rule outcome")
        _check(patterns["Pattern 1"]["detected"] is True and
               patterns["Pattern 2"]["detected"] is False and
               patterns["Pattern 3"]["detected"] is False and
               patterns["Pattern 2"]["total_flips"] == 3 and
               added.get("detects_pattern_2") is True and added.get("detects_pattern_3") is False,
               name + ": expected counterexample or evaluation not supported")
        _check(case.get("receiver_has_original") is False and case.get("instructor_view_only") is True,
               name + ": invalid receiver knowledge boundary")


def validate_fixed_bank(bank: dict, section: str) -> None:
    """Validate authored keyed content and recompute scientific facts for all forms."""
    if section == "C1":
        validate_c1_bank(bank)
        return
    if section == "C4":  # CHANGED: generalized group-check science validated separately.
        validate_c4_bank(bank)
        return
    _check(section in {"C2", "C3"}, "unsupported fixed bank")
    _check(isinstance(bank, dict) and bank.get("schema_version") == f"ekagra.{section.lower()}.fixed_assessment_bank.v1",
           f"{section}: incompatible bank schema")
    _check(bank.get("study_id") == "EkagraAI" and bank.get("transition_id") == section,
           f"{section}: wrong study/transition")
    _check(isinstance(bank.get("sets"), dict) and set(bank["sets"]) == {"A", "B", "C"},
           f"{section}: exactly three sets required")
    roles = {"C2": ("single_parity_even_flip_limitation", "two_dimensional_single_cell_check_interpretation",
                    "two_dimensional_two_bit_same_row_detection"),
             "C3": ("flip_count_to_group_outcome", "justified_inference_from_checking_results",
                    "undetected_four_corner_pattern_interpretation")}[section]
    for set_id, record in bank["sets"].items():
        label = f"{section} {set_id}"
        _check(record.get("set_id") == f"{section}-SET-{set_id}", label + ": wrong set ID")
        public, private = record.get("public", {}), record.get("private", {})
        public_mcqs, private_mcqs = public.get("mcqs", []), private.get("mcqs", [])
        _check(len(public_mcqs) == len(private_mcqs) == 3, label + ": expected three MCQs")
        if section == "C3":
            _check(isinstance(public.get("notation"), str) and bool(public["notation"].strip()),
                   label + ": missing learner-facing cell notation")
        for index, (question, answer) in enumerate(zip(public_mcqs, private_mcqs), 1):
            _check(question.get("id") == answer.get("id") == f"MCQ{index}", label + ": wrong MCQ ID")
            _check(answer.get("role") == roles[index-1], label + ": wrong MCQ role")
            _check(isinstance(question.get("stem"), str) and question["stem"].strip(), label + ": empty MCQ stem")
            options = question.get("options", [])
            _check(isinstance(options, list) and len(options) == 4 and [o.get("id") for o in options] == list("ABCD"),
                   label + ": expected A/B/C/D options")
            _check(all(isinstance(o.get("text"), str) and o["text"].strip() for o in options)
                   and len({o["text"] for o in options}) == 4, label + ": missing/duplicate options")
            key = answer.get("correct_option_id")
            _check(isinstance(key, str) and key in "ABCD" and next(o["text"] for o in options if o["id"] == key) == answer.get("correct_answer"),
                   label + ": wrong answer key")
            _verify_non_c1_case(section, set_id, index, question, answer)
        subject = public.get("subjective", {})
        _check(subject.get("id") == "SUB1" and isinstance(subject.get("prompt"), str) and subject["prompt"].strip(),
               label + ": missing subjective question")
        _verify_subjective_case(section, set_id, subject["prompt"], private.get("subjective_resolved", {}))


def construct_fixed_assessment(compiled, blueprint: dict) -> dict:
    """Freeze C1-C4 verified questions with independently shuffled, mapped options."""
    section = blueprint.get("transition_id")
    set_id = blueprint.get("fixed_bank_set_id")
    _check(blueprint.get("task_type") == "V051_FIXED_ASSESSMENT"
           and section in {"C1", "C2", "C3", "C4"} and set_id in {"A", "B", "C"},
           "not a supported fixed-assessment blueprint")
    bank = compiled.authored["v051"]["fixed_assessment_banks"][section]
    validate_fixed_bank(bank, section)
    record = bank["sets"][set_id]
    public_mcqs, private_mcqs = [], []
    rng = secrets.SystemRandom()
    for question, key in zip(record["public"]["mcqs"], record["private"]["mcqs"]):
        order = list(range(4))
        rng.shuffle(order)
        options = [{"id": chr(65+i), "text": question["options"][old]["text"]} for i, old in enumerate(order)]
        original_key_index = next(i for i, option in enumerate(question["options"])
                                  if option["id"] == key["correct_option_id"])
        public_question = {"id": question["id"], "stem": question["stem"], "options": options}
        if "grid" in question:
            public_question["grid"] = question["grid"]  # CHANGED: preserve grid visuals at freeze.
        if "arrangement" in question:
            public_question["arrangement"] = question["arrangement"]  # CHANGED: C4 group membership, sequence and bit positions.
        public_mcqs.append(public_question)
        private_mcqs.append({"id": key["id"], "correct_option_id": chr(65 + order.index(original_key_index)),
                             "role": key["role"], "subsection_refs": key["subsection_refs"], "oracle": key["oracle"]})
    public = {"mcqs": public_mcqs, "subjective": record["public"]["subjective"]}
    if "notation" in record["public"]:
        public["notation"] = record["public"]["notation"]  # CHANGED
    private = {"mcqs": private_mcqs, "subjective_resolved": record["private"]["subjective_resolved"]}
    metadata = {"blueprint_id": blueprint["id"], "fixed_set_id": set_id,
                "fixed_bank_source_hash": compiled.authored["v051"]["source_hashes"][f"11_FIXED_ASSESSMENTS/{section}.json"],
                "generation_method": "verified_authored_fixed_no_writer_reviewer", "v051": True}
    fingerprint = hashlib.sha256(_compact({"public": public, "private": private, "metadata": metadata}).encode("utf-8")).hexdigest()
    return {"public": public, "private": private, "metadata": metadata, "fingerprint": fingerprint, "status": "FROZEN"}


def construct_fixed_c1_assessment(compiled, blueprint: dict) -> dict:
    """Backwards-compatible entrypoint for existing fixed C1 regression tests."""
    _check(blueprint.get("transition_id") == "C1", "C1-only assessment wrapper")
    return construct_fixed_assessment(compiled, blueprint)
