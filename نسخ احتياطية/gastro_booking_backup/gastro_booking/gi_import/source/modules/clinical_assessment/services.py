"""Clinical Assessment orchestration services."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.clinical_assessment.ai_generator import AssessmentAIGenerator
from app.modules.clinical_assessment.catalogue_seed import seed_diagnosis_rules_if_empty
from app.modules.clinical_assessment.constants import (
    AUDIT_PREFIX,
    RUN_STATUS_FINALIZED,
    RUN_STATUS_GENERATED,
    RUN_STATUS_REVIEWED,
    STATUS_ACCEPTED,
    STATUS_CONFIRMED,
    STATUS_MANUAL,
    STATUS_MODIFIED,
    STATUS_REJECTED,
    STATUS_SUGGESTED,
    STATUS_SUSPECTED,
)
from app.modules.clinical_assessment.context_builder import AssessmentContextBuilder
from app.modules.clinical_assessment.differential_engine import DifferentialDiagnosisEngine
from app.modules.clinical_assessment.models import (
    ClinicalAssessmentRun,
    DiagnosisSuggestion,
    PhysicianDiagnosisDecision,
)
from app.modules.clinical_assessment.permissions import require_assessment_use, require_assessment_view
from app.modules.clinical_history_ai.constants import DRAFT_STATUS_APPROVED, SESSION_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistoryDraft, GuidedHistorySession
from app.modules.encounters.models import ClinicalEncounter


def ensure_rules_seeded() -> int:
    return seed_diagnosis_rules_if_empty()


def generate_assessment(acting_user, encounter_id: int) -> ClinicalAssessmentRun:
    require_assessment_use(acting_user)
    ensure_rules_seeded()

    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")

    history_session = GuidedHistorySession.query.filter_by(
        encounter_id=encounter_id, is_archived=False
    ).first()
    if history_session is None or history_session.status != SESSION_STATUS_APPROVED:
        raise ValidationError("Approved structured history is required before differential assessment.")

    approved_draft = (
        GuidedHistoryDraft.query.filter_by(
            session_id=history_session.id,
            status=DRAFT_STATUS_APPROVED,
            is_archived=False,
        )
        .order_by(GuidedHistoryDraft.created_at.desc())
        .first()
    )
    if approved_draft is None:
        raise ValidationError("Approved history draft not found.")

    context = AssessmentContextBuilder().build(acting_user, encounter_id)
    engine = DifferentialDiagnosisEngine()
    deterministic = engine.generate(context)

    ai_result = AssessmentAIGenerator().generate(
        acting_user,
        encounter_id=encounter_id,
        patient_id=encounter.patient_id,
        clinical_context=context,
        deterministic_suggestions=deterministic,
    )

    run = ClinicalAssessmentRun(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        guided_history_session_id=history_session.id,
        ai_session_uuid=ai_result["ai_session_uuid"],
        provider_key=ai_result["provider_key"],
        model_name=ai_result["model_name"],
        status=RUN_STATUS_GENERATED,
        knowledge_sources=context.get("knowledge_sources") or [],
        clinical_context=context,
        department_id=encounter.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(run)
    db.session.flush()

    suggestions = deterministic
    for item in suggestions:
        suggestion = DiagnosisSuggestion(
            assessment_run_id=run.id,
            encounter_id=encounter.id,
            patient_id=encounter.patient_id,
            diagnosis_name=item["diagnosis_name"],
            category=item["category"],
            priority_rank=item["priority_rank"],
            supporting_findings=item.get("supporting_findings") or [],
            missing_information=item.get("missing_information") or [],
            contradicting_findings=item.get("contradicting_findings") or [],
            inclusion_reason=item.get("inclusion_reason"),
            confidence_indicator=item.get("confidence_indicator", "medium"),
            knowledge_references=item.get("knowledge_references") or [],
            clinical_findings_used=item.get("clinical_findings_used") or [],
            ai_session_uuid=ai_result["ai_session_uuid"],
            version=item.get("version", 1),
            status=STATUS_SUGGESTED,
            department_id=encounter.department_id,
            created_by_id=acting_user.id,
        )
        db.session.add(suggestion)

    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.generation_completed",
        user=acting_user,
        target_type="ClinicalAssessmentRun",
        target_id=run.id,
        details={
            "encounter_id": encounter.id,
            "ai_session_uuid": run.ai_session_uuid,
            "provider_key": run.provider_key,
            "model_name": run.model_name,
            "suggestion_count": len(suggestions),
            "knowledge_sources": run.knowledge_sources,
        },
    )
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.suggestions_shown",
        user=acting_user,
        target_type="ClinicalAssessmentRun",
        target_id=run.id,
        details={"suggestion_names": [s["diagnosis_name"] for s in suggestions]},
    )
    return run


def get_run(acting_user, run_id: int) -> ClinicalAssessmentRun:
    require_assessment_view(acting_user)
    run = ClinicalAssessmentRun.query.get(run_id)
    if run is None or run.is_archived:
        raise NotFoundError(f"No assessment run with id {run_id}")
    return run


def get_latest_run_for_encounter(acting_user, encounter_id: int) -> ClinicalAssessmentRun | None:
    require_assessment_view(acting_user)
    return (
        ClinicalAssessmentRun.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(ClinicalAssessmentRun.created_at.desc())
        .first()
    )


def list_suggestions(acting_user, run_id: int) -> list[DiagnosisSuggestion]:
    run = get_run(acting_user, run_id)
    return (
        DiagnosisSuggestion.query.filter_by(assessment_run_id=run.id, is_archived=False)
        .order_by(DiagnosisSuggestion.priority_rank)
        .all()
    )


def _get_suggestion(acting_user, suggestion_id: int) -> DiagnosisSuggestion:
    require_assessment_view(acting_user)
    suggestion = DiagnosisSuggestion.query.get(suggestion_id)
    if suggestion is None or suggestion.is_archived:
        raise NotFoundError(f"No diagnosis suggestion with id {suggestion_id}")
    return suggestion


def _record_decision(
    acting_user,
    *,
    suggestion: DiagnosisSuggestion | None,
    encounter_id: int,
    patient_id: int,
    assessment_run_id: int | None,
    diagnosis_name: str,
    physician_status: str,
    original_name: str | None = None,
    notes: str | None = None,
    modified_fields: dict | None = None,
) -> PhysicianDiagnosisDecision:
    decision = PhysicianDiagnosisDecision(
        encounter_id=encounter_id,
        patient_id=patient_id,
        assessment_run_id=assessment_run_id,
        suggestion_id=suggestion.id if suggestion else None,
        diagnosis_name=diagnosis_name,
        original_suggestion_name=original_name,
        physician_status=physician_status,
        physician_notes=notes,
        modified_fields=modified_fields or {},
        department_id=getattr(acting_user, "department_id", 1),
        created_by_id=acting_user.id,
    )
    db.session.add(decision)
    return decision


def accept_suggestion(acting_user, suggestion_id: int, *, notes: str | None = None) -> PhysicianDiagnosisDecision:
    require_assessment_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        assessment_run_id=suggestion.assessment_run_id,
        diagnosis_name=suggestion.diagnosis_name,
        physician_status=STATUS_ACCEPTED,
        original_name=suggestion.diagnosis_name,
        notes=notes,
    )
    db.session.commit()
    _audit_physician_action(acting_user, "accepted", suggestion, decision)
    return decision


def reject_suggestion(acting_user, suggestion_id: int, *, notes: str | None = None) -> PhysicianDiagnosisDecision:
    require_assessment_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        assessment_run_id=suggestion.assessment_run_id,
        diagnosis_name=suggestion.diagnosis_name,
        physician_status=STATUS_REJECTED,
        original_name=suggestion.diagnosis_name,
        notes=notes,
    )
    db.session.commit()
    _audit_physician_action(acting_user, "rejected", suggestion, decision)
    return decision


def modify_suggestion(
    acting_user,
    suggestion_id: int,
    *,
    diagnosis_name: str,
    notes: str | None = None,
) -> PhysicianDiagnosisDecision:
    require_assessment_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        assessment_run_id=suggestion.assessment_run_id,
        diagnosis_name=diagnosis_name,
        physician_status=STATUS_MODIFIED,
        original_name=suggestion.diagnosis_name,
        notes=notes,
        modified_fields={"diagnosis_name": diagnosis_name},
    )
    db.session.commit()
    _audit_physician_action(acting_user, "modified", suggestion, decision)
    return decision


def add_manual_diagnosis(
    acting_user,
    encounter_id: int,
    *,
    diagnosis_name: str,
    notes: str | None = None,
    physician_status: str = STATUS_MANUAL,
) -> PhysicianDiagnosisDecision:
    require_assessment_use(acting_user)
    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")

    run = get_latest_run_for_encounter(acting_user, encounter_id)
    decision = _record_decision(
        acting_user,
        suggestion=None,
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        assessment_run_id=run.id if run else None,
        diagnosis_name=diagnosis_name,
        physician_status=physician_status,
        notes=notes,
    )
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.manual_diagnosis_added",
        user=acting_user,
        target_type="PhysicianDiagnosisDecision",
        target_id=decision.id,
        details={"diagnosis_name": diagnosis_name, "encounter_id": encounter_id},
    )
    return decision


def confirm_diagnosis(acting_user, suggestion_id: int, *, notes: str | None = None) -> PhysicianDiagnosisDecision:
    require_assessment_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        assessment_run_id=suggestion.assessment_run_id,
        diagnosis_name=suggestion.diagnosis_name,
        physician_status=STATUS_CONFIRMED,
        original_name=suggestion.diagnosis_name,
        notes=notes,
    )
    run = suggestion.assessment_run
    if run:
        run.status = RUN_STATUS_FINALIZED
    db.session.commit()
    _audit_physician_action(acting_user, "confirmed", suggestion, decision)
    return decision


def mark_suspected(acting_user, suggestion_id: int, *, notes: str | None = None) -> PhysicianDiagnosisDecision:
    require_assessment_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        assessment_run_id=suggestion.assessment_run_id,
        diagnosis_name=suggestion.diagnosis_name,
        physician_status=STATUS_SUSPECTED,
        original_name=suggestion.diagnosis_name,
        notes=notes,
    )
    db.session.commit()
    _audit_physician_action(acting_user, "suspected", suggestion, decision)
    return decision


def get_physician_decisions(acting_user, encounter_id: int) -> list[PhysicianDiagnosisDecision]:
    require_assessment_view(acting_user)
    return (
        PhysicianDiagnosisDecision.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(PhysicianDiagnosisDecision.created_at.desc())
        .all()
    )


def get_final_assessment(acting_user, encounter_id: int) -> dict[str, Any]:
    require_assessment_view(acting_user)
    run = get_latest_run_for_encounter(acting_user, encounter_id)
    if run is None:
        return {"run": None, "suggestions": [], "decisions": [], "grouped": {}}

    suggestions = list_suggestions(acting_user, run.id)
    decisions = get_physician_decisions(acting_user, encounter_id)
    engine = DifferentialDiagnosisEngine()
    grouped = engine.group_by_category([suggestion_to_dict(s) for s in suggestions])

    return {
        "run": run_to_dict(run),
        "suggestions": [suggestion_to_dict(s) for s in suggestions],
        "decisions": [decision_to_dict(d) for d in decisions],
        "grouped": grouped,
    }


def _audit_physician_action(acting_user, action: str, suggestion: DiagnosisSuggestion, decision) -> None:
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.physician_{action}",
        user=acting_user,
        target_type="PhysicianDiagnosisDecision",
        target_id=decision.id,
        details={
            "suggestion_id": suggestion.id,
            "diagnosis_name": decision.diagnosis_name,
            "encounter_id": suggestion.encounter_id,
            "knowledge_references": suggestion.knowledge_references,
            "ai_session_uuid": suggestion.ai_session_uuid,
        },
    )


def run_to_dict(run: ClinicalAssessmentRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "encounter_id": run.encounter_id,
        "patient_id": run.patient_id,
        "ai_session_uuid": run.ai_session_uuid,
        "provider_key": run.provider_key,
        "model_name": run.model_name,
        "status": run.status,
        "knowledge_sources": run.knowledge_sources,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def suggestion_to_dict(suggestion: DiagnosisSuggestion) -> dict[str, Any]:
    return {
        "id": suggestion.id,
        "assessment_run_id": suggestion.assessment_run_id,
        "diagnosis_name": suggestion.diagnosis_name,
        "category": suggestion.category,
        "priority_rank": suggestion.priority_rank,
        "supporting_findings": suggestion.supporting_findings,
        "missing_information": suggestion.missing_information,
        "contradicting_findings": suggestion.contradicting_findings,
        "inclusion_reason": suggestion.inclusion_reason,
        "confidence_indicator": suggestion.confidence_indicator,
        "knowledge_references": suggestion.knowledge_references,
        "clinical_findings_used": suggestion.clinical_findings_used,
        "ai_session_uuid": suggestion.ai_session_uuid,
        "version": suggestion.version,
        "status": suggestion.status,
    }


def decision_to_dict(decision: PhysicianDiagnosisDecision) -> dict[str, Any]:
    return {
        "id": decision.id,
        "suggestion_id": decision.suggestion_id,
        "diagnosis_name": decision.diagnosis_name,
        "original_suggestion_name": decision.original_suggestion_name,
        "physician_status": decision.physician_status,
        "physician_notes": decision.physician_notes,
        "modified_fields": decision.modified_fields,
        "version": decision.version,
        "created_at": decision.created_at.isoformat() if decision.created_at else None,
    }
