"""Pure contract regressions for Codex to run AFTER integration.

Intentionally not executed when the handoff patch was authored.
"""
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from ruamel.yaml import YAML
from sqlalchemy import select

from solo_harness.studies.controlled_c1 import (
    ControlledC1Error, active_move, c11_instance, contract,
    contract_hash, new_c11_state, unambiguous_reply_feedback, visual_descriptor,
)


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE / "studies/networks_error_detection_parity_f1/v0.5"
SOURCE = PACKAGE / "studies/networks_error_detection_parity_f1/v0.5/08_SCIENTIFIC_YAML/subsection_interventions.yaml"


def source_cells():
    return YAML(typ="safe").load(SOURCE.read_text(encoding="utf-8"))["cells"]


def progress_for(pedagogy):
    moves = contract()["subsections"]["C1.1"]["moves_by_pedagogy"][pedagogy]
    return SimpleNamespace(subsection_id="C1.1", pedagogy_id=pedagogy,
                           required_move_ids=[m["id"] for m in moves],
                           instructional_state={"controlled_c11": new_c11_state()})


@pytest.mark.parametrize("pedagogy,expected", [("P1", 4), ("P2", 5), ("P3", 4)])
def test_source_move_alignment(pedagogy, expected):
    compiled = SimpleNamespace(authored={"v051": {"scientific": {"subsection_interventions.yaml": {"cells": source_cells()}}}})
    progress = progress_for(pedagogy)
    move, position = active_move(compiled, progress)
    assert position == 0 and move["id"] == f"C1.1-{pedagogy}-M01"
    assert len(progress.required_move_ids) == expected


def test_all_c1_contract_moves_match_locked_source_actions():
    originals = {c["id"]: c for c in source_cells()}
    total = 0
    for subsection, specs in contract()["subsections"].items():
        for pedagogy, moves in specs["moves_by_pedagogy"].items():
            locked = originals[f"{subsection}-{pedagogy}"]["core_moves"]
            assert [m["id"] for m in moves] == [m["id"] for m in locked]
            for m, orig in zip(moves, locked):
                assert m["source_instructional_action"] == orig["instructional_action"]
                assert m["required_content_refs"] == orig["covers_content_refs"]
                total += 1
    assert total == 52


@pytest.mark.parametrize("pedagogy,count", [("P1", 1), ("P2", 1), ("P3", 2)])
def test_verified_case_values_are_fixed_and_correct(pedagogy, count):
    instance = c11_instance(pedagogy)
    assert instance["verified"] and len(instance["public"]["cases"]) == count
    primary = instance["public"]["cases"][0]
    assert primary["answers"] == ["Yes", "Yes", "No"]
    assert primary["bit_sequence"] == "110" and primary["number_of_ones"] == 2
    assert primary["position_labels"] == [1, 2, 3]
    if pedagogy == "P3":
        contrast = instance["public"]["cases"][1]
        assert contrast["answers"] == ["Yes", "No", "No"]
        assert contrast["bit_sequence"] == "100" and contrast["number_of_ones"] == 1
    assert instance["case_fingerprints"]


def test_exact_literal_chat_feedback_is_formative_only():
    moves = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"]
    instance = c11_instance("P2")
    value = unambiguous_reply_feedback(moves[2], "110", instance)
    assert value["matches"] is True and value["verified_expected"] == "110"
    assert "mastery" in value["purpose"]
    assert unambiguous_reply_feedback(moves[2], "why 110?", instance) is None
    assert unambiguous_reply_feedback(moves[3], "3", instance)["matches"] is False


def test_visual_is_passive_and_hidden_state_has_no_llm_operations():
    move = contract()["subsections"]["C1.1"]["moves_by_pedagogy"]["P2"][2]
    descriptor = visual_descriptor(move, c11_instance("P2"), "prompt")
    assert descriptor["component"] == "mapping" and descriptor["stage"] == "prompt"
    assert "html" not in descriptor and "js" not in descriptor and "events" not in descriptor


def test_persisted_version_drift_fails_closed():
    compiled = SimpleNamespace(authored={"v051": {"scientific": {"subsection_interventions.yaml": {"cells": source_cells()}}}})
    p = progress_for("P1")
    p.instructional_state["controlled_c11"]["contract_sha256"] = "different"
    with pytest.raises(ControlledC1Error):
        active_move(compiled, p)
    assert len(contract_hash()) == 64


class _FixedSelector:
    def __init__(self, pedagogy):
        self.pedagogy = pedagogy

    def choice(self, values):
        return self.pedagogy if self.pedagogy in values else sorted(values)[0]


class _ControlledPilotClient:
    """Deterministic model boundary used only to exercise real persistence."""

    def prepare(self, request):
        from solo_harness.runtime.ai import PreparedLLMRequest
        return PreparedLLMRequest(request, {}, "{}", {})

    async def send(self, prepared):
        from solo_harness.runtime.ai import RawLLMResponse
        request = prepared.request
        pilot = "[CONTROLLED_C11_CURRENT_TUTOR_CONTEXT]" in request.messages[0].content
        if request.logical_role == "TUTOR":
            payload = {
                "learner_message": "A fixed, treatment-faithful explanation for the active move.",
                "ready_for_judge": pilot,
            }
        else:
            payload = {"decision": "ADVANCE", "guidance": "The current move was delivered accurately."}
        return RawLLMResponse(None, 200, json.dumps(payload),
                              {"choices": [{"message": {"parsed": payload}}]}, payload,
                              "stop", False, {}, 1)


