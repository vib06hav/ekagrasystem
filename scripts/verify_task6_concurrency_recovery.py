"""Task 6: concurrent PostgreSQL operation leases and saved-response recovery."""
from __future__ import annotations

import asyncio
import json
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings
from solo_harness.db.engine import make_session_factory
from solo_harness.db.models import AssessmentInstance, AssessmentResponse, Attempt, LLMCall, Message, Session
from solo_harness.runtime.ai import AIExecutionRuntime, PreparedLLMRequest
from solo_harness.runtime.engine import SessionRuntime


class NoSendClient:
    def __init__(self): self.sends = 0
    def prepare(self, request): return PreparedLLMRequest(request, {}, "{}", {})
    async def send(self, prepared):
        self.sends += 1
        raise AssertionError("a saved response must never be sent again")


def tutor_payload(complete=False):
    data = {"learner_message": "Synthetic persisted Tutor reply.", "fidelity_note": "task6 fixture", "teaching_complete": complete}
    return {"choices": [{"message": {"content": json.dumps(data)}}]}


def main():
    cfg = get_settings()
    factory = make_session_factory(cfg.database_url)
    catalog = bootstrap(cfg)
    runtime = SessionRuntime(catalog)
    db = factory()
    source = db.scalar(select(Session).order_by(Session.created_at.desc()))
    assert source is not None
    study_id = source.study_version_id
    client = NoSendClient()

    # Two independent database sessions race to reserve distinct Tutor messages.
    tutor_session = runtime.create_session(db, study_id, build_id="task6-tutor", institutional_id="task6-tutor-" + uuid.uuid4().hex[:12], commit=True)
    barrier = threading.Barrier(2)
    tutor_results = []
    def reserve_tutor(text):
        local = factory()
        try:
            barrier.wait(timeout=10)
            call_id = AIExecutionRuntime(runtime, client, cfg).reserve_tutor(local, tutor_session.id, text, commit=True)
            tutor_results.append({"reserved": str(call_id)})
        except ValueError as exc:
            tutor_results.append({"rejected": str(exc)})
        finally:
            local.close()
    workers = [threading.Thread(target=reserve_tutor, args=(f"Learner concurrent message {n}",)) for n in (1, 2)]
    [worker.start() for worker in workers]; [worker.join() for worker in workers]
    tutor_calls = list(db.scalars(select(LLMCall).where(LLMCall.session_id == tutor_session.id, LLMCall.purpose == "TUTOR")).all())
    tutor_messages = list(db.scalars(select(Message).join(Attempt).where(Attempt.session_id == tutor_session.id, Message.role == "LEARNER")).all())

    # Two independent sessions race to retry the same failed JUDGE operation.
    source_item = db.scalar(select(AssessmentInstance).where(AssessmentInstance.status == "CLOSED").order_by(AssessmentInstance.closed_at.desc()))
    source_response = db.scalar(select(AssessmentResponse).where(AssessmentResponse.assessment_instance_id == source_item.id))
    judge_session = runtime.create_session(db, study_id, build_id="task6-judge", institutional_id="task6-judge-" + uuid.uuid4().hex[:12], commit=False)
    judge_attempt = db.get(Attempt, judge_session.current_attempt_id)
    item = AssessmentInstance(session_id=judge_session.id, attempt_id=judge_attempt.id, transition_id=judge_attempt.transition_id, assessment_family_id=source_item.assessment_family_id, assessment_form_id=source_item.assessment_form_id, status="AWAITING_EVALUATION", candidate_form_ids=source_item.candidate_form_ids, selection_method="TASK6", selection_audit={"fixture": "concurrent judge retry"}, blueprint_snapshot=source_item.blueprint_snapshot, resolved_component_ids=source_item.resolved_component_ids, frozen_public_snapshot=source_item.frozen_public_snapshot, frozen_private_snapshot=source_item.frozen_private_snapshot, frozen_package_fingerprint=source_item.frozen_package_fingerprint, frozen_schema_version=source_item.frozen_schema_version, frozen_metadata_snapshot=source_item.frozen_metadata_snapshot, delivery_status="DEVELOPMENT_ONLY", frozen_at=datetime.now(timezone.utc))
    db.add(item); db.flush()
    db.add(AssessmentResponse(assessment_instance_id=item.id, response_text=source_response.response_text, response_format="plain", client_action_id=uuid.uuid4(), structured_response=source_response.structured_response, response_schema_version="v04.native.2"))
    judge_session.phase = "ASSESSMENT_AWAITING_EVALUATION"; judge_attempt.status = "AWAITING_EVALUATION"
    failed = LLMCall(session_id=judge_session.id, attempt_id=judge_attempt.id, assessment_instance_id=item.id, purpose="JUDGE", status="FAILED", retry_group_id=uuid.uuid4(), retry_number=0, provider="fault", model="fault", generation_parameters={}, request_payload={}, request_body_text="{}", error_class="TIMEOUT", error_message="injected")
    db.add(failed); db.commit()
    barrier = threading.Barrier(2)
    retry_results = []
    def reserve_retry():
        local = factory()
        try:
            barrier.wait(timeout=10)
            call_id = AIExecutionRuntime(runtime, client, cfg).reserve_manual_retry(local, judge_session.id, commit=True)
            retry_results.append({"reserved": str(call_id)})
        except ValueError as exc:
            retry_results.append({"rejected": str(exc)})
        finally:
            local.close()
    workers = [threading.Thread(target=reserve_retry) for _ in range(2)]
    [worker.start() for worker in workers]; [worker.join() for worker in workers]
    judge_calls = list(db.scalars(select(LLMCall).where(LLMCall.session_id == judge_session.id, LLMCall.purpose == "JUDGE").order_by(LLMCall.started_at)).all())

    # Application failure after receipt rolls back side effects but retains the raw response.
    recovery_session = runtime.create_session(db, study_id, build_id="task6-received", institutional_id="task6-received-" + uuid.uuid4().hex[:12], commit=False)
    recovery_attempt = db.get(Attempt, recovery_session.current_attempt_id)
    payload = tutor_payload(complete=True)
    received = LLMCall(session_id=recovery_session.id, attempt_id=recovery_attempt.id, assessment_instance_id=None, purpose="TUTOR", status="RECEIVED", retry_group_id=uuid.uuid4(), retry_number=0, provider="fault", model="fault", generation_parameters={}, request_payload={"schema_name": "TutorProse"}, request_body_text="{}", raw_response_text=json.dumps(payload), response_payload=payload)
    db.add(received); db.commit()
    ai = AIExecutionRuntime(runtime, client, cfg)
    original_complete = runtime.complete_intervention
    def fail_apply(*args, **kwargs): raise RuntimeError("injected local application failure")
    runtime.complete_intervention = fail_apply
    asyncio.run(ai.execute(db, received.id))
    db.expire_all()
    held = db.get(LLMCall, received.id)
    held_state = {"status": held.status, "error_class": held.error_class}
    messages_after_failure = len(list(db.scalars(select(Message).where(Message.llm_call_id == received.id)).all()))
    runtime.complete_intervention = original_complete
    build_runs = []
    async def stop_after_reservation(_db, call_id): build_runs.append(str(call_id))
    ai.execute = stop_after_reservation
    asyncio.run(ai._finalize_received(db, received.id))
    asyncio.run(ai._finalize_received(db, received.id))
    db.expire_all()
    recovered = db.get(LLMCall, received.id)
    messages_after_recovery = len(list(db.scalars(select(Message).where(Message.llm_call_id == received.id)).all()))

    trace = {
        "concurrent_tutor": {"results": tutor_results, "tutor_call_count": len(tutor_calls), "learner_message_count": len(tutor_messages)},
        "concurrent_judge_retry": {"results": retry_results, "judge_call_count": len(judge_calls), "retry_number": judge_calls[-1].retry_number, "retry_of": judge_calls[-1].request_payload.get("retry_of")},
        "saved_response_application_failure": {"held_status": held_state["status"], "held_error_class": held_state["error_class"], "messages_after_failure": messages_after_failure, "recovered_status": recovered.status, "messages_after_recovery": messages_after_recovery, "reserved_build_runs": len(build_runs), "provider_sends": client.sends},
    }
    assert len(tutor_calls) == 1 and len(tutor_messages) == 1 and sum("rejected" in x for x in tutor_results) == 1
    assert len(judge_calls) == 2 and judge_calls[-1].retry_number == 1 and sum("rejected" in x for x in retry_results) == 1
    assert held_state["status"] == "RECEIVED" and held_state["error_class"] == "APPLICATION_FAILURE" and messages_after_failure == 0
    assert recovered.status == "SUCCEEDED" and messages_after_recovery == 1 and len(build_runs) == 1 and client.sends == 0
    (cfg.research_data_dir / "task6_concurrency_recovery_trace.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(json.dumps(trace))


if __name__ == "__main__": main()
