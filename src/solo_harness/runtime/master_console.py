"""Isolated developer launches. No participant route calls this module.

Master-console sessions use the authentic Tutor, fixed assessment, submission and
Judge pathways; only their initial entry point bypasses earlier study sections.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from solo_harness.db.models import AssessmentInstance, Attempt, Session
from solo_harness.runtime.fixed_assessment import construct_fixed_assessment

SECTIONS = ("C1", "C2", "C3", "C4")
PEDAGOGIES = ("P1", "P2", "P3", "random")
SETS = ("A", "B", "C", "random")


def create_master_session(db, runtime, study_version_id, *, section: str, pedagogy: str,
                          mode: str, assessment_set: str = "random", build_id: str = "dev") -> Session:
    """Create one synthetic, auditable, immediately usable internal session.

    The direct-assessment shortcut does not fabricate teaching, Paas, or LLM rows.
    Existing assessment submission/Judge/grading routes remain authoritative.
    """
    if section not in SECTIONS or pedagogy not in PEDAGOGIES or mode not in {"teaching", "assessment"}:
        raise ValueError("unsupported master console selection")
    if assessment_set not in SETS:
        raise ValueError("unsupported fixed assessment set")
    if mode == "teaching" and assessment_set != "random":
        raise ValueError("a fixed assessment set is only selectable in assessment mode")
    compiled = runtime.catalog.load(db, study_version_id)
    if not runtime._v051(compiled) or set(compiled.protocol["transition_ids"]) != set(SECTIONS):
        raise ValueError("master console requires the full immutable C1-C4 study")
    if not set(SECTIONS).issubset((compiled.authored.get("v051") or {}).get("fixed_assessment_banks", {})):
        raise ValueError("all four fixed assessment banks must be registered")

    session = runtime.create_v051_internal_test_session(
        db, study_version_id, build_id=build_id, commit=False,
        controlled_c11_pilot=True, controlled_c1_full_pilot=True,
        unified_controlled_study=True,
        initial_pedagogy_id=None if pedagogy == "random" else pedagogy,
        starting_transition_id=section, direct_assessment=(mode == "assessment"),
    )
    # Synthetic values must match the existing enrollment schema but NEVER
    # indicate that a human consented or provided demographic answers.
    session.institutional_id = "DEV-" + secrets.token_hex(16).upper()
    session.age = 20
    session.gender = "other"
    session.educational_qualification = "undergraduate"
    session.runtime_config_snapshot = {
        **(session.runtime_config_snapshot or {}),
        "master_console_test": True,
        "master_console_entry_section": section,
        "master_console_entry_mode": mode,
        "master_console_selected_pedagogy": pedagogy,
        "master_console_selected_set": assessment_set if mode == "assessment" else None,
        "master_console_synthetic_demographics": True,
        "master_console_no_participant_consent": True,
        "master_console_capture_gate_bypassed": True,
        "master_console_assessment_prerequisites_bypassed": mode == "assessment",
    }
    attempt = db.get(Attempt, session.current_attempt_id)
    runtime._event(db, session, "MASTER_CONSOLE_SESSION_STARTED", {
        "section": section, "mode": mode, "pedagogy_selection": pedagogy,
        "assigned_pedagogy": attempt.pedagogy_id,
        "synthetic_participant": True, "consent_bypassed": True,
        "capture_bypassed": True,
    }, attempt.id)

    if mode == "assessment":
        family = compiled.assessment_families[section]
        forms = [form for form in family["forms"] if form.get("task_type") == "V051_FIXED_ASSESSMENT"]
        if len(forms) != 3:
            raise ValueError("fixed assessment forms are unavailable")
        if assessment_set == "random":
            decision = runtime.selector.choose([form["id"] for form in forms])
            selected_id = decision.selected_id
            method = decision.selection_method
        else:
            selected_id = f"{section}-SET-{assessment_set}"
            method = "master_console_explicit_set"
        form = next((form for form in forms if form["id"] == selected_id), None)
        if form is None:
            raise ValueError("selected assessment set is not registered")
        package = construct_fixed_assessment(compiled, form)
        now = datetime.now(timezone.utc)
        selection_audit = {
            "selected_id": selected_id,
            "eligible_candidate_ids": sorted(f["id"] for f in forms),
            "excluded_used_ids": [],
            "selection_method": method,
            "master_console_direct_assessment": True,
            "timestamp": now.isoformat(),
        }
        db.add(AssessmentInstance(
            session_id=session.id, attempt_id=attempt.id, transition_id=section,
            assessment_family_id=family["id"], assessment_form_id=selected_id,
            status="ACTIVE", candidate_form_ids=selection_audit["eligible_candidate_ids"],
            selection_method=method, selection_audit=selection_audit,
            blueprint_snapshot=form,
            resolved_component_ids={
                "kc_ids": form["target_kc_ids"],
                "relation_ids": form["target_relation_ids"],
                "evidence_ids": form["target_evidence_ids"],
                "misconception_ids": form["relevant_misconception_ids"],
            },
            frozen_public_snapshot=package["public"],
            frozen_private_snapshot=package["private"],
            frozen_metadata_snapshot={**package["metadata"], "master_console_direct_assessment": True},
            frozen_package_fingerprint=package["fingerprint"],
            frozen_schema_version="v051.fixed.1", delivery_status=package["status"],
            frozen_at=now,
        ))
        attempt.status = "ASSESSMENT_ACTIVE"
        session.phase = "ASSESSMENT_ACTIVE"
        session.started_at = now
        runtime._event(db, session, "MASTER_CONSOLE_ASSESSMENT_OPENED", {
            "form_id": selected_id, "selection_method": method,
            "fingerprint": package["fingerprint"],
            "teaching_completed": False, "paas_recorded": False,
        }, attempt.id)
    db.commit()
    return session


def is_master_session(session: Session | None) -> bool:
    return bool(session and isinstance(session.runtime_config_snapshot, dict)
                and session.runtime_config_snapshot.get("internal_v051_testing") is True
                and session.runtime_config_snapshot.get("master_console_test") is True)
