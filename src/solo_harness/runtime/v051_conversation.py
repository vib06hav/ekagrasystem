"""Minimal semantic contracts and prompt assembly for the v0.5 candidate."""

from __future__ import annotations



import json

from typing import Literal



from pydantic import BaseModel, ConfigDict, Field





class _Wire(BaseModel):

    model_config = ConfigDict(extra="forbid", strict=True)





class ConversationJudgeOutput(_Wire):

    """The Judge makes the semantic decision; persistence owns its provenance."""

    decision: Literal["CONTINUE", "ADVANCE", "HOLD"]

    guidance: str = Field(min_length=1, max_length=4000)





class V051TutorOutput(_Wire):

    """Natural learner-facing instruction plus a non-authoritative review hint."""

    learner_message: str = Field(min_length=1, max_length=4000)

    ready_for_judge: bool = False





def v051_tutor_prompt(compiled, progress, context: dict, dialogue: list[dict], judge_guidance: dict | None, instructional_instance: dict | None = None) -> str:

    """Compile only the persisted candidate snapshot into a Tutor request."""

    payload = {

        "active_section_id": context["parent_cell"]["transition_id"],

        "active_subsection": context["subsection"],

        "global_pedagogy": context["global_pedagogy"],

        "section_pedagogy_cell": context["parent_cell"],

        "subsection_pedagogy_cell": context["child_cell"],

        "locked_knowledge": context["knowledge"],

        "scope_restrictions": context["restrictions"],

        "previous_conversation_judge_guidance": judge_guidance,

        "verified_instructional_instance": instructional_instance,

        "dialogue": dialogue,

        "runtime_rules": {"no_mastery_gate": True, "tutor_readiness_is_non_authoritative": True,

                          "judge_review_follows_tutor_readiness_without_mandatory_learner_turn": True,

                          "no_assessment_content_or_keys": True},

    }

    return (compiled.authored["v051"]["prompts"]["TUTOR_PROMPT.md"]

            + "\n\n[V051_ACTIVE_SUBSECTION_TUTOR_CONTEXT]\n"

            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

            + "\n\n[OUTPUT_SCHEMA]\n"

            + json.dumps(V051TutorOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))





def conversation_judge_prompt(compiled, progress, context: dict, dialogue: list[dict], instructional_instance: dict | None) -> str:

    payload = {

        "active_section_id": context["parent_cell"]["transition_id"], "active_subsection": context["subsection"],

        "global_pedagogy": context["global_pedagogy"], "section_pedagogy_cell": context["parent_cell"],

        "subsection_pedagogy_cell": context["child_cell"], "locked_knowledge": context["knowledge"],

        "restrictions": context["restrictions"], "verified_instructional_instance": instructional_instance,

        "dialogue": dialogue,

    }

    return (compiled.authored["v051"]["prompts"]["CONVERSATION_JUDGE_PROMPT.md"]

            + "\n\n[V051_CONVERSATION_JUDGE_CONTEXT]\n"

            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

            + "\n\n[OUTPUT_SCHEMA]\n"

            + json.dumps(ConversationJudgeOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))






