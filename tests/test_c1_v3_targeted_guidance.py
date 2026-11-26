"""Milestone 3.1: C1 revision V3 = the flag-off Tutor prompt + two short targeted rules, and nothing else.

V3 has NO historical context, no continuity guidance, no bridge instructions, no opening instructions and no optional
invitations. The two rules: (1) grounded examples only; (2) a bare acknowledgement is not an answer to a pending P2 question.

Verification layers (kept separate, as in earlier milestones):
  UNIT      prompt construction, revisions, pins, leak audits over all 52 moves / all 11 P2 guided moves.
  SCRIPTED  hand-written Tutor replies driven through the real ORM runtime. They prove plumbing and state, NOT model behaviour.
  LIVE      not performed here. The response checkers below are reusable on real model output.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from types import SimpleNamespace

import pytest
from sqlalchemy import select

import test_c1_conversation_context as base
import test_c1_conversational_continuity as cont
from solo_harness.db.models import LLMCall
from solo_harness.runtime import controlled_c1_prompt_context as pc
from solo_harness.runtime import v051_conversation as vc
from solo_harness.runtime.controlled_c1_prompt_context import (
    CONVERSATION_CONTEXT_REVISION, CONVERSATION_CONTEXT_REVISION_V2, CONVERSATION_CONTEXT_REVISION_V3,
    CURRENT_CONTEXT_REVISION, OPTIONAL_INVITATION_MOVES, SESSION_CONFIG_KEY, V2_FROZEN_OPTIONAL_INVITATION_MOVES,
    conversation_context_revision,
    conversation_context_snapshot_entry, delivery_spec, science_library, selected_facts)
from solo_harness.studies.controlled_c1 import contract

V3 = CONVERSATION_CONTEXT_REVISION_V3
GUIDE = "[TARGETED_GUIDANCE_V3]"
V2_GUIDE = "[CONVERSATIONAL_CONTINUITY_V2]"
OFF_PIN = base.HEAD_TUTOR_PROMPTS_SHA256
V1_PIN = "15df212d14c6d196de8a99b0e5c3c1948b81016f11dcab63b1e920dbaa40ebe0"
V2_PIN = "266cdd716f7c3d09b8a56ccce4bd01e4427631941b2c4c3a19561128f938658f"      # V2 frozen: the eight evaluated invitation moves active
V3_PIN = "95a4bbd343ff365b9765d5c8df014eccc255d2ef928689ea1e503cb0f2e461ee"      # wording refinement (Milestone 3.2)
ALL = base.ALL


def build(move, index, dialogue=None, **kw):
    return vc.controlled_c1_tutor_prompt(SimpleNamespace(), {}, dialogue or [], None, None, move, index, **kw)


def off(move, index, dialogue=None, **kw):
    return build(move, index, dialogue, **kw)


def v1(move, index, dialogue=None, **kw):
    return build(move, index, dialogue, conversation_context_enabled=True, **kw)


def v2(move, index, dialogue=None, **kw):
    return build(move, index, dialogue, conversation_context_enabled=True, conversational_continuity=True, **kw)


def v3(move, index, dialogue=None, **kw):
    return build(move, index, dialogue, targeted_guidance=True, **kw)


def payload(text):
    return base._payload(text)


def agg(fn):
    digest = hashlib.sha256()
    for _, _, i, m in ALL:
        digest.update(fn(m, i).encode())
    return digest.hexdigest()


P2_GUIDED = [(sub, i, m) for sub, b in contract()["subsections"].items()
             for i, m in enumerate(b["moves_by_pedagogy"]["P2"]) if m["learner_response_policy"] == "guided"]


# ====================================================================================================
# deterministic response checkers (reusable on live output)
# ====================================================================================================
INTERNAL_LANGUAGE = re.compile(r"\b(current facts|available (evidence|facts)|verified facts|the evidence|context|prompt|"
                               r"instructions? (provided|given)|system message)\b", re.I)


def uses_internal_language(text):
    return bool(INTERNAL_LANGUAGE.search(text))


def bitstrings(text):
    return set(re.findall(r"(?<![0-9A-Za-z])[01]{2,}(?![0-9A-Za-z])", text))


def invented_bitstrings(text, move, index):
    return sorted(bitstrings(text) - cont.allowed_bitstrings(move, index))


def reveals_answer(text, answer_pattern):
    return bool(re.search(answer_pattern, text, re.I))


def concise_restatement(text, key_words, limit=32):
    words = re.findall(r"[a-z0-9=']+", text.lower())
    return len(words) <= limit and all(k in text.lower() for k in key_words)


def restatement_loop(replies, key_words, repeats=3):
    return sum(1 for r in replies if all(k in r.lower() for k in key_words)) >= repeats


def test_checkers_catch_what_they_claim_to_catch():
    m = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"][2]
    assert uses_internal_language("No other examples are in our current facts.")
    assert uses_internal_language("That is not in the available evidence or the context.")
    assert not uses_internal_language("We will keep working with the example we have.")
    assert invented_bitstrings("Try 010 as another example.", m, 2) == ["010"]
    assert invented_bitstrings("110 has two 1s.", m, 2) == []
    assert reveals_answer("So Yes, Yes, No is 110.", r"(?<![0-9])110(?![0-9])")
    assert not reveals_answer("Try it in smaller steps: what is the first Yes?", r"(?<![0-9])110(?![0-9])")
    assert concise_restatement("Just the first two answers: what bit is each Yes?", ["yes"])
    assert not concise_restatement("w " * 80 + "yes", ["yes"])
    loop = ["Using Yes=1, how would you write Yes?"] * 3
    assert restatement_loop(loop, ["yes"]) and not restatement_loop(loop[:2], ["yes"])


# ====================================================================================================
# 1-4. empty allowlist, no context, no V1/V2 guidance, flag-off byte-identical
# ====================================================================================================
def test_invitation_allowlist_is_empty():
    assert OPTIONAL_INVITATION_MOVES == frozenset() and isinstance(OPTIONAL_INVITATION_MOVES, frozenset)


def test_v3_never_emits_an_invitation_flag_and_frozen_v2_emits_it_only_for_the_eight_evaluated_moves():
    assert all("continuity" not in payload(v3(m, i)) for _, _, i, m in ALL)
    assert all("invitation" not in v3(m, i).split(GUIDE, 1)[1].lower() for _, _, i, m in ALL[:6])
    flagged = {m["id"] for _, _, i, m in ALL if payload(v2(m, i))["continuity"]["optional_invitation_allowed"]}
    assert flagged == set(V2_FROZEN_OPTIONAL_INVITATION_MOVES) and len(flagged) == 8          # reproducibility of V2
    assert OPTIONAL_INVITATION_MOVES == frozenset()                                            # current policy: none


def test_repopulating_the_current_allowlist_cannot_change_v2_or_enable_v3_invitations(monkeypatch):
    m = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"][1]
    before_v2 = v2(m, 1)
    monkeypatch.setattr(pc, "OPTIONAL_INVITATION_MOVES", frozenset({m["id"], "C1.1-P1-M03"}))
    assert v2(m, 1) == before_v2                       # V2 reads only its own frozen set
    assert "continuity" not in payload(v3(m, 1)) and "invitation" not in v3(m, 1).lower().split(GUIDE.lower(), 1)[1]


def test_changing_the_frozen_v2_set_is_detected(monkeypatch):
    """Negative control: the V2 pin and the frozen-eight test exist to catch exactly this edit."""
    monkeypatch.setattr(pc, "V2_FROZEN_OPTIONAL_INVITATION_MOVES", frozenset())
    assert agg(lambda m, i: v2(m, i)) != V2_PIN


@pytest.mark.parametrize("sub,ped,index,move", ALL, ids=[x[3]["id"] for x in ALL])
def test_v3_prompt_has_no_historical_context_even_when_history_and_approvals_are_offered(sub, ped, index, move):
    moves = contract()["subsections"][sub]["moves_by_pedagogy"][ped]
    history = []
    for j, m2 in enumerate(moves[:index + 1]):
        history += [base.tutor(f"t{j}", m2["id"], f"Sentinel closing text {j} for {m2['id']} with plenty of ordinary words in it", sub=sub, ped=ped),
                    base.learner(f"l{j}", f"learner sentinel {j}")]
    text = v3(move, index, history, approved_move_message_ids={m2["id"]: [f"t{j}"] for j, m2 in enumerate(moves)},
              approved_doubt_message_ids=["t0"])
    p = payload(text)
    assert "conversation_context" not in p and "continuity" not in p
    # stronger than a sentinel search: the V3 payload is exactly the flag-off payload for the same inputs, so nothing
    # (not even the existing, authored conditional-move exchange) differs
    assert p == payload(off(move, index, history))


def test_v3_cannot_be_combined_with_the_v1_v2_options():
    m = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][2]
    for kw in (dict(conversation_context_enabled=True), dict(conversational_continuity=True),
               dict(conversation_context_enabled=True, conversational_continuity=True)):
        with pytest.raises(ValueError, match="exclusive"):
            build(m, 2, targeted_guidance=True, **kw)


def test_v3_prompt_excludes_every_v1_v2_continuity_instruction():
    forbidden = (V2_GUIDE, "read-only background", "conversation_context", "Connect, do not restart", "Optional invitation",
                 "recent_tutor_openings", "previous_subsection_topics", "first_message_of_this_move", "Transitions look back",
                 "Vary naturally", "open by linking", "Building on", "previous_move_closing", "clarifications_given",
                 "low-pressure invitation", "continuity.")
    for _, _, i, m in ALL:
        text = v3(m, i)
        assert GUIDE in text
        for phrase in forbidden:
            assert phrase not in text, (m["id"], phrase)


def test_flag_off_prompt_is_byte_identical_to_head():
    assert agg(lambda m, i: off(m, i)) == OFF_PIN


def test_v3_is_the_flag_off_prompt_plus_exactly_the_targeted_paragraph_and_nothing_else():
    for _, _, i, m in ALL:
        assert v3(m, i).replace(vc._TARGETED_GUIDANCE_V3, "", 1) == off(m, i), m["id"]
    # with a populated dialogue and a learner line too: payload identical, only the instruction paragraph differs
    move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"][2]
    d = [base.tutor("a", move["id"], "Using Yes=1 and No=0, how would you write Yes, Yes, No as bits?", ped="P2"),
         base.learner("l", "ok")]
    assert payload(v3(move, 2, d)) == payload(off(move, 2, d))
    assert v3(move, 2, d).replace(vc._TARGETED_GUIDANCE_V3, "", 1) == off(move, 2, d)


def test_all_revision_prompts_are_pinned():
    assert agg(lambda m, i: off(m, i)) == OFF_PIN
    assert agg(lambda m, i: v1(m, i)) == V1_PIN             # V1 frozen exactly
    assert agg(lambda m, i: v2(m, i)) == V2_PIN             # V2 frozen, invitations disabled
    assert agg(lambda m, i: v3(m, i)) == V3_PIN


def _guidance():
    return re.sub(r"\s+", " ", vc._TARGETED_GUIDANCE_V3)


def test_v3_guidance_is_short_and_states_each_required_rule():
    g = _guidance()
    assert len(vc._TARGETED_GUIDANCE_V3.split()) < 150
    for needle in ("Use only the examples, numbers and bit strings you were given for this move",
                   "Never invent a replacement example or a value you were not given",
                   "say naturally that you will work through the example you already have",
                   "and explain it from a fresh angle",
                   'A bare acknowledgement ("ok", "got it") is not an answer',
                   "put that same question again briefly, in a smaller and simpler form, without giving its answer",
                   "If the learner acknowledges again without answering, do not ask the question yet again"):
        assert needle in g, needle
    for forbidden in ("must answer", "mastery", "before you can continue", "required to"):
        assert forbidden not in g.lower()


def test_v3_uncertainty_handling_is_exactly_the_approved_sentence_and_no_separate_scaffolding_is_introduced():
    g = _guidance()
    assert "Handle it as you would any 'I'm not sure' reply under your guided-move rules above." in g
    for gone in ("hint-then-consolidate", "treat that as uncertainty", "says they are unsure", "normal hint", "scaffold", "narrow"):
        assert gone not in g.lower(), gone


def test_v3_guidance_contains_no_internal_terminology():
    g = _guidance().lower()
    for term in ("verified", "facts", "evidence", "context", "prompt", "ready_for_judge", "judge", "conversation_context",
                 "payload", "schema", "move card", "active_move"):
        assert term not in g, term
    # the prohibition is stated in plain words, without listing the very terms it forbids
    assert "never refer to your instructions or to any inner workings when speaking to the learner" in g


def test_v3_guidance_prescribes_no_opening_phrase_and_adds_no_new_behaviour():
    g = _guidance()
    for opener in ("Building on", "Let's", "Sure", "Certainly", "Great", "No rush", "Of course", "Absolutely"):
        assert opener not in g, opener
    # exactly two paragraphs: grounded examples; bare acknowledgement (with its loop guard and the approved uncertainty sentence)
    body = vc._TARGETED_GUIDANCE_V3.split("\n\n")
    assert len([b for b in body if b.strip()]) == 2
    assert body[0].startswith("[TARGETED_GUIDANCE_V3]\nExamples must be grounded.")
    assert body[1].startswith("A bare acknowledgement")


# ====================================================================================================
# 5-6. revisions and stamping
# ====================================================================================================
def test_revision_decoding_keeps_v1_v2_and_adds_v3():
    for rev in (CONVERSATION_CONTEXT_REVISION, CONVERSATION_CONTEXT_REVISION_V2, V3):
        assert conversation_context_revision({SESSION_CONFIG_KEY: rev}) == rev
    for bad in (None, {}, {SESSION_CONFIG_KEY: "C1_CONVERSATION_CONTEXT_V4"}, {SESSION_CONFIG_KEY: ""}, {SESSION_CONFIG_KEY: True}, "V3"):
        assert conversation_context_revision(bad) is None


def test_new_sessions_are_stamped_v3_when_the_flag_is_on_and_unstamped_when_off():
    assert CURRENT_CONTEXT_REVISION == V3
    assert conversation_context_snapshot_entry(True) == {SESSION_CONFIG_KEY: V3}
    assert conversation_context_snapshot_entry(False) == {}
    db = base._db()
    try:
        compiled, version = base._world(db)
        runtime, _ = base._stack(compiled, base._RecordingLLM(), True)
        on = runtime.create_v051_internal_test_session(db, version.id, unified_controlled_study=True, initial_pedagogy_id="P1",
                                                       c1_conversation_context=True).id
        off_id = runtime.create_v051_internal_test_session(db, version.id, unified_controlled_study=True, initial_pedagogy_id="P1").id
        assert db.get(base.Session, on).runtime_config_snapshot[SESSION_CONFIG_KEY] == V3
        assert SESSION_CONFIG_KEY not in db.get(base.Session, off_id).runtime_config_snapshot
    finally:
        base._close_db(db)


def test_v1_and_v2_stamped_sessions_keep_their_original_behaviour_and_never_get_v3_text():
    def body(room):
        room.script(cont.filler("C1.1-P1-M01"), cont.filler("C1.1-P1-M02"))
        room.say(); room.next()
        call = room.say()
        assert V2_GUIDE in call["system"] and GUIDE not in call["system"]
        assert call["context"]["revision"] == CONVERSATION_CONTEXT_REVISION_V2
    cont.with_room("P1", body)                                                    # Room stamps V2 by default

    def body_v1(room):
        room.script(cont.filler("C1.1-P1-M01"), cont.filler("C1.1-P1-M02"))
        room.say(); room.next()
        call = room.say()
        assert V2_GUIDE not in call["system"] and GUIDE not in call["system"]
        assert call["context"]["revision"] == CONVERSATION_CONTEXT_REVISION and "continuity" not in call["payload"]
    db = base._db()
    try:
        room = cont.Room(db, "P1", on=True, revision=CONVERSATION_CONTEXT_REVISION)
        body_v1(room)
    finally:
        base._close_db(db)


def test_only_the_current_revision_is_ever_written_to_a_session_and_nothing_else_names_v1_or_v2():
    """New opted-in sessions can only be V3: the sole writer is conversation_context_snapshot_entry, and no other source
    file refers to a revision constant."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "solo_harness"
    allowed = {"controlled_c1_prompt_context.py", "v051_conversation.py", "ai.py"}
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "CONVERSATION_CONTEXT_REVISION" in text and path.name not in allowed:
            offenders.append(path.name)
    assert offenders == []
    for name in ("engine.py", "web.py"):                                   # they only call the helper that stamps CURRENT
        text = (root / ("runtime/" + name if name == "engine.py" else name)).read_text(encoding="utf-8")
        assert "conversation_context_snapshot_entry" in text and "_V1" not in text.split("conversation_context_snapshot_entry")[1][:120]
    assert conversation_context_snapshot_entry(True)[SESSION_CONFIG_KEY] == V3


