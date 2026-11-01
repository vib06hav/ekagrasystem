"""Versioned, learner-reported Paas-style mental-effort instrument.

This is an EkagraAI wording adaptation of the 9-category mental-effort rating,
not a claim that this sentence was verbatim in Paas (1992). Final participant
wording and placement require approval in the research protocol.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from solo_harness.db.models import Attempt, PaasResponse, Session


INSTRUMENT_ID = "EKAGRAAI_PAAS_MENTAL_EFFORT_9"
INSTRUMENT_VERSION = "1.0"
QUESTION = "How much mental effort did you invest in the teaching activity you just completed?"
ANCHORS = (
    "Very, very low mental effort",
    "Very low mental effort",
    "Low mental effort",
    "Rather low mental effort",
    "Neither low nor high mental effort",
    "Rather high mental effort",
    "High mental effort",
    "Very high mental effort",
    "Very, very high mental effort",
)


def instrument_snapshot() -> dict:
    return {
        "instrument_id": INSTRUMENT_ID,
        "instrument_version": INSTRUMENT_VERSION,
        "question": QUESTION,
        "anchors": [{"value": i, "label": label} for i, label in enumerate(ANCHORS, 1)],
        "referent": "JUST_COMPLETED_TUTOR_INTERVENTION",
    }


def validate_rating(value: int) -> int:
    # bool is a subtype of int but is not a response category.
    if type(value) is not int or not 1 <= value <= 9:
        raise ValueError("Paas response must be one integer from 1 through 9")
    return value


def record_paas_response(db, session_id, rating: int, *, commit: bool = False) -> PaasResponse:
    """Record exactly one rating for the current attempt under its session lock.

    Call with `begin_assessment_after_paas` and build reservation in the SAME
    outer database transaction. This function never triggers provider work.
    """
    rating = validate_rating(rating)
    session = db.scalar(select(Session).where(Session.id == session_id).with_for_update())
    if session is None or session.phase != "PAAS_PENDING" or session.status != "ACTIVE":
        raise ValueError("Paas rating is not expected in the current session phase")
    attempt = db.get(Attempt, session.current_attempt_id)
    if attempt is None or attempt.session_id != session.id or attempt.completion_reason is None:
        raise ValueError("Paas requires a completed teaching attempt")
    already = db.scalar(select(PaasResponse.id).where(PaasResponse.attempt_id == attempt.id))
    if already is not None:
        raise ValueError("Paas rating has already been submitted for this attempt")
    snapshot = instrument_snapshot()
    response = PaasResponse(
        session_id=session.id,
        attempt_id=attempt.id,
        transition_id=attempt.transition_id,
        pedagogy_id=attempt.pedagogy_id,
        completion_reason=attempt.completion_reason,
        instrument_id=INSTRUMENT_ID,
        instrument_version=INSTRUMENT_VERSION,
        rating=rating,
        question_snapshot=snapshot["question"],
        anchors_snapshot=snapshot["anchors"],
    )
    db.add(response)
    db.flush()
    if commit:
        db.commit()
    return response
