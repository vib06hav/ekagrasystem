"""Single v0.4 execution workflow: provider transport, prompts, freezing, and judging."""
from __future__ import annotations
import asyncio, hashlib, json, random, time, uuid
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Any, Literal, Protocol
import httpx
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, or_, select
from solo_harness.config import Settings
from solo_harness.db.models import AssessmentInstance, AssessmentResponse, Attempt, LLMCall, Message, Session, StudyVersion, V04Evaluation
from solo_harness.runtime.engine import SessionRuntime

class CanonicalMessage(BaseModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    role: Literal["system","user","assistant"]
    content: str
@dataclass(frozen=True)
class LLMRequest:
    logical_role:str; operation_id:uuid.UUID; retry_group_id:uuid.UUID; retry_number:int; provider:str; model:str
    messages:tuple[CanonicalMessage,...]; response_schema_name:str; response_schema_version:str; response_json_schema:dict[str,Any]; generation_parameters:dict[str,Any]; timeout_seconds:int; audit_context:dict[str,Any]
@dataclass(frozen=True)
class PreparedLLMRequest: request:LLMRequest; body:dict; body_text:str; redacted_headers:dict
@dataclass(frozen=True)
class RawLLMResponse:
    provider_request_id:str|None; status_code:int; raw_response_text:str; response_payload:dict|None; structured_candidate:object|str|None; finish_reason:str|None; refusal:bool; usage:dict; latency_ms:int
class ProviderError(RuntimeError):
    def __init__(self, error_class,message,retryable): super().__init__(message); self.error_class,self.retryable=error_class,retryable
class LLMClient(Protocol):
    def prepare(self, request:LLMRequest)->PreparedLLMRequest: ...
    async def send(self, prepared:PreparedLLMRequest)->RawLLMResponse: ...
class OpenAICompatibleClient:
    def __init__(self,settings): self.base_url=(settings.aicredits_base_url or "").rstrip("/"); self.api_key=settings.aicredits_api_key.get_secret_value() if settings.aicredits_api_key else ""; self.timeout=httpx.Timeout(settings.llm_request_timeout_seconds,connect=settings.llm_connect_timeout_seconds)
    def prepare(self,request):
        if not self.base_url or not self.api_key: raise ProviderError("CONFIGURATION_ERROR","LLM provider configuration is incomplete",False)
        body={"model":request.model,"messages":[m.model_dump() for m in request.messages],**request.generation_parameters,"response_format":{"type":"json_schema","json_schema":{"name":request.response_schema_name,"strict":True,"schema":request.response_json_schema}}}
        return PreparedLLMRequest(request,body,json.dumps(body,sort_keys=True,separators=(",",":")),{"Authorization":"Bearer [REDACTED]","Content-Type":"application/json"})
    async def send(self,prepared):
        started=time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client: response=await client.post(self.base_url+"/chat/completions",headers={"Authorization":"Bearer "+self.api_key,"Content-Type":"application/json"},json=prepared.body)
        except httpx.TimeoutException as exc: raise ProviderError("TIMEOUT",str(exc),True) from exc
        except httpx.ConnectError as exc: raise ProviderError("CONNECTION_ERROR",str(exc),True) from exc
        if response.status_code>=400: raise ProviderError("PROVIDER_ERROR",f"HTTP {response.status_code}: {response.text[:1000]}",response.status_code>=500 or response.status_code==429)
        try: payload=response.json()
        except ValueError: payload=None
        choice=((payload or {}).get("choices") or [{}])[0]; message=choice.get("message") or {}
        return RawLLMResponse(response.headers.get("x-request-id"),response.status_code,response.text,payload,message.get("parsed") or message.get("content"),choice.get("finish_reason"),bool(message.get("refusal")),(payload or {}).get("usage") or {},int((time.perf_counter()-started)*1000))
def _decode(value):
    if isinstance(value,dict): return value
    if not isinstance(value,str): raise ValueError("provider returned no structured output")
    text=value.strip(); text=text[3:].lstrip("json\n")[:-3].strip() if text.startswith("```") and text.endswith("```") else text
    return json.loads(text)

class AIExecutionRuntime:
    def __init__(self,runtime:SessionRuntime,client:LLMClient,settings:Settings): self.runtime,self.client,self.settings=runtime,client,settings
    def _request(self,role,messages,model,schema,audit):
        return LLMRequest(role,uuid.uuid4(),uuid.uuid4(),0,self.settings.llm_provider,model,tuple(messages),schema.__name__,"1.0",schema.model_json_schema(),{"temperature":self.settings.judge_temperature if role=="JUDGE" else self.settings.tutor_temperature,"max_tokens":self.settings.judge_max_output_tokens if role=="JUDGE" else self.settings.tutor_max_output_tokens},self.settings.llm_request_timeout_seconds,audit)
    def _reserve(self,db,session,attempt,assessment,role,messages,schema,audit):
        request=self._request(role,messages,self.settings.judge_model if role=="JUDGE" else self.settings.tutor_model,schema,audit); prepared=self.client.prepare(request)
        call=LLMCall(session_id=session.id,attempt_id=attempt.id,assessment_instance_id=assessment.id if assessment else None,purpose=role,status="STARTED",retry_group_id=request.retry_group_id,retry_number=0,provider=request.provider,model=request.model,generation_parameters=request.generation_parameters,compiled_prompt_text="\n\n".join(m.content for m in messages),request_payload={"messages":[m.model_dump() for m in messages],"schema":request.response_json_schema,"schema_name":request.response_schema_name,"audit":audit},request_body_text=prepared.body_text)
        db.add(call); db.flush(); self.runtime._event(db,session,"LLM_CALL_STARTED",{"role":role,"call_id":str(call.id)},attempt.id); return call.id
    def _science(self):
        from solo_harness.studies.scientific_v04 import load_scientific_v04
        return load_scientific_v04(self.settings.study_dir)
    def reserve_tutor(self,db,session_id,learner_text=None,commit=True):
        from solo_harness.runtime.v04_native import TutorProse,tutor_messages
        from solo_harness.studies.v04_instructional import resolve_instructional_instance
        # The session lock is the stage lease: distinct HTTP idempotency keys may
        # not create two Tutor turns for one attempt.
        session=db.scalar(select(Session).where(Session.id==session_id).with_for_update())
        attempt=db.get(Attempt,session.current_attempt_id) if session else None
        if not session or session.phase!="INTERVENTION_ACTIVE": raise ValueError("tutor unavailable")
        active=db.scalar(select(LLMCall.id).where(
            LLMCall.session_id==session.id, LLMCall.attempt_id==attempt.id,
            LLMCall.purpose=="TUTOR", or_(
                LLMCall.status.in_(("STARTED","SENDING")),
                and_(LLMCall.status=="RECEIVED", LLMCall.error_class.is_distinct_from("APPLICATION_FAILURE")),
            ),
        ))
        if active: raise ValueError("a Tutor operation is already active")
        if learner_text is not None:
            if not learner_text.strip(): raise ValueError("empty learner response")
            seq=(db.scalar(select(Message.sequence_no).where(Message.attempt_id==attempt.id).order_by(Message.sequence_no.desc())) or 0)+1; db.add(Message(attempt_id=attempt.id,sequence_no=seq,role="LEARNER",content_text=learner_text.strip(),content_format="plain",material_ids=[],exposed_kc_ids=[],exposed_relation_ids=[]))
        if attempt.status=="ASSIGNED": attempt.status="INTERVENTION_ACTIVE"; attempt.intervention_started_at=datetime.now(timezone.utc); session.started_at=session.started_at or datetime.now(timezone.utc)
        cell=self.runtime._compiled(db,session).cells[f"{attempt.transition_id}:{attempt.pedagogy_id}"]; dialogue=db.scalars(select(Message).where(Message.attempt_id==attempt.id).order_by(Message.sequence_no)).all()
        details=dict(attempt.outcome_details or {}); instructional=details.get("v04_instructional_instance")
        if instructional is None:
            instructional=resolve_instructional_instance(self._science(),cell["id"])
            details["v04_instructional_instance"]=instructional; attempt.outcome_details=details
        messages=tutor_messages(self._science(),cell["id"],[{"role":"assistant" if m.role=="TUTOR" else "user","content":m.content_text} for m in dialogue],instructional); call=self._reserve(db,session,attempt,None,"TUTOR",messages,TutorProse,{"v04":True,"cell_id":cell["id"],"instructional_instance_id":instructional["instance_id"]})
        if commit: db.commit()
        return call
    def reserve_assessment(self,db,session_id,assessment_id=None,commit=True):
        # The build row is a durable constructor lease.  Locking the session and
        # reusing an active lease prevents duplicate builds after retries or when
        # two recovery workers observe the same interrupted transition.
        session=db.scalar(select(Session).where(Session.id==session_id).with_for_update())
        if not session: raise ValueError("session unavailable")
        attempt=db.get(Attempt,session.current_attempt_id); item=db.get(AssessmentInstance,assessment_id) if assessment_id else db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id==attempt.id))
        if not item: raise ValueError("assessment unavailable")
        existing=db.scalar(select(LLMCall).where(LLMCall.assessment_instance_id==item.id,LLMCall.purpose=="ASSESSMENT_BUILD",LLMCall.status.in_(["STARTED","RECEIVED"])).order_by(LLMCall.started_at.desc()).with_for_update())
        if existing:
            return existing.id
        if session.phase!="ASSESSMENT_GENERATING" or item.status!="GENERATING": raise ValueError("assessment unavailable")
        # This is an orchestration marker only.  The constructor below creates the
        # real writer/reviewer LLMCall rows; do not spend a redundant provider call.
        call=LLMCall(session_id=session.id,attempt_id=attempt.id,assessment_instance_id=item.id,purpose="ASSESSMENT_BUILD",status="STARTED",retry_group_id=uuid.uuid4(),retry_number=0,provider=self.settings.llm_provider,model=self.settings.tutor_model or "",generation_parameters={},compiled_prompt_text=None,request_payload={"operation":"v04_assessment_build"},request_body_text="{}")
        db.add(call); db.flush(); item.generation_llm_call_id=call.id; self.runtime._event(db,session,"V04_ASSESSMENT_BUILD_RESERVED",{"assessment_id":str(item.id),"call_id":str(call.id)},attempt.id)
        if commit: db.commit()
        return call.id
    def reserve_f1_judge(self,db,session_id,response,commit=True):
        from solo_harness.runtime.v04_native import SubjectiveJudgment,judge_messages
        session=db.scalar(select(Session).where(Session.id==session_id).with_for_update())
        attempt=db.get(Attempt,session.current_attempt_id) if session else None; item=db.get(AssessmentInstance,response.assessment_instance_id)
        if session.phase!="ASSESSMENT_AWAITING_EVALUATION": raise ValueError("judge unavailable")
        active=db.scalar(select(LLMCall.id).where(
            LLMCall.session_id==session.id, LLMCall.attempt_id==attempt.id, LLMCall.purpose=="JUDGE",
            or_(LLMCall.status.in_(("STARTED","SENDING")), and_(LLMCall.status=="RECEIVED", LLMCall.error_class.is_distinct_from("APPLICATION_FAILURE"))),
        ))
        if active: raise ValueError("a Judge operation is already active")
        resolved=(item.frozen_private_snapshot or {}).get("subjective_resolved")
        if not resolved: raise ValueError("missing frozen subjective context")
        messages=judge_messages(self._science(),resolved,item.frozen_public_snapshot["subjective"]["prompt"],response.response_text); call=self._reserve(db,session,attempt,item,"JUDGE",messages,SubjectiveJudgment,{"v04_blind":True})
        if commit: db.commit()
        return call
    async def _call(self,role,messages,schema):
        raw=await self.client.send(self.client.prepare(self._request(role,messages,self.settings.judge_model if role=="JUDGE" else self.settings.tutor_model,schema,{}))); return schema.model_validate(_decode(raw.structured_candidate or raw.raw_response_text)),raw
    async def _freeze(self,db,call,session,attempt):
        from solo_harness.runtime.v04_assessment import construct_four_item_assessment
        from solo_harness.runtime.v04_recorded import AssessmentCheckpoint, PersistedModelInvoker
        item=db.get(AssessmentInstance,call.assessment_instance_id); scientific=self._science()
        records=db.scalars(select(Attempt).where(Attempt.session_id==session.id)).all()
        instructional=[(a.outcome_details or {}).get("v04_instructional_instance") for a in records]
        instructional=[x for x in instructional if x]
        package=await construct_four_item_assessment(scientific,item.assessment_form_id,PersistedModelInvoker(db,self,session.id,item.id),AssessmentCheckpoint(db,item.id),completed=AssessmentCheckpoint(db,item.id).completed(),prior_instructional_instance_ids={x["instance_id"] for x in instructional},prior_instructional_case_fingerprints={f for x in instructional for f in x.get("case_fingerprints",[])})
        # All four checkpoint records already exist.  This final mutation is the
        # only public/private package freeze and happens as one transaction.
        item=db.scalar(select(AssessmentInstance).where(AssessmentInstance.id==item.id).with_for_update())
        metadata={**package["metadata"],"generation_checkpoints":dict((item.frozen_metadata_snapshot or {}).get("generation_checkpoints",{}))}
        item.frozen_public_snapshot=package["public"]; item.frozen_private_snapshot=package["private"]; item.frozen_metadata_snapshot=metadata; item.frozen_package_fingerprint=package["fingerprint"]; item.frozen_schema_version="v04.native.2"; item.delivery_status=package["status"]; item.frozen_at=datetime.now(timezone.utc); item.status="ACTIVE"; attempt.status="ASSESSMENT_ACTIVE"; session.phase="ASSESSMENT_ACTIVE"; call.status="SUCCEEDED"; call.completed_at=datetime.now(timezone.utc); call.parsed_response={"frozen":True,"items":4}; self.runtime._event(db,session,"V04_ASSESSMENT_FROZEN",{"assessment_id":str(item.id),"fingerprint":package["fingerprint"]},attempt.id); db.commit()
    def _saved_candidate(self, call):
        payload=call.response_payload or {}
        message=((payload.get("choices") or [{}])[0].get("message") or {})
        return message.get("parsed") or message.get("content") or call.raw_response_text
    def _application_failure(self, db, call_id, exc):
        """Keep a persisted provider response available for local re-application."""
        db.rollback()
        call=db.scalar(select(LLMCall).where(LLMCall.id==call_id).with_for_update())
        if call and call.status=="RECEIVED":
            payload=dict(call.request_payload or {})
            failures=list(payload.get("response_application_failures", []))
            failures.append({"at":datetime.now(timezone.utc).isoformat(),"message":str(exc)[:500]})
            call.request_payload={**payload,"response_application_failures":failures}
            call.error_class="APPLICATION_FAILURE"; call.error_message=str(exc)[:4000]; call.completed_at=None
            db.commit()

    async def _finalize_received(self, db, call_id):
        """Apply one saved provider response exactly once; never call the provider."""
        from solo_harness.runtime.v04_native import MCQProse, SemanticReview, SubjectiveJudgment, SubjectiveProse, SubjectiveReview, TutorProse
        call=db.scalar(select(LLMCall).where(LLMCall.id==call_id).with_for_update())
        if not call or call.status!="RECEIVED": return
        schemas={"TUTOR":TutorProse,"ASSESSMENT_WRITER":MCQProse if call.request_payload.get("schema_name")=="MCQProse" else SubjectiveProse,"SEMANTIC_REVIEW":SemanticReview if call.request_payload.get("schema_name")=="SemanticReview" else SubjectiveReview,"JUDGE":SubjectiveJudgment}
        schema=schemas.get(call.purpose)
        if schema is None:
            return
        try:
            out=schema.model_validate(_decode(self._saved_candidate(call)))
        except Exception as exc:
            call.status="INVALID_OUTPUT"; call.error_class="VALIDATION_FAILURE"; call.error_message=str(exc)[:4000]; call.completed_at=datetime.now(timezone.utc); db.commit(); return
        try:
            session=db.get(Session,call.session_id); attempt=db.get(Attempt,call.attempt_id)
            # A previously failed local application is now being re-applied.
            # Clear the marker only inside the successful transaction.
            call.error_class=None; call.error_message=None
            if call.purpose in ("ASSESSMENT_WRITER","SEMANTIC_REVIEW"):
                # A received assessment role is applied as its own durable result.
                # Accepted-item checkpoints remain the constructor's recovery boundary.
                call.parsed_response=out.model_dump(mode="json"); call.status="SUCCEEDED"; call.completed_at=datetime.now(timezone.utc); db.commit(); return
            if call.purpose=="TUTOR":
                if not db.scalar(select(Message.id).where(Message.llm_call_id==call.id)):
                    seq=(db.scalar(select(Message.sequence_no).where(Message.attempt_id==attempt.id).order_by(Message.sequence_no.desc())) or 0)+1
                    db.add(Message(attempt_id=attempt.id,sequence_no=seq,role="TUTOR",content_text=out.learner_message,content_format="markdown",llm_call_id=call.id,instructional_trace={"fidelity_note":out.fidelity_note},material_ids=[],exposed_kc_ids=[],exposed_relation_ids=[]))
                call.parsed_response=out.model_dump(mode="json"); call.status="SUCCEEDED"; call.completed_at=datetime.now(timezone.utc)
                build_id=None
                if out.teaching_complete and session.phase=="INTERVENTION_ACTIVE":
                    # The state transition and durable build reservation share one
                    # transaction; a restart can never observe generation with no build.
                    assessment=self.runtime.complete_intervention(db,session.id,"TUTOR_COMPLETE",commit=False)
                    build_id=self.reserve_assessment(db,session.id,assessment.id,commit=False)
                db.commit()
                if build_id: await self.execute(db,build_id)
                return
            call.parsed_response=out.model_dump(mode="json"); call.status="SUCCEEDED"; call.completed_at=datetime.now(timezone.utc)
            if out.gradable_status=="GRADABLE" and out.subjective_points is not None and not out.review_reason:
                from solo_harness.runtime.v04_execution import finalize_v04_evaluation
                if not db.scalar(select(V04Evaluation.id).join(AssessmentResponse, V04Evaluation.assessment_response_id==AssessmentResponse.id).where(AssessmentResponse.assessment_instance_id==call.assessment_instance_id)):
                    finalize_v04_evaluation(db,self.runtime,session.id,out,call.id)
                else: db.commit()
            else:
                call.error_class="REVIEW_HOLD"; call.error_message=out.review_reason; db.commit()
        except Exception as exc:
            self._application_failure(db,call_id,exc)
    async def execute(self,db,call_id):
        call=db.scalar(select(LLMCall).where(LLMCall.id==call_id).with_for_update())
        if not call: return
        if call.status=="RECEIVED": await self._finalize_received(db,call.id); return
        if call.status!="STARTED": return
        if call.purpose=="ASSESSMENT_BUILD":
            session=db.get(Session,call.session_id); attempt=db.get(Attempt,call.attempt_id); await self._freeze(db,call,session,attempt); return
        # Persist the send lease, then release the database transaction before
        # provider I/O and retry sleeps.  A second worker observes SENDING.
        request_payload=dict(call.request_payload); request_body=call.request_body_text; purpose=call.purpose; model=call.model
        call.status="SENDING"; db.commit()
        transient=[]
        try:
            schema=type("Schema",(),{"__name__":request_payload["schema_name"],"model_json_schema":staticmethod(lambda:request_payload["schema"])})
            request=self._request(purpose,tuple(CanonicalMessage.model_validate(x) for x in request_payload["messages"]),model,schema,{})
            prepared=PreparedLLMRequest(request,json.loads(request_body),request_body,{})
            for automatic_attempt in range(3):
                try:
                    raw=await self.client.send(prepared); break
                except ProviderError as exc:
                    transient.append({"attempt":automatic_attempt+1,"error_class":exc.error_class,"message":str(exc)[:500]})
                    if not exc.retryable or automatic_attempt==2: raise
                    await asyncio.sleep(2**automatic_attempt)
            call=db.scalar(select(LLMCall).where(LLMCall.id==call_id).with_for_update())
            if not call or call.status!="SENDING": return
            call.request_payload={**call.request_payload,"automatic_transport_retries":transient}
            call.provider_request_id=raw.provider_request_id; call.raw_response_text=raw.raw_response_text; call.response_payload=raw.response_payload; call.latency_ms=raw.latency_ms; call.status="RECEIVED"; db.commit()
            await self._finalize_received(db,call_id)
        except Exception as exc:
            db.rollback()
            call=db.scalar(select(LLMCall).where(LLMCall.id==call_id).with_for_update())
            if call and call.status=="SENDING":
                call.request_payload={**call.request_payload,"automatic_transport_retries":transient}
                call.status="FAILED"; call.error_class="TECHNICAL_FAILURE"; call.error_message=str(exc)[:4000]; call.completed_at=datetime.now(timezone.utc); db.commit()
    def reserve_manual_retry(self,db,session_id,commit=True,authorized_requeue=False):
        """Retry only the server-side operation that is currently on hold.

        No learner input, assessment response, or frozen package is replaced.
        """
        session=db.scalar(select(Session).where(Session.id==session_id).with_for_update())
        if not session or not session.current_attempt_id: raise ValueError("no active session")
        attempt=db.get(Attempt,session.current_attempt_id)
        if session.phase=="ASSESSMENT_GENERATING":
            item=db.scalar(select(AssessmentInstance).where(AssessmentInstance.attempt_id==attempt.id))
            active=db.scalar(select(LLMCall.id).where(LLMCall.assessment_instance_id==item.id,LLMCall.purpose=="ASSESSMENT_BUILD",LLMCall.status.in_(("STARTED","SENDING","RECEIVED"))))
            previous=db.scalar(select(LLMCall).where(LLMCall.assessment_instance_id==item.id,LLMCall.purpose=="ASSESSMENT_BUILD").order_by(LLMCall.started_at.desc()))
        else:
            active=db.scalar(select(LLMCall.id).where(
                LLMCall.session_id==session.id, LLMCall.attempt_id==attempt.id,
                or_(LLMCall.status.in_(("STARTED","SENDING")), and_(LLMCall.status=="RECEIVED", LLMCall.error_class.is_distinct_from("APPLICATION_FAILURE"))),
            ))
            previous=db.scalar(select(LLMCall).where(LLMCall.session_id==session.id,LLMCall.attempt_id==attempt.id).order_by(LLMCall.started_at.desc()))
        if active: raise ValueError("an operation is already active")
        if previous and previous.status=="RECEIVED" and previous.error_class=="APPLICATION_FAILURE":
            return previous.id
        if not previous or not (previous.status in ("FAILED","INVALID_OUTPUT") or previous.error_class=="REVIEW_HOLD" or (authorized_requeue and previous.status=="TECHNICAL_HOLD")):
            raise ValueError("no recoverable operation")
        if previous.retry_number >= 3 and not authorized_requeue:
            previous.status="TECHNICAL_HOLD"; previous.error_class="RETRY_EXHAUSTED"; previous.error_message="Recovery retry limit exhausted; learner outcome remains unscored."; previous.completed_at=datetime.now(timezone.utc)
            db.commit(); raise ValueError("retry limit exhausted")
        if session.phase=="INTERVENTION_ACTIVE":
            call=self.reserve_tutor(db,session_id,commit=False)
        elif session.phase=="ASSESSMENT_GENERATING":
            call=self.reserve_assessment(db,session_id,item.id,commit=False)
        elif session.phase=="ASSESSMENT_AWAITING_EVALUATION":
            response=db.scalar(select(AssessmentResponse).join(AssessmentInstance,AssessmentResponse.assessment_instance_id==AssessmentInstance.id).where(AssessmentInstance.attempt_id==attempt.id))
            if not response: raise ValueError("no submitted response to retry")
            call=self.reserve_f1_judge(db,session_id,response,commit=False)
        else: raise ValueError("no retryable operation")
        retry=db.get(LLMCall,call)
        retry.retry_group_id=previous.retry_group_id; retry.retry_number=previous.retry_number+1
        retry.request_payload={**retry.request_payload,"retry_of":str(previous.id),"retry_reason":previous.error_class,"authorized_requeue":authorized_requeue}
        if commit: db.commit()
        return call
    def reserve_development_assessment(self,db,session_id,commit=True):
        """Audited escape hatch for local provider verification, never research delivery."""
        if not self.settings.enable_f1_v04_development: raise ValueError("development advance is disabled")
        session=db.get(Session,session_id); attempt=db.get(Attempt,session.current_attempt_id) if session else None
        if not session or not attempt or session.phase!="INTERVENTION_ACTIVE": raise ValueError("development advance is unavailable")
        details=dict(attempt.outcome_details or {}); details["development_only_advance"]={"reason":"NATURAL_TUTOR_COMPLETION_UNAVAILABLE","at":datetime.now(timezone.utc).isoformat()}; attempt.outcome_details=details
        assessment=self.runtime.complete_intervention(db,session.id,"DEVELOPMENT_ONLY_MANUAL_ADVANCE",commit=False)
        call=self.reserve_assessment(db,session.id,assessment.id,commit=False)
        if commit: db.commit()
        return call