def controlled_c1_tutor_prompt(compiled, context: dict, dialogue: list[dict], guidance: dict | None,
                               instructional_instance: dict | None, move: dict, index: int,
                               verified_learner_reply: dict | None = None, *,
                               response_mode: Literal["MOVE", "DOUBT"] = "MOVE",
                               pending_doubt: dict | None = None) -> str:
    """Prepare only verified active-move teaching context, for C1.1 through C1.4.

    Deliberately PURE: this function never schedules calls, advances a move,
    decides whether a guided answer was adequate, or decides a doubt is solved.
    These decisions belong to runtime orchestration and the Conversation Judge.
    """
    from solo_harness.runtime.controlled_c1_prompt_context import (
        validate_move, delivery_spec, selected_facts, previously_covered_topics,
        prior_facts_for_question, current_move_dialogue, latest_learner_text,
        learner_science_guard, execution_overlay_hash, conditional_prior_exchange,
    )
    from solo_harness.studies.controlled_c1 import contract_hash

    subsection, pedagogy = validate_move(move, index)
    if response_mode not in ("MOVE", "DOUBT"):
        raise ValueError("unsupported controlled C1 Tutor response mode")
    if response_mode == "DOUBT" and not isinstance(pending_doubt, dict):
        raise ValueError("post-approval doubt response requires its pending-doubt record")
    if instructional_instance is not None:
        if instructional_instance.get("subsection_id", subsection) != subsection or instructional_instance.get("pedagogy_id", pedagogy) != pedagogy:
            raise ValueError("persisted instructional instance does not match active C1 move")
        if instructional_instance.get("verified") is False:
            raise ValueError("unverified instructional instance not eligible for controlled C1")
    scoped = current_move_dialogue(dialogue, move["id"])
    spec = delivery_spec(move)
    guided = move["learner_response_policy"] == "guided"
    learner_after_question = any(item["role"] == "LEARNER" for item in scoped)
    first_guided = guided and not learner_after_question and response_mode == "MOVE"
    latest = (str(pending_doubt.get("text") or "") if response_mode == "DOUBT"
              else latest_learner_text(scoped))
    repairs = (guidance.get("next_allowed_instruction") if guidance and guidance.get("last_action") == "CONTINUE" else None)
    move_card = {
        "id": move["id"],
        "response_policy": move["learner_response_policy"],
        "teaching_goal": spec["focus"],
        "scope_avoidances": ("Do not reveal the answer before the learner has replied."
                             if first_guided else spec.get("avoid", "")),
        "guided_question": spec.get("guided_question") if guided else None,
        "small_prerequisite": bool(spec.get("micro_move")),
        "final_synthesis": bool(spec.get("final_consolidation")),
        "suggested_word_budget": spec.get("target_words", 32),
    }
    # This payload intentionally excludes exact_delivery, subsection plans,
    # full scientific knowledge, the original source action and future moves.
    payload = {
        "controlled_scope": "C1_ACTIVE_MOVE_ONLY",
        "prompt_revision": "C1_MOVE_SCOPED_FLEXIBLE_V3_2",  # CHANGED: V3.2 prompt policy version
        "source_contract_sha256": contract_hash(),
        "delivery_overlay_sha256": execution_overlay_hash(),
        "subsection": subsection,
        "pedagogy": pedagogy,
        "response_mode": response_mode,
        "first_move_of_subsection": index == 0,
        "active_move": move_card,
        "verified_facts_for_this_turn": selected_facts(move, first_guided_turn=first_guided),
        "previous_approved_topic_labels_only": previously_covered_topics(move, index),
        "current_move_dialogue_only": scoped,
        "prior_exchange_ONLY_for_conditional_misconception_check": conditional_prior_exchange(dialogue, move),
        "learner_question_text_if_any": latest or None,
        "small_related_science_guard_ONLY_for_expressed_question": learner_science_guard(move, latest) if latest else None,
        "previously_covered_facts_ONLY_for_learner_question": (
            prior_facts_for_question(move, index) if latest else None),
        "verified_learner_reply_fact_check": verified_learner_reply,
        "judge_repair_guidance_if_any": repairs,
        "pending_post_approval_doubt": pending_doubt if response_mode == "DOUBT" else None,
        "first_guided_question_turn": first_guided,
        "visible_example_labels_if_relevant": (
            {"Example A": "1", "Example B": "110"}
            if move["id"] == "C1.1-P2-M02" and not first_guided else None),
        "science_scope_guards": _controlled_c1_scope_guards(subsection),
        "runtime_rules": {
            "tutor_never_advances_moves": True,
            "next_only_on_learner_action_after_judge_approval": True,
            "no_mastery_or_assessment_gate": True,
            "no_unrequested_future_move_content": True,
            "visuals_are_backend_verified_and_frontend_owned": True,
        },
    }
    # CHANGED: V3.1 targeted general safeguards; preserve the existing wire schema.
    instructions = """
[CONTROLLED_C1_NATURAL_TUTOR_RULES_V3]
Teach a beginner with no assumed networking or bits background. Use simple,
connected English as a patient human teacher, not notes from an internal
lesson plan. Normally 2–3 SHORT sentences (roughly 20–35 words); a tiny
counting step can be one sentence. If a learner needs a real clarification,
answer accurately even if it requires a little more text; split long
answers into clear steps rather than using jargon. Avoid filler and
unnecessary repetition. Do not start with 'The learner has...',
'Before we continue, remember...', 'Conclude once...', 'Work one example...',
or any backend or teacher-directive phrasing.

Use active_move.teaching_goal and verified_facts_for_this_turn to decide
WHAT must be taught. These are internal facts, NOT text to copy. Compose
YOUR OWN explanation. Never recite JSON keys, meta-instructions, topic
labels or any system progress statement. The fixed scientific facts are
authoritative. Ground each claim and its implications in those facts;
do not invent values, causal explanations, or guarantees the facts do
not establish. Before agreeing with a learner's claim, check whether
it is correct; acknowledge the correct part and explicitly correct any
mistaken part instead of appearing to endorse it.
The simple bit patterns in this lesson represent agreed Yes/No answers,
not necessarily binary NUMBERS; a count of ones does not measure their
'numerical total value'. Only a legitimate learner question can warrant
brief related clarification outside this move. Never spontaneously teach
a later move or subsection, and never start C2's bit-flip count theorem.

On the FIRST move of EACH subsection, introduce the immediate topic and
its necessary terms before a technical demonstration or contrast. Do not
open as though the learner has already heard this new subsection. For P3,
make the contrast understandable before drawing its conclusion. For a
final synthesis, connect the central idea briefly; do not replay every
step or omit an explicitly required scientific qualifier.

P1 worked examples: demonstrate the required fixed example directly;
no mandatory learner response.
P2 guided moves: on the FIRST guided turn ask the SPECIFIC authored
active_move.guided_question without revealing its correct answer.
Set ready_for_judge=false while awaiting an answer. After a real learner
reply, respond to its meaning, acknowledge visual labels if used, then
explain the correct verified fact without requiring learner correctness.
If the learner interrupts with a QUESTION rather than attempting an
answer, answer THAT question directly and return to the SAME pending
guided question; do not treat the doubt itself as an answer or invent a
new quiz. Keep ready_for_judge=false if the original guided obligation
is still pending. An incorrect answer, uncertainty or 'I don't know'
may be handled with a brief explanation: NO learner mastery gate.
Non-guided explain/model/compare moves and conditional moves require
NO extra learner reply. For a conditional misconception-support move,
correct ONLY a misconception that appeared, otherwise briefly affirm
the needed principle without an artificial question.
P3 comparisons: keep the matching conditions clear and contrast only
the required cases. Do not turn comparison into forced questioning.

When the learner asks a question, answer its actual intent before
returning to pending instruction. If they ask WHY, give a verified
purpose or cause rather than restating WHAT happened. Correct false
premises directly, and acknowledge when the supplied facts do not
establish an explanation. 'We have not covered this' is not enough.
In DOUBT mode the move is already approved:
answer the latest pending doubt within that context, do not restart the
move, and request Judge review only after a complete answer. Do not ask
'Do you understand?', require a confirmation, mention Next/buttons,
backend IDs, judge decisions, or reveal assessments.

The Tutor's ready_for_judge is a non-authoritative REVIEW REQUEST. It
never advances the move. Reply only in the supplied JSON output schema.
"""
    return ("You are EkagraAI's controlled C1 Tutor. Follow only this active move.\n"
            + instructions + "\n[CONTROLLED_C1_CURRENT_TUTOR_CONTEXT_V3]\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n[OUTPUT_SCHEMA]\n"
            + json.dumps(V051TutorOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))


