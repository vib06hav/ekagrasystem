import json
import uuid
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from solo_harness.runtime.ai import AssessmentGenerationOutput, CanonicalMessage, JudgeOutput, LLMRequest, PreparedLLMRequest, PromptCompiler, ProviderError, TutorTurnOutput, _decode_json_text, _provider_content_candidate, _validate_openai_strict_schema, validate_generated_assessment, validate_judge_evidence_scope


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


@pytest.mark.parametrize("correctness", ["CORRECT", "MINOR_ERROR", "MATERIALLY_INCORRECT"])
def test_judge_contract_accepts_each_gradable_correctness_value(correctness):
    assert JudgeOutput.model_validate(judge_payload(correctness=correctness)).correctness == correctness


def test_judge_contract_derives_not_gradable_without_redundant_boolean():
    value = JudgeOutput.model_validate(judge_payload(
        correctness="NOT_GRADABLE",
        not_gradable_reason="OFF_TOPIC",
        observed_solo_state_id=None,
    ))
    assert not value.gradable
    assert "gradable" not in value.model_dump()


@pytest.mark.parametrize("overrides", [
    {"not_gradable_reason": "OFF_TOPIC"},
    {"correctness": "NOT_GRADABLE", "not_gradable_reason": "UNINTERPRETABLE", "observed_solo_state_id": "R"},
    {"correctness": "NOT_GRADABLE", "observed_solo_state_id": None},
    {"observed_solo_state_id": None},
])
def test_judge_contract_rejects_conflicting_gradability_fields(overrides):
    with pytest.raises(ValidationError):
        JudgeOutput.model_validate(judge_payload(**overrides))


def test_judge_contract_accepts_not_gradable_only_with_consistent_fields():
    value = JudgeOutput.model_validate(judge_payload(
        correctness="NOT_GRADABLE",
        not_gradable_reason="UNINTERPRETABLE",
        observed_solo_state_id=None,
    ))
    assert not value.gradable


@pytest.mark.parametrize("alias", ["PARTIAL", "NOT_DEMONSTRATED", "CONTRADICTED"])
def test_judge_contract_rejects_correctness_aliases(alias):
    with pytest.raises(ValidationError):
        JudgeOutput.model_validate(judge_payload(correctness=alias))


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
    assert "at most 300 characters" in provider_text
    assert "at most 700 characters" in provider_text


@pytest.mark.parametrize("transition_id", ["C1", "C2", "C3", "C4"])
def test_new_judge_prompt_has_scoped_authored_guidance_and_no_treatment_data(transition_id):
    from pathlib import Path
    from solo_harness.studies.compiler import compile_study
    from solo_harness.studies.loader import load
    study = compile_study(load(Path("studies/python_fibonacci_memoization/v0.5")))
    version = SimpleNamespace(id=uuid.uuid4(), content_hash="a" * 64, compiler_contract_version="3.1", snapshot_hash="b" * 64)
    blueprint = study.assessment_families[transition_id]["forms"][0]
    assessment = SimpleNamespace(id=uuid.uuid4(), transition_id=transition_id, assessment_form_id=blueprint["id"], blueprint_snapshot=blueprint, resolved_component_ids={}, prompt_snapshot="Explain the task in your own words.", hidden_scoring_context_snapshot="Private item context.")
    envelope = PromptCompiler().compile_judge(version, study, assessment, SimpleNamespace(response_text="Learner response."))
    provider_text = "\n".join(item.content for item in envelope.ordered_messages)
    assert "[AUTHORED_JUDGE_CONTRACT]" in provider_text and "[SELECTED_RUBRIC_GUIDANCE]" in provider_text
    assert len(envelope.canonical_prompt_text) <= PromptCompiler.MAX_JUDGE_CHARS
    assert "P1" not in provider_text and "Tutor conversation" not in provider_text