def test_a_session_opted_in_through_the_engine_is_never_v1_or_v2():
    db = base._db()
    try:
        compiled, version = base._world(db)
        runtime, _ = base._stack(compiled, base._RecordingLLM(), True)
        for ped in ("P1", "P2", "P3"):
            sid = runtime.create_v051_internal_test_session(db, version.id, unified_controlled_study=True, initial_pedagogy_id=ped,
                                                            c1_conversation_context=True).id
            assert db.get(base.Session, sid).runtime_config_snapshot[SESSION_CONFIG_KEY] == V3
    finally:
        base._close_db(db)


def test_stamping_a_frozen_revision_on_an_existing_session_is_never_done_by_the_runtime():
    """Decoding V1/V2 must not rewrite the stamp: run a Tutor call on a V1-stamped session and re-read it."""
    db = base._db()
    try:
        room = cont.Room(db, "P1", on=True, revision=CONVERSATION_CONTEXT_REVISION)
        room.script(cont.filler("C1.1-P1-M01"))
        room.say()
        assert db.get(base.Session, room.sid).runtime_config_snapshot[SESSION_CONFIG_KEY] == CONVERSATION_CONTEXT_REVISION
    finally:
        base._close_db(db)


def _v3_room(db, ped):
    return cont.Room(db, ped, on=True, revision=V3)


