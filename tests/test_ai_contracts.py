import json
import uuid
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from solo_harness.runtime.ai import AssessmentGenerationOutput, CanonicalMessage, JudgeOutput, LLMRequest, PreparedLLMRequest, PromptCompiler, ProviderError, TutorTurnOutput, _decode_json_text, _provider_content_candidate, _validate_openai_strict_schema


def judge_payload(**overrides):
    payload = {
        "schema_version": "1.0",
        "not_gradable_reason": None,
        "correctness": "CORRECT",
        "observed_solo_state_id": "U",
        "criterion_evidence": [],
        "misconception_evidence": [],
        "confidence": None,
        "ambiguity_summary": None,
        "overall_evidence_summary": "Evidence present.",
    }
    payload.update(overrides)
    return payload


class UnitLLMClient:
    """Unit-test-only request preparation double."""
    def prepare(self, request):
        body = {"model": request.model, "messages": [message.model_dump() for message in request.messages], "response_schema": request.response_json_schema, **request.generation_parameters}
        return PreparedLLMRequest(request, body, json.dumps(body, sort_keys=True, separators=(",", ":")), {"Authorization": "Bearer [REDACTED]", "Content-Type": "application/json"})


def test_tutor_contract_accepts_a_valid_structured_turn():
    value = TutorTurnOutput.model_validate({"schema_version": "1.0", "learner_message": "Try the base cases first.", "disposition": "CONTINUE", "current_move_id": "C1-P2-MOVE-1", "next_move_id": None, "progress_summary": "Discussed base cases."})
    assert value.current_move_id == "C1-P2-MOVE-1"


def test_judge_contract_discards_inapplicable_not_gradable_reason():
    value = JudgeOutput.model_validate(judge_payload(not_gradable_reason="OFF_TOPIC"))
    assert value.not_gradable_reason is None


def test_judge_contract_derives_not_gradable_without_redundant_boolean():
    value = JudgeOutput.model_validate(judge_payload(
        correctness="NOT_GRADABLE",
        not_gradable_reason="OFF_TOPIC",
        observed_solo_state_id=None,
    ))
    assert not value.gradable
    assert "gradable" not in value.model_dump()


def test_judge_contract_discards_observed_state_when_not_gradable():
    value = JudgeOutput.model_validate(judge_payload(
        correctness="NOT_GRADABLE",
        not_gradable_reason="UNINTERPRETABLE",
        observed_solo_state_id="R",
    ))
    assert value.observed_solo_state_id is None


def test_judge_contract_supplies_generic_reason_for_explicit_not_gradable_result():
    value = JudgeOutput.model_validate(judge_payload(correctness="NOT_GRADABLE", observed_solo_state_id=None))
    assert value.not_gradable_reason == "INSUFFICIENT_TO_EVALUATE"


def test_judge_normalizes_provider_evidence_synonym_without_fabricating_evidence():
    value=JudgeOutput.model_validate(judge_payload(correctness="PARTIAL", overall_evidence_summary="Some evidence."))
    assert value.correctness=="MINOR_ERROR" and value.criterion_evidence==[]


def test_test_client_preserves_exact_prepared_request():
    client = UnitLLMClient()
    request = LLMRequest("TUTOR", uuid.uuid4(), uuid.uuid4(), 0, "fake", "fake-model", (CanonicalMessage(role="system", content="contract"),), "Example", "1.0", {"type": "object"}, {"temperature": 0}, 10, {})
    prepared = client.prepare(request)
    assert json.loads(prepared.body_text) == prepared.body
    assert prepared.redacted_headers["Authorization"] == "Bearer [REDACTED]"


def test_judge_prompt_is_blind_to_treatment_and_dialogue():
    from pathlib import Path
    from solo_harness.studies.compiler import compile_study
    from solo_harness.studies.loader import load
    compiler = PromptCompiler(); study = compile_study(load(Path("studies/python_fibonacci_memoization/v0.1")))
    version = SimpleNamespace(id=uuid.uuid4(), content_hash="a" * 64, compiler_contract_version="3.0", snapshot_hash="b" * 64)
    blueprint=study.assessment_families["C1"]["forms"][0]
    assessment = SimpleNamespace(id=uuid.uuid4(), transition_id="C1", assessment_form_id=blueprint["id"], blueprint_snapshot=blueprint, resolved_component_ids={}, prompt_snapshot="Explain this response.", hidden_scoring_context_snapshot="private item context")
    response = SimpleNamespace(response_text="My answer is n-1.")
    envelope = compiler.compile_judge(version, study, assessment, response)
    provider_text = "\n".join(item.content for item in envelope.ordered_messages)
    assert "P1" not in provider_text
    assert "prior-attempt" not in provider_text.lower()
    assert "Tutor dialogue" not in provider_text