def _controlled_c1_scope_guards(subsection: str) -> list[str]:
    """Short prohibitions, not full next-move science or a second syllabus."""
    guards = {
        "C1.1": ["Yes/No bit positions indicate answer order, not numeric place values.",
                 "Do not treat the number of ones as the total numerical magnitude.",
                 "No encoding, binary arithmetic, bytes or transmission-error claim for two different answer sequences."],
        "C1.2": ["Flip is during transmission; sent 10110 → received 10010 changes the THIRD bit.",
                 "Receiver ordinarily does not possess original clean bits.",
                 "No software-bug, lost-packet or physical-channel mechanism explanations."],
        "C1.3": ["p is SYMBOLIC for an extra bit position, not a transmitted character nor a determined parity-bit value.",
                 "Do not claim checking information detects every possible data change; it can help reveal corruption but is no guarantee.",  # CHANGED: V3.2 scientific non-implication
                 "No concrete even/odd bit calculation in this subsection."],
        "C1.4": ["Parity count ALWAYS includes the appended/received parity bit.",
                 "A parity PASS does not prove error-free transmission.",
                 "Do not teach C2 theorem about odd/even NUMBERS OF FLIPPED BITS."],
    }
    return guards[subsection]


def controlled_c1_judge_prompt(compiled, context: dict, dialogue: list[dict], instructional_instance: dict | None,
                               move: dict, index: int, last_move: bool, previous_evidence: dict, *,
                               review_mode: Literal["MOVE_REVIEW", "DOUBT_REVIEW"] = "MOVE_REVIEW",
                               pending_doubt: dict | None = None) -> str:
    """Move fidelity + expressed doubt auditor; never starts the next move."""
    from solo_harness.runtime.controlled_c1_prompt_context import (
        validate_move, delivery_spec, selected_facts, current_move_dialogue,
        prior_facts_for_question, latest_learner_text, learner_science_guard,
        expressed_learner_questions, prior_approved_messages, execution_overlay_hash,
        conditional_prior_exchange,
    )
    from solo_harness.studies.controlled_c1 import contract_hash

    subsection, pedagogy = validate_move(move, index)
    if review_mode not in ("MOVE_REVIEW", "DOUBT_REVIEW"):
        raise ValueError("unsupported controlled C1 Judge review mode")
    if review_mode == "DOUBT_REVIEW" and not isinstance(pending_doubt, dict):
        raise ValueError("post-approval doubt review requires pending question")
    if instructional_instance is not None:
        if instructional_instance.get("subsection_id", subsection) != subsection or instructional_instance.get("pedagogy_id", pedagogy) != pedagogy:
            raise ValueError("Judge case does not match active C1 move")
    scoped = current_move_dialogue(dialogue, move["id"])
    spec = delivery_spec(move)
    latest = (str(pending_doubt.get("text") or "") if review_mode == "DOUBT_REVIEW"
              else latest_learner_text(scoped))
    judge_card = {
        "id": move["id"],
        "response_policy": move["learner_response_policy"],
        "required_content_refs": move["required_content_refs"],
        "teaching_goal": spec["focus"],
        "original_completion_evidence": move["completion_evidence"],
        "critical_checks_must_be_visible_not_assumed": spec["critical_checks"],
        "required_guided_question": spec.get("guided_question") if move["learner_response_policy"] == "guided" else None,
        "allow_brief_micro_move": spec.get("micro_move", False),
        "final_synthesis": spec.get("final_consolidation", False),
    }
    payload = {
        "controlled_scope": "C1_ACTIVE_MOVE_ONLY",
        "prompt_revision": "C1_MOVE_SCOPED_FLEXIBLE_V3_2",  # CHANGED: V3.2 prompt policy version
        "source_contract_sha256": contract_hash(),
        "delivery_overlay_sha256": execution_overlay_hash(),
        "review_mode": review_mode,
        "subsection": subsection,
        "pedagogy": pedagogy,
        "first_move_of_subsection": index == 0,
        "active_move": judge_card,
        "verified_facts_FOR_REVIEW_NOT_PROOF_OF_DELIVERY": selected_facts(move),
        "current_move_learner_visible_dialogue_ONLY_EVIDENCE": scoped,
        "prior_exchange_ONLY_for_conditional_misconception_check": conditional_prior_exchange(dialogue, move),
        "expressed_learner_questions_to_evaluate": expressed_learner_questions(scoped),
        "pending_post_approval_doubt": pending_doubt if review_mode == "DOUBT_REVIEW" else None,
        "relevant_background_ONLY_to_review_asked_question": (
            prior_facts_for_question(move, index) if latest else None),
        "science_guard_ONLY_if_question_asked": learner_science_guard(move, latest) if latest else None,
        "scientific_nonimplications": _controlled_c1_scope_guards(subsection),
        "last_move_requires_subsection_coverage_review": bool(last_move and review_mode == "MOVE_REVIEW"),
        "previous_approved_move_evidence": previous_evidence if last_move and review_mode == "MOVE_REVIEW" else None,
        "previous_approved_tutor_messages": (
            prior_approved_messages(dialogue, previous_evidence)
            if last_move and review_mode == "MOVE_REVIEW" else None),
    }
    # CHANGED: V3.1 targeted general safeguards; preserve the existing wire schema.
    instructions = """
[CONTROLLED_C1_EVIDENCE_BASED_JUDGE_RULES_V3]
You are an independent auditor of INSTRUCTIONAL DELIVERY, not student
mastery. Fixed facts and the active contract define what must be taught.
The verified facts in your context are REFERENCE MATERIAL, NOT evidence
that the Tutor actually spoke those words. Do not infer that a required
fact was explained just because it appears in the prompt, a visual, the
contract or a past move. Check the actual learner-visible Tutor messages.
For the final move, use separately approved previous-move evidence for
subsection coverage, but require THIS move's own specified conclusion
explicitly in this move. A short natural paraphrase is acceptable;
no particular sentence must be copied.

Before deciding, verify EVERY mandatory critical check
against learner-visible teaching; topic-level relevance or implied coverage is
not enough. A missing required definition, example, or contrast needs
a focused CONTINUE repair. Also check scientific accuracy including
contradictory acknowledgments, the assigned P1/P2/P3 mechanism, unanswered learner questions, and unfinished
required interactions.
A correct later explanation does not erase an earlier misleading
agreement with an incorrect learner claim. A required contrast needs
both cases actually explained. Review the entire active-move exchange:
do not claim a guided question was absent when it is visible earlier.

Special scientific safeguards: C1.1 counting ones is for later checking,
NOT computing or comparing the sequence's 'total numerical values'.
The original order of answers is NOT binary numeral weighting.
For C1.2, a 10110-to-10010 example changes position 3, and the receiver
normally lacks the clean original. For C1.3, p is ONLY a symbolic bit
position, not an actual transmitted letter or already chosen 0/1.
For C1.4, count the parity bit in the COMPLETE frame; a passing parity
check does NOT guarantee no error. Do not approve C2 bit-flip number
laws being taught unsolicited in C1.

For WHY questions, a restatement of the procedure or definition
is not a purpose or cause. Do not treat a reply as resolved unless it
addresses the question using supported facts; if relevant information
is outside the current move, a minimal accurate clarification is fine.
A refusal based solely on the lesson boundary is not a resolution.
If one learner question is left unanswered, a later correct
response to the original guided question does NOT erase that omission.

A guided move requires its authored question, one genuine learner
answer attempt (including 'I don't know'), accurate Tutor follow-through,
and the required move content. If the Tutor explains the correct answer
after a wrong attempt, that learner interaction is COMPLETE: do NOT
require a second attempt, confirmation, or proof of understanding. If
required teaching is missing, request THAT repair without another learner
quiz. A learner QUESTION interrupting a pending guided question is not
itself an answer attempt; preserve the original question until handled.
Conditional, explain, model, and compare moves require no extra reply.

A missing important fact, unsupported inference, scientific mistake,
missing response to an expressed doubt, or unfinished guided teaching
requires CONTINUE with brief SPECIFIC corrective guidance. Do NOT use
CONTINUE for a merely awkward but correct style issue, which would cause
unnecessary repeat teaching; report the style issue in ADVANCE guidance.
HOLD only for genuinely unrecoverable/unsafe problems, not normal doubt.
Do not mistake brevity for missing teaching: one sentence can meet a
micro-move. First-move opening must introduce the necessary terms before
a comparison; do not approve a confusing, unexplained opening.

MOVE_REVIEW: ADVANCE means teaching is complete and conversation is ready
for a learner-controlled Next action. It does NOT authorize automatically
sending the next Tutor message. Any unanswered learner question blocks.
DOUBT_REVIEW: the move was ALREADY approved. Judge ONLY the precise pending
post-approval doubt and its Tutor response. ADVANCE returns to approved-
awaiting-Next without re-crediting or skipping the move; no learner
confirmation required. For a weak/scientifically wrong answer, CONTINUE
and request a small direct repair.
Return ONLY the schema's decision and specific concise guidance.
"""
    return ("You are EkagraAI's independent controlled C1 Conversation Judge.\n" + instructions
            + "\n[CONTROLLED_C1_CURRENT_JUDGE_CONTEXT_V3]\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            + "\n[OUTPUT_SCHEMA]\n"
            + json.dumps(ConversationJudgeOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))