def test_assessment_resolver_uses_explicit_transition_not_blueprint_id_prefix():
    from pathlib import Path
    from solo_harness.studies.compiler import compile_study
    from solo_harness.studies.loader import load
    study = compile_study(load(Path("studies/python_fibonacci_memoization/v0.5")))
    blueprint = dict(study.assessment_families["C1"]["forms"][0]); blueprint["id"] = "unrelated-name"
    study.assessment_families["C1"]["forms"][0]["id"] = "unrelated-name"
    assert PromptCompiler().resolver.assessment(study, blueprint, "C1")["blueprint"]["id"] == "unrelated-name"
    with pytest.raises(ValueError, match="does not belong"):
        PromptCompiler().resolver.assessment(study, blueprint, "C2")


def test_json_text_contract_accepts_fenced_json_and_content_parts():
    assert _decode_json_text("```json\n{\"schema_version\":\"1.0\"}\n```") == {"schema_version": "1.0"}
    payload = {"choices": [{"message": {"content": [{"type": "text", "text": "{\"ok\":"}, {"type": "text", "text": "true}"}]}}]}
    assert _provider_content_candidate(payload) == '{"ok":true}'


@pytest.mark.parametrize("text", ["note {\"schema_version\":\"1.0\"}", "{\"schema_version\":\"1.0\"} trailing", "```json\n{\"schema_version\":\"1.0\"}\n```"])
def test_new_json_contract_rejects_non_object_wrapping(text):
    with pytest.raises(ValueError):
        _decode_json_text(text, strict=True)


def test_new_json_contract_accepts_one_complete_object_with_whitespace_or_bom():
    assert _decode_json_text("\ufeff  {\"schema_version\":\"1.0\"}\n", strict=True) == {"schema_version": "1.0"}


def test_generated_assessment_gate_accepts_matching_function_and_rejects_mismatch_or_leakage():
    from pathlib import Path
    fixtures = json.loads((Path(__file__).parent / "fixtures/generated_assessments.json").read_text(encoding="utf-8"))
    blueprint = {"required_response_features": ["uses recurrence explanation"]}
    matching = AssessmentGenerationOutput(schema_version="1.0", **fixtures["valid_compute_term"])
    validate_generated_assessment(matching, blueprint)
    mismatch = AssessmentGenerationOutput(schema_version="1.0", **fixtures["invalid_compute_term_fib"])
    with pytest.raises(ValueError, match="different learner-facing function"):
        validate_generated_assessment(mismatch, blueprint)
    leak = AssessmentGenerationOutput(schema_version="1.0", **fixtures["invalid_leakage"])
    with pytest.raises(ValueError, match="leaks"):
        validate_generated_assessment(leak, blueprint)


def test_judge_evidence_scope_requires_exactly_once_and_not_gradable_empty_arrays():
    evidence = {"status": "DEMONSTRATED", "citations": [], "concise_summary": "Shown."}
    misconception = {"status": "NOT_DETECTED", "citations": [], "concise_summary": "Absent."}
    blueprint = {"target_evidence_ids": ["E1", "E2"], "relevant_misconception_ids": ["M1"]}
    valid = JudgeOutput.model_validate(judge_payload(criterion_evidence=[{**evidence, "criterion_id": "E1"}, {**evidence, "criterion_id": "E2"}], misconception_evidence=[{**misconception, "misconception_id": "M1"}]))
    validate_judge_evidence_scope(valid, blueprint)
    duplicate = valid.model_copy(update={"criterion_evidence": [valid.criterion_evidence[0], valid.criterion_evidence[0]]})
    with pytest.raises(ValueError, match="exactly once"):
        validate_judge_evidence_scope(duplicate, blueprint)
    not_gradable = JudgeOutput.model_validate(judge_payload(correctness="NOT_GRADABLE", not_gradable_reason="OFF_TOPIC", observed_solo_state_id=None, criterion_evidence=[] , misconception_evidence=[]))
    validate_judge_evidence_scope(not_gradable, blueprint)


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