def test_v3_sessions_send_v3_guidance_only_and_record_the_revision_in_the_audit():
    db = base._db()
    try:
        room = _v3_room(db, "P1")
        room.script(cont.filler("C1.1-P1-M01"), cont.filler("C1.1-P1-M02"))
        room.say(); room.next(); call = room.say()
        assert GUIDE in call["system"] and call["context"] is None and "continuity" not in call["payload"]
        assert V2_GUIDE not in call["system"] and "conversation_context" not in call["system"]
        rows = db.scalars(select(LLMCall).where(LLMCall.session_id == room.sid, LLMCall.purpose == "TUTOR")).all()
        assert rows and all(r.request_payload["audit"]["c1_conversation_context_revision"] == V3 for r in rows)
        assert all(GUIDE in r.compiled_prompt_text for r in rows)
        judges = db.scalars(select(LLMCall).where(LLMCall.session_id == room.sid, LLMCall.purpose == "CONVERSATION_JUDGE")).all()
        assert judges and all(GUIDE not in j.compiled_prompt_text and "c1_conversation_context_revision" not in j.request_payload["audit"]
                              for j in judges)
    finally:
        base._close_db(db)


def test_an_unstamped_session_gets_the_flag_off_prompt_even_after_a_restart():
    db = base._db()
    try:
        room = cont.Room(db, "P1", on=False)
        room.script(cont.filler("C1.1-P1-M01"), cont.filler("C1.1-P1-M02"))
        room.say(); room.next()
        room.runtime, room.ai = base._stack(base.compile_v051(base.load_scientific_v051(base.SCIENTIFIC)), room.llm, True)
        call = room.say()
        assert GUIDE not in call["system"] and call["context"] is None
    finally:
        base._close_db(db)


