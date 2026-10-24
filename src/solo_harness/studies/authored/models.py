from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class StudyManifest(StrictModel):
    study_id: str
    content_version: str
    study_schema_version: str
    title: str
    markdown_provenance: dict[str, str] = Field(default_factory=dict)
    files: dict[str, object]


class KnowledgeComponent(StrictModel):
    id: str
    name: str
    definition: str


class Relation(StrictModel):
    id: str
    name: str
    definition: str
    kc_ids: list[str] = Field(default_factory=list)


class Misconception(StrictModel):
    id: str
    name: str
    definition: str
    conflicts_with: list[str] = Field(default_factory=list)


class SoloState(StrictModel):
    id: str
    definition: str


class Transition(StrictModel):
    id: str
    from_state_id: str
    target_state_id: str
    target_kc_ids: list[str]
    target_relation_ids: list[str] = Field(default_factory=list)
    relevant_misconception_ids: list[str] = Field(default_factory=list)
    future_kc_ids: list[str] = Field(default_factory=list)
    structural_change: str
    assumed_at_entry: str
    target_structure: dict[str, str]
    relevant_misconception_guidance: str
    not_yet_required: str
    canonical_slice: str


class KnowledgePack(StrictModel):
    topic_id: str
    domain: str
    topic: str
    prerequisite_assumptions: str
    conceptual_frontier: dict[str, str]
    in_scope: list[str]
    out_of_scope: list[str]
    knowledge_components: list[KnowledgeComponent]
    relations: list[Relation]
    misconceptions: list[Misconception]
    solo_states: list[SoloState]
    transitions: list[Transition]


class PedagogyFamily(StrictModel):
    id: str
    name: str
    core_mechanism: str
    permissions: list[str] = Field(default_factory=list)
    prohibitions: list[str] = Field(default_factory=list)
    tutor_role: str
    prohibited_behavior: str
    treatment_fidelity_test: str


class ProcedureStage(StrictModel):
    id: str
    title: str
    guidance: str


class AuthoredGuidanceSection(StrictModel):
    id: str
    title: str
    content: str


class TutorPromptRecipe(StrictModel):
    id: str
    pedagogy_id: str
    role_instruction: str
    move_generation_instruction: str
    learner_check_instruction: str
    completion_instruction: str
    prohibited_behavior: list[str] = Field(default_factory=list)


class InterventionMove(StrictModel):
    id: str
    transition_id: str
    pedagogy_id: str
    title: str
    purpose: str
    kc_ids: list[str] = Field(default_factory=list)
    relation_ids: list[str] = Field(default_factory=list)
    misconception_ids: list[str] = Field(default_factory=list)
    material_blueprint: str
    allowed_behavior: list[str] = Field(default_factory=list)
    prohibited_behavior: list[str] = Field(default_factory=list)
    completion_evidence: str
    next_move_ids: list[str] = Field(default_factory=list)


class InterventionCell(StrictModel):
    id: str
    transition_id: str
    pedagogy_id: str
    instructional_intent: str
    missing_structure: str
    target_kc_ids: list[str]
    target_relation_ids: list[str] = Field(default_factory=list)
    relevant_misconception_ids: list[str] = Field(default_factory=list)
    move_ids: list[str]
    moves: list[InterventionMove]
    prohibitions: list[str] = Field(default_factory=list)
    completion_condition: str
    treatment_constraints: str
    max_tutor_turns: int = Field(gt=0)
    elapsed_budget_seconds: int | None = Field(default=None, gt=0)


class AssessmentForm(StrictModel):
    id: str
    title: str
    task_type: str
    generation_goal: str
    scenario_seed: str
    equivalence_constraints: list[str]
    required_response_features: list[str]
    misconception_probes: list[str]
    prohibited_leakage: list[str]
    target_kc_ids: list[str]
    target_relation_ids: list[str]
    material_tag: str
    target_evidence_ids: list[str]
    relevant_misconception_ids: list[str]


class AssessmentFamily(StrictModel):
    id: str
    transition_id: str
    construct_text: str = Field(alias="construct")
    required_evidence_overview: str
    equivalence_envelope: str
    global_rules: dict[str, str]
    forms: list[AssessmentForm]


class JudgeContract(StrictModel):
    id: str
    instructions: list[str]
    forbidden_inputs: list[str]
    generic_contract: str
    output_concepts: str
    solo_interpretation: dict[str, str]
    correctness_policy: str


class EvidenceCriterion(StrictModel):
    id: str
    name: str
    definition: str


class JudgeRubric(StrictModel):
    id: str
    transition_id: str
    target_state_id: str
    evidence_ids: list[str]
    blocking_misconception_ids: list[str] = Field(default_factory=list)
    success_rule: dict[str, object]
    target_state_definition: str
    core_target: str
    correctness_expectations: str
    evidence_criteria: list[EvidenceCriterion]
    state_guidance: dict[str, str]
    blocking_misconception_guidance: str
    success_rule_text: str


class ProtocolConfig(StrictModel):
    initial_state_id: str
    transition_ids: list[str]
    pedagogy_ids: list[str]
    max_attempts_per_transition: int = Field(gt=0)
    assessment_strategy: Literal["random_unseen"]
    pedagogy_strategy: Literal["random_without_replacement"]
    renewed_cycle: bool = False
    authored_rules: dict[str, str]


class AuthoredStudy(StrictModel):
    manifest: StudyManifest
    knowledge: KnowledgePack
    pedagogies: list[PedagogyFamily]
    tutor_prompt_recipes: list[TutorPromptRecipe]
    cells: list[InterventionCell]
    assessment_families: list[AssessmentFamily]
    judge_contract: JudgeContract
    judge_rubrics: list[JudgeRubric]
    protocol: ProtocolConfig
    shared_intervention_envelope: dict[str, str]