def controlled_c11_tutor_prompt(compiled, context: dict, dialogue: list[dict], guidance: dict | None,
                                 instructional_instance: dict, move: dict, index: int,
                                 verified_learner_reply: dict | None = None, *,
                                 response_mode: Literal["MOVE", "DOUBT"] = "MOVE",
                                 pending_doubt: dict | None = None) -> str:
    """Backward-compatible C1.1 entry point; unchanged arguments for current runtime."""
    if not move["id"].startswith("C1.1-"):
        raise ValueError("C1.1 compatibility entry point used with different subsection")
    return controlled_c1_tutor_prompt(compiled, context, dialogue, guidance, instructional_instance,
                                      move, index, verified_learner_reply,
                                      response_mode=response_mode, pending_doubt=pending_doubt)


def controlled_c11_judge_prompt(compiled, context: dict, dialogue: list[dict], instructional_instance: dict,
                                 move: dict, index: int, last_move: bool, previous_evidence: dict, *,
                                 review_mode: Literal["MOVE_REVIEW", "DOUBT_REVIEW"] = "MOVE_REVIEW",
                                 pending_doubt: dict | None = None) -> str:
    """Backward-compatible C1.1 entry point; Judge still only authorizes Next."""
    if not move["id"].startswith("C1.1-"):
        raise ValueError("C1.1 compatibility entry point used with different subsection")
    return controlled_c1_judge_prompt(compiled, context, dialogue, instructional_instance,
                                      move, index, last_move, previous_evidence,
                                      review_mode=review_mode, pending_doubt=pending_doubt)
