"""Pure C3 isolated-pilot prompt builders; the shared execution engine stays shared."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from solo_harness.runtime.controlled_executor import contract, contract_hash
from solo_harness.runtime.controlled_unified_prompts import _dialogue_for_move, _selected_facts
from solo_harness.runtime.v051_conversation import ConversationJudgeOutput, V051TutorOutput

PILOT_VERSION = "C3_ISOLATED_PROMPT_SEPARATION_V1"
P2_STAGES = ("QUESTION", "HINT_1", "HINT_2", "FINAL")
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[’'-][A-Za-z0-9]+)*")


class C3GuidedFinalInconsistent(RuntimeError):
    """A forced FINAL must use the existing Tutor readiness flag."""
_C31_M01_COMPLETION = (
    "Tutor distinguishes the six data cells from the six checking cells, explains "
    "that all seven complete row/column checks initially pass, and explains why "
    "overlapping row and column checks matter. The highlighted data cell and corner "
    "remain scientifically correct verified visual facts; spoken coordinate recital is not required."
)

TUTOR_RULES = """Teach only the current C3 move using the verified example shown. Speak to a learner who recently completed Class 12. Use short, direct sentences. Explain why the important checks pass or fail, rather than repeating every bit and label from the grid. Do not add introductions that teach nothing. Keep ordinary teaching within the word limit supplied for this move and stage; shorter is fine.

In C3.1, start with known bit changes and explain their effect on row and column checks. In C3.2, start with the checks the receiver can see and explain only what those checks support. The receiver cannot see the original sent grid. Passing checks do not prove no changes occurred. Avoid claims that an exact error history was proved by the results.

For Worked Examples, demonstrate the complete example: give the results and explain why. Do not ask the learner to supply an answer. For Contrasting Cases, explain both cases, what is the same, what differs, and why that changes the result. Do not turn either pedagogy into a required quiz. If an authored goal says to name or identify a result, that directs your explanation, not a learner request.

For Guided Questioning, the backend stage records what was last delivered: QUESTION, HINT_1, HINT_2, or FINAL; it does not predetermine your next response. At QUESTION with no pending learner reply, ask the one authored question without revealing its answer. When a learner reply is pending, including while the persisted stage is QUESTION, do not repeat the question: interpret the reply using the actual question, verified facts, and current-move dialogue. If the answer is adequate, acknowledge it, give the final explanation, and return ready_for_judge=true. Otherwise give the targeted authored hint and return ready_for_judge=false. At a HINT stage, use the learner's actual statement to address its specific gap. Use the authored hint as a guide, not as a reason to ignore the learner's actual answer. Do not say 'exactly', 'correct', 'spot on' or equivalent for the whole answer while still in a HINT stage. A learner asking 'what?' or proposing bit locations deserves a concrete explanation of how those proposed locations affect the observed checks. Do not state the complete target answer at either hint stage. In C3.2 P2 M05, do not tell the learner to assume exactly one error during a hint: reserve that condition for FINAL. C3.1 hints must not give the requested PASS/FAIL results prematurely. C3.2 hints may keep the observed checking results visible, but must not reveal a proposed change history before FINAL. Hint 2 may be more specific than Hint 1 but must still require learner reasoning. At FINAL, explain the correct reasoning even if the learner remains wrong. After two delivered hints, give the complete final explanation and return ready_for_judge=true. Do not require a correct learner answer, a mastery check, an extra confirmation answer, or a new question after an adequate answer. For receiver-evidence lessons, distinguish a candidate location from a uniquely justified correction and scope claims to these parity checks; do not imply every error-correcting method has the same limitations. A Judge repair is a final-delivery repair only and must not reopen learner-answer assessment.

Use natural wording such as "row 1, column 2" instead of internal codes. Do not mention study contracts, internal stages, visual mode names or the Judge. Do not introduce a new bit grid or later subsection content. When a learner asks an ordinary doubt, address that doubt rather than repeating the whole lesson.

