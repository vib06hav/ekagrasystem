"""Fast contract checks for Tutor-first subsection review timing."""
import json
from pathlib import Path
from types import SimpleNamespace

from solo_harness.runtime.v051_conversation import (
    ConversationJudgeOutput, V051TutorOutput, conversation_judge_prompt, v051_tutor_prompt,
)
from solo_harness.studies.scientific_v051 import load_scientific_v051
from solo_harness.studies.v051_native_compiler import compile_v051, resolve_v051_tutor_context


SOURCE = Path("studies/networks_error_detection_parity_f1/v0.5.1")


def test_tutor_review_readiness_does_not_require_an_extra_learner_turn():
    compiled = compile_v051(load_scientific_v051(SOURCE))
    context = resolve_v051_tutor_context(compiled, "C1.1", "P1")
    prompt = v051_tutor_prompt(compiled, SimpleNamespace(subsection_id="C1.1"), context, [], None, None)
    payload = json.loads(prompt.split("[V051_ACTIVE_SUBSECTION_TUTOR_CONTEXT]\n", 1)[1].split("\n\n[OUTPUT_SCHEMA]", 1)[0])
    assert payload["runtime_rules"]["judge_review_follows_tutor_readiness_without_mandatory_learner_turn"]
    assert "wait_for_a_real_learner_turn_before_judge_review" not in payload["runtime_rules"]
    assert set(V051TutorOutput.model_fields) == {"learner_message", "ready_for_judge"}


def test_judge_prompt_supports_zero_learner_turns_without_requiring_identifiers():
    compiled = compile_v051(load_scientific_v051(SOURCE))
    context = resolve_v051_tutor_context(compiled, "C1.1", "P1")
    prompt = conversation_judge_prompt(compiled, SimpleNamespace(subsection_id="C1.1"), context,
                                        [{"role": "TUTOR", "content": "Some instruction."}], None)
    payload = json.loads(prompt.split("[V051_CONVERSATION_JUDGE_CONTEXT]\n", 1)[1].split("\n\n[OUTPUT_SCHEMA]", 1)[0])
    assert payload["dialogue"] == [{"role": "TUTOR", "content": "Some instruction."}]
    assert "latest_learner_message_id" not in payload
    assert set(ConversationJudgeOutput.model_fields) == {"decision", "guidance"}
