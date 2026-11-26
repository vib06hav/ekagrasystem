"""Milestone 2: natural conversational continuity for the C1 Tutor (revision V2 sessions only).

Three kinds of verification live here and must not be confused:

1. UNIT: prompt construction, flags, revisions, boundary topics and the deterministic response checkers.
2. SCRIPTED CONVERSATIONS: hand-written, realistic multi-turn exchanges driven through the real ORM runtime with a
   scripted LLM. They prove the plumbing: which prompt each turn received, state and approvals, doubts, isolation. The
   Tutor replies are written by hand, so they say nothing about how a real model will behave.
3. LIVE LLM: not performed. The checkers below are written so they can be reused on real model output later.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from types import SimpleNamespace

import pytest
from sqlalchemy import select

import test_c1_conversation_context as base        # shared helpers and harness; no test functions are imported
from solo_harness.db.models import LLMCall, SubsectionProgress
from solo_harness.runtime.controlled_c1_prompt_context import (
    CONVERSATION_CONTEXT_REVISION, CONVERSATION_CONTEXT_REVISION_V2, OPTIONAL_INVITATION_MOVES, SESSION_CONFIG_KEY,
    V2_FROZEN_OPTIONAL_INVITATION_MOVES,
    boundary_topics, build_conversation_context, delivery_spec, prior_facts_for_question, selected_facts,
)
from solo_harness.runtime.controlled_executor import state
from solo_harness.runtime.v051_conversation import controlled_c1_judge_prompt, controlled_c1_tutor_prompt
from solo_harness.studies.controlled_c1 import contract

TUTOR_MARKER = base.TUTOR_MARKER
ALL = base.ALL
GUIDANCE_HEADING = "[CONVERSATIONAL_CONTINUITY_V2]"


def prompt(move, index, dialogue=None, *, enabled=True, continuity=True, **kw):
    return controlled_c1_tutor_prompt(SimpleNamespace(), {}, dialogue or [], None, None, move, index,
                                      conversation_context_enabled=enabled, conversational_continuity=continuity, **kw)


def payload(text):
    return base._payload(text)


# ====================================================================================================
# 1. UNIT: deterministic response checkers (reusable on live output)
# ====================================================================================================
STOCK_PRAISE = re.compile(r"^\W*(great|excellent|good question|that'?s a (good|great|excellent) question|well done|"
                          r"perfect|awesome|fantastic)\b", re.I)
UNDERSTAND_CHECK = re.compile(r"do you understand|does that make sense|are you following", re.I)


def words_of(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def has_stock_praise(text):
    return bool(STOCK_PRAISE.search(text))


def asks_if_understood(text):
    return bool(UNDERSTAND_CHECK.search(text))


def repeats_opening(text, recent_openings, n=3):
    mine = words_of(text)[:n]
    return any(mine == words_of(o)[:n] for o in recent_openings if len(words_of(o)) >= n)


def trigram_overlap(a, b):
    grams = lambda t: {tuple(w[i:i + 3]) for w in [words_of(t)] for i in range(max(len(w) - 2, 0))}
    ga, gb = grams(a), grams(b)
    return len(ga & gb) / max(min(len(ga), len(gb)), 1)


def bitstrings(text):
    return set(re.findall(r"(?<![0-9A-Za-z])[01]{2,}(?![0-9A-Za-z])", text))


def allowed_bitstrings(move, index):
    facts = list(selected_facts(move).values()) + list(prior_facts_for_question(move, index).values())
    return set().union(*(bitstrings(f) for f in facts)) | {"110", "100"}


def check_reply(text, move, index, *, recent_openings=(), earlier_replies=()):
    """Return a list of problems; empty means the reply passes every deterministic check."""
    problems = []
    if has_stock_praise(text):
        problems.append("stock praise")
    if asks_if_understood(text):
        problems.append("understanding check")
    if recent_openings and repeats_opening(text, recent_openings):
        problems.append("repeated opening")
    if any(trigram_overlap(text, earlier) > 0.6 for earlier in earlier_replies):
        problems.append("restates an earlier reply")
    if not bitstrings(text) <= allowed_bitstrings(move, index):
        problems.append(f"unverified bit strings {sorted(bitstrings(text) - allowed_bitstrings(move, index))}")
    return problems


def test_checkers_flag_what_they_claim_to_flag():
    move, i = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][2], 2
    assert has_stock_praise("Great! Let's move on.") and has_stock_praise("Excellent answer, that is right.")
    assert has_stock_praise("That's a good question — here is why.")
    assert not has_stock_praise("The third bit is 0, so 110 has two 1s.")
    assert asks_if_understood("Does that make sense?") and not asks_if_understood("Here is the count.")
    assert repeats_opening("Remember that a bit is 0 or 1.", ["Remember that a flip can go either way."])
    assert not repeats_opening("Think of 110 as three answers.", ["Remember that a flip can go either way."])
    assert trigram_overlap("the first two bits are one and the last is zero", "the first two bits are one and the last is zero") == 1
    assert trigram_overlap("completely different words here today", "nothing in common whatsoever with that") == 0
    assert check_reply("Take 110: two 1s.", move, i) == []
    assert any("unverified" in p for p in check_reply("Try 101101 now.", move, i))      # a later subsection's frame


# ====================================================================================================
# 1. UNIT: prompt construction
# ====================================================================================================
def test_v2_prompt_carries_the_guidance_and_the_continuity_block_and_v1_does_not():
    move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][2]
    v2, v1 = prompt(move, 2), prompt(move, 2, continuity=False)
    assert GUIDANCE_HEADING in v2 and GUIDANCE_HEADING not in v1
    assert payload(v2)["continuity"]["revision"] == CONVERSATION_CONTEXT_REVISION_V2
    assert "continuity" not in payload(v1)
    assert payload(v2)["conversation_context"]["revision"] == CONVERSATION_CONTEXT_REVISION_V2
    assert payload(v1)["conversation_context"]["revision"] == CONVERSATION_CONTEXT_REVISION
    assert "previous_subsection_topics" in payload(v2)["conversation_context"]
    assert "previous_subsection_topics" not in payload(v1)["conversation_context"]


def test_continuity_requires_the_context_to_be_enabled_at_all():
    move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][2]
    off = controlled_c1_tutor_prompt(SimpleNamespace(), {}, [], None, None, move, 2)
    assert prompt(move, 2, enabled=False, continuity=True) == off
    assert GUIDANCE_HEADING not in off and "continuity" not in payload(off)


def test_guidance_contains_each_required_principle():
    g = prompt(contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][2], 2).split(GUIDANCE_HEADING, 1)[1]
    g = re.sub(r"\s+", " ", g.split("The Tutor's ready_for_judge", 1)[0])           # the guidance is hard-wrapped
    for needle in ("respond to that specific contribution", "answer it directly first", "no Tutor message has actually answered",
                   "Do not claim it was answered before", "No stock praise", "never \"Do you understand?\"",
                   "Connect, do not restart", "refer back to the earlier explanation", "recent_tutor_openings",
                   "Never change meaning for the sake of variety", "Transitions look back, not ahead",
                   "Never preview", "FIRST delivery of the move", "may run longer when accuracy needs it",
                   "Never invent numbers or bit strings", "Never discuss assessments",
                   "do not imply they said anything", "P1 demonstrates", "P2 asks the authored", "P3 shows the matched cases",
                   "extended Socratic dialogue", "ONE short, low-pressure invitation", "It is never required"):
        assert needle in g, needle
    for scenario in ("Correct answer", "Incorrect or partly correct answer", "Confusion or a request for another explanation",
                     "Request for another example", "Short acknowledgement", "Repeated question", "Unrelated question",
                     "Learner moves on without replying"):
        assert scenario in g, scenario


def test_guidance_adds_no_mandatory_gate_or_correctness_language():
    g = prompt(contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"][2], 2).split(GUIDANCE_HEADING, 1)[1]
    g = g.split("The Tutor's ready_for_judge", 1)[0].lower()
    for forbidden in ("must answer", "required to answer", "before you can continue", "mastery", "unlock", "wait for the learner to"):
        assert forbidden not in g, forbidden


def test_v2_adds_exactly_the_continuity_block_the_topics_key_and_the_guidance():
    d = base.history() + [base.tutor("t4", base.M[2], "Counting.")]
    kw = dict(approved_move_message_ids=base.APPROVED)
    v1 = controlled_c1_tutor_prompt(SimpleNamespace(), {}, d, None, None, base.MOVES[2], 2, conversation_context_enabled=True, **kw)
    v2 = controlled_c1_tutor_prompt(SimpleNamespace(), {}, d, None, None, base.MOVES[2], 2, conversation_context_enabled=True,
                                    conversational_continuity=True, **kw)
    p1, p2 = payload(v1), payload(v2)
    assert set(p2) - set(p1) == {"continuity"}
    assert {k: v for k, v in p2.items() if k not in ("continuity", "conversation_context")} == \
           {k: v for k, v in p1.items() if k != "conversation_context"}
    ctx1, ctx2 = p1["conversation_context"], p2["conversation_context"]
    assert {k: v for k, v in ctx2.items() if k not in ("revision", "previous_subsection_topics")} == \
           {k: v for k, v in ctx1.items() if k != "revision"}
    assert v2.replace(base.M[0], "") != v1 and GUIDANCE_HEADING in v2 and GUIDANCE_HEADING not in v1


def test_first_message_flag_tracks_whether_this_move_has_spoken():
    move = base.MOVES[2]
    assert payload(prompt(move, 2))["continuity"]["first_message_of_this_move"] is True
    spoken = [base.tutor("a", move["id"], "I already said something about this move.")]
    assert payload(prompt(move, 2, spoken))["continuity"]["first_message_of_this_move"] is False
    other = [base.tutor("b", base.M[1], "A previous move.")]
    assert payload(prompt(move, 2, other))["continuity"]["first_message_of_this_move"] is True


def test_frozen_v2_allows_invitations_for_exactly_the_eight_evaluated_moves_while_the_current_policy_is_empty():
    """V2 reproduces what was evaluated in Milestone 3. The CURRENT policy (used by no prompt) is empty: see test_c1_v3_*."""
    assert OPTIONAL_INVITATION_MOVES == frozenset()
    flagged = {m["id"] for _, _, i, m in ALL if payload(prompt(m, i))["continuity"]["optional_invitation_allowed"]}
    assert flagged == set(V2_FROZEN_OPTIONAL_INVITATION_MOVES) and len(flagged) == 8
    by_id = {m["id"]: m for _, _, _, m in ALL}
    assert all(by_id[mid]["learner_response_policy"] in ("model", "compare") for mid in flagged)     # never guided or explain
    assert {mid.split("-")[1] for mid in flagged} == {"P1", "P3"}


def test_pedagogy_instructions_and_schema_survive_in_v2_for_every_pedagogy():
    from solo_harness.runtime.v051_conversation import V051TutorOutput
    for ped in ("P1", "P2", "P3"):
        move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"][ped][1]
        text = prompt(move, 1)
        for phrase in ("P1 worked examples: demonstrate the required fixed example directly;",
                       "P2 guided moves: on the FIRST guided turn ask the SPECIFIC authored",
                       "P3 comparisons: keep the matching conditions clear", "tutor_never_advances_moves"):
            assert phrase in text
        assert payload(text)["pedagogy"] == ped and payload(text)["prompt_revision"] == "C1_MOVE_SCOPED_FLEXIBLE_V3_2"
        assert json.loads(text.split("\n[OUTPUT_SCHEMA]\n", 1)[1]) == V051TutorOutput.model_json_schema()


def test_judge_prompts_and_c2_to_c4_prompts_are_unaffected_by_milestone_two():
    digest = hashlib.sha256()
    for sub, ped, i, m in ALL:
        n = len(contract()["subsections"][sub]["moves_by_pedagogy"][ped])
        digest.update(controlled_c1_judge_prompt(None, {}, [], None, m, i, i == n - 1, {}).encode())
    assert digest.hexdigest() == "04124ac699a32e9be4accbef0a4b47262bd5d1b8c136ed681c4f129534aee53b"


def test_disabled_and_v1_prompts_are_pinned():
    off, v1 = hashlib.sha256(), hashlib.sha256()
    for _, _, i, m in ALL:
        off.update(controlled_c1_tutor_prompt(None, {}, [], None, None, m, i).encode())
        v1.update(controlled_c1_tutor_prompt(None, {}, [], None, None, m, i, conversation_context_enabled=True).encode())
    assert off.hexdigest() == base.HEAD_TUTOR_PROMPTS_SHA256                       # byte-identical to HEAD
    assert v1.hexdigest() == V1_PINNED


# Milestone 1 (context only) prompts for empty dialogue; V1-stamped sessions must keep producing exactly these.
V1_PINNED = "15df212d14c6d196de8a99b0e5c3c1948b81016f11dcab63b1e920dbaa40ebe0"


@pytest.mark.parametrize("sub,ped,index,move", ALL, ids=[x[3]["id"] for x in ALL])
def test_v2_prompt_never_contains_facts_that_belong_only_to_later_moves(sub, ped, index, move):
    moves = contract()["subsections"][sub]["moves_by_pedagogy"][ped]
    own = {t for m in moves[:index + 1] for t in selected_facts(m).values()}
    later_only = {t for m in moves[index + 1:] for t in selected_facts(m).values()} - own
    dialogue = []
    for j, m2 in enumerate(moves):
        dialogue += [base.tutor(f"t{j}", m2["id"], f"Sentinel message {j} for {m2['id']} with plenty of words to be substantive here"),
                     base.learner(f"l{j}", f"learner sentinel {j}")]
    text = prompt(move, index, dialogue + [base.learner("q", "why does that matter?")],
                  approved_move_message_ids={m2["id"]: [f"t{j}"] for j, m2 in enumerate(moves)})
    for fact in later_only:
        assert fact not in text, (move["id"], fact)


def test_v2_prompt_stays_inside_a_sane_size_budget_even_with_full_context():
    move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][2]
    long_text = " ".join(["word"] * 80)
    d = [base.tutor("a", base.M[0], long_text, mode="DOUBT"), base.tutor("b", base.M[0], long_text + " x", mode="DOUBT"),
         base.tutor("c", base.M[0], long_text + " y", mode="DOUBT"), base.tutor("e", base.M[1], long_text),
         base.learner("l0", "q" * 400), base.learner("l1", "q" * 400)]
    text = prompt(move, 2, d, approved_move_message_ids={base.M[1]: ["e"]}, approved_doubt_message_ids=["a", "b", "c"])
    assert len(text) < 15000


# ====================================================================================================
# 1. UNIT: subsection boundary topics (labels only)
# ====================================================================================================
C11_P1 = [m["id"] for m in contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"]]


def test_boundary_topics_are_authored_labels_of_approved_moves_of_the_immediate_predecessor():
    out = boundary_topics({"subsection_id": "C1.1", "approved_move_ids": C11_P1}, "C1.2", "P1")
    assert out["subsection_id"] == "C1.1"
    expected = []
    for m in contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"]:
        for key in delivery_spec(m)["verified_fact_keys"]:
            label = key.replace("_", " ")
            if label not in expected:
                expected.append(label)
    assert out["topics_already_taught"] == expected[:10]
    assert all("_" not in t and len(t.split()) <= 3 for t in out["topics_already_taught"])      # labels, never sentences


def test_boundary_topics_use_only_moves_the_ledger_shows_as_approved():
    full = boundary_topics({"subsection_id": "C1.1", "approved_move_ids": C11_P1}, "C1.2", "P1")["topics_already_taught"]
    part = boundary_topics({"subsection_id": "C1.1", "approved_move_ids": C11_P1[:1]}, "C1.2", "P1")["topics_already_taught"]
    assert part == ["information data", "bits"] and set(part) < set(full)
    assert boundary_topics({"subsection_id": "C1.1", "approved_move_ids": []}, "C1.2", "P1")["topics_already_taught"] == []


@pytest.mark.parametrize("evidence,subsection", [
    (None, "C1.2"), ("x", "C1.2"), ({}, "C1.2"),
    ({"subsection_id": "C1.1", "approved_move_ids": C11_P1}, "C1.1"),        # first subsection has no predecessor
    ({"subsection_id": "C1.1", "approved_move_ids": C11_P1}, "C1.3"),        # not the immediate predecessor
    ({"subsection_id": "C1.2", "approved_move_ids": C11_P1}, "C1.2"),        # names the wrong subsection
    ({"subsection_id": "C1.3", "approved_move_ids": C11_P1}, "C1.2"),        # a LATER subsection is never summarised
])
def test_boundary_topics_degrade_to_empty_for_anything_but_the_immediate_predecessor(evidence, subsection):
    assert boundary_topics(evidence, subsection, "P1") == {"subsection_id": None, "topics_already_taught": []}


def test_boundary_topics_ignore_move_ids_of_other_pedagogies_and_unknown_ids():
    p2_ids = [m["id"] for m in contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"]]
    out = boundary_topics({"subsection_id": "C1.1", "approved_move_ids": p2_ids + ["C1.1-P1-M99", 7, None]}, "C1.2", "P1")
    assert out["topics_already_taught"] == []


def test_boundary_topics_appear_only_on_the_first_move_and_only_in_v2():
    second = contract()["subsections"]["C1.2"]["moves_by_pedagogy"]["P1"]
    ev = {"subsection_id": "C1.1", "approved_move_ids": C11_P1}
    first = payload(prompt(second[0], 0, boundary_evidence=ev))["conversation_context"]["previous_subsection_topics"]
    later = payload(prompt(second[1], 1, boundary_evidence=ev))["conversation_context"]["previous_subsection_topics"]
    v1 = payload(prompt(second[0], 0, continuity=False, boundary_evidence=ev))["conversation_context"]
    assert first["subsection_id"] == "C1.1" and first["topics_already_taught"]
    assert later == {"subsection_id": None, "topics_already_taught": []}
    assert "previous_subsection_topics" not in v1


def test_boundary_topics_expose_no_future_or_assessment_material():
    second = contract()["subsections"]["C1.2"]["moves_by_pedagogy"]["P1"]
    text = prompt(second[0], 0, boundary_evidence={"subsection_id": "C1.1", "approved_move_ids": C11_P1})
    topics = payload(text)["conversation_context"]["previous_subsection_topics"]["topics_already_taught"]
    later_keys = {k.replace("_", " ") for sub in ("C1.2", "C1.3", "C1.4")
                  for m in contract()["subsections"][sub]["moves_by_pedagogy"]["P1"] for k in delivery_spec(m)["verified_fact_keys"]}
    assert not set(topics) & later_keys
    assert not re.search(r"MCQ|assessment|C1-SET", json.dumps(topics))


# ====================================================================================================
# 2. SCRIPTED CONVERSATIONS (real ORM runtime, scripted LLM, hand-written Tutor replies)
# ====================================================================================================
class TranscriptLLM(base._RecordingLLM):
    """Plays hand-written Tutor replies, in order, per session. Everything else behaves like the base scripted LLM."""

    def __init__(self):
        super().__init__()
        self.script = {}

    async def send(self, prepared):
        system = prepared.request.messages[0].content
        if prepared.request.logical_role == "TUTOR" and TUTOR_MARKER in system and self.script.get(self.who):
            text, ready = self.script[self.who].pop(0)
            data = payload(system)
            self.number += 1
            self.calls.append({"who": self.who, "move": data["active_move"]["id"], "mode": data["response_mode"],
                               "context": data.get("conversation_context"), "payload": data, "system": system,
                               "reply": text})
            return self._raw({"learner_message": text, "ready_for_judge": ready})
        return await super().send(prepared)


class Room:
    def __init__(self, db, ped="P1", on=True, revision=CONVERSATION_CONTEXT_REVISION_V2):
        self.db = db
        compiled, version = base._world(db)
        self.llm = TranscriptLLM()
        self.runtime, self.ai = base._stack(compiled, self.llm, False)
        kwargs = {"c1_conversation_context": True} if on else {}
        self.sid = self.runtime.create_v051_internal_test_session(
            db, version.id, unified_controlled_study=True, initial_pedagogy_id=ped, **kwargs).id
        if on:
            base.stamp_revision(db, self.sid, revision)        # V2 is frozen/deprecated but must keep working for stamped sessions
        self.who = "S"

    def script(self, *turns):
        self.llm.script.setdefault(self.who, []).extend(turns)

    def say(self, learner_text=None):
        self.llm.who = self.who
        asyncio.run(self.ai.execute(self.db, self.ai.reserve_tutor(self.db, self.sid, learner_text=learner_text)))
        return self.llm.calls[-1]

    def active(self):
        return self.db.scalar(select(SubsectionProgress).where(SubsectionProgress.session_id == self.sid,
                                                               SubsectionProgress.status == "ACTIVE"))

    def status(self):
        self.db.refresh(self.active())
        return state(self.active())["status"]

    def next(self):
        a = self.active()
        self.db.refresh(a)
        self.runtime.continue_controlled_c11_move(self.db, self.sid, state(a)["approval_version"])

    def index(self):
        a = self.active()
        self.db.refresh(a)
        return state(a)["move_index"]


def filler(move_id):
    return (f"A scripted opening explanation for {move_id} written with enough ordinary words to count as a "
            f"substantive teaching message here", True)


def with_room(ped, body, on=True):
    db = base._db()
    try:
        body(Room(db, ped, on))
    finally:
        base._close_db(db)


def test_p1_worked_example_clarification_then_purpose_without_restarting_the_example():
    """C1.1-P1-M03: demonstration, a question about one step, then why the result matters."""
    demo = ("Take 110. The first bit is 1, the second is 1 and the third is 0, so it holds two 1s even though it is "
            "three bits long.")
    step = ("I counted only the bits that are 1: the first and the second. The third bit is 0, so it adds nothing "
            "to the count.")
    why = ("We count 1s because parity checking will later use how many 1s a sequence has. It is a simple "
           "prerequisite for error-checking and says nothing about the sequence as a number.")

    def body(room):
        room.script(filler("C1.1-P1-M01"), filler("C1.1-P1-M02"), (demo, True), (step, True), (why, True))
        room.say(); room.next(); room.say(); room.next()
        first = room.say()                                    # the worked example
        assert room.status() == "APPROVED_AWAITING_NEXT"
        second = room.say("how did you get two?")
        assert room.status() == "APPROVED_AWAITING_NEXT" and room.index() == 2
        third = room.say("why does the count matter?")
        assert room.status() == "APPROVED_AWAITING_NEXT" and room.index() == 2          # doubts never move the move

        # the first message: V2 guidance, an allowed optional invitation (frozen V2 behaviour), and a link back to the previous move
        c1 = first["payload"]
        assert c1["continuity"] == {"revision": CONVERSATION_CONTEXT_REVISION_V2, "first_message_of_this_move": True,
                                    "optional_invitation_allowed": True}
        assert c1["conversation_context"]["previous_move_id"] == "C1.1-P1-M02"
        # the clarification turn is answered in DOUBT mode, with the demonstration visible and the question isolated
        p2 = second["payload"]
        assert p2["response_mode"] == "DOUBT" and p2["learner_question_text_if_any"] == "how did you get two?"
        assert p2["pending_post_approval_doubt"]["text"] == "how did you get two?"
        assert [m["content"] for m in p2["current_move_dialogue_only"] if m["role"] == "TUTOR"] == [demo]
        assert p2["continuity"]["first_message_of_this_move"] is False
        # the "why" turn sees the whole exchange, so the Tutor can answer without replaying the example
        p3 = third["payload"]
        assert [(m["role"]) for m in p3["current_move_dialogue_only"]] == ["TUTOR", "LEARNER", "TUTOR", "LEARNER"]
        assert p3["learner_question_text_if_any"] == "why does the count matter?"
        assert "count_purpose" in p3["verified_facts_for_this_turn"]
        # the hand-written replies satisfy every deterministic checker
        move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][2]
        assert check_reply(demo, move, 2) == []
        assert check_reply(step, move, 2, earlier_replies=[demo]) == []
        assert check_reply(why, move, 2, earlier_replies=[demo, step]) == []
        assert trigram_overlap(why, demo) < 0.3            # the purpose answer does not replay the example
    with_room("P1", body)


def test_p2_guided_sequence_survives_an_incorrect_then_partial_answer_and_continues():
    """C1.1-P2-M03: question, wrong answer, hint, partial answer, consolidation; then the next authored question."""
    question = "Using Yes=1 and No=0, how would you write Yes, Yes, No as bits?"
    hint = ("That reads as 1, 0, 1, which would be Yes, No, Yes. Our answers in order were Yes, Yes, No, so what "
            "does the second answer become?")
    consolidation = ("Yes, the second answer is also 1. So Yes, Yes, No is 110, with the three answers sitting in "
                     "positions 1, 2 and 3.")
    nxt = "A small step we will need later: how many 1s are in 110?"

    def body(room):
        room.script(filler("C1.1-P2-M01"),
                    ("Which has several bits: 1 or 110?", False), ("1 is a single bit; 110 holds three bits in order, so B has several.", True),
                    (question, False), (hint, False), (consolidation, True), (nxt, False))
        room.say(); room.next()                                              # M01
        room.say(); assert room.status() == "AWAITING_LEARNER"               # M02 question
        room.say("Example A"); room.next()                                   # M02 answered (wrong), explained
        q = room.say(); assert room.status() == "AWAITING_LEARNER"           # M03 question
        h = room.say("101")                                                  # incorrect
        assert room.status() == "AWAITING_LEARNER"                           # the guided sequence keeps waiting
        c = room.say("the first two are 1 and then 1?")                      # partial
        assert room.status() == "APPROVED_AWAITING_NEXT" and room.index() == 2
        room.next()
        n = room.say()                                                       # next authored question, new move

        assert q["payload"]["first_guided_question_turn"] is True
        assert q["payload"]["continuity"]["optional_invitation_allowed"] is False            # P2 is never invited
        assert h["payload"]["first_guided_question_turn"] is False
        assert h["payload"]["verified_learner_reply_fact_check"] == {
            "kind": "bit_sequence", "submitted": "101", "verified_expected": "110", "matches": False,
            "purpose": "formative feedback, not mastery or progression"}
        assert [m["content"] for m in h["payload"]["current_move_dialogue_only"]] == [question, "101"]
        assert [m["role"] for m in c["payload"]["current_move_dialogue_only"]] == ["TUTOR", "LEARNER", "TUTOR", "LEARNER"]
        ctx = n["context"]                       # the next move is a first guided question; frozen V2 still carries history
        assert ctx["previous_move_id"] == "C1.1-P2-M03" and ctx["previous_move_closing"] == consolidation
        assert ctx["recent_learner_turns"] == [{"move_id": "C1.1-P2-M03", "text": "101"},
                                               {"move_id": "C1.1-P2-M03", "text": "the first two are 1 and then 1?"}]
        assert h["context"]["previous_move_id"] == "C1.1-P2-M02"
        assert {"move_id": "C1.1-P2-M02", "text": "Example A"} in h["context"]["recent_learner_turns"]
        move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"][2]
        for text, earlier in ((hint, [question]), (consolidation, [question, hint])):
            assert check_reply(text, move, 2, earlier_replies=earlier) == []
    with_room("P2", body)


def test_p3_contrasting_cases_stay_intact_and_the_principle_is_stated_whatever_the_learner_says():
    """C1.1-P3-M02: matched cases, the learner names one difference, the Tutor acknowledges it and states the principle."""
    cases = ("Here are two matched sequences under the same Yes=1, No=0 rule. Yes, Yes, No gives 110 and Yes, No, No "
             "gives 100. Both are three bits long.")
    reply = ("Yes, the middle bit differs: 1 in 110 and 0 in 100. That one position is the whole difference, and it "
             "shows that a bit's position tells us which answer it stands for.")

    def body(room):
        room.script(filler("C1.1-P3-M01"), (cases, True), (reply, True))
        room.say(); room.next()
        first = room.say()
        learner_turn = room.say("the second one has a 0 in the middle")
        assert room.status() == "APPROVED_AWAITING_NEXT" and room.index() == 1
        assert first["payload"]["pedagogy"] == "P3" and first["payload"]["continuity"]["optional_invitation_allowed"] is True
        p = learner_turn["payload"]
        assert [m["content"] for m in p["current_move_dialogue_only"] if m["role"] == "TUTOR"] == [cases]   # cases untouched
        assert p["learner_question_text_if_any"] == "the second one has a 0 in the middle"
        move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P3"][1]
        assert check_reply(cases, move, 1) == [] and check_reply(reply, move, 1, earlier_replies=[cases]) == []
        assert {"110", "100"} <= bitstrings(cases) and "position" in reply           # both cases and the principle present
    with_room("P3", body)


def test_cross_move_question_in_one_move_supports_continuity_in_the_next_without_future_content():
    answer = ("Yes — Yes is 1 and No is 0 only by the convention we agreed for this example; it is not a rule of "
              "computers in general.")

    def body(room):
        room.script(filler("C1.1-P1-M01"), (answer, True), filler("C1.1-P1-M02"))
        room.say()                                                       # M01 approved
        room.say("is Yes always 1?")                                     # doubt answered and approved
        room.next()
        nxt = room.say()                                                 # first message of M02
        ctx = nxt["context"]
        assert nxt["move"] == "C1.1-P1-M02" and ctx["previous_move_id"] == "C1.1-P1-M01"
        assert ctx["recent_learner_turns"] == [{"move_id": "C1.1-P1-M01", "text": "is Yes always 1?"}]
        assert ctx["clarifications_given"] == [answer]
        assert ctx["previous_move_closing"].startswith("A scripted opening explanation for C1.1-P1-M01")
        # nothing of later moves or other subsections reached the Tutor
        later = {t for m in contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][2:] for t in selected_facts(m).values()}
        own = set(selected_facts(contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][1]).values())
        assert not any(f in nxt["system"] for f in later - own)
        assert not re.search(r"C1\.[234]-P", json.dumps(ctx))
        assert nxt["payload"]["continuity"]["first_message_of_this_move"] is True
    with_room("P1", body)


def test_repetition_the_recent_openings_are_visible_and_a_varied_reply_passes_while_a_repeat_fails():
    same = "Remember that a bit is either 0 or 1, and that the Yes or No convention is only an illustration here."
    varied = "In 110 the 1s mark the two Yes answers and the 0 marks the No, so the count of 1s is two."

    def body(room):
        room.script((same, True), (same + " Again.", True), (same + " Once more.", True), (same + " Last.", True), (varied, True))
        for _ in range(3):
            room.say(); room.next()
        # the fourth move now has four recent identical openings available to it
        fourth = room.say()
        openings = fourth["context"]["recent_tutor_openings"]
        assert len(openings) == 3 and len({" ".join(o.split()[:4]) for o in openings}) == 1
        assert "recent_tutor_openings" in fourth["system"].split(GUIDANCE_HEADING, 1)[1]
        move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"][3]
        assert "repeated opening" in check_reply(same + " Last.", move, 3, recent_openings=openings)
        assert check_reply(varied, move, 3, recent_openings=openings) == []
        # the meaning is unchanged: both replies carry the convention
        assert "convention" in same and "No" in varied
    with_room("P1", body)


# ---------------------------------------------------------------- the eleven learner situations, as prompts
SITUATIONS = [
    ("correct answer", "C1.1", "P2", 2, "110"),
    ("incorrect answer", "C1.1", "P2", 2, "101"),
    ("partially correct answer", "C1.1", "P2", 2, "the first two are 1"),
    ("conceptual question", "C1.1", "P1", 2, "why does the count matter?"),
    ("confusion", "C1.2", "P1", 1, "i dont get what position 3 means"),
    ("another explanation", "C1.2", "P3", 2, "can you explain that another way"),
    ("another example", "C1.4", "P1", 1, "can you show another example?"),
    ("short acknowledgement", "C1.1", "P2", 3, "ok"),
    ("repeated question", "C1.4", "P1", 2, "why is the last bit counted?"),
    ("unrelated question", "C1.3", "P3", 1, "can you help with my statistics homework"),
    ("no response", "C1.2", "P2", 1, None),
]


@pytest.mark.parametrize("name,sub,ped,index,learner_text", SITUATIONS, ids=[x[0] for x in SITUATIONS])
def test_each_learner_situation_reaches_the_tutor_with_its_context_and_the_guidance_inside_the_pedagogy(name, sub, ped, index, learner_text):
    moves = contract()["subsections"][sub]["moves_by_pedagogy"][ped]
    move = moves[index]
    prior = [base.tutor("p", moves[index - 1]["id"], "An approved earlier explanation that carries comfortably more than fifteen ordinary words so that it counts as substantive.",
                        sub=sub, ped=ped),
             base.tutor("c", move["id"], "The first message of the current move, already delivered to the learner here.", sub=sub, ped=ped)]
    dialogue = prior + ([base.learner("l", learner_text)] if learner_text else [])
    text = prompt(move, index, dialogue, approved_move_message_ids={moves[index - 1]["id"]: ["p"]})
    data = payload(text)
    assert GUIDANCE_HEADING in text and data["pedagogy"] == ped and data["active_move"]["id"] == move["id"]
    assert data["learner_question_text_if_any"] == (learner_text or None)
    assert data["conversation_context"]["previous_move_closing"].startswith("An approved earlier explanation")
    assert data["conversation_context"]["previous_move_id"] == moves[index - 1]["id"]
    assert not re.search(r"later move|next move's", json.dumps(data["verified_facts_for_this_turn"]))


# ====================================================================================================
# 2. SCRIPTED: revision, flag and lifecycle safeguards for Milestone 2
# ====================================================================================================
def test_a_v1_session_keeps_milestone_one_behaviour_exactly_after_the_milestone_two_code_exists():
    def body(room):
        snapshot = dict(room.db.get(base.Session, room.sid).runtime_config_snapshot)
        snapshot[SESSION_CONFIG_KEY] = CONVERSATION_CONTEXT_REVISION            # a session stamped before Milestone 2
        room.db.get(base.Session, room.sid).runtime_config_snapshot = snapshot
        room.db.commit()
        room.script(filler("C1.1-P1-M01"), filler("C1.1-P1-M02"))
        room.say(); room.next()
        call = room.say()
        assert GUIDANCE_HEADING not in call["system"] and "continuity" not in call["payload"]
        assert call["context"]["revision"] == CONVERSATION_CONTEXT_REVISION and "previous_subsection_topics" not in call["context"]
        row = room.db.scalars(select(LLMCall).where(LLMCall.session_id == room.sid, LLMCall.purpose == "TUTOR")
                              .order_by(LLMCall.started_at)).all()[-1]
        assert row.request_payload["audit"]["c1_conversation_context_revision"] == CONVERSATION_CONTEXT_REVISION
    with_room("P1", body)


def test_a_session_without_the_stamp_never_receives_guidance_even_after_a_restart():
    def body(room):
        room.script(filler("C1.1-P1-M01"), filler("C1.1-P1-M02"))
        room.say(); room.next()
        room.runtime, room.ai = base._stack(base.compile_v051(base.load_scientific_v051(base.SCIENTIFIC)), room.llm, True)
        call = room.say()
        assert GUIDANCE_HEADING not in call["system"] and call["context"] is None
        rows = room.db.scalars(select(LLMCall).where(LLMCall.session_id == room.sid, LLMCall.purpose == "TUTOR")).all()
        assert all("c1_conversation_context_revision" not in r.request_payload["audit"] for r in rows)
        assert all(GUIDANCE_HEADING not in r.compiled_prompt_text for r in rows)
    with_room("P1", body, on=False)


def test_v2_audit_identifies_the_revision_and_the_guidance_is_in_the_recorded_prompt():
    def body(room):
        room.script(filler("C1.1-P1-M01"))
        room.say()
        row = room.db.scalars(select(LLMCall).where(LLMCall.session_id == room.sid, LLMCall.purpose == "TUTOR")).one()
        assert row.request_payload["audit"]["c1_conversation_context_revision"] == CONVERSATION_CONTEXT_REVISION_V2
        assert GUIDANCE_HEADING in row.compiled_prompt_text
        judges = room.db.scalars(select(LLMCall).where(LLMCall.session_id == room.sid,
                                                       LLMCall.purpose == "CONVERSATION_JUDGE")).all()
        assert judges and all(GUIDANCE_HEADING not in j.compiled_prompt_text and
                              "c1_conversation_context_revision" not in j.request_payload["audit"] for j in judges)
    with_room("P1", body)


def test_boundary_topics_flow_end_to_end_only_into_the_first_move_of_the_next_subsection():
    def body(room):
        c11 = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"]
        room.script(*[filler(m["id"]) for m in c11], filler("C1.2-P1-M01"), filler("C1.2-P1-M02"))
        for i in range(len(c11)):
            room.say(); room.next()
        first = room.say()                                          # C1.2-P1-M01
        room.next()
        second = room.say()                                         # C1.2-P1-M02
        assert first["move"] == "C1.2-P1-M01" and second["move"] == "C1.2-P1-M02"
        topics = first["context"]["previous_subsection_topics"]
        assert topics["subsection_id"] == "C1.1" and "information data" in topics["topics_already_taught"]
        assert second["context"]["previous_subsection_topics"] == {"subsection_id": None, "topics_already_taught": []}
        # strict isolation is unchanged: no message text and no learner turn crosses the boundary
        assert first["context"]["previous_move_id"] is None and first["context"]["previous_move_closing"] == ""
        assert first["context"]["recent_learner_turns"] == [] and first["context"]["recent_tutor_openings"] == []
        assert not any(label in first["system"] for label in ("sent", "receiver view", "instructor view")
                       if label in topics["topics_already_taught"])
    with_room("P1", body)


def test_boundary_topics_never_cross_between_two_sessions_or_attempts():
    db = base._db()
    try:
        compiled, version = base._world(db)
        llm = TranscriptLLM()
        runtime, ai = base._stack(compiled, llm, False)
        sessions = {}
        for who in ("A", "B"):
            sessions[who] = base.stamp_revision(db, runtime.create_v051_internal_test_session(
                db, version.id, unified_controlled_study=True, initial_pedagogy_id="P1", c1_conversation_context=True).id,
                CONVERSATION_CONTEXT_REVISION_V2)
        c11 = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P1"]
        for who in ("A", "B"):                         # A completes C1.1; B stays in its first move
            llm.script[who] = [filler(m["id"]) for m in c11] + [filler("C1.2-P1-M01")]
        for i in range(len(c11)):
            llm.who = "A"
            asyncio.run(ai.execute(db, ai.reserve_tutor(db, sessions["A"])))
            a = db.scalar(select(SubsectionProgress).where(SubsectionProgress.session_id == sessions["A"],
                                                           SubsectionProgress.status == "ACTIVE"))
            db.refresh(a)
            runtime.continue_controlled_c11_move(db, sessions["A"], state(a)["approval_version"])
        llm.who = "B"
        asyncio.run(ai.execute(db, ai.reserve_tutor(db, sessions["B"])))
        llm.who = "A"
        asyncio.run(ai.execute(db, ai.reserve_tutor(db, sessions["A"])))
        b_call = next(c for c in llm.calls if c["who"] == "B")
        a_last = [c for c in llm.calls if c["who"] == "A"][-1]
        assert b_call["move"] == "C1.1-P1-M01" and b_call["context"]["previous_subsection_topics"]["topics_already_taught"] == []
        assert a_last["move"] == "C1.2-P1-M01" and a_last["context"]["previous_subsection_topics"]["topics_already_taught"]
    finally:
        base._close_db(db)


def test_c2_c3_c4_prompts_remain_byte_identical_in_a_v2_session(monkeypatch):
    """Run a complete C1-C4 course in a V2 session. Only C1 Tutor calls may carry guidance or context."""
    import test_unified_c1_c4_sqlite_runtime as harness
    original = base.SessionRuntime.create_v051_internal_test_session

    def stamped_v2(self, db, *a, **k):
        session = original(self, db, *a, c1_conversation_context=True, **k)
        base.stamp_revision(db, session.id, CONVERSATION_CONTEXT_REVISION_V2)
        return session
    monkeypatch.setattr(harness, "_ScriptedLLM", base._RecordingLLM)
    monkeypatch.setattr(base.SessionRuntime, "create_v051_internal_test_session", stamped_v2)
    db = base._db()
    try:
        harness._run_complete_study(db, "P2")
        seen = {}
        for call in db.scalars(select(LLMCall).where(LLMCall.purpose == "TUTOR")).all():
            section = call.request_payload["audit"]["pilot_move_id"][:2]
            marked = GUIDANCE_HEADING in call.compiled_prompt_text
            seen.setdefault(section, set()).add(marked)
            assert marked == (section == "C1") and ("conversation_context" in call.compiled_prompt_text) == (section == "C1")
        assert seen == {"C1": {True}, "C2": {False}, "C3": {False}, "C4": {False}}
    finally:
        base._close_db(db)
