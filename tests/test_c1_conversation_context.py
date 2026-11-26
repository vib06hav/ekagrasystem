"""Milestone 1: cross-move conversation context for the C1 Tutor (read-only, derived, no new state).

Pure-helper and prompt-payload tests need no database. The end-to-end test uses the same SQLite-adapted
ORM harness as test_unified_c1_c4_sqlite_runtime.py and a scripted LLM; it makes no provider call.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from solo_harness.runtime import v051_conversation as conversation
from solo_harness.runtime.controlled_c1_prompt_context import (
    CONVERSATION_CONTEXT_REVISION, build_conversation_context,
)
from solo_harness.runtime.v051_conversation import (
    V051TutorOutput, controlled_c1_judge_prompt, controlled_c1_tutor_prompt,
)
from solo_harness.studies.controlled_c1 import contract, contract_hash

TUTOR_MARKER = "[CONTROLLED_C1_CURRENT_TUTOR_CONTEXT_V3]\n"
PED = "P1"
SUB = "C1.1"
CLOSING = ("Yes, the first answer sits in position 1, and the second and third answers "
           "follow it in positions 2 and 3 of the sequence.")
MOVES = contract()["subsections"][SUB]["moves_by_pedagogy"][PED]
M = [m["id"] for m in MOVES]            # C1.1-P1-M01 .. M04
CURRENT = 2                              # the active move in most tests: C1.1-P1-M03, previous is M02


def tutor(mid, move_id, text, *, mode="MOVE", sub=SUB, ped=PED, digest=None, trace=None):
    base = {"subsection_id": sub, "pedagogy_id": ped, "ready_for_judge": True, "pilot_move_id": move_id,
            "pilot_contract_sha256": contract_hash() if digest is None else digest, "pilot_response_mode": mode}
    return {"id": mid, "role": "TUTOR", "content": text, "instructional_trace": base if trace is None else trace}


def learner(mid, text):
    return {"id": mid, "role": "LEARNER", "content": text, "instructional_trace": None}


def ctx(dialogue, index=CURRENT, **kwargs):
    return build_conversation_context(dialogue, MOVES[index], index, **kwargs)


def history():
    """A realistic attempt: M01 and M02 delivered and approved, one learner turn and one doubt in M02."""
    return [
        tutor("t1", M[0], "Information is what we want to share. Data is how we represent it."),
        tutor("t2", M[1], "Following Yes, Yes, No we write 110 in positions one, two and three, so each answer gets its own place in order."),
        learner("l1", "so the first Yes is position 1?"),
        tutor("t3", M[1], CLOSING),
        learner("l2", "ok"),
    ]


APPROVED = {M[0]: ["t1"], M[1]: ["t2", "t3"]}


# ---------------------------------------------------------------- positive cases
def test_previous_approved_tutor_message_is_the_closing():
    c = ctx(history(), approved_move_message_ids=APPROVED)
    assert c["previous_move_id"] == M[1]
    assert c["previous_move_closing"] == CLOSING   # last approved of M02, not M01
    assert c["revision"] == CONVERSATION_CONTEXT_REVISION and c["kind"] == "HISTORICAL_READ_ONLY_CONTEXT"


def test_recent_learner_turns_keep_order_and_original_wording():
    c = ctx(history(), approved_move_message_ids=APPROVED)
    assert c["recent_learner_turns"] == [{"move_id": M[1], "text": "so the first Yes is position 1?"},
                                         {"move_id": M[1], "text": "ok"}]


def test_only_the_last_two_learner_turns_are_kept():
    d = history() + []
    d.insert(4, learner("l1b", "extra middle turn"))
    texts = [t["text"] for t in ctx(d, approved_move_message_ids=APPROVED)["recent_learner_turns"]]
    assert texts == ["extra middle turn", "ok"]


def test_approved_doubt_reply_becomes_a_clarification():
    d = [tutor("t1", M[0], "Intro explanation of bits."),
         learner("l1", "why do we need bits?"),
         tutor("td", M[0], "Computers store and send information as two-valued bits.", mode="DOUBT"),
         tutor("t2", M[1], "Now the mapping.")]
    c = ctx(d, index=2, approved_move_message_ids={M[0]: ["t1"]}, approved_doubt_message_ids=["td"])
    assert c["clarifications_given"] == ["Computers store and send information as two-valued bits."]


def test_recent_tutor_openings_are_first_eight_words_of_last_four_in_order():
    d = [tutor(f"t{i}", M[min(i, 2)], f"Opening{i} one two three four five six seven eight nine ten.") for i in range(6)]
    openings = ctx(d)["recent_tutor_openings"]
    assert openings == [f"Opening{i} one two three four five six seven" for i in (2, 3, 4, 5)]


def test_scope_is_exactly_the_immediately_preceding_move():
    d = history()
    d.append(tutor("t4", M[2], "Counting the 1s in 110 gives two, which is fewer than the three bits in the sequence, so count and length differ."))
    c = ctx(d, index=3, approved_move_message_ids={**APPROVED, M[2]: ["t4"]})
    assert c["previous_move_id"] == M[2] and c["previous_move_closing"].startswith("Counting the 1s")
    assert c["recent_learner_turns"] == []                      # M03 had no learner turn; M02's are not "preceding"


# ---------------------------------------------------------------- negative and boundary cases
def test_no_previous_move_gives_empty_context():
    c = ctx([tutor("t0", M[0], "Hello.")], index=0)
    assert (c["previous_move_id"], c["previous_move_closing"], c["recent_learner_turns"],
            c["clarifications_given"]) == (None, "", [], [])


def test_previous_move_without_an_approved_message_has_no_closing():
    assert ctx(history(), approved_move_message_ids={})["previous_move_closing"] == ""
    assert ctx(history(), approved_move_message_ids=None)["previous_move_closing"] == ""
    assert ctx(history(), approved_move_message_ids={M[1]: []})["previous_move_closing"] == ""


def test_unapproved_tutor_message_is_never_the_closing():
    d = history() + []
    d.insert(2, tutor("t2x", M[1], "A repair attempt that the Judge never approved."))
    d.append(tutor("t3x", M[1], "Another unapproved message."))
    c = ctx(d, approved_move_message_ids=APPROVED)
    assert c["previous_move_closing"] == CLOSING
    assert "unapproved" not in json.dumps(c["previous_move_closing"]).lower()


def test_unapproved_doubt_reply_is_not_a_clarification():
    d = [tutor("t1", M[0], "Intro."), learner("l1", "why?"),
         tutor("bad", M[0], "A reply the Judge sent back for repair.", mode="DOUBT"),
         tutor("good", M[0], "The repaired, approved reply.", mode="DOUBT"),
         tutor("t2", M[1], "Next.")]
    c = ctx(d, index=2, approved_move_message_ids={M[0]: ["t1"]}, approved_doubt_message_ids=["good"])
    assert c["clarifications_given"] == ["The repaired, approved reply."]


def test_duplicate_clarifications_are_collapsed_and_capped_at_three():
    d = [tutor("t1", M[0], "Intro.")]
    for i, text in enumerate(["Same  answer.", "same answer.", "Second.", "Third.", "Fourth."]):
        d.append(tutor(f"d{i}", M[0], text, mode="DOUBT"))
    d.append(tutor("t2", M[1], "Next."))
    c = ctx(d, index=2, approved_move_message_ids={M[0]: ["t1"]},
            approved_doubt_message_ids=[f"d{i}" for i in range(5)])
    assert c["clarifications_given"] == ["Same  answer.", "Second.", "Third.", "Fourth."][-3:]


def test_move_message_is_not_a_clarification_and_current_move_doubts_are_excluded():
    d = [tutor("t1", M[0], "Intro."), tutor("t2", M[1], "Mapping."),
         tutor("cur", M[2], "A doubt reply inside the CURRENT move.", mode="DOUBT")]
    c = ctx(d, approved_move_message_ids={M[0]: ["t1"], M[1]: ["t2"]}, approved_doubt_message_ids=["cur", "t1", "t2"])
    assert c["clarifications_given"] == []


@pytest.mark.parametrize("bad_trace", [
    None, "not a dict", {},
    {"subsection_id": SUB, "pedagogy_id": PED, "pilot_move_id": M[1]},                          # no contract hash
    {"subsection_id": "C1.2", "pedagogy_id": PED, "pilot_move_id": M[1], "pilot_contract_sha256": "x"},
])
def test_missing_or_invalid_trace_is_handled_safely_and_excluded(bad_trace):
    d = [tutor("bad", M[1], "Message with an unusable trace.", trace=bad_trace if bad_trace is not None else None)]
    d[0]["instructional_trace"] = bad_trace
    c = ctx(d, approved_move_message_ids={M[1]: ["bad"]})
    assert c["previous_move_closing"] == "" and c["recent_tutor_openings"] == []


@pytest.mark.parametrize("kwargs", [dict(digest="0" * 64), dict(sub="C1.2"), dict(ped="P2"), dict(move_id="C1.1-P1-M99")])
def test_wrong_hash_subsection_pedagogy_or_unknown_move_is_excluded(kwargs):
    move_id = kwargs.pop("move_id", M[1])
    d = [tutor("x", move_id, "Foreign message.", **kwargs)]
    c = ctx(d, approved_move_message_ids={M[1]: ["x"]})
    assert c["previous_move_closing"] == "" and c["recent_tutor_openings"] == []


def test_other_subsection_messages_never_cross_a_subsection_boundary():
    # Active move is the FIRST move of C1.2. Even a fully approved C1.1 tail must not leak in.
    second = contract()["subsections"]["C1.2"]["moves_by_pedagogy"][PED]
    d = [tutor("a", "C1.1-P1-M04", "End of the first subsection.", sub="C1.1"), learner("l", "learner of C1.1")]
    c = build_conversation_context(d, second[0], 0, approved_move_message_ids={"C1.1-P1-M04": ["a"]},
                                   approved_doubt_message_ids=["a"])
    assert c["previous_move_id"] is None and c["previous_move_closing"] == ""
    assert (c["recent_learner_turns"], c["clarifications_given"], c["recent_tutor_openings"]) == ([], [], [])


def test_future_move_messages_and_their_approvals_are_excluded():
    d = history() + [tutor("t5", M[3], "FUTURE move teaching text that must stay hidden."),
                     learner("lf", "learner reply after the future move"),
                     tutor("t6", M[2], "FUTURE-ORDER message of the active move.")]
    c = ctx(d, approved_move_message_ids={**APPROVED, M[3]: ["t5"]}, approved_doubt_message_ids=["t5"])
    blob = json.dumps(c)
    assert "FUTURE move" not in blob and "after the future move" not in blob
    assert all("FUTURE move" not in o for o in c["recent_tutor_openings"])


def test_learner_turns_stop_at_the_active_moves_first_message():
    d = history() + [tutor("t4", M[2], "Counting begins."), learner("l3", "answer inside the CURRENT move")]
    assert "CURRENT move" not in json.dumps(ctx(d, approved_move_message_ids=APPROVED))


def test_assessment_style_rows_are_excluded():
    d = history() + [
        {"id": "a1", "role": "ASSESSMENT", "content": "MCQ1 which option is correct? A B C D", "instructional_trace": None},
        tutor("a2", M[1], "MCQ2 assessment stem", trace={"assessment_id": "x", "subsection_id": SUB}),
        {"id": "a3", "role": "LEARNER_ASSESSMENT", "content": "my assessment answer", "instructional_trace": None}]
    blob = json.dumps(ctx(d, approved_move_message_ids=APPROVED))
    assert "MCQ" not in blob and "assessment answer" not in blob


def test_malformed_dialogue_degrades_to_empty_without_raising():
    garbage = [None, 7, "text", {}, {"role": "TUTOR"}, {"role": "TUTOR", "id": 1, "content": None, "instructional_trace": {}},
               {"role": "LEARNER", "content": 5}]
    c = ctx(garbage, approved_move_message_ids="nope", approved_doubt_message_ids=[1, None, "x"])
    assert c["previous_move_closing"] == "" and c["recent_learner_turns"] == [] and c["recent_tutor_openings"] == []
    assert ctx([], approved_move_message_ids=None)["clarifications_given"] == []


def test_long_messages_are_truncated_safely():
    long_tutor = " ".join(f"w{i}" for i in range(200))
    d = [tutor("t2", M[1], long_tutor), learner("l1", "x" * 1000)]
    c = ctx(d, approved_move_message_ids={M[1]: ["t2"]})
    assert c["previous_move_closing"].endswith("…") and len(c["previous_move_closing"].split()) == 60
    assert len(c["recent_learner_turns"][0]["text"]) <= 281 and c["recent_learner_turns"][0]["text"].endswith("…")
    fits = "A sixteen word explanation that is comfortably under the sixty word limit and so stays exactly as written."
    short = ctx([tutor("t2", M[1], fits)], approved_move_message_ids={M[1]: ["t2"]})
    assert short["previous_move_closing"] == fits                          # untouched when within the limit


def test_misconception_codes_and_next_step_label_are_not_part_of_this_milestone():
    assert not {"observed_misconceptions", "next_step_label"} & set(ctx(history()))


def test_builder_is_pure_it_does_not_mutate_its_inputs():
    d, approved = history(), {k: list(v) for k, v in APPROVED.items()}
    before = json.dumps([d, approved], sort_keys=True)
    ctx(d, approved_move_message_ids=approved, approved_doubt_message_ids=["t3"])
    assert json.dumps([d, approved], sort_keys=True) == before


# ---------------------------------------------------------------- prompt payload
def _payload(prompt):
    return json.loads(prompt.split(TUTOR_MARKER, 1)[1].split("\n[OUTPUT_SCHEMA]", 1)[0])


def _tutor_prompt(dialogue, index=CURRENT, **kw):
    kw.setdefault("conversation_context_enabled", True)
    return controlled_c1_tutor_prompt(SimpleNamespace(), {}, dialogue, None, None, MOVES[index], index, **kw)


def test_payload_exposes_a_separate_clearly_labelled_conversation_context():
    prompt = _tutor_prompt(history(), approved_move_message_ids=APPROVED)
    payload = _payload(prompt)
    c = payload["conversation_context"]
    assert c["kind"] == "HISTORICAL_READ_ONLY_CONTEXT" and "not an instruction" in c["usage"]
    assert CLOSING in json.dumps(c)
    # Separate from the current-move dialogue and from verified facts:
    assert CLOSING not in json.dumps(payload["current_move_dialogue_only"])
    assert CLOSING not in json.dumps(payload["verified_facts_for_this_turn"])
    assert "conversation_context is read-only background" in prompt
    assert "never" in prompt.split("conversation_context is read-only background", 1)[1][:600].lower()


def test_history_changes_only_the_conversation_context_field():
    with_history = _payload(_tutor_prompt(history() + [tutor("t4", M[2], "Counting.")], approved_move_message_ids=APPROVED))
    only_current = _payload(_tutor_prompt([tutor("t4", M[2], "Counting.")]))
    for key in set(with_history) | set(only_current):
        if key != "conversation_context":
            assert with_history[key] == only_current[key], key
    assert with_history["conversation_context"] != only_current["conversation_context"]


def test_missing_history_gives_an_empty_but_present_context():
    c = _payload(_tutor_prompt([]))["conversation_context"]
    assert c["previous_move_closing"] == "" and c["recent_learner_turns"] == []
    assert c["clarifications_given"] == [] and c["recent_tutor_openings"] == []


ALL = [(sub, ped, i, m) for sub, block in contract()["subsections"].items()
       for ped, moves in block["moves_by_pedagogy"].items() for i, m in enumerate(moves)]


@pytest.mark.parametrize("sub,ped,index,move", ALL, ids=[x[3]["id"] for x in ALL])
def test_no_move_ever_sees_a_later_moves_messages_or_a_foreign_subsection(sub, ped, index, move):
    """Feed every move a dialogue holding sentinel messages for ALL moves of ALL subsections."""
    moves = contract()["subsections"][sub]["moves_by_pedagogy"][ped]
    dialogue, approved = [], {}
    for s2, block in contract()["subsections"].items():
        for p2, ms in block["moves_by_pedagogy"].items():
            for j, m2 in enumerate(ms):
                mid = f"id-{m2['id']}"
                dialogue.append(tutor(mid, m2["id"], f"SENTINEL {m2['id']} text", sub=s2, ped=p2))
                dialogue.append(tutor(mid + "-d", m2["id"], f"SENTINEL {m2['id']} doubt", sub=s2, ped=p2, mode="DOUBT"))
                dialogue.append(learner(mid + "-l", f"LEARNER {m2['id']}"))
                approved[m2["id"]] = [mid]
    doubts = [f"id-{m2['id']}-d" for b in contract()["subsections"].values() for ms in b["moves_by_pedagogy"].values() for m2 in ms]
    c = build_conversation_context(dialogue, move, index, approved_move_message_ids=approved, approved_doubt_message_ids=doubts)
    seen = set(re.findall(r"C1\.\d-P\d-M\d\d", json.dumps(c)))
    allowed = {m["id"] for m in moves[:index + 1]}
    assert seen <= allowed, (move["id"], seen - allowed)
    assert not any(s.startswith("C1.") and not s.startswith(sub + "-") for s in seen)


# ---------------------------------------------------------------- regression guards
def test_tutor_output_schema_is_unchanged():
    assert set(V051TutorOutput.model_fields) == {"learner_message", "ready_for_judge"}
    prompt = _tutor_prompt([])
    assert json.loads(prompt.split("\n[OUTPUT_SCHEMA]\n", 1)[1]) == V051TutorOutput.model_json_schema()


def test_pedagogy_instructions_and_revision_are_retained():
    prompt = _tutor_prompt([])
    for phrase in ("P1 worked examples: demonstrate the required fixed example directly;",
                   "P2 guided moves: on the FIRST guided turn ask the SPECIFIC authored",
                   "P3 comparisons: keep the matching conditions clear",
                   "tutor_never_advances_moves"):
        assert phrase in prompt
    assert _payload(prompt)["prompt_revision"] == "C1_MOVE_SCOPED_FLEXIBLE_V3_2"


def test_judge_prompts_are_byte_identical_to_before_this_milestone():
    digest = hashlib.sha256()
    for sub, ped, i, m in ALL:
        n = len(contract()["subsections"][sub]["moves_by_pedagogy"][ped])
        digest.update(controlled_c1_judge_prompt(None, {}, [], None, m, i, i == n - 1, {}).encode())
    # Computed from the HEAD copy of v051_conversation.py before the change: identical.
    assert digest.hexdigest() == "04124ac699a32e9be4accbef0a4b47262bd5d1b8c136ed681c4f129534aee53b"
    assert "conversation_context" not in controlled_c1_judge_prompt(None, {}, [], None, MOVES[1], 1, False, {})


def test_c2_c3_c4_tutor_prompts_are_unchanged_and_carry_no_context():
    from solo_harness.runtime.controlled_executor import contract as unified, instance
    from solo_harness.runtime.controlled_unified_prompts import tutor_prompt
    digest, count = hashlib.sha256(), 0
    for section in ("C2", "C3", "C4"):
        for sub, block in unified(section)["subsections"].items():
            for ped in ("P1", "P2", "P3"):
                for i, move in enumerate(block["moves_by_pedagogy"][ped]):
                    text = tutor_prompt(SimpleNamespace(), {}, [], None, instance(sub, ped), move, i)
                    assert "conversation_context" not in text
                    digest.update(text.encode())
                    count += 1
    assert count == 135
    assert digest.hexdigest() == "dd14c33466e041303321a2aeac2c9cab983ec1d0482b59d27d0142a4547dc130"


# ---------------------------------------------------------------- end to end (SQLite ORM, scripted LLM)
from test_unified_c1_c4_sqlite_runtime import _ScriptedLLM, _close_db, _db, _settings   # noqa: E402
from solo_harness.db.models import SubsectionProgress  # noqa: E402
from solo_harness.runtime.ai import AIExecutionRuntime, RawLLMResponse, approved_doubt_message_ids  # noqa: E402
from solo_harness.runtime.controlled_executor import state  # noqa: E402
from solo_harness.runtime.engine import SessionRuntime  # noqa: E402
from solo_harness.studies.activation import activate  # noqa: E402
from solo_harness.studies.scientific_v051 import load_scientific_v051  # noqa: E402
from solo_harness.studies.v051_native_compiler import compile_v051  # noqa: E402
from pathlib import Path  # noqa: E402

SCIENTIFIC = Path(__file__).resolve().parents[1] / "studies/networks_error_detection_parity_f1/v0.5"


class _RecordingLLM(_ScriptedLLM):
    """Scripted LLM that records each Tutor call's conversation_context and numbers every reply."""

    def __init__(self):
        super().__init__()
        self.who, self.calls, self.doubt_replies, self.number, self.continue_doubt_once = None, [], {}, 0, False

    @staticmethod
    def _raw(payload):
        return RawLLMResponse(None, 200, json.dumps(payload), {"choices": [{"message": {"parsed": payload}}]},
                              payload, "stop", False, {}, 1)

    async def send(self, prepared):
        role = prepared.request.logical_role
        system = prepared.request.messages[0].content
        if role == "TUTOR" and TUTOR_MARKER not in system:      # a C2-C4 prompt: behave exactly like the base class
            return await super().send(prepared)
        if role == "TUTOR":
            data = _payload(system)
            raw = await super().send(prepared)
            payload = dict(raw.structured_candidate)
            self.number += 1
            # Label the reply by the TRUE active move. The inherited scripted LLM finds the move by scanning
            # the prompt for "...-M01", which a context that mentions an earlier move can mislead.
            payload["learner_message"] = (f"Scripted teaching for {data['active_move']['id']} [reply {self.number}] "
                                          "with enough words to count as a substantive explanation for the learner here")
            self.calls.append({"who": self.who, "move": data["active_move"]["id"], "mode": data["response_mode"],
                               "context": data.get("conversation_context"), "payload": data, "system": system})
            if data["response_mode"] == "DOUBT":
                self.doubt_replies.setdefault(self.who, []).append(payload["learner_message"])
            return self._raw(payload)
        if role == "CONVERSATION_JUDGE" and self.continue_doubt_once and '"review_mode":"DOUBT_REVIEW"' in system:
            self.continue_doubt_once = False
            return self._raw({"decision": "CONTINUE", "guidance": "Answer the doubt more completely."})
        return await super().send(prepared)