# ====================================================================================================
# 7-8. answer leakage through history on a first guided question
# ====================================================================================================
SENTINEL = "ZXQ-HISTORY-SENTINEL"


def _poisoned_history(sub, ped, move, index, answers):
    """Every history field of the previous move holds the withheld answer strings plus a sentinel."""
    moves = contract()["subsections"][sub]["moves_by_pedagogy"][ped]
    prev = moves[index - 1]
    stuffing = f"{SENTINEL} " + " ".join(answers) + " plus enough ordinary words so this counts as a substantive approved explanation"
    return [base.tutor("p1", prev["id"], stuffing, sub=sub, ped=ped),
            base.learner("p2", f"{SENTINEL} {' '.join(answers)}"),
            base.tutor("p3", prev["id"], f"{SENTINEL} clarification {' '.join(answers)} with enough words to be an excerpt here", mode="DOUBT", sub=sub, ped=ped)], \
        {prev["id"]: ["p1"]}, ["p3"]


def _answers(sub, move):
    spec = delivery_spec(move)
    lib = science_library(sub)
    withheld = " ".join(lib[k] for k in spec["verified_fact_keys"] if k not in (spec.get("first_guided_fact_keys") or []))
    return sorted(bitstrings(withheld)) or ["ANSWERTOKEN"]


@pytest.mark.parametrize("sub,index,move", P2_GUIDED, ids=[x[2]["id"] for x in P2_GUIDED])
def test_frozen_v1_v2_still_carry_history_on_a_first_guided_question_exactly_as_evaluated(sub, index, move):
    """REPRODUCIBILITY, not an endorsement: V2 was observed to leak through this path and stays frozen for stamped sessions."""
    history, approved, doubts = _poisoned_history(sub, "P2", move, index, _answers(sub, move))
    for build_fn in (v1, v2):
        text = build_fn(move, index, history, approved_move_message_ids=approved, approved_doubt_message_ids=doubts)
        assert payload(text)["first_guided_question_turn"] is True
        assert SENTINEL in text, (build_fn.__name__, move["id"])