def _pilot_settings():
    return SimpleNamespace(llm_provider="test", judge_model="judge", tutor_model="tutor",
                           judge_temperature=0, tutor_temperature=0,
                           judge_max_output_tokens=1000, tutor_max_output_tokens=1000,
                           llm_request_timeout_seconds=10)


def _controlled_runtime(db, pedagogy):
    from solo_harness.runtime.engine import RandomSelector, SessionRuntime
    from solo_harness.studies.activation import activate
    from solo_harness.studies.scientific_v051 import load_scientific_v051
    from solo_harness.studies.v051_native_compiler import compile_v051

    compiled = compile_v051(load_scientific_v051(ROOT))
    version = activate(db, compiled)
    runtime = SessionRuntime(SimpleNamespace(load=lambda _db, _id: compiled),
                             selector=RandomSelector(_FixedSelector(pedagogy)))
    session = runtime.create_v051_internal_test_session(
        db, version.id, controlled_c11_pilot=True, commit=True
    )
    return runtime, session.id


@pytest.mark.skipif(not os.environ.get("EKAGRA_STAGE3_DATABASE_URL"),
                    reason="set EKAGRA_STAGE3_DATABASE_URL for PostgreSQL pilot integration")
@pytest.mark.parametrize("pedagogy", ["P1", "P3"])
def test_controlled_c11_non_guided_pedagogies_complete_ordered_moves(pedagogy):
    from solo_harness.db.engine import make_session_factory
    from solo_harness.db.models import Message, SubsectionProgress
    from solo_harness.runtime.ai import AIExecutionRuntime

    with make_session_factory(os.environ["EKAGRA_STAGE3_DATABASE_URL"])() as db:
        runtime, session_id = _controlled_runtime(db, pedagogy)
        call_id = AIExecutionRuntime(runtime, _ControlledPilotClient(), _pilot_settings()).reserve_tutor(db, session_id, commit=True)
        asyncio.run(AIExecutionRuntime(runtime, _ControlledPilotClient(), _pilot_settings()).execute(db, call_id))
        progress = db.scalar(select(SubsectionProgress).where(
            SubsectionProgress.session_id == session_id, SubsectionProgress.subsection_id == "C1.1"
        ))
        assert progress.status == "COMPLETED"
        assert set(progress.move_evidence) == set(progress.required_move_ids)
        assert set(progress.content_evidence) == set(progress.required_content_ids)
        traces = db.scalars(select(Message).where(Message.attempt_id == progress.attempt_id, Message.role == "TUTOR")).all()
        assert all(trace.instructional_trace["pilot_contract_sha256"] == contract_hash() for trace in traces[:len(progress.required_move_ids)])


@pytest.mark.skipif(not os.environ.get("EKAGRA_STAGE3_DATABASE_URL"),
                    reason="set EKAGRA_STAGE3_DATABASE_URL for PostgreSQL pilot integration")
def test_controlled_c11_guided_moves_require_learner_turns_and_resolve_visuals():
    from solo_harness.db.engine import make_session_factory
    from solo_harness.db.models import Message, SubsectionProgress
    from solo_harness.runtime.ai import AIExecutionRuntime

    with make_session_factory(os.environ["EKAGRA_STAGE3_DATABASE_URL"])() as db:
        runtime, session_id = _controlled_runtime(db, "P2")
        ai = AIExecutionRuntime(runtime, _ControlledPilotClient(), _pilot_settings())
        call_id = ai.reserve_tutor(db, session_id, commit=True)
        asyncio.run(ai.execute(db, call_id))
        progress = db.scalar(select(SubsectionProgress).where(
            SubsectionProgress.session_id == session_id, SubsectionProgress.subsection_id == "C1.1"
        ))
        assert progress.instructional_state["controlled_c11"]["move_index"] == 1
        for reply in ("I do not know.", "110", "2"):
            call_id = ai.reserve_tutor(db, session_id, reply, commit=True)
            asyncio.run(ai.execute(db, call_id))
        db.refresh(progress)
        assert progress.status == "COMPLETED"
        traces = db.scalars(select(Message).where(Message.attempt_id == progress.attempt_id, Message.role == "TUTOR")).all()
        visuals = [message.instructional_trace.get("pilot_visual") for message in traces if message.instructional_trace.get("pilot_visual")]
        assert visuals and all("html" not in visual for visual in visuals)
        assert any(visual["stage"] == "prompt" for visual in visuals)
        assert any(visual["stage"] == "complete" for visual in visuals)


@pytest.mark.skipif(not os.environ.get("EKAGRA_STAGE3_DATABASE_URL"),
                    reason="set EKAGRA_STAGE3_DATABASE_URL for PostgreSQL pilot integration")
def test_controlled_c11_rejects_direct_subsection_bypass():
    from solo_harness.db.engine import make_session_factory
    from solo_harness.runtime.engine import ConversationJudgeRejected

    with make_session_factory(os.environ["EKAGRA_STAGE3_DATABASE_URL"])() as db:
        runtime, session_id = _controlled_runtime(db, "P1")
        with pytest.raises(ConversationJudgeRejected, match="move-level Judge authorization"):
            runtime.advance_v051_subsection(db, session_id, "C1.1", commit=False)