def _drive_c11_p2(db, runtime, ai, llm, session_ids):
    """Interleave two P2 sessions through C1.1 and into the first move of C1.2."""
    moves = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"]
    for i, move in enumerate(moves):
        for who, sid in session_ids.items():
            llm.who = who
            asyncio.run(ai.execute(db, ai.reserve_tutor(db, sid)))
            active = db.scalar(select(SubsectionProgress).where(SubsectionProgress.session_id == sid,
                                                                SubsectionProgress.status == "ACTIVE"))
            if move["learner_response_policy"] == "guided":
                asyncio.run(ai.execute(db, ai.reserve_tutor(db, sid, learner_text=f"{who}-answer-{move['id']}")))
                db.refresh(active)
            assert state(active)["status"] == "APPROVED_AWAITING_NEXT", (who, move["id"], state(active)["status"])
            if i == 0:
                before = (state(active)["approval_version"], state(active)["move_index"])
                llm.continue_doubt_once = True
                asyncio.run(ai.execute(db, ai.reserve_tutor(db, sid, learner_text=f"{who}-doubt-question?")))
                db.refresh(active)
                assert state(active)["status"] == "APPROVED_AWAITING_NEXT"
                assert (state(active)["approval_version"], state(active)["move_index"]) == before   # doubt never moves it
            runtime.continue_controlled_c11_move(db, sid, state(active)["approval_version"])
    for who, sid in session_ids.items():          # first move of C1.2 for each session
        llm.who = who
        asyncio.run(ai.execute(db, ai.reserve_tutor(db, sid)))