def test_json_text_contract_accepts_fenced_json_and_content_parts():
    assert _decode_json_text("```json\n{\"schema_version\":\"1.0\"}\n```") == {"schema_version": "1.0"}
    payload = {"choices": [{"message": {"content": [{"type": "text", "text": "{\"ok\":"}, {"type": "text", "text": "true}"}]}}]}
    assert _provider_content_candidate(payload) == '{"ok":true}'


def test_judge_schema_uses_distinct_evidence_identifier_objects():
    schema = JudgeOutput.model_json_schema()
    assert schema["$defs"]["CriterionEvidence"]["required"] == ["status", "citations", "concise_summary", "criterion_id"]
    assert schema["$defs"]["MisconceptionEvidence"]["required"] == ["misconception_id", "status", "citations", "concise_summary"]
    assert "kc_evidence" not in schema["properties"] and "relation_evidence" not in schema["properties"]


def test_all_ai_contracts_are_valid_openai_strict_schemas():
    for model in (TutorTurnOutput, AssessmentGenerationOutput, JudgeOutput):
        _validate_openai_strict_schema(model.model_json_schema())


def test_provider_native_mode_sends_strict_json_schema():
    client = object.__new__(__import__("solo_harness.runtime.ai", fromlist=["OpenAICompatibleClient"]).OpenAICompatibleClient)
    client.base_url = "https://example.invalid/v1"
    client.api_key = "test-key"
    client.structured_output_mode = "provider_native_json_schema"
    request = LLMRequest("JUDGE", uuid.uuid4(), uuid.uuid4(), 0, "test", "test-model", (CanonicalMessage(role="system", content="contract"),), "JudgeOutput", "1.0", JudgeOutput.model_json_schema(), {"max_tokens": 6000}, 10, {})
    prepared = client.prepare(request)
    assert prepared.body["response_format"]["type"] == "json_schema"
    assert prepared.body["response_format"]["json_schema"]["strict"] is True


def test_strict_schema_validator_rejects_optional_object_properties():
    with pytest.raises(ProviderError, match="require every property"):
        _validate_openai_strict_schema({
            "type": "object",
            "additionalProperties": False,
            "properties": {"required_value": {"type": "string"}, "optional_value": {"type": "string"}},
            "required": ["required_value"],
        })


def test_assessment_contract_is_generated_prose_plus_hidden_context_only():
    value = AssessmentGenerationOutput.model_validate({"schema_version":"1.0","learner_prompt":"Explain how this recursive program should combine its smaller calls.","hidden_scoring_context":"Require the two predecessor relationship and correct base cases."})
    assert "recursive" in value.learner_prompt


def test_tutor_prompt_is_component_scoped_and_uses_only_last_two_exchanges():
    from pathlib import Path
    from solo_harness.studies.compiler import compile_study
    from solo_harness.studies.loader import load
    study=compile_study(load(Path("studies/python_fibonacci_memoization/v0.1")))
    version=SimpleNamespace(id=uuid.uuid4(),content_hash="a"*64,compiler_contract_version="3.0",snapshot_hash="b"*64)
    dialogue=[]
    for n in range(6):
        dialogue.append(SimpleNamespace(role="TUTOR",content_text=f"old tutor {n}",instructional_trace={"current_move_id":"C1-P2-MOVE-1","next_move_id":"C1-P2-MOVE-1","progress_summary":"compact"}))
        dialogue.append(SimpleNamespace(role="LEARNER",content_text=f"old learner {n}",instructional_trace=None))
    envelope=PromptCompiler().compile_tutor(version,study,study.cells["C1:P2"],None,dialogue)
    text="\n".join(x.content for x in envelope.ordered_messages)
    assert "old tutor 3" not in text and "old learner 3" not in text
    assert "old tutor 4" in text and "old learner 5" in text
    assert '"K14"' not in text and '"M10"' not in text and "ASSESSMENT_BLUEPRINT" not in text and "criterion_evidence" not in text
    assert envelope.audit_context["prompt_chars"] < PromptCompiler.MAX_TUTOR_CHARS


def test_all_assessment_blueprints_have_no_frozen_prompt_fields():
    from pathlib import Path
    from solo_harness.studies.loader import load
    study=load(Path("studies/python_fibonacci_memoization/v0.1"))
    forms=[f for family in study.assessment_families for f in family.forms]
    assert len(forms)==16
    for form in forms:
        data=form.model_dump()
        assert "prompt" not in data and "hidden_scoring_context" not in data
        assert form.generation_goal and form.required_response_features