The diagram shows verified facts. Your words must explain the relationship needed for the current move; do not assume a diagram alone counts as teaching."""

# CHANGED: Additional decision discipline is only appended to P2 MOVE Tutor prompts.
P2_TUTOR_DECISION_CHECK = (
    "For Guided Questioning, decide response sufficiency BEFORE drafting learner_message. "
    "Judge the substance against exactly what the authored question asks, using the whole current-move dialogue. "
    "A tentative or uncertain-sounding answer that gives the requested idea is sufficient; do not demand "
    "confident wording, repeated confirmation, or an unasked explanation. An answer that gets one "
    "requested part right but gives another requested part incorrectly is not yet sufficient: acknowledge "
    "the correct part and use a targeted hint for the gap, unless the learner explicitly requests the "
    "solution or two hints have already been delivered. Do not use the need for a full final explanation "
    "as a reason to skip hints after an incorrect or incomplete answer. When returning ready_for_judge=false, "
    "write a genuine hint that leaves the answer to the authored question for the learner to infer: "
    "do not say the target PASS/FAIL result, error count, assumption, or a directly equivalent conclusion. "
    "A hint may direct attention to how to reason, but must not supply the decisive conclusion. "
    "When returning ready_for_judge=true, give the complete correct explanation in the same response. "
    "These rules apply to every C3 Guided Questioning move; they do not add a learner mastery gate."
)

JUDGE_P2_RULES = """Judge the entire learner-visible Tutor dialogue for the active move, not only its last message, hidden scientific facts, or a diagram alone. Preserve all existing scientific correctness rules and the distinction between C3.1 (known changes to outcomes) and C3.2 (observed outcomes to possible explanations). Reject unresolved scientific errors, misleading learner feedback, or teaching that introduces the next move. An explicit accurate correction may resolve an earlier Tutor mistake.

For Worked Examples and Contrasting Cases, require demonstrated or comparative teaching, not a mandatory learner answer. Reject a C3.1 count that treats the corner as separate from the six checking cells, and reject a claim that one failed check establishes an intersection. Do not require learner mastery.

For Guided Questioning, verify that the learner had an opportunity to answer the authored question before the final answer. If a learner was wrong or unsure, the Tutor should offer an appropriate first hint, allow another attempt, then offer a different second hint if still needed. After the final learner attempt, or if the learner explicitly asks for the solution, the Tutor should give the full correct explanation. A correct reply needs no hint. At HINT stages, reject feedback that falsely describes an incomplete answer as wholly correct, repeats an already established component, or reveals the answer. For C3.2 P2 M05, reject an HINT that directly tells the learner to assume exactly one error. A short yes/no answer is sufficient when the authored question asks only for yes/no; do not demand an unasked explanation. Learner correctness is never an approval or progression requirement.

Judge the final Tutor explanation for the required scientific relationships. A concise correct explanation is sufficient; do not require extra narration, repeated coordinate statements, or a mastery check. Check for premature answer reveals and incorrect hints. The backend, not the Judge, owns the stage counter and visual reveal state.