def test_end_to_end_context_is_scoped_by_session_subsection_move_and_approval():
    db = _db()
    try:
        compiled = compile_v051(load_scientific_v051(SCIENTIFIC))
        version = activate(db, compiled, make_active=True, allow_unified_candidate=True)
        runtime = SessionRuntime(SimpleNamespace(load=lambda *_: compiled))
        sessions = {who: stamp_revision(db, runtime.create_v051_internal_test_session(
            db, version.id, unified_controlled_study=True, initial_pedagogy_id="P2", c1_conversation_context=True).id,
            CONVERSATION_CONTEXT_REVISION_V2) for who in ("A", "B")}
        llm = _RecordingLLM()
        ai = AIExecutionRuntime(runtime, llm, _settings())
        _drive_c11_p2(db, runtime, ai, llm, sessions)

        moves = [m["id"] for m in contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"]]
        for who, other in (("A", "B"), ("B", "A")):
            calls = [c for c in llm.calls if c["who"] == who]
            # 1. nothing from the other session, ever
            assert all(f"{other}-" not in json.dumps(c["context"]) for c in calls)
            # 2. never a later move than the active one; never another subsection until C1.2
            for c in calls:
                cur = moves.index(c["move"]) if c["move"] in moves else None
                seen = set(re.findall(r"C1\.\d-P\d-M\d\d", json.dumps(c["context"])))
                if cur is not None:
                    assert seen <= set(moves[:cur + 1]), (who, c["move"], seen)
            # 3. M02 (the move after the one with the doubt) carries the closing, the learner turns and ONE clarification
            m02 = next(c for c in calls if c["move"] == moves[1] and c["mode"] == "MOVE")["context"]   # M02's first (guided) call
            assert m02["previous_move_id"] == moves[0]
            assert m02["previous_move_closing"].startswith("Scripted teaching for C1.1-P2-M01 [reply")
            assert f"{who}-doubt-question?" in [t["text"] for t in m02["recent_learner_turns"]]
            first_reply, approved_reply = llm.doubt_replies[who]            # first was sent back with CONTINUE
            assert first_reply != approved_reply
            assert m02["clarifications_given"] == [approved_reply]          # the approved one only
            assert first_reply not in m02["clarifications_given"] and first_reply != m02["previous_move_closing"]
            # 3b. every closing names exactly the immediately preceding move, never an earlier or later one
            for c in calls:
                if c["context"]["previous_move_id"] and c["context"]["previous_move_closing"]:   # a first guided question has none
                    assert c["context"]["previous_move_id"] == moves[moves.index(c["move"]) - 1]
                    assert c["context"]["previous_move_closing"].startswith(
                        f"Scripted teaching for {c['context']['previous_move_id']} [reply")
            # 4. the very first move of C1.1 and of C1.2 start with empty history
            first = next(c for c in calls if c["move"] == moves[0] and c["mode"] == "MOVE")["context"]
            assert first["previous_move_id"] is None and first["previous_move_closing"] == ""
            c12 = [c for c in calls if c["move"].startswith("C1.2-")][0]["context"]
            assert (c12["previous_move_id"], c12["previous_move_closing"], c12["recent_learner_turns"],
                    c12["clarifications_given"], c12["recent_tutor_openings"]) == (None, "", [], [], [])

        # 5. approved-doubt provenance is attempt-scoped: exactly one approved reply per session, never the other's
        for who, sid in sessions.items():
            progress = db.scalar(select(SubsectionProgress).where(SubsectionProgress.session_id == sid,
                                                                  SubsectionProgress.subsection_id == "C1.1"))
            ids = approved_doubt_message_ids(db, progress.attempt_id, progress.id)
            assert len(ids) == 1
        a_progress = db.scalar(select(SubsectionProgress).where(SubsectionProgress.session_id == sessions["A"],
                                                                SubsectionProgress.subsection_id == "C1.1"))
        b_progress = db.scalar(select(SubsectionProgress).where(SubsectionProgress.session_id == sessions["B"],
                                                                SubsectionProgress.subsection_id == "C1.1"))
        assert set(approved_doubt_message_ids(db, a_progress.attempt_id, a_progress.id)).isdisjoint(
            approved_doubt_message_ids(db, b_progress.attempt_id, b_progress.id))
        assert approved_doubt_message_ids(db, a_progress.attempt_id, b_progress.id) == []   # wrong ledger: nothing
    finally:
        _close_db(db)


# ====================================================================================================
# Refinement: closing selection, per-session opt-in, resume consistency, auditability
# ====================================================================================================
from solo_harness.runtime.controlled_c1_prompt_context import (   # noqa: E402
    CONVERSATION_CONTEXT_REVISION_V2, CONVERSATION_CONTEXT_REVISION_V3, CURRENT_CONTEXT_REVISION, SESSION_CONFIG_KEY,
    boundary_topics,
    conversation_context_revision, conversation_context_snapshot_entry,
)
from solo_harness.db.models import LLMCall, Session  # noqa: E402

HEAD_TUTOR_PROMPTS_SHA256 = "ef1cb7ff877f0e3d390aaa3b7b4bffd7d21fbe3353094a31bf1ec9b8fe091a85"
HEAD_JUDGE_PROMPT = "C1_MOVE_SCOPED_FLEXIBLE_V3_2"


def words(n, stem="word"):
    return " ".join(f"{stem}{i}" for i in range(n))


# ---------------------------------------------------------------- closing selection
def _closing(messages, approved_ids, extra=()):
    d = list(messages) + list(extra)
    return ctx(d, approved_move_message_ids={M[1]: approved_ids})["previous_move_closing"]


def test_closing_skips_a_trailing_acknowledgement_for_the_substantive_explanation():
    explanation = words(20, "exp")
    d = [tutor("a", M[1], explanation), tutor("b", M[1], "Right, exactly.")]
    assert _closing(d, ["a", "b"]) == explanation


def test_closing_skips_a_short_repair_fragment():
    explanation = words(25, "exp")
    d = [tutor("a", M[1], explanation), tutor("b", M[1], "Remember the convention is only illustrative.")]
    assert _closing(d, ["a", "b"]) == explanation


def test_closing_prefers_the_latest_of_several_substantive_messages():
    d = [tutor("a", M[1], words(20, "first")), tutor("b", M[1], words(18, "later")), tutor("c", M[1], "ok")]
    assert _closing(d, ["a", "b", "c"]).startswith("later0 ")


def test_closing_is_empty_when_no_approved_message_is_substantive():
    d = [tutor("a", M[1], "Short one."), tutor("b", M[1], words(14, "w"))]
    assert _closing(d, ["a", "b"]) == ""


@pytest.mark.parametrize("count,kept", [(14, False), (15, True)])
def test_closing_substantive_threshold_is_exactly_fifteen_words(count, kept):
    assert bool(_closing([tutor("a", M[1], words(count))], ["a"])) is kept


def test_closing_never_uses_an_unapproved_message_even_if_it_is_longer_and_later():
    approved_text, unapproved_text = words(16, "approved"), words(40, "unapproved")
    d = [tutor("a", M[1], approved_text), tutor("b", M[1], unapproved_text)]
    assert _closing(d, ["a"]) == approved_text
    assert _closing(d, []) == "" and _closing(d, ["zzz"]) == ""


def test_closing_ignores_a_substantive_doubt_mode_message():
    d = [tutor("a", M[1], "Brief.") , tutor("dq", M[1], words(30, "doubt"), mode="DOUBT")]
    assert _closing(d, ["a", "dq"]) == ""


def test_punctuation_only_tokens_do_not_count_as_words():
    padded = "— … ?! " * 12 + "three real words"
    assert _closing([tutor("a", M[1], padded)], ["a"]) == ""


def test_substantive_closing_is_still_scoped_to_the_preceding_move_and_current_subsection():
    d = [tutor("a", M[0], words(30, "older")), tutor("f", M[3], words(30, "future")),
         tutor("x", M[1], words(30, "foreign"), sub="C1.2")]
    c = ctx(d, approved_move_message_ids={M[0]: ["a"], M[3]: ["f"], M[1]: ["x"]})
    assert c["previous_move_closing"] == ""


# ---------------------------------------------------------------- the per-session opt-in
def test_revision_helper_reads_only_a_recognised_revision():
    assert conversation_context_revision({SESSION_CONFIG_KEY: CONVERSATION_CONTEXT_REVISION}) == CONVERSATION_CONTEXT_REVISION
    for snapshot in (None, {}, {"unified_controlled_study": True}, {SESSION_CONFIG_KEY: None}, {SESSION_CONFIG_KEY: True},
                     {SESSION_CONFIG_KEY: "C1_CONVERSATION_CONTEXT_V99"}, "text", 5, []):
        assert conversation_context_revision(snapshot) is None, snapshot


def test_snapshot_entry_is_empty_when_disabled():
    assert conversation_context_snapshot_entry(False) == {}
    assert conversation_context_snapshot_entry(True) == {SESSION_CONFIG_KEY: CONVERSATION_CONTEXT_REVISION_V3}
    assert CURRENT_CONTEXT_REVISION == CONVERSATION_CONTEXT_REVISION_V3


def test_the_global_flag_defaults_off():
    from solo_harness.config import Settings
    assert Settings.model_fields["enable_c1_conversation_context"].default is False


# ---------------------------------------------------------------- flag disabled: the original prompt
def test_disabled_prompts_are_byte_identical_to_the_pre_milestone_prompts():
    digest = hashlib.sha256()
    for _, _, i, m in ALL:
        digest.update(controlled_c1_tutor_prompt(None, {}, [], None, None, m, i).encode())
    assert digest.hexdigest() == HEAD_TUTOR_PROMPTS_SHA256          # computed from the HEAD copy of the module


def test_disabled_prompt_ignores_history_and_approval_arguments_completely():
    d = history() + [tutor("t4", M[2], "Counting.")]
    plain = controlled_c1_tutor_prompt(SimpleNamespace(), {}, d, None, None, MOVES[CURRENT], CURRENT)
    loaded = controlled_c1_tutor_prompt(SimpleNamespace(), {}, d, None, None, MOVES[CURRENT], CURRENT,
                                        approved_move_message_ids=APPROVED, approved_doubt_message_ids=["t3"])
    assert plain == loaded
    assert "conversation_context" not in plain and "read-only background" not in plain
    assert "conversation_context" not in _payload(plain)


def test_enabled_prompt_adds_exactly_the_field_and_the_note_and_nothing_else():
    d = history() + [tutor("t4", M[2], "Counting.")]
    off = controlled_c1_tutor_prompt(SimpleNamespace(), {}, d, None, None, MOVES[CURRENT], CURRENT)
    on = controlled_c1_tutor_prompt(SimpleNamespace(), {}, d, None, None, MOVES[CURRENT], CURRENT,
                                    conversation_context_enabled=True, approved_move_message_ids=APPROVED)
    off_payload, on_payload = _payload(off), _payload(on)
    assert set(on_payload) - set(off_payload) == {"conversation_context"}
    assert {k: v for k, v in on_payload.items() if k != "conversation_context"} == off_payload
    assert "read-only background" in on and "read-only background" not in off


def test_judge_prompt_text_and_revision_are_independent_of_the_flag():
    j = controlled_c1_judge_prompt(None, {}, history(), None, MOVES[CURRENT], CURRENT, False, {})
    assert "conversation_context" not in j and f'"prompt_revision":"{HEAD_JUDGE_PROMPT}"' in j


# ---------------------------------------------------------------- session lifecycle (SQLite ORM, scripted LLM)
def stamp_revision(db, sid, revision):
    """Force a frozen revision on a disposable test session (newly created sessions are stamped with the CURRENT revision, V3)."""
    session = db.get(Session, sid)
    session.runtime_config_snapshot = {**session.runtime_config_snapshot, SESSION_CONFIG_KEY: revision}
    db.commit()
    return sid


def _world(db):
    compiled = compile_v051(load_scientific_v051(SCIENTIFIC))
    version = activate(db, compiled, make_active=True, allow_unified_candidate=True)
    return compiled, version


def _stack(compiled, llm, flag):
    runtime = SessionRuntime(SimpleNamespace(load=lambda *_: compiled))
    settings = _settings()
    settings.enable_c1_conversation_context = flag      # the runtime must NOT consult this after creation
    return runtime, AIExecutionRuntime(runtime, llm, settings)


def _new_session(db, runtime, version, on, revision=CONVERSATION_CONTEXT_REVISION_V2):
    kwargs = {"c1_conversation_context": True} if on else {}
    sid = runtime.create_v051_internal_test_session(db, version.id, unified_controlled_study=True,
                                                    initial_pedagogy_id="P1", **kwargs).id
    return stamp_revision(db, sid, revision) if on else sid


def _deliver(db, ai, llm, sid, who):
    llm.who = who
    asyncio.run(ai.execute(db, ai.reserve_tutor(db, sid)))
    active = db.scalar(select(SubsectionProgress).where(SubsectionProgress.session_id == sid,
                                                        SubsectionProgress.status == "ACTIVE"))
    assert state(active)["status"] == "APPROVED_AWAITING_NEXT"
    return active


def test_new_sessions_are_stamped_only_when_opted_in_and_legacy_sessions_stay_off():
    db = _db()
    try:
        compiled, version = _world(db)
        runtime, _ = _stack(compiled, _RecordingLLM(), True)
        on = runtime.create_v051_internal_test_session(db, version.id, unified_controlled_study=True,
                                                       initial_pedagogy_id="P1", c1_conversation_context=True).id
        off = _new_session(db, runtime, version, False)
        assert db.get(Session, on).runtime_config_snapshot[SESSION_CONFIG_KEY] == CONVERSATION_CONTEXT_REVISION_V3
        assert SESSION_CONFIG_KEY not in db.get(Session, off).runtime_config_snapshot
    finally:
        _close_db(db)


def test_resumed_sessions_keep_the_configuration_they_were_created_with():
    db = _db()
    try:
        compiled, version = _world(db)
        llm = _RecordingLLM()
        runtime, ai = _stack(compiled, llm, True)                       # flag ON while the sessions are created
        sessions = {"ON": _new_session(db, runtime, version, True), "LEGACY": _new_session(db, runtime, version, False)}
        for who, sid in sessions.items():
            active = _deliver(db, ai, llm, sid, who)
            runtime.continue_controlled_c11_move(db, sid, state(active)["approval_version"])
        # "Restart": brand-new runtime objects, and the global flag now says the OPPOSITE for each session.
        for who, sid, flag_now in (("ON", sessions["ON"], False), ("LEGACY", sessions["LEGACY"], True)):
            runtime2, ai2 = _stack(compiled, llm, flag_now)
            _deliver(db, ai2, llm, sid, who)
        second = {who: [c for c in llm.calls if c["who"] == who][-1] for who in sessions}
        assert second["ON"]["move"] == M[1] and second["ON"]["context"]["previous_move_id"] == M[0]
        assert second["ON"]["context"]["previous_move_closing"].startswith(f"Scripted teaching for {M[0]} [reply")
        assert second["LEGACY"]["move"] == M[1] and second["LEGACY"]["context"] is None
        # the stamp itself never changed
        assert db.get(Session, sessions["ON"]).runtime_config_snapshot[SESSION_CONFIG_KEY] == CONVERSATION_CONTEXT_REVISION_V2
        assert SESSION_CONFIG_KEY not in db.get(Session, sessions["LEGACY"]).runtime_config_snapshot
    finally:
        _close_db(db)


def test_the_context_revision_is_identifiable_on_every_recorded_tutor_call():
    db = _db()
    try:
        compiled, version = _world(db)
        llm = _RecordingLLM()
        runtime, ai = _stack(compiled, llm, False)
        sessions = {"ON": _new_session(db, runtime, version, True), "OFF": _new_session(db, runtime, version, False)}
        for who, sid in sessions.items():
            active = _deliver(db, ai, llm, sid, who)
            runtime.continue_controlled_c11_move(db, sid, state(active)["approval_version"])
            _deliver(db, ai, llm, sid, who)
        for who, sid in sessions.items():
            tutor_calls = db.scalars(select(LLMCall).where(LLMCall.session_id == sid, LLMCall.purpose == "TUTOR")).all()
            judge_calls = db.scalars(select(LLMCall).where(LLMCall.session_id == sid,
                                                           LLMCall.purpose == "CONVERSATION_JUDGE")).all()
            assert len(tutor_calls) == 2 and judge_calls
            for call in tutor_calls:
                audit = call.request_payload["audit"]
                if who == "ON":
                    assert audit["c1_conversation_context_revision"] == CONVERSATION_CONTEXT_REVISION_V2
                    assert f'"revision":"{CONVERSATION_CONTEXT_REVISION_V2}"' in call.compiled_prompt_text
                else:
                    assert "c1_conversation_context_revision" not in audit
                    assert "conversation_context" not in call.compiled_prompt_text
                assert f'"prompt_revision":"{HEAD_JUDGE_PROMPT}"' in call.compiled_prompt_text    # unchanged
            for call in judge_calls:                       # the Judge call and its audit are untouched by the feature
                assert "c1_conversation_context_revision" not in call.request_payload["audit"]
                assert "conversation_context" not in call.compiled_prompt_text
                assert f'"prompt_revision":"{HEAD_JUDGE_PROMPT}"' in call.compiled_prompt_text
    finally:
        _close_db(db)


def test_a_context_enabled_session_never_sends_context_to_c2_c3_or_c4(monkeypatch):
    """Run a complete C1-C4 course in an opted-in session. Only C1 Tutor calls may carry the context."""
    import test_unified_c1_c4_sqlite_runtime as harness
    created = []

    class Spy(_RecordingLLM):
        def __init__(self):
            super().__init__()
            created.append(self)

    original = SessionRuntime.create_v051_internal_test_session

    def stamped_v1(self, db, *a, **k):
        session = original(self, db, *a, c1_conversation_context=True, **k)
        stamp_revision(db, session.id, CONVERSATION_CONTEXT_REVISION)
        return session
    monkeypatch.setattr(harness, "_ScriptedLLM", Spy)
    monkeypatch.setattr(SessionRuntime, "create_v051_internal_test_session", stamped_v1)
    db = _db()
    try:
        harness._run_complete_study(db, "P1")
        calls = db.scalars(select(LLMCall).where(LLMCall.purpose == "TUTOR")).all()
        by_section = {}
        for call in calls:
            section = call.request_payload["audit"]["pilot_move_id"][:2]
            has = "c1_conversation_context_revision" in call.request_payload["audit"]
            by_section.setdefault(section, set()).add(has)
            assert ("conversation_context" in call.compiled_prompt_text) == has, call.request_payload["audit"]["pilot_move_id"]
        assert by_section == {"C1": {True}, "C2": {False}, "C3": {False}, "C4": {False}}
    finally:
        _close_db(db)
