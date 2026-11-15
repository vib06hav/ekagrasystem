"""Candidate v0.5 four-item construction on the existing persisted LLM path.

The source snapshot supplies every item contract.  This module only realizes a
fresh, small oracle-checked instance, asks the normal writer/reviewer roles for
learner wording, and freezes the resulting public/private package upstream.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

from solo_harness.runtime.ai import CanonicalMessage
from solo_harness.runtime.native_assessment import (
    RecordedResult, ScientificReviewHold, validate_mcq, validate_subjective,
)
from solo_harness.runtime.native_contracts import MCQProse, SemanticReview, SubjectiveProse, SubjectiveReview
from solo_harness.runtime.v051_judge import V05SubjectiveJudgment
from solo_harness.studies.v051_scenarios import resolve_v051_typed_case, scientific_case_fingerprints


def _compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fresh_verified_case(compiled, contract: dict, seed: int | None = None) -> dict:
    """Resolve a slot through its typed policy, never through family defaults."""
    return resolve_v051_typed_case(compiled, contract["id"], seed)


def _messages(compiled, contract, case, schema, role, rendered=None):
    source = compiled.authored["v051"]
    prompt_name = "ASSESSMENT_GENERATION_PROMPT.md" if role == "ASSESSMENT_WRITER" else "SEMANTIC_REVIEW_PROMPT.md"
    payload = {"item_contract": contract, "verified_scenario": case["public"] if role == "ASSESSMENT_WRITER" else case, "learner_facing_proposal": rendered,
               "source_protocol": source["scientific"]["protocol.yaml"], "source_scenario_rules": source["scientific"]["scenario_rules.yaml"],
               "rules": "Use exactly this contract and verified scenario. Do not invent facts; reject ambiguity, wrong scope, or non-unique MCQ keys."}
    return (CanonicalMessage(role="system", content=source["prompts"][prompt_name] + "\n\n[V051_ASSESSMENT_CONTEXT]\n" + _compact(payload) + "\n\n[OUTPUT_SCHEMA]\n" + _compact(schema.model_json_schema())),)


async def construct_v051_assessment(compiled, blueprint: dict, invoke, checkpoint, completed=None, prior_instructional_fingerprints=None):
    """Construct/recover a source-contract-driven 3-MCQ + subjective package."""
    slots = blueprint.get("v051_item_contracts", [])
    if len(slots) != 4 or [item.get("type") for item in slots] != ["MCQ", "MCQ", "MCQ", "SUBJECTIVE"]:
        raise ValueError("invalid v0.5 four-item blueprint")
    accepted = dict(completed or {})
    excluded = set(prior_instructional_fingerprints or ())
    # Recovered checkpoints count as already exposed assessment cases as well.
    seen = set()
    for record in accepted.values():
        case = record.get("case", {})
        if case.get("cases"):
            seen.update(scientific_case_fingerprints(case["cases"]))
    for index, contract in enumerate(slots, 1):
        label = f"MCQ{index}" if contract["type"] == "MCQ" else "SUB1"
        if label in accepted: continue
        hold = "no acceptable semantic review"
        for retry in range(2):
            case = fresh_verified_case(compiled, contract)
            fingerprints = set(scientific_case_fingerprints(case["cases"]))
            if fingerprints & excluded:
                hold = "assessment case collided with recorded instructional example"; continue
            if fingerprints & seen:
                hold = "assessment case reused an earlier item in this assessment"; continue
            schema = MCQProse if contract["type"] == "MCQ" else SubjectiveProse
            writer = await invoke("ASSESSMENT_WRITER", _messages(compiled, contract, case, schema, "ASSESSMENT_WRITER"), schema, {"v051": True, "blueprint_id": blueprint["id"], "slot_id": contract["id"], "attempt": retry + 1})
            if not isinstance(writer, RecordedResult) or not isinstance(writer.parsed, schema): raise ValueError("writer missing persisted result")
            proposal = {"stem": writer.parsed.stem, "options": [writer.parsed.correct_option, *writer.parsed.distractors]} if isinstance(writer.parsed, MCQProse) else {"question": writer.parsed.question}
            review_schema = SemanticReview if isinstance(writer.parsed, MCQProse) else SubjectiveReview
            review = await invoke("SEMANTIC_REVIEW", _messages(compiled, contract, case, review_schema, "SEMANTIC_REVIEW", proposal), review_schema, {"v051": True, "blueprint_id": blueprint["id"], "slot_id": contract["id"], "writer_call_id": writer.call_id, "attempt": retry + 1})
            try:
                if isinstance(writer.parsed, MCQProse): validate_mcq(proposal["stem"], proposal["options"], review.parsed)
                else: validate_subjective(proposal["question"], review.parsed)
            except ScientificReviewHold as exc:
                hold = str(exc); continue
            record = {"slot_id": contract["id"], "instance_id": hashlib.sha256(_compact(case).encode()).hexdigest(), "contract": contract, "case": case, "proposal": proposal, "writer_call_id": writer.call_id, "reviewer_call_id": review.call_id, "review": review.parsed.model_dump(mode="json")}
            await checkpoint(label, record); accepted[label] = record
            seen.update(fingerprints)
            break
        else: raise ScientificReviewHold(f"{contract['id']} remains on review hold: {hold}")
    public_mcqs, private_mcqs = [], []
    for label in ("MCQ1", "MCQ2", "MCQ3"):
        record = accepted[label]; options = record["proposal"]["options"]; order = list(range(4)); secrets.SystemRandom().shuffle(order)
        displayed = [{"id": chr(65 + i), "text": options[item]} for i, item in enumerate(order)]
        public_mcqs.append({"id": label, "stem": record["proposal"]["stem"], "options": displayed})
        private_mcqs.append({"id": label, "correct_option_id": displayed[order.index(0)]["id"], "contract": record["contract"], "verified_case": record["case"]})
    subject = accepted["SUB1"]
    public = {"mcqs": public_mcqs, "subjective": {"id": "SUB1", "prompt": subject["proposal"]["question"]}}
    private = {"mcqs": private_mcqs, "subjective_resolved": {"contract": subject["contract"], "case": subject["case"]}}
    fingerprint = hashlib.sha256(_compact({"public": public, "private": private}).encode()).hexdigest()
    return {"public": public, "private": private, "metadata": {"blueprint_id": blueprint["id"], "generation_checkpoints": accepted, "v051": True}, "fingerprint": fingerprint, "status": "FROZEN"}


def v051_judge_messages(compiled, resolved: dict, frozen_question: str, learner_response: str):
    source = compiled.authored["v051"]
    contract = resolved["contract"]
    judge_contract = source["scientific"]["judge.yaml"]
    prompt = source["prompts"]["SUBJECTIVE_JUDGE_PROMPT.md"]
    mode = contract.get("assessment_mode")
    if mode in ("fixed_c1_receiver_only", "fixed_c2_multistructural_patterns", "fixed_c3_relational_causal", "fixed_c4_extended_abstract"):
        import copy
        judge_contract = copy.deepcopy(judge_contract)
        for anchor in judge_contract.get("transition_anchors", []):
            if anchor.get("transition_id") == contract.get("transition_id"):
                anchor["min_1"] = contract["score_anchor"]["1"]
                anchor["full_2"] = contract["score_anchor"]["2"]
                anchor["zero"] = contract["score_anchor"]["0"]
        if mode == "fixed_c2_multistructural_patterns":
            prompt = prompt.replace(
                "- **C2:** Two distinct correct properties spanning 1D and full 2D may earn 1; do NOT demand a C3-style causal chain.",
                "- **C2:** On this fixed 2D-pattern question, apply its specific rubric: at least two distinct correctly analysed patterns for 1 point; all three patterns and limits for 2. Do not require an unasked 1D discussion or C3-level derivation.",
            )
        prompt += ("\n\n[FIXED_ITEM_SCORING_PRIORITY]\nThe frozen item-specific score_anchor 0/1/2 and evidence_elements "
                   "override any differing generic transition examples. Score only the explicitly asked question. "
                   "For fixed C1, sender reconstruction is NOT required for full credit. "
                   "For fixed C2, one isolated pattern is INSUFFICIENT for 1 point; two independently correct patterns are required. "
                   "For fixed C3, one correctly explained case-linked causal direction earns 1 point; both directions earn 2. "
                   "For fixed C4, a justified generalized pattern or counterexample earns 1 point; correct predictions, counterexample and added-rule evaluation together earn 2. "
                   "Do not require exact reference wording. Apply contradiction and alternative-reasoning rules.")
        if mode == "fixed_c1_receiver_only":
            prompt += "\n[FIXED_C1_ITEM_SCORING_PRIORITY]\nReceiver-only item scoring priority applies."
    if mode and mode.startswith("fixed_"):
        contract = dict(contract)
        contract.pop("calibration_examples", None)
        verified_case = dict(resolved["case"])
        verified_case.pop("reference_answer_for_calibration_only", None)
    else:
        verified_case = resolved["case"]
    payload = {"subjective_item": {"prompt": frozen_question, "contract": contract}, "verified_scenario": verified_case, "learner_response": learner_response, "judge_contract": judge_contract}
    return (CanonicalMessage(role="system", content=prompt
                             + "\n\n[V051_BLIND_SUBJECTIVE_JUDGE_CONTEXT]\n" + _compact(payload)
                             + "\n\n[OUTPUT_SCHEMA]\n" + _compact(V05SubjectiveJudgment.model_json_schema())),)
