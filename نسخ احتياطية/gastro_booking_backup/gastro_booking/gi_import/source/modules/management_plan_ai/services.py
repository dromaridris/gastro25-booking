"""Management Plan Assistant orchestration services."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.clinical_assessment import services as assessment_services
from app.modules.clinical_history_ai.constants import SESSION_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistorySession
from app.modules.clinical_interpretation.models import ClinicalInterpretationRun
from app.modules.encounters.models import ClinicalEncounter
from app.modules.management_plan_ai.catalogue_seed import seed_management_rules_if_empty
from app.modules.management_plan_ai.constants import (
    AUDIT_PREFIX,
    DECISION_ACCEPTED,
    DECISION_MANUAL,
    DECISION_MODIFIED,
    DECISION_REJECTED,
    PLAN_STATUS_APPROVED,
    PLAN_STATUS_DRAFT,
    PLAN_STATUS_MODIFIED,
    PLAN_STATUS_REJECTED,
    PLAN_STATUS_REVIEWED,
    SUGGESTION_STATUS_SUGGESTED,
)
from app.modules.management_plan_ai.context_builder import ManagementContextBuilder
from app.modules.management_plan_ai.management_engine import ManagementEngine
from app.modules.management_plan_ai.models import (
    ManagementPlan,
    ManagementSuggestion,
    PhysicianManagementDecision,
)
from app.modules.management_plan_ai.permissions import (
    require_management_plan_ai_use,
    require_management_plan_ai_view,
)
from app.modules.management_plan_ai.recommendation_generator import ManagementRecommendationGenerator


def ensure_rules_seeded() -> int:
    return seed_management_rules_if_empty()


def generate_plan(acting_user, encounter_id: int) -> ManagementPlan:
    require_management_plan_ai_use(acting_user)
    ensure_rules_seeded()

    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")

    history_session = GuidedHistorySession.query.filter_by(
        encounter_id=encounter_id, is_archived=False
    ).first()
    if history_session is None or history_session.status != SESSION_STATUS_APPROVED:
        raise ValidationError("Approved structured history is required before management planning.")

    assessment = assessment_services.get_latest_run_for_encounter(acting_user, encounter_id)
    if assessment is None:
        raise ValidationError("Clinical assessment is required before management planning.")

    context = ManagementContextBuilder().build(acting_user, encounter_id)
    working = context.get("working_diagnoses") or []
    if not working:
        raise ValidationError(
            "Confirmed or suspected physician diagnosis is required before management planning."
        )

    engine = ManagementEngine()
    deterministic = engine.generate(context)

    ai_result = ManagementRecommendationGenerator().generate(
        acting_user,
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        clinical_context=context,
        deterministic_suggestions=deterministic,
    )

    interpretation_run = (
        ClinicalInterpretationRun.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(ClinicalInterpretationRun.created_at.desc())
        .first()
    )

    plan = ManagementPlan(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        assessment_run_id=assessment.id,
        interpretation_run_id=interpretation_run.id if interpretation_run else None,
        ai_session_uuid=ai_result["ai_session_uuid"],
        provider_key=ai_result["provider_key"],
        model_name=ai_result["model_name"],
        status=PLAN_STATUS_DRAFT,
        working_diagnoses=working,
        knowledge_sources=context.get("knowledge_sources") or [],
        clinical_context=context,
        department_id=encounter.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(plan)
    db.session.flush()

    for item in deterministic:
        suggestion = ManagementSuggestion(
            plan_id=plan.id,
            encounter_id=encounter.id,
            patient_id=encounter.patient_id,
            suggestion_key=item["suggestion_key"],
            category=item["category"],
            description=item["description"],
            clinical_indication=item.get("clinical_indication"),
            related_diagnosis=item.get("related_diagnosis"),
            supporting_evidence=item.get("supporting_evidence") or [],
            knowledge_references=item.get("knowledge_references") or [],
            guideline_references=item.get("guideline_references") or [],
            priority=item.get("priority", "recommended"),
            confidence_indicator=item.get("confidence_indicator", "medium"),
            ai_session_uuid=ai_result["ai_session_uuid"],
            status=SUGGESTION_STATUS_SUGGESTED,
            version=item.get("version", 1),
            department_id=encounter.department_id,
            created_by_id=acting_user.id,
        )
        db.session.add(suggestion)

    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.generation_completed",
        user=acting_user,
        target_type="ManagementPlan",
        target_id=plan.id,
        details={
            "encounter_id": encounter.id,
            "ai_session_uuid": plan.ai_session_uuid,
            "knowledge_sources": plan.knowledge_sources,
            "working_diagnoses": working,
            "suggestion_count": len(deterministic),
        },
    )
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.suggestions_displayed",
        user=acting_user,
        target_type="ManagementPlan",
        target_id=plan.id,
        details={
            "categories": list({s["category"] for s in deterministic}),
            "descriptions": [s["description"][:80] for s in deterministic],
        },
    )
    return plan


def get_plan(acting_user, plan_id: int) -> ManagementPlan:
    require_management_plan_ai_view(acting_user)
    plan = ManagementPlan.query.get(plan_id)
    if plan is None or plan.is_archived:
        raise NotFoundError(f"No management plan with id {plan_id}")
    return plan


def get_latest_plan_for_encounter(acting_user, encounter_id: int) -> ManagementPlan | None:
    require_management_plan_ai_view(acting_user)
    return (
        ManagementPlan.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(ManagementPlan.created_at.desc())
        .first()
    )


def get_plan_view(acting_user, encounter_id: int) -> dict[str, Any]:
    plan = get_latest_plan_for_encounter(acting_user, encounter_id)
    if plan is None:
        return {"plan": None, "suggestions": [], "decisions": [], "grouped": {}}

    suggestions = (
        ManagementSuggestion.query.filter_by(plan_id=plan.id, is_archived=False)
        .order_by(ManagementSuggestion.id)
        .all()
    )
    decisions = (
        PhysicianManagementDecision.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(PhysicianManagementDecision.created_at.desc())
        .all()
    )
    engine = ManagementEngine()
    grouped = engine.group_by_category([suggestion_to_dict(s) for s in suggestions])

    return {
        "plan": plan_to_dict(plan),
        "suggestions": [suggestion_to_dict(s) for s in suggestions],
        "decisions": [decision_to_dict(d) for d in decisions],
        "grouped": grouped,
    }


def _get_suggestion(acting_user, suggestion_id: int) -> ManagementSuggestion:
    require_management_plan_ai_view(acting_user)
    suggestion = ManagementSuggestion.query.get(suggestion_id)
    if suggestion is None or suggestion.is_archived:
        raise NotFoundError(f"No management suggestion with id {suggestion_id}")
    return suggestion


def _record_decision(
    acting_user,
    *,
    suggestion: ManagementSuggestion | None,
    plan: ManagementPlan | None,
    encounter_id: int,
    patient_id: int,
    category: str | None,
    description: str,
    original_description: str | None,
    physician_status: str,
    notes: str | None = None,
    modified_fields: dict | None = None,
) -> PhysicianManagementDecision:
    decision = PhysicianManagementDecision(
        plan_id=plan.id if plan else (suggestion.plan_id if suggestion else None),
        suggestion_id=suggestion.id if suggestion else None,
        encounter_id=encounter_id,
        patient_id=patient_id,
        category=category,
        description=description,
        original_description=original_description,
        physician_status=physician_status,
        physician_notes=notes,
        modified_fields=modified_fields or {},
        department_id=getattr(acting_user, "department_id", 1),
        created_by_id=acting_user.id,
    )
    db.session.add(decision)
    return decision


def accept_suggestion(
    acting_user, suggestion_id: int, *, notes: str | None = None
) -> PhysicianManagementDecision:
    require_management_plan_ai_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        plan=suggestion.plan,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        category=suggestion.category,
        description=suggestion.description,
        original_description=suggestion.description,
        physician_status=DECISION_ACCEPTED,
        notes=notes,
    )
    db.session.commit()
    _audit_decision(acting_user, "accepted", suggestion, decision)
    return decision


def reject_suggestion(
    acting_user, suggestion_id: int, *, notes: str | None = None
) -> PhysicianManagementDecision:
    require_management_plan_ai_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        plan=suggestion.plan,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        category=suggestion.category,
        description=suggestion.description,
        original_description=suggestion.description,
        physician_status=DECISION_REJECTED,
        notes=notes,
    )
    db.session.commit()
    _audit_decision(acting_user, "rejected", suggestion, decision)
    return decision


def modify_suggestion(
    acting_user,
    suggestion_id: int,
    *,
    description: str | None = None,
    category: str | None = None,
    notes: str | None = None,
) -> PhysicianManagementDecision:
    require_management_plan_ai_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    modified_fields: dict[str, Any] = {}
    desc = description or suggestion.description
    cat = category or suggestion.category
    if description:
        modified_fields["description"] = description
    if category:
        modified_fields["category"] = category

    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        plan=suggestion.plan,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        category=cat,
        description=desc,
        original_description=suggestion.description,
        physician_status=DECISION_MODIFIED,
        notes=notes,
        modified_fields=modified_fields,
    )
    if suggestion.plan:
        suggestion.plan.status = PLAN_STATUS_MODIFIED
    db.session.commit()
    _audit_decision(acting_user, "modified", suggestion, decision)
    return decision


def add_manual_plan_item(
    acting_user,
    encounter_id: int,
    *,
    description: str,
    category: str | None = None,
    notes: str | None = None,
) -> PhysicianManagementDecision:
    require_management_plan_ai_use(acting_user)
    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")

    plan = get_latest_plan_for_encounter(acting_user, encounter_id)
    decision = _record_decision(
        acting_user,
        suggestion=None,
        plan=plan,
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        category=category,
        description=description,
        original_description=None,
        physician_status=DECISION_MANUAL,
        notes=notes,
    )
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.physician_manual",
        user=acting_user,
        target_type="PhysicianManagementDecision",
        target_id=decision.id,
        details={"encounter_id": encounter_id, "description": description[:120]},
    )
    return decision


def review_plan(acting_user, plan_id: int) -> ManagementPlan:
    plan = get_plan(acting_user, plan_id)
    plan.status = PLAN_STATUS_REVIEWED
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.plan_reviewed",
        user=acting_user,
        target_type="ManagementPlan",
        target_id=plan.id,
        details={"encounter_id": plan.encounter_id},
    )
    return plan


def approve_plan(acting_user, plan_id: int) -> ManagementPlan:
    require_management_plan_ai_use(acting_user)
    plan = get_plan(acting_user, plan_id)
    plan.status = PLAN_STATUS_APPROVED
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.plan_approved",
        user=acting_user,
        target_type="ManagementPlan",
        target_id=plan.id,
        details={"encounter_id": plan.encounter_id},
    )
    return plan


def reject_plan(acting_user, plan_id: int, *, reason: str | None = None) -> ManagementPlan:
    plan = get_plan(acting_user, plan_id)
    plan.status = PLAN_STATUS_REJECTED
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.plan_rejected",
        user=acting_user,
        target_type="ManagementPlan",
        target_id=plan.id,
        details={"reason": reason},
    )
    return plan


def _audit_decision(acting_user, action: str, suggestion: ManagementSuggestion, decision) -> None:
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.physician_{action}",
        user=acting_user,
        target_type="PhysicianManagementDecision",
        target_id=decision.id,
        details={
            "suggestion_id": suggestion.id,
            "category": suggestion.category,
            "description": decision.description[:120],
            "knowledge_references": suggestion.knowledge_references,
            "ai_session_uuid": suggestion.ai_session_uuid,
        },
    )


def plan_to_dict(plan: ManagementPlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "encounter_id": plan.encounter_id,
        "patient_id": plan.patient_id,
        "assessment_run_id": plan.assessment_run_id,
        "interpretation_run_id": plan.interpretation_run_id,
        "ai_session_uuid": plan.ai_session_uuid,
        "provider_key": plan.provider_key,
        "model_name": plan.model_name,
        "status": plan.status,
        "working_diagnoses": plan.working_diagnoses,
        "knowledge_sources": plan.knowledge_sources,
        "version": plan.version,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


def suggestion_to_dict(suggestion: ManagementSuggestion) -> dict[str, Any]:
    return {
        "id": suggestion.id,
        "plan_id": suggestion.plan_id,
        "suggestion_key": suggestion.suggestion_key,
        "category": suggestion.category,
        "description": suggestion.description,
        "clinical_indication": suggestion.clinical_indication,
        "related_diagnosis": suggestion.related_diagnosis,
        "supporting_evidence": suggestion.supporting_evidence,
        "knowledge_references": suggestion.knowledge_references,
        "guideline_references": suggestion.guideline_references,
        "priority": suggestion.priority,
        "confidence_indicator": suggestion.confidence_indicator,
        "ai_session_uuid": suggestion.ai_session_uuid,
        "status": suggestion.status,
        "version": suggestion.version,
    }


def decision_to_dict(decision: PhysicianManagementDecision) -> dict[str, Any]:
    return {
        "id": decision.id,
        "plan_id": decision.plan_id,
        "suggestion_id": decision.suggestion_id,
        "category": decision.category,
        "description": decision.description,
        "original_description": decision.original_description,
        "physician_status": decision.physician_status,
        "physician_notes": decision.physician_notes,
        "modified_fields": decision.modified_fields,
        "created_at": decision.created_at.isoformat() if decision.created_at else None,
    }