@pytest.mark.parametrize("sub,index,move", P2_GUIDED, ids=[x[2]["id"] for x in P2_GUIDED])
def test_opt_in_suppression_removes_all_history_on_every_p2_first_guided_question(sub, index, move):
    """The tested mechanism for any future history-carrying revision. No current revision enables it."""
    answers = _answers(sub, move)
    history, approved, doubts = _poisoned_history(sub, "P2", move, index, answers)
    baseline = off(move, index, history)            # flag off: what the Tutor already sees
    for build_fn in (v1, v2):
        text = build_fn(move, index, history, approved_move_message_ids=approved, approved_doubt_message_ids=doubts,
                        suppress_history_on_first_guided=True)
        p = payload(text)
        assert p["first_guided_question_turn"] is True and SENTINEL not in text, move["id"]
        ctx = p["conversation_context"]
        assert (ctx["previous_move_closing"], ctx["recent_learner_turns"], ctx["clarifications_given"], ctx["recent_tutor_openings"]) \
            == ("", [], [], [])
        for answer in answers:                         # nothing beyond what the flag-off prompt already contains
            assert text.count(answer) <= baseline.count(answer), (move["id"], answer)


@pytest.mark.parametrize("sub,index,move", P2_GUIDED, ids=[x[2]["id"] for x in P2_GUIDED])
def test_v3_has_no_history_at_all_on_any_p2_first_guided_question(sub, index, move):
    history, approved, doubts = _poisoned_history(sub, "P2", move, index, _answers(sub, move))
    text3 = v3(move, index, history, approved_move_message_ids=approved, approved_doubt_message_ids=doubts)
    assert SENTINEL not in text3 and "conversation_context" not in text3
    assert payload(text3) == payload(off(move, index, history))


@pytest.mark.parametrize("sub,index,move", P2_GUIDED, ids=[x[2]["id"] for x in P2_GUIDED])
def test_positive_control_suppression_still_delivers_history_once_the_learner_has_replied(sub, index, move):
    """Without this the suppression test could pass vacuously."""
    history, approved, doubts = _poisoned_history(sub, "P2", move, index, ["ANSWERTOKEN"])
    current = base.tutor("c", move["id"], "The authored guided question.", sub=sub, ped="P2")
    d = history + [current, base.learner("r", "I think so")]
    for build_fn in (v1, v2):
        text = build_fn(move, index, d, approved_move_message_ids=approved, approved_doubt_message_ids=doubts,
                        suppress_history_on_first_guided=True)
        assert payload(text)["first_guided_question_turn"] is False
        assert SENTINEL in text


# Real contexts copied from the Milestone 3 V2 evaluation (artifacts are read-only; these three led to leaked answers).
EVALUATED_V2_CONTEXTS = [
    ("That's right, 110 is our multi-bit example made of three symbols, while 1 is a single bit.", [{"move_id": "C1.1-P2-M02", "text": "Example B"}]),
    ("Example B, labeled 110, uses multiple symbols together rather than just one. A single bit is one symbol, either 0 or 1, while 110 is an ordered multi-bit sequence.",
     [{"move_id": "C1.1-P2-M02", "text": "Example B"}]),
    ("Example B uses multiple symbols together. A single bit holds just one, but 110 combines three positions.", [{"move_id": "C1.1-P2-M02", "text": "Example B"}]),
]


@pytest.mark.parametrize("closing,learner_turns", EVALUATED_V2_CONTEXTS)
def test_the_evaluated_v2_first_guided_contexts_are_reproduced_exactly_by_frozen_v2(closing, learner_turns):
    sub, ped = "C1.1", "P2"
    moves = contract()["subsections"][sub]["moves_by_pedagogy"][ped]
    dialogue = [base.tutor("closing", moves[1]["id"], closing, sub=sub, ped=ped)] + \
               [base.learner(f"l{k}", t["text"]) for k, t in enumerate(learner_turns)]
    ctx = payload(v2(moves[2], 2, dialogue, approved_move_message_ids={moves[1]["id"]: ["closing"]}))["conversation_context"]
    assert ctx["previous_move_closing"] == closing and ctx["recent_learner_turns"] == learner_turns
    # ... and it is exactly this "110" that V2 then echoed into the question; V3 cannot, because it carries no history
    assert "110" in ctx["previous_move_closing"]
    assert "conversation_context" not in v3(moves[2], 2, dialogue, approved_move_message_ids={moves[1]["id"]: ["closing"]})


def test_c11_p2_m03_110_exposure_by_revision():
    sub, ped = "C1.1", "P2"
    moves = contract()["subsections"][sub]["moves_by_pedagogy"][ped]
    move, index = moves[2], 2
    history = [base.tutor("p", moves[1]["id"], "You pointed to Example B, which is 110. Notice that it uses three symbols, so it is the multi-bit one.",
                          sub=sub, ped=ped)]
    approved = {moves[1]["id"]: ["p"]}
    baseline = off(move, index, history).count("110")
    for frozen in (v1, v2):                            # frozen revisions carry it (the evaluated V2 leak path)
        assert frozen(move, index, history, approved_move_message_ids=approved).count("110") > baseline
    for safe in (v1(move, index, history, approved_move_message_ids=approved, suppress_history_on_first_guided=True),
                 v2(move, index, history, approved_move_message_ids=approved, suppress_history_on_first_guided=True),
                 v3(move, index, history, approved_move_message_ids=approved)):
        assert safe.count("110") == baseline and "Example B, which is 110" not in safe
    raw = pc.build_conversation_context(history, move, index, approved_move_message_ids=approved)
    assert "110" in raw["previous_move_closing"]                                                  # negative control


def test_the_existing_withholding_of_answer_facts_is_unchanged_on_a_first_guided_turn():
    sub, ped = "C1.1", "P2"
    move = contract()["subsections"][sub]["moves_by_pedagogy"][ped][2]
    for build_fn in (off, v1, v2, v3):
        p = payload(build_fn(move, 2))
        assert list(p["verified_facts_for_this_turn"]) == ["rule"] and p["first_guided_question_turn"] is True
        assert "primary_mapping" not in p["verified_facts_for_this_turn"]