C3.1 P1 M01: Verify that the Tutor distinguishes six data cells from six checking cells, explains that row and column checks overlap, and establishes all seven initial passing checks. The highlighted data cell and corner bit must be scientifically correct in the verified diagram, but the Tutor does not need to repeat their coordinate labels to prove the overlap."""


# CHANGED: Extra P2-only fidelity lens; the approved JUDGE_P2_RULES above is unchanged.
P2_JUDGE_SEQUENCE_CHECK = (
    "For this Guided Questioning move, verify instruction order as well as final scientific accuracy. "
    "Read the authored question, each learner reply, and the next Tutor message together. "
    "A wrong or incomplete reply followed immediately by the complete solution, while a hint was still "
    "available and the learner had not requested the solution, is not compliant Guided Questioning. "
    "An answer containing the requested correct idea remains sufficient even when phrased as a guess "
    "or uncertainty; do not require an additional learner confirmation. "
    "A HINT must not say or directly entail the requested answer, even if it otherwise explains correct science. "
    "Do not infer that a hint was appropriate simply because a final explanation followed. "
    "When a violation is present, do not ADVANCE solely because FINAL is scientifically correct; "
    "use CONTINUE with specific achievable repair guidance, without asking the learner another question. "
    "A later final repair can acknowledge and accurately correct earlier misleading teaching, but it cannot "
    "pretend a previously revealed hint was sound; do not demand a retroactive hint or learner reenactment. "
    "Retain the existing scientific criteria and no-mastery-gate rule."
)

@lru_cache(maxsize=1)
def _overlay() -> dict:
    path = Path(__file__).parent.parent / "studies" / "controlled_c3_isolated_pilot_overlay_v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    authored = {item["move_id"]: item for item in data.get("moves", [])}
    contract_moves = {move["id"]: move for cell in contract("C3")["subsections"].values()
                      for moves in cell["moves_by_pedagogy"].values() for move in moves}
    if set(authored) != set(contract_moves) or len(authored) != 30:
        raise ValueError("C3 isolated-pilot overlay must cover exactly the current 30 C3 moves")
    for move_id, item in authored.items():
        source = contract_moves[move_id]
        if (item["pedagogy"] != move_id.split("-")[1]
                or item["visual_mode"] != (source.get("visual") or {}).get("mode")
                or item["required_content_refs"] != source["required_content_refs"]):
            raise ValueError("C3 isolated-pilot overlay differs from the authored C3 contract: " + move_id)
        if item["pedagogy"] == "P2":
            if not all(item.get(key) for key in ("guided_question", "hint_1", "hint_2", "stage_word_caps")):
                raise ValueError("C3 P2 overlay lacks approved guidance: " + move_id)
        elif not isinstance(item.get("normal_delivery_word_cap"), int):
            raise ValueError("C3 non-P2 overlay lacks a delivery cap: " + move_id)
    return authored


def pilot_enabled(session, progress) -> bool:
    snapshot = getattr(session, "runtime_config_snapshot", None) or {}
    return bool(progress and getattr(progress, "subsection_id", "").startswith("C3.")
                and snapshot.get("internal_v051_testing") is True
                and snapshot.get("c3_isolated_pilot_version") == PILOT_VERSION)


def new_guided_state(move_id: str) -> dict:
    return {"move_id": move_id, "stage": "QUESTION", "hint_count": 0,
            "question_visual_message_id": None, "complete_visual_message_id": None}


def guided_delivery_stage(stage: str, hint_count: int, has_learner_reply: bool,
                          tutor_ready_for_judge: bool) -> str:
    """Resolve delivery only from the existing Tutor flag and the persisted two-hint bound."""
    if stage not in P2_STAGES or hint_count not in (0, 1, 2):
        raise ValueError("invalid persisted C3 guided state")
    if stage == "FINAL":  # CHANGED: Judge repair stays FINAL even without a new learner reply.
        if not tutor_ready_for_judge:
            raise C3GuidedFinalInconsistent("C3 FINAL Tutor delivery must set ready_for_judge=true")
        return "FINAL"
    if not has_learner_reply:  # CHANGED: initial question cannot declare completion.
        if tutor_ready_for_judge:
            raise C3GuidedFinalInconsistent("C3 QUESTION Tutor delivery must set ready_for_judge=false")
        return "QUESTION"
    if hint_count >= 2:  # CHANGED: two delivered hints require actual Tutor readiness.
        if not tutor_ready_for_judge:
            raise C3GuidedFinalInconsistent("C3 FINAL Tutor delivery must set ready_for_judge=true")
        return "FINAL"
    if tutor_ready_for_judge:
        return "FINAL"
    return "HINT_1" if hint_count == 0 else "HINT_2"


def _overlay_move(move: dict) -> dict:
    if not move["id"].startswith("C3."):
        raise ValueError("C3 isolated-pilot prompt used outside C3")
    return _overlay()[move["id"]]


def learner_message_word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def learner_message_word_cap(move: dict, stage: str | None) -> int:
    overlay = _overlay_move(move)
    if overlay["pedagogy"] != "P2":
        return overlay["normal_delivery_word_cap"]
    if stage not in P2_STAGES:
        raise ValueError("C3 P2 word cap requires a guided stage")
    return overlay["stage_word_caps"][stage.lower() if stage != "FINAL" else "final_explanation"]


def word_limit_rewrite_instruction(word_count: int, cap: int, previous_output: dict,  # CHANGED
                                   delivery_stage: str | None = None) -> str:
    if delivery_stage is None:  # CHANGED: Keep the existing P1/P3 rewrite prompt exactly.
        return ("[C3_WORD_LIMIT_REWRITE]\nYour previous learner_message had "
                f"{word_count} words; this stage has a hard maximum of {cap}. "
                "Return a shorter, scientifically complete learner_message only in the same JSON schema. "
                "Do not truncate a sentence or omit a required scientific relationship.\n"
                "[PREVIOUS_STRUCTURED_TUTOR_RESPONSE]\n"
                + json.dumps(previous_output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    # CHANGED: P2 word-count repair may shorten prose, never change semantic delivery.
    readiness = previous_output["ready_for_judge"]
    purpose = ("This is a HINT: retain a targeted clue, not the requested answer or full explanation. "
               if delivery_stage in ("HINT_1", "HINT_2") else
               "This is a FINAL: retain the essential correct explanation. "
               if delivery_stage == "FINAL" else
               "Preserve the original question or teaching purpose. ")
    return ("[C3_WORD_LIMIT_REWRITE]\nYour previous learner_message had "
            f"{word_count} words; this delivery has a hard maximum of {cap}. "
            + purpose
            + f"Keep ready_for_judge exactly {str(readiness).lower()}; do not reconsider answer adequacy, "
              "teaching stage, or hint versus final choice. Shorten learner_message only. "
              "Do not invent facts, state an answer during a hint, truncate sentences, "
              "or omit a required relationship from a FINAL explanation.\n"
            "[PREVIOUS_STRUCTURED_TUTOR_RESPONSE]\n"
            + json.dumps(previous_output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _p2_stage(move: dict, dialogue: list[dict], stage: str | None) -> str | None:
    if move["learner_response_policy"] != "guided":
        return None
    resolved = stage or ("FINAL" if any(row["role"] == "LEARNER" for row in _dialogue_for_move(dialogue, move["id"])) else "QUESTION")
    if resolved not in P2_STAGES:
        raise ValueError("invalid C3 P2 stage")
    return resolved


def _tutor_move(move: dict, overlay: dict, stage: str | None, hint_count: int,
                has_learner_reply: bool) -> dict:
    active = {"id": move["id"], "pedagogy": overlay["pedagogy"], "tutor_goal": overlay["tutor_goal"],
              "guided_question": overlay.get("guided_question"), "stage": stage,
              "word_cap": overlay["normal_delivery_word_cap"] if stage is None else None}
    if stage:
        active.update({"hint_count_already_delivered": hint_count,
                       "learner_reply_pending_evaluation": has_learner_reply,
                       "stage_word_caps": overlay["stage_word_caps"]})
        if stage != "FINAL" and has_learner_reply and hint_count < 2:
            active["authored_hint_if_needed"] = overlay["hint_1" if hint_count == 0 else "hint_2"]
        if stage == "FINAL" or (has_learner_reply and hint_count >= 2):
            active["final_explanation_required"] = True
    if move["id"] == "C3.2-P2-M02":
        active["move_specific_guard"] = "The two displayed examples have different observed checking results; do not claim they produce the same checking pattern. Accept any single same-row explanation using columns 1 and 2, not only row 1."  # CHANGED
    if move["id"] == "C3.1-P3-M05":
        active["move_specific_guard"] = "Make the synthesis recognizably contrastive: briefly compare the same-row and distributed two-change cases before stating the shared parity rule."  # CHANGED
    return active


def _judge_requirements(move: dict, overlay: dict) -> dict:
    requirements = {"id": move["id"], "pedagogy": overlay["pedagogy"], "required_concepts": {
        ref: contract("C3")["subsections"][move["id"].split("-")[0]]["content_reference_legend"][ref]
        for ref in move["required_content_refs"]},
        "completion_evidence": _C31_M01_COMPLETION if move["id"] == "C3.1-P1-M01" else move["completion_evidence"],
        "source_instructional_action": move["source_instructional_action"],
        "authored_guided_question": overlay.get("guided_question"),
        "approved_hints": [overlay["hint_1"], overlay["hint_2"]] if overlay["pedagogy"] == "P2" else []}
    if move["id"] == "C3.2-P2-M02":
        requirements["move_specific_guard"] = "The two displayed examples have different observed checking results; flag any claim that they produce the same checking pattern."
    return requirements


def tutor_prompt(compiled, context, dialogue: list[dict], guidance, instance, move: dict, index: int,
                 verified_learner_reply=None, *, response_mode="MOVE", pending_doubt=None,
                 p2_stage: str | None = None, p2_hint_count: int = 0,
                 has_learner_reply: bool = False) -> str:
    if response_mode not in ("MOVE", "DOUBT") or (response_mode == "DOUBT" and not pending_doubt):
        raise ValueError("invalid C3 isolated-pilot Tutor response mode")
    overlay = _overlay_move(move)
    scoped = _dialogue_for_move(dialogue, move["id"])
    stage = _p2_stage(move, dialogue, p2_stage)
    payload = {"pilot_version": PILOT_VERSION, "source_contract_sha256": contract_hash(_progress_for(move)),
               "active_move": _tutor_move(move, overlay, stage, p2_hint_count, has_learner_reply),
               "verified_facts_for_active_move_only": _selected_facts(move),
               "current_move_dialogue": scoped, "response_mode": response_mode,
               "pending_post_approval_doubt": pending_doubt,
               "judge_repair_guidance_if_any": (guidance or {}).get("next_allowed_instruction")
                   if (guidance or {}).get("last_action") == "CONTINUE" else None,
               "runtime_rules": {"no_mastery_gate": True, "visuals_server_owned": True,
                                 "backend_enforces_ordinary_word_cap": True,
                                 "tutor_interprets_learner_reply": True}}
    # CHANGED: P1/P3 and P2 doubt prompts retain their existing Tutor rules exactly.
    p2_decision_check = ("\n\n" + P2_TUTOR_DECISION_CHECK
                         if overlay["pedagogy"] == "P2" and response_mode == "MOVE" else "")
    return ("You are EkagraAI's isolated C3 pilot Tutor.\n" + TUTOR_RULES + p2_decision_check
            + "\n[ISOLATED_C3_TUTOR_CONTEXT]\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n[OUTPUT_SCHEMA]\n" + json.dumps(V051TutorOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))


def judge_prompt(compiled, context, dialogue: list[dict], instance, move: dict, index: int,
                 last_move: bool, prior_evidence: dict, *, review_mode="MOVE_REVIEW", pending_doubt=None) -> str:
    if review_mode not in ("MOVE_REVIEW", "DOUBT_REVIEW") or (review_mode == "DOUBT_REVIEW" and not pending_doubt):
        raise ValueError("invalid C3 isolated-pilot Judge review mode")
    overlay = _overlay_move(move)
    payload = {"pilot_version": PILOT_VERSION, "judge_requirements": _judge_requirements(move, overlay),
               "verified_facts_FOR_REVIEW_NOT_PROOF": _selected_facts(move),
               "learner_visible_current_move": _dialogue_for_move(dialogue, move["id"]),
               "review_mode": review_mode, "pending_doubt": pending_doubt,
               "last_move_of_subsection": last_move,
               "prior_approved_move_ids": sorted(prior_evidence) if last_move else []}
    rules = """You are EkagraAI's independent isolated C3 Conversation Judge. Review actual learner-visible Tutor delivery, not learner mastery. The verified facts are reference only, never proof of what the Tutor said. Check every detailed completion requirement and scientific claim against the active verified facts. Require concise repair when an obligation is missing or wrong; do not require a mastery check, filler, or verbatim authored wording. HOLD is only for genuine scientific or safety uncertainty."""
    # CHANGED: Add the sequence lens only for P2 move reviews, not P1/P3 or doubt review.
    sequence_check = ("\n\n" + P2_JUDGE_SEQUENCE_CHECK
                      if overlay["pedagogy"] == "P2" and review_mode == "MOVE_REVIEW" else "")
    return (rules + "\n\n" + JUDGE_P2_RULES + sequence_check + "\n[ISOLATED_C3_JUDGE_CONTEXT]\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n[OUTPUT_SCHEMA]\n" + json.dumps(ConversationJudgeOutput.model_json_schema(), sort_keys=True, separators=(",", ":")))


def _progress_for(move):
    from types import SimpleNamespace
    return SimpleNamespace(subsection_id=move["id"].split("-")[0])
