from dataclasses import dataclass

from solo_harness.studies.authored.models import AuthoredStudy


class StudyValidationError(ValueError):
    pass


def _ids(items, label: str) -> set[str]:
    values = [x.id for x in items]
    if len(values) != len(set(values)):
        raise StudyValidationError(f"duplicate {label} IDs")
    return set(values)


def validate(study: AuthoredStudy) -> None:
    def substantive(value: str, label: str, minimum: int = 60):
        if not isinstance(value, str) or len(value.strip()) < minimum:
            raise StudyValidationError(f"{label} is missing or placeholder-like")

    if len(study.knowledge.knowledge_components) != 14 or len(study.knowledge.relations) != 12 or len(study.knowledge.misconceptions) != 10:
        raise StudyValidationError("knowledge pack must contain K1-K14, R1-R12, and M1-M10")
    if len(study.knowledge.solo_states) != 5 or len(study.knowledge.transitions) != 4:
        raise StudyValidationError("knowledge pack must contain five SOLO states and four transitions")
    if len(study.pedagogies) != 3 or len(study.cells) != 12:
        raise StudyValidationError("intervention pack must contain three pedagogies and twelve cells")
    if len(study.tutor_prompt_recipes) != 3 or {r.pedagogy_id for r in study.tutor_prompt_recipes} != {p.id for p in study.pedagogies}:
        raise StudyValidationError("one Tutor prompt recipe per pedagogy is required")
    substantive(study.knowledge.prerequisite_assumptions, "prerequisite assumptions")
    for key, value in study.knowledge.conceptual_frontier.items():
        substantive(value, f"conceptual frontier {key}")
    for item in study.knowledge.knowledge_components:
        substantive(item.definition, f"knowledge component {item.id}", 25)
    for item in study.knowledge.relations:
        substantive(item.definition, f"relation {item.id}", 25)
    for item in study.knowledge.misconceptions:
        substantive(item.definition, f"misconception {item.id}", 25)
    for item in study.knowledge.solo_states:
        substantive(item.definition, f"SOLO state {item.id}", 20)
    for transition in study.knowledge.transitions:
        substantive(transition.structural_change, f"transition {transition.id} structural change", 30)
        substantive(transition.assumed_at_entry, f"transition {transition.id} assumed knowledge", 10)
        substantive(transition.canonical_slice, f"transition {transition.id} canonical slice")
    for pedagogy in study.pedagogies:
        substantive(pedagogy.core_mechanism, f"pedagogy {pedagogy.id} mechanism")
        substantive(pedagogy.tutor_role, f"pedagogy {pedagogy.id} Tutor role")
        substantive(pedagogy.prohibited_behavior, f"pedagogy {pedagogy.id} prohibitions")
        substantive(pedagogy.treatment_fidelity_test, f"pedagogy {pedagogy.id} fidelity test")
    kc_ids = _ids(study.knowledge.knowledge_components, "knowledge component")
    rel_ids = _ids(study.knowledge.relations, "relation")
    misconception_ids = _ids(study.knowledge.misconceptions, "misconception")
    state_ids = _ids(study.knowledge.solo_states, "SOLO state")
    transition_ids = _ids(study.knowledge.transitions, "transition")
    pedagogy_ids = _ids(study.pedagogies, "pedagogy")
    cell_ids = _ids(study.cells, "intervention cell")
    family_ids = _ids(study.assessment_families, "assessment family")
    rubric_ids = _ids(study.judge_rubrics, "Judge rubric")
    if study.protocol.initial_state_id not in state_ids:
        raise StudyValidationError("protocol initial state does not exist")
    if [t.id for t in study.knowledge.transitions] != study.protocol.transition_ids:
        raise StudyValidationError("protocol transition order does not match knowledge transitions")
    if set(study.protocol.pedagogy_ids) != pedagogy_ids:
        raise StudyValidationError("protocol pedagogies do not match configured pedagogies")
    for transition in study.knowledge.transitions:
        if transition.from_state_id not in state_ids or transition.target_state_id not in state_ids:
            raise StudyValidationError(f"transition {transition.id} has unknown state")
        if not set(transition.target_kc_ids).issubset(kc_ids) or not set(transition.target_relation_ids).issubset(rel_ids):
            raise StudyValidationError(f"transition {transition.id} has broken knowledge reference")
        if not set(transition.relevant_misconception_ids).issubset(misconception_ids):
            raise StudyValidationError(f"transition {transition.id} has broken misconception reference")
    expected_cells = {(t, p) for t in transition_ids for p in pedagogy_ids}
    actual_cells = {(c.transition_id, c.pedagogy_id) for c in study.cells}
    if actual_cells != expected_cells or len(cell_ids) != len(expected_cells):
        raise StudyValidationError("intervention matrix must contain exactly one cell for every transition/pedagogy pair")
    for cell in study.cells:
        if not set(cell.target_kc_ids).issubset(kc_ids) or not set(cell.target_relation_ids).issubset(rel_ids):
            raise StudyValidationError(f"cell {cell.id} has broken knowledge reference")
        if not set(cell.relevant_misconception_ids).issubset(misconception_ids):
            raise StudyValidationError(f"cell {cell.id} has broken misconception reference")
        transition = next(t for t in study.knowledge.transitions if t.id == cell.transition_id)
        if set(cell.target_kc_ids) & set(transition.future_kc_ids):
            raise StudyValidationError(f"cell {cell.id} targets future knowledge")
        if not cell.moves or cell.move_ids != [move.id for move in cell.moves]:
            raise StudyValidationError(f"cell {cell.id} lacks ordered intervention moves")
        for move in cell.moves:
            if move.transition_id != cell.transition_id or move.pedagogy_id != cell.pedagogy_id:
                raise StudyValidationError(f"move {move.id} is assigned to the wrong cell")
            if not set(move.kc_ids).issubset(kc_ids) or not set(move.relation_ids).issubset(rel_ids) or not set(move.misconception_ids).issubset(misconception_ids):
                raise StudyValidationError(f"move {move.id} has a broken component reference")
            if not set(move.next_move_ids).issubset(set(cell.move_ids)):
                raise StudyValidationError(f"move {move.id} has an invalid next move")
            substantive(move.material_blueprint, f"move {move.id} blueprint", 25)
        substantive(cell.completion_condition, f"cell {cell.id} completion guidance", 30)
    if {f.transition_id for f in study.assessment_families} != transition_ids or len(family_ids) != len(transition_ids):
        raise StudyValidationError("one assessment family per transition is required")
    for family in study.assessment_families:
        _ids(family.forms, f"assessment form in {family.id}")
        if len(family.forms) != 4:
            raise StudyValidationError(f"assessment family {family.id} has insufficient forms; exactly four are required")
        substantive(family.construct_text, f"assessment family {family.id} construct")
        substantive(family.equivalence_envelope, f"assessment family {family.id} equivalence envelope")
        for form in family.forms:
            substantive(form.generation_goal, f"assessment blueprint {form.id} goal", 30)
            substantive(form.scenario_seed, f"assessment blueprint {form.id} scenario seed", 25)
            if not form.required_response_features:
                raise StudyValidationError(f"assessment blueprint {form.id} lacks response features")
            if not set(form.target_kc_ids).issubset(kc_ids) or not set(form.target_relation_ids).issubset(rel_ids):
                raise StudyValidationError(f"assessment blueprint {form.id} has broken knowledge reference")
    if {r.transition_id for r in study.judge_rubrics} != transition_ids or len(rubric_ids) != len(transition_ids):
        raise StudyValidationError("one Judge rubric per transition is required")
    for rubric in study.judge_rubrics:
        if rubric.target_state_id not in state_ids or not set(rubric.blocking_misconception_ids).issubset(misconception_ids):
            raise StudyValidationError(f"rubric {rubric.id} has broken reference")
        evidence = {criterion.id: criterion for criterion in rubric.evidence_criteria}
        if set(evidence) != set(rubric.evidence_ids):
            raise StudyValidationError(f"rubric {rubric.id} evidence definitions do not match evidence IDs")
        for evidence_id, criterion in evidence.items():
            substantive(criterion.definition, f"rubric evidence {evidence_id}", 45)
        substantive(rubric.core_target, f"rubric {rubric.id} core target", 25)
        substantive(rubric.success_rule_text, f"rubric {rubric.id} success rule")
        family = next(item for item in study.assessment_families if item.transition_id == rubric.transition_id)
        for form in family.forms:
            if not set(form.target_evidence_ids).issubset(set(rubric.evidence_ids)):
                raise StudyValidationError(f"assessment {form.id} references evidence outside rubric {rubric.id}")