# ====================================================================================================
# 9-10. bare acknowledgement with a pending guided question (prompt level + scripted ORM)
# ====================================================================================================
QUESTION = "Using Yes=1 and No=0, how would you write Yes, Yes, No as bits?"
ANSWER = r"(?<![0-9])110(?![0-9])"


def test_bare_ok_prompt_carries_the_rule_the_pending_question_and_no_history():
    move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"][2]
    d = [base.tutor("q", move["id"], QUESTION, ped="P2"), base.learner("l", "ok")]
    text = v3(move, 2, d)
    p = payload(text)
    assert GUIDE in text and p["learner_question_text_if_any"] == "ok" and "conversation_context" not in p
    assert [m["content"] for m in p["current_move_dialogue_only"]] == [QUESTION, "ok"]          # the pending question is visible
    assert p["active_move"]["response_policy"] == "guided"
    assert "put that same question again briefly" in re.sub(r"\s+", " ", text)
    # the flag-off prompt had no such rule (so the behaviour change is attributable to V3 alone)
    assert "bare acknowledgement" not in off(move, 2, d) and "bare acknowledgement" not in v1(move, 2, d)


def _p2_room(db):
    room = _v3_room(db, "P2")
    return room


def _reach_c11_p2_m03(room, *, then):
    """M01 explain, M02 guided (answered), then M03's first guided question; `then` supplies the rest of the script."""
    room.script(cont.filler("C1.1-P2-M01"),
                ("Which has several bits: 1 or 110?", False), ("1 is a single bit; 110 holds three bits in order, so B has several.", True),
                (QUESTION, False), *then)
    room.say(); room.next()
    room.say(); assert room.status() == "AWAITING_LEARNER"
    room.say("Example B"); room.next()
    q = room.say(); assert room.status() == "AWAITING_LEARNER"
    return q


def test_scripted_bare_ok_keeps_the_guided_question_open_with_a_concise_restatement():
    restate = "No rush. Just the first two answers: what bit is each Yes?"
    consolidate = "That's fine. Yes is 1 and No is 0, so Yes, Yes, No is 110, in positions 1, 2 and 3."
    db = base._db()
    try:
        room = _p2_room(db)
        q = _reach_c11_p2_m03(room, then=[(restate, False), (consolidate, True)])
        before = room.status()
        ok = room.say("ok")
        # state: the move is still waiting, not approved, not advanced, and Next is unavailable
        s = room.status()
        assert room.index() == 2 and s == "AWAITING_LEARNER" == before
        with pytest.raises(ValueError):
            room.runtime.continue_controlled_c11_move(db, room.sid, state_version(room))
        # the Tutor saw the V3 rule, the question, and the bare acknowledgement, with no history
        assert GUIDE in ok["system"] and ok["context"] is None
        assert [m["content"] for m in ok["payload"]["current_move_dialogue_only"]][-2:] == [QUESTION, "ok"]
        # the (hand-written) restatement is concise and does not reveal the answer; a revealing reply would be flagged
        assert concise_restatement(restate, ["yes"]) and not reveals_answer(restate, ANSWER)
        assert reveals_answer("Since Yes is 1 and No is 0, that gives 110.", ANSWER)               # negative control
        # an honest "I'm not sure" then follows the existing consolidation and the move completes
        room.say("I'm not sure")
        assert room.status() == "APPROVED_AWAITING_NEXT" and room.index() == 2
        judge_calls = db.scalars(select(LLMCall).where(LLMCall.session_id == room.sid, LLMCall.purpose == "CONVERSATION_JUDGE")).all()
        m03_reviews = [c for c in judge_calls if c.request_payload["audit"].get("pilot_move_id") == "C1.1-P2-M03"]
        assert len(m03_reviews) == 1                                  # no review (and no repair loop) was triggered by "ok"
    finally:
        base._close_db(db)


def state_version(room):
    a = room.active()
    room.db.refresh(a)
    return base.state(a)["approval_version"]


def test_scripted_repeated_uncertainty_follows_existing_scaffolding_without_an_endless_restatement():
    restate = "No rush. Just the first two answers: what bit is each Yes?"
    hint = "Both of the first two answers are Yes, and Yes is 1, so start with 1, 1. What does the final No become?"
    consolidate = "No problem. No is 0, so Yes, Yes, No is 110, with the answers in positions 1, 2 and 3."
    db = base._db()
    try:
        room = _p2_room(db)
        _reach_c11_p2_m03(room, then=[(restate, False), (hint, False), (consolidate, True)])
        a = room.say("ok")
        b = room.say("ok")                                       # a SECOND bare acknowledgement: the rule says treat it as uncertainty
        assert room.status() == "AWAITING_LEARNER" and room.index() == 2
        c = room.say("I don't know")
        assert room.status() == "APPROVED_AWAITING_NEXT"
        # the second call saw the first restatement and the first "ok" (so the Tutor can avoid repeating itself)
        assert [m["content"] for m in b["payload"]["current_move_dialogue_only"] if m["role"] == "TUTOR"][-1] == restate
        assert "Handle it as you would any 'I'm not sure' reply under your guided-move rules above." in re.sub(r"\s+", " ", b["system"])
        # no autonomous loop: exactly one Tutor call per learner turn, and one Judge review for the whole move
        tutor_calls = [c for c in room.llm.calls if c["move"] == "C1.1-P2-M03"]
        assert len(tutor_calls) == 4                               # question, ok, ok, "I don't know"
        replies = [restate, hint, consolidate]
        assert not restatement_loop(replies, ["first two answers"])
        assert restatement_loop([restate] * 3, ["first two answers"])                                  # negative control
        assert sum(1 for r in replies if reveals_answer(r, ANSWER)) == 1 and reveals_answer(consolidate, ANSWER)   # only AFTER uncertainty
    finally:
        base._close_db(db)


