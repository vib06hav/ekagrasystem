"""F1 v0.4 assessment construction service (not a separate HTTP/runtime).

Integrate this into the *single* participant session engine. Every model call
must be invoked via the application's durable, persisted LLM-call adapter.
The explicit checkpoint callback stores accepted items before generating more.
Mathematical truth is oracle-derived; semantic verification is still fallible
and requires further human review before participant deployment.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel

from solo_harness.runtime.ai import CanonicalMessage
from solo_harness.runtime.v04_native import (
    MCQProse, SemanticReview, SubjectiveProse, SubjectiveReview,
    assessment_messages, review_messages, resolve_slot,
)
from solo_harness.studies.scientific_v04 import ScientificStudyV04


class ScientificReviewHold(ValueError):
    """Do not freeze or grade an item with unverifiable natural-language meaning."""


@dataclass(frozen=True)
class RecordedResult:
    call_id: str
    parsed: BaseModel


# Integration contract: invoke MUST persist and finalize a real LLMCall for each
# distinct writer/reviewer call and must return its committed call ID.
RecordedInvoke = Callable[[str, tuple[CanonicalMessage, ...], type[BaseModel], dict[str, Any]], Awaitable[RecordedResult]]
Checkpoint = Callable[[str, dict[str, Any]], Awaitable[None]]


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def validate_mcq(stem: str, options: list[str], review: SemanticReview) -> None:
    """Structural & reviewer-backed semantic gate; not a claim of formal NLP proof."""
    if len(options) != 4 or len({_normalized(o) for o in options}) != 4:
        raise ScientificReviewHold("missing or duplicate options")
    if not stem.strip() or any(not o.strip() for o in options):
        raise ScientificReviewHold("empty learner-facing text")
    if (review.verdict != "ACCEPT" or not review.stem_matches_contract
            or not review.assumptions_visible or not review.exactly_one_defensible_option):
        raise ScientificReviewHold("semantic reviewer did not affirm the assessment construct")
    truth = [x.truth_status for x in review.option_assessments]
    if truth != ["TRUE", "FALSE", "FALSE", "FALSE"]:
        raise ScientificReviewHold("reviewer could not verify the oracle-bound answer and three false alternatives")
    if not all(x.matches_intended_meaning and x.scientific_reason.strip() for x in review.option_assessments):
        raise ScientificReviewHold("a displayed proposition does not match its authored scientific meaning")


def validate_subjective(question: str, review: SubjectiveReview) -> None:
    if not question.strip() or review.verdict != "ACCEPT" or not all((
        review.elicits_slot_evidence, review.assumes_only_visible_facts,
        review.scientifically_consistent, review.does_not_reveal_answer,
    )):
        raise ScientificReviewHold("subjective question did not pass scientific review")


def _require_call(result: RecordedResult, expected: type[BaseModel]) -> BaseModel:
    if not isinstance(result, RecordedResult) or not result.call_id or not isinstance(result.parsed, expected):
        raise ValueError("model role did not return validated output with persisted call identity")
    return result.parsed


async def construct_four_item_assessment(
    study: ScientificStudyV04,
    blueprint_id: str,
    invoke: RecordedInvoke,
    checkpoint: Checkpoint,
    *,
    completed: dict[str, dict[str, Any]] | None = None,
    prior_instructional_instance_ids: set[str] | None = None,
    prior_instructional_case_fingerprints: set[str] | None = None,
    max_semantic_attempts: int = 2,
) -> dict[str, Any]:
    """Build exactly four reviewed items; independently vary each numeric case.

    `checkpoint` must durably persist each ACCEPTED item before returning.
    `completed` must contain those exact persisted accepted records on recovery.
    The caller atomically freezes the resulting public/private package once.
    Failure leaves a retryable generation state, never a learner failure.
    """
    if max_semantic_attempts < 1 or max_semantic_attempts > 4:
        raise ValueError("unsafe number of semantic regeneration attempts")
    blueprint = study.blueprint(blueprint_id)
    if len(blueprint["items"]) != 4 or [x["type"] for x in blueprint["items"]] != ["MCQ", "MCQ", "MCQ", "SUBJECTIVE"]:
        raise ValueError("invalid v0.4 blueprint order")
    accepted = dict(completed or {})
    exposed = set(prior_instructional_instance_ids or ())
    if prior_instructional_case_fingerprints is None:
        raise ValueError("instructional numerical exposure fingerprints must be supplied (empty set only if truly none)")
    seen_facts = set(prior_instructional_case_fingerprints)
    for position, slot in enumerate(blueprint["items"], start=1):
        label = f"MCQ{position}" if slot["type"] == "MCQ" else "SUB1"
        if label in accepted:
            if (accepted[label].get("slot_id") != slot["id"]
                    or accepted[label].get("instance_id") in exposed
                    or not accepted[label].get("writer_call_id") or not accepted[label].get("reviewer_call_id")):
                raise ValueError("checkpoint does not match frozen scientific slot")
            for prior_case in accepted[label]["resolved"]["case"]["cases"]:
                seen_facts.add(hashlib.sha256(_compact(prior_case["public"]).encode()).hexdigest())
            continue
        reason = "No reviewer accepted this item"
        for attempt_index in range(max_semantic_attempts):
            # New seed is drawn independently of pedagogy; never reuse exposed facts.
            for _ in range(64):
                resolved = resolve_slot(study, slot["id"], secrets.randbits(64))
                realized_facts = {hashlib.sha256(_compact(c["public"]).encode()).hexdigest()
                                  for c in resolved["case"]["cases"]}
                if resolved["instance_id"] not in exposed and not (realized_facts & seen_facts):
                    break
            else:
                raise ValueError("cannot sample a numerically disjoint assessment instance")
            schema = MCQProse if slot["type"] == "MCQ" else SubjectiveProse
            writer = await invoke("ASSESSMENT_WRITER", assessment_messages(study, resolved), schema,
                                  {"blueprint_id": blueprint_id, "item_order": position, "attempt": attempt_index + 1})
            prose = _require_call(writer, schema)
            if isinstance(prose, MCQProse):
                proposal = {"stem": prose.stem, "options": [prose.correct_option, *prose.distractors]}
                review_schema = SemanticReview
            else:
                proposal = {"question": prose.question}
                review_schema = SubjectiveReview
            reviewer = await invoke("SEMANTIC_REVIEW", review_messages(study, resolved, proposal), review_schema,
                                    {"blueprint_id": blueprint_id, "item_order": position,
                                     "writer_call_id": writer.call_id, "attempt": attempt_index + 1})
            review = _require_call(reviewer, review_schema)
            try:
                if isinstance(prose, MCQProse):
                    validate_mcq(prose.stem, proposal["options"], review)
                else:
                    validate_subjective(prose.question, review)
            except ScientificReviewHold as exc:
                reason = str(exc)
                continue
            record = {"slot_id": slot["id"], "instance_id": resolved["instance_id"],
                      "resolved": resolved, "proposal": proposal,
                      "writer_call_id": writer.call_id, "reviewer_call_id": reviewer.call_id,
                      "review": review.model_dump(mode="json")}
            # Persistence is a required boundary: accepted items survive crashes.
            await checkpoint(label, record)
            accepted[label] = record
            seen_facts.update(realized_facts)
            break
        else:
            raise ScientificReviewHold(f"{slot['id']} remains on review hold: {reason}")

    public_mcqs = []
    private_mcqs = []
    audit = []
    for label in ("MCQ1", "MCQ2", "MCQ3"):
        record = accepted[label]
        proposed = record["proposal"]["options"]
        perm = list(range(4))
        secrets.SystemRandom().shuffle(perm)
        displayed = [{"id": chr(ord("A") + i), "text": proposed[index]} for i, index in enumerate(perm)]
        public_mcqs.append({"id": label, "stem": record["proposal"]["stem"], "options": displayed})
        private_mcqs.append({"id": label, "correct_option_id": displayed[perm.index(0)]["id"],
                             "slot_id": record["slot_id"], "instance_id": record["instance_id"],
                             "oracle": record["resolved"]["case"]["oracle"]})
        audit.append({"id": label, "slot_id": record["slot_id"],
                      "writer_call_id": record["writer_call_id"], "reviewer_call_id": record["reviewer_call_id"]})
    subject = accepted["SUB1"]
    public = {"instructions": "Answer all four questions.", "mcqs": public_mcqs,
              "subjective": {"id": "SUB1", "prompt": subject["proposal"]["question"]}}
    private = {"mcqs": private_mcqs, "subjective_resolved": subject["resolved"],
               "assessment_call_audit": [*audit, {"id": "SUB1", "slot_id": subject["slot_id"],
                                             "writer_call_id": subject["writer_call_id"],
                                             "reviewer_call_id": subject["reviewer_call_id"]}]}
    metadata = {"scientific_content_hash": study.content_hash, "scientific_source_hashes": study.source_hashes,
                "blueprint_id": blueprint_id, "schema_version": "v04.native.2",
                "semantic_review_boundary": "model-review-hold; not formally proven and not human-approved"}
    fingerprint = hashlib.sha256(_compact({"public": public, "private": private, "metadata": metadata}).encode()).hexdigest()
    return {"public": public, "private": private, "metadata": metadata, "fingerprint": fingerprint,
            "status": "DEVELOPMENT_ONLY"}