# ====================================================================================================
# 11. grounded examples (prompt level + checkers; real behaviour needs a live evaluation)
# ====================================================================================================
EXAMPLE_SCENARIOS = [("P1", "C1.1", 2), ("P2", "C1.1", 2), ("P3", "C1.1", 2), ("P1", "C1.2", 1), ("P3", "C1.4", 2)]


@pytest.mark.parametrize("ped,sub,index", EXAMPLE_SCENARIOS)
def test_example_request_prompt_has_only_the_authored_examples_and_the_grounding_rule(ped, sub, index):
    moves = contract()["subsections"][sub]["moves_by_pedagogy"][ped]
    move = moves[index]
    d = [base.tutor("a", move["id"], "The first message of this move, already shown to the learner here.", sub=sub, ped=ped),
         base.learner("l", "can you show me another example?")]
    text = v3(move, index, d)
    p = payload(text)
    assert GUIDE in text and p["learner_question_text_if_any"] == "can you show me another example?"
    assert "Never invent a replacement example" in re.sub(r"\s+", " ", text)
    allowed = cont.allowed_bitstrings(move, index) | bitstrings(json.dumps(p["science_scope_guards"]))
    assert bitstrings(json.dumps(p["verified_facts_for_this_turn"])) <= allowed
    assert "Never invent a replacement example" not in off(move, index, d)          # the rule is new in V3


def test_invented_examples_and_internal_language_are_detected_and_grounded_replies_pass():
    move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][2]
    invented = ["Certainly! Consider the pattern 101, which also has two ones.", "For another example, 010 has a single one."]
    leaking = ["We must stick with 110 because no other examples are in our current facts.", "That is not in the available evidence."]
    grounded = ["We'll keep working with 110 and look at it another way: the two 1s come from the first two Yes answers.",
                "Let's stay with the example we have, 110, and count its ones once more."]
    assert all(invented_bitstrings(t, move, 2) for t in invented)
    assert all(uses_internal_language(t) for t in leaking)
    for t in grounded:
        assert not invented_bitstrings(t, move, 2) and not uses_internal_language(t)


# ====================================================================================================
# 12. P1 worked examples and P3 matched cases remain intact
# ====================================================================================================
def test_p1_p2_p3_instructions_and_payloads_are_untouched_by_v3():
    for ped in ("P1", "P2", "P3"):
        for sub in ("C1.1", "C1.2", "C1.3", "C1.4"):
            for i, m in enumerate(contract()["subsections"][sub]["moves_by_pedagogy"][ped]):
                a, b = payload(off(m, i)), payload(v3(m, i))
                assert a == b and a["pedagogy"] == ped
    move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][2]
    flat = re.sub(r"\s+", " ", v3(move, 2))
    for phrase in ("P1 worked examples: demonstrate the required fixed example directly;",
                   "P2 guided moves: on the FIRST guided turn ask the SPECIFIC authored",
                   "P3 comparisons: keep the matching conditions clear",
                   "Non-guided explain/model/compare moves and conditional moves require NO extra learner reply",
                   "tutor_never_advances_moves"):
        assert phrase in flat, phrase
    from solo_harness.runtime.v051_conversation import V051TutorOutput
    assert json.loads(v3(move, 2).split("\n[OUTPUT_SCHEMA]\n", 1)[1]) == V051TutorOutput.model_json_schema()


def test_scripted_p1_demonstration_and_p3_matched_cases_flow_through_v3_without_invitations():
    demo = ("Take 110. The first bit is 1, the second is 1 and the third is 0, so it holds two 1s even though it is three bits long.")
    cases = ("Here are two matched sequences under the same Yes=1, No=0 rule. Yes, Yes, No gives 110 and Yes, No, No gives 100. "
             "Both are three bits long.")
    db = base._db()
    try:
        room = _v3_room(db, "P1")
        room.script(cont.filler("C1.1-P1-M01"), cont.filler("C1.1-P1-M02"), (demo, True))
        room.say(); room.next(); room.say(); room.next(); call = room.say()
        assert room.status() == "APPROVED_AWAITING_NEXT" and "?" not in demo and call["context"] is None
        assert [m["content"] for m in call["payload"]["current_move_dialogue_only"]] == []
    finally:
        base._close_db(db)
    db = base._db()
    try:
        room = _v3_room(db, "P3")
        room.script(cont.filler("C1.1-P3-M01"), (cases, True))
        room.say(); room.next(); call = room.say()
        assert room.status() == "APPROVED_AWAITING_NEXT" and call["payload"]["pedagogy"] == "P3"
        assert {"110", "100"} <= bitstrings(cases) and "?" not in cases
    finally:
        base._close_db(db)


# ====================================================================================================
# 13-14. Judge and C2-C4 unchanged
# ====================================================================================================
def test_judge_prompts_are_byte_identical_to_before_and_carry_no_v3_text():
    digest = hashlib.sha256()
    for sub, ped, i, m in ALL:
        n = len(contract()["subsections"][sub]["moves_by_pedagogy"][ped])
        text = vc.controlled_c1_judge_prompt(None, {}, [], None, m, i, i == n - 1, {})
        assert GUIDE not in text and "targeted" not in text.lower()
        digest.update(text.encode())
    assert digest.hexdigest() == "04124ac699a32e9be4accbef0a4b47262bd5d1b8c136ed681c4f129534aee53b"


def test_c2_c3_c4_prompts_are_unchanged_and_a_v3_course_sends_v3_text_only_on_c1(monkeypatch):
    from solo_harness.runtime.controlled_executor import contract as unified, instance
    from solo_harness.runtime.controlled_unified_prompts import tutor_prompt
    digest, count = hashlib.sha256(), 0
    for section in ("C2", "C3", "C4"):
        for sub, block in unified(section)["subsections"].items():
            for ped in ("P1", "P2", "P3"):
                for i, move in enumerate(block["moves_by_pedagogy"][ped]):
                    text = tutor_prompt(SimpleNamespace(), {}, [], None, instance(sub, ped), move, i)
                    assert GUIDE not in text
                    digest.update(text.encode())
                    count += 1
    assert count == 135 and digest.hexdigest() == "dd14c33466e041303321a2aeac2c9cab983ec1d0482b59d27d0142a4547dc130"

    import test_unified_c1_c4_sqlite_runtime as harness
    original = base.SessionRuntime.create_v051_internal_test_session
    monkeypatch.setattr(harness, "_ScriptedLLM", base._RecordingLLM)
    monkeypatch.setattr(base.SessionRuntime, "create_v051_internal_test_session",
                        lambda self, *a, **k: original(self, *a, c1_conversation_context=True, **k))      # stamped V3 (the default)
    db = base._db()
    try:
        harness._run_complete_study(db, "P2")
        seen = {}
        for call in db.scalars(select(LLMCall).where(LLMCall.purpose == "TUTOR")).all():
            section = call.request_payload["audit"]["pilot_move_id"][:2]
            has_guide = GUIDE in call.compiled_prompt_text
            seen.setdefault(section, set()).add(has_guide)
            assert has_guide == (section == "C1")
            assert ("c1_conversation_context_revision" in call.request_payload["audit"]) == (section == "C1")
            assert "conversation_context" not in call.compiled_prompt_text and V2_GUIDE not in call.compiled_prompt_text
        assert seen == {"C1": {True}, "C2": {False}, "C3": {False}, "C4": {False}}
    finally:
        base._close_db(db)


# ====================================================================================================
# Milestone 3.2 pre-run check: ready_for_judge. V3 deliberately does NOT restate the base rule.
# ====================================================================================================
READY_RULE = "Set ready_for_judge=false while awaiting an answer."


def _flat(text):
    return re.sub(r"\s+", " ", text)


def test_v3_retains_the_original_ready_for_judge_instruction_exactly_once_and_adds_no_duplicate():
    for _, _, i, m in ALL:
        o, t = _flat(off(m, i)), _flat(v3(m, i))
        assert READY_RULE in t and t.count(READY_RULE) == o.count(READY_RULE) == 1, m["id"]
        assert t.count("ready_for_judge") == o.count("ready_for_judge"), m["id"]          # no extra mention anywhere
    assert "ready_for_judge" not in vc._TARGETED_GUIDANCE_V3


def test_the_original_instruction_sits_inside_the_p2_guided_move_rule_that_v3_leaves_untouched():
    flat = _flat(v3(contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"][2], 2))
    assert ("P2 guided moves: on the FIRST guided turn ask the SPECIFIC authored active_move.guided_question without revealing its correct answer. "
            + READY_RULE) in flat


def test_a_ready_flag_on_a_first_guided_turn_causes_no_judge_review_in_flag_off_or_v3():
    """V3 is prompt-only: even a Tutor that wrongly sets ready_for_judge on the first guided turn cannot trigger a premature review,
    because the engine requires a learner reply first. Checked identically for the flag-off control and V3."""
    for revision_on in (False, True):
        db = base._db()
        try:
            room = cont.Room(db, "P2", on=revision_on, revision=V3)
            room.script(cont.filler("C1.1-P2-M01"),
                        ("Which has several bits: 1 or 110?", False), ("1 is a single bit; 110 holds three bits in order, so B has several.", True),
                        (QUESTION, True))                     # <- WRONG on purpose: ready_for_judge=True on a first guided turn
            room.say(); room.next()
            room.say(); room.say("Example B"); room.next()
            room.say()
            assert room.status() == "AWAITING_LEARNER", revision_on
            reviews = [c for c in db.scalars(select(LLMCall).where(LLMCall.session_id == room.sid, LLMCall.purpose == "CONVERSATION_JUDGE")).all()
                       if c.request_payload["audit"].get("pilot_move_id") == "C1.1-P2-M03"]
            assert reviews == [], revision_on
        finally:
            base._close_db(db)


def test_in_v3_a_review_happens_only_after_a_real_reply_and_only_when_the_tutor_asks_for_one():
    db = base._db()
    try:
        room = _v3_room(db, "P2")
        _reach_c11_p2_m03(room, then=[("No rush. Just the first two answers: what bit is each Yes?", False),
                                      ("No problem. No is 0, so Yes, Yes, No is 110, in positions 1, 2 and 3.", True)])
        def m03_reviews():
            return [c for c in db.scalars(select(LLMCall).where(LLMCall.session_id == room.sid, LLMCall.purpose == "CONVERSATION_JUDGE")).all()
                    if c.request_payload["audit"].get("pilot_move_id") == "C1.1-P2-M03"]
        assert m03_reviews() == []                         # after the first guided turn
        room.say("ok")                                     # restatement with ready_for_judge=false
        assert m03_reviews() == [] and room.status() == "AWAITING_LEARNER"
        room.say("I'm not sure")                           # consolidation with ready_for_judge=true
        assert len(m03_reviews()) == 1 and room.status() == "APPROVED_AWAITING_NEXT"
    finally:
        base._close_db(db)
