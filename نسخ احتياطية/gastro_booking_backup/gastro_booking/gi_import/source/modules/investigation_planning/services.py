"""Investigation Planning orchestration services."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.clinical_assessment import services as assessment_services
from app.modules.clinical_history_ai.constants import SESSION_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistorySession
from app.modules.encounters.models import ClinicalEncounter
from app.modules.investigation_planning.catalogue_seed import seed_investigation_library_if_empty
from app.modules.investigation_planning.constants import (
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
from app.modules.investigation_planning.context_builder import InvestigationContextBuilder
from app.modules.investigation_planning.investigation_engine import InvestigationSuggestionEngine
from app.modules.investigation_planning.models import (
    InvestigationPlan,
    InvestigationSuggestion,
    PhysicianInvestigationDecision,
)
from app.modules.investigation_planning.permissions import (
    require_investigation_plan_use,
    require_investigation_plan_view,
)
from app.modules.investigation_planning.recommendation_generator import InvestigationRecommendationGenerator


def ensure_library_seeded() -> int:
    return seed_investigation_library_if_empty()


def generate_plan(acting_user, encounter_id: int) -> InvestigationPlan:
    require_investigation_plan_use(acting_user)
    ensure_library_seeded()

    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")

    history_session = GuidedHistorySession.query.filter_by(
        encounter_id=encounter_id, is_archived=False
    ).first()
    if history_session is None or history_session.status != SESSION_STATUS_APPROVED:
        raise ValidationError("Approved structured history is required before investigation planning.")

    assessment = assessment_services.get_latest_run_for_encounter(acting_user, encounter_id)
    if assessment is None:
        raise ValidationError("Differential assessment is required before investigation planning.")

    context = InvestigationContextBuilder().build(acting_user, encounter_id)
    engine = InvestigationSuggestionEngine()
    deterministic = engine.generate(context)

    ai_result = InvestigationRecommendationGenerator().generate(
        acting_user,
        encounter_id=encounter_id,
        patient_id=encounter.patient_id,
        clinical_context=context,
        deterministic_suggestions=deterministic,
    )

    plan = InvestigationPlan(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        assessment_run_id=assessment.id,
        ai_session_uuid=ai_result["ai_session_uuid"],
        provider_key=ai_result["provider_key"],
        model_name=ai_result["model_name"],
        status=PLAN_STATUS_DRAFT,
        knowledge_sources=context.get("knowledge_sources") or [],
        clinical_context=context,
        department_id=encounter.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(plan)
    db.session.flush()

    for item in deterministic:
        db.session.add(
            InvestigationSuggestion(
                plan_id=plan.id,
                encounter_id=encounter.id,
                patient_id=encounter.patient_id,
                investigation_id=item["investigation_id"],
                investigation_name=item["investigation_name"],
                category=item["category"],
                priority=item["priority"],
                workup_group=item["workup_group"],
                reason=item.get("reason"),
                related_diagnosis=item.get("related_diagnosis"),
                clinical_purpose=item.get("clinical_purpose"),
                missing_info_addressed=item.get("missing_info_addressed"),
                knowledge_references=item.get("knowledge_references") or [],
                confidence_indicator=item.get("confidence_indicator", "medium"),
                ai_session_uuid=ai_result["ai_session_uuid"],
                duplicate_skipped=item.get("duplicate_skipped", False),
                status=SUGGESTION_STATUS_SUGGESTED,
                version=item.get("version", 1),
                department_id=encounter.department_id,
                created_by_id=acting_user.id,
            )
        )

    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.generation_completed",
        user=acting_user,
        target_type="InvestigationPlan",
        target_id=plan.id,
        details={
            "encounter_id": encounter.id,
            "ai_session_uuid": plan.ai_session_uuid,
            "knowledge_sources": plan.knowledge_sources,
            "suggestion_count": len(deterministic),
        },
    )
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.suggestions_displayed",
        user=acting_user,
        target_type="InvestigationPlan",
        target_id=plan.id,
        details={"investigation_names": [i["investigation_name"] for i in deterministic]},
    )
    return plan


def get_plan(acting_user, plan_id: int) -> InvestigationPlan:
    require_investigation_plan_view(acting_user)
    plan = InvestigationPlan.query.get(plan_id)
    if plan is None or plan.is_archived:
        raise NotFoundError(f"No investigation plan with id {plan_id}")
    return plan


def get_latest_plan_for_encounter(acting_user, encounter_id: int) -> InvestigationPlan | None:
    require_investigation_plan_view(acting_user)
    return (
        InvestigationPlan.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(InvestigationPlan.created_at.desc())
        .first()
    )


def get_plan_view(acting_user, encounter_id: int) -> dict[str, Any]:
    plan = get_latest_plan_for_encounter(acting_user, encounter_id)
    if plan is None:
        return {"plan": None, "suggestions": [], "decisions": [], "grouped": {}}

    suggestions = (
        InvestigationSuggestion.query.filter_by(plan_id=plan.id, is_archived=False)
        .order_by(InvestigationSuggestion.id)
        .all()
    )
    decisions = (
        PhysicianInvestigationDecision.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(PhysicianInvestigationDecision.created_at.desc())
        .all()
    )
    engine = InvestigationSuggestionEngine()
    grouped = engine.group_by_workup([suggestion_to_dict(s) for s in suggestions])

    return {
        "plan": plan_to_dict(plan),
        "suggestions": [suggestion_to_dict(s) for s in suggestions],
        "decisions": [decision_to_dict(d) for d in decisions],
        "grouped": grouped,
    }


def _get_suggestion(acting_user, suggestion_id: int) -> InvestigationSuggestion:
    require_investigation_plan_view(acting_user)
    suggestion = InvestigationSuggestion.query.get(suggestion_id)
    if suggestion is None or suggestion.is_archived:
        raise NotFoundError(f"No investigation suggestion with id {suggestion_id}")
    return suggestion


def _record_decision(
    acting_user,
    *,
    suggestion: InvestigationSuggestion | None,
    plan: InvestigationPlan | None,
    encounter_id: int,
    patient_id: int,
    investigation_name: str,
    category: str | None,
    priority: str | None,
    physician_status: str,
    physician_reason: str | None = None,
    modified_fields: dict | None = None,
) -> PhysicianInvestigationDecision:
    decision = PhysicianInvestigationDecision(
        plan_id=plan.id if plan else (suggestion.plan_id if suggestion else None),
        suggestion_id=suggestion.id if suggestion else None,
        encounter_id=encounter_id,
        patient_id=patient_id,
        investigation_name=investigation_name,
        category=category,
        priority=priority,
        physician_status=physician_status,
        physician_reason=physician_reason,
        modified_fields=modified_fields or {},
        department_id=getattr(acting_user, "department_id", 1),
        created_by_id=acting_user.id,
    )
    db.session.add(decision)
    return decision


def accept_suggestion(
    acting_user, suggestion_id: int, *, reason: str | None = None
) -> PhysicianInvestigationDecision:
    require_investigation_plan_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        plan=suggestion.plan,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        investigation_name=suggestion.investigation_name,
        category=suggestion.category,
        priority=suggestion.priority,
        physician_status=DECISION_ACCEPTED,
        physician_reason=reason,
    )
    db.session.commit()
    _audit_decision(acting_user, "accepted", suggestion, decision)
    return decision


def reject_suggestion(
    acting_user, suggestion_id: int, *, reason: str | None = None
) -> PhysicianInvestigationDecision:
    require_investigation_plan_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        plan=suggestion.plan,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        investigation_name=suggestion.investigation_name,
        category=suggestion.category,
        priority=suggestion.priority,
        physician_status=DECISION_REJECTED,
        physician_reason=reason,
    )
    db.session.commit()
    _audit_decision(acting_user, "rejected", suggestion, decision)
    return decision


def modify_suggestion(
    acting_user,
    suggestion_id: int,
    *,
    investigation_name: str | None = None,
    priority: str | None = None,
    reason: str | None = None,
) -> PhysicianInvestigationDecision:
    require_investigation_plan_use(acting_user)
    suggestion = _get_suggestion(acting_user, suggestion_id)
    modified_fields = {}
    name = investigation_name or suggestion.investigation_name
    pri = priority or suggestion.priority
    if investigation_name:
        modified_fields["investigation_name"] = investigation_name
    if priority:
        modified_fields["priority"] = priority

    decision = _record_decision(
        acting_user,
        suggestion=suggestion,
        plan=suggestion.plan,
        encounter_id=suggestion.encounter_id,
        patient_id=suggestion.patient_id,
        investigation_name=name,
        category=suggestion.category,
        priority=pri,
        physician_status=DECISION_MODIFIED,
        physician_reason=reason,
        modified_fields=modified_fields,
    )
    if suggestion.plan:
        suggestion.plan.status = PLAN_STATUS_MODIFIED
    db.session.commit()
    _audit_decision(acting_user, "modified", suggestion, decision)
    return decision


def add_manual_investigation(
    acting_user,
    encounter_id: int,
    *,
    investigation_name: str,
    category: str | None = None,
    priority: str | None = None,
    reason: str | None = None,
) -> PhysicianInvestigationDecision:
    require_investigation_plan_use(acting_user)
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
        investigation_name=investigation_name,
        category=category,
        priority=priority,
        physician_status=DECISION_MANUAL,
        physician_reason=reason,
    )
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.manual_investigation_added",
        user=acting_user,
        target_type="PhysicianInvestigationDecision",
        target_id=decision.id,
        details={"investigation_name": investigation_name, "encounter_id": encounter_id},
    )
    return decision


def review_plan(acting_user, plan_id: int) -> InvestigationPlan:
    plan = get_plan(acting_user, plan_id)
    plan.status = PLAN_STATUS_REVIEWED
    db.session.commit()
    return plan


def approve_plan(acting_user, plan_id: int) -> InvestigationPlan:
    require_investigation_plan_use(acting_user)
    plan = get_plan(acting_user, plan_id)
    plan.status = PLAN_STATUS_APPROVED
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.plan_approved",
        user=acting_user,
        target_type="InvestigationPlan",
        target_id=plan.id,
        details={"encounter_id": plan.encounter_id},
    )
    return plan


def reject_plan(acting_user, plan_id: int, *, reason: str | None = None) -> InvestigationPlan:
    plan = get_plan(acting_user, plan_id)
    plan.status = PLAN_STATUS_REJECTED
    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.plan_rejected",
        user=acting_user,
        target_type="InvestigationPlan",
        target_id=plan.id,
        details={"reason": reason},
    )
    return plan


def _audit_decision(acting_user, action: str, suggestion: InvestigationSuggestion, decision) -> None:
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.physician_{action}",
        user=acting_user,
        target_type="PhysicianInvestigationDecision",
        target_id=decision.id,
        details={
            "suggestion_id": suggestion.id,
            "investigation_name": decision.investigation_name,
            "knowledge_references": suggestion.knowledge_references,
            "ai_session_uuid": suggestion.ai_session_uuid,
        },
    )


def plan_to_dict(plan: InvestigationPlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "encounter_id": plan.encounter_id,
        "patient_id": plan.patient_id,
        "assessment_run_id": plan.assessment_run_id,
        "ai_session_uuid": plan.ai_session_uuid,
        "provider_key": plan.provider_key,
        "model_name": plan.model_name,
        "status": plan.status,
        "knowledge_sources": plan.knowledge_sources,
        "version": plan.version,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


def suggestion_to_dict(suggestion: InvestigationSuggestion) -> dict[str, Any]:
    return {
        "id": suggestion.id,
        "plan_id": suggestion.plan_id,
        "investigation_id": suggestion.investigation_id,
        "investigation_name": suggestion.investigation_name,
        "category": suggestion.category,
        "priority": suggestion.priority,
        "workup_group": suggestion.workup_group,
        "reason": suggestion.reason,
        "related_diagnosis": suggestion.related_diagnosis,
        "clinical_purpose": suggestion.clinical_purpose,
        "missing_info_addressed": suggestion.missing_info_addressed,
        "knowledge_references": suggestion.knowledge_references,
        "confidence_indicator": suggestion.confidence_indicator,
        "ai_session_uuid": suggestion.ai_session_uuid,
        "duplicate_skipped": suggestion.duplicate_skipped,
        "status": suggestion.status,
        "version": suggestion.version,
    }


def decision_to_dict(decision: PhysicianInvestigationDecision) -> dict[str, Any]:
    return {
        "id": decision.id,
        "suggestion_id": decision.suggestion_id,
        "investigation_name": decision.investigation_name,
        "category": decision.category,
        "priority": decision.priority,
        "physician_status": decision.physician_status,
        "physician_reason": decision.physician_reason,
        "modified_fields": decision.modified_fields,
        "version": decision.version,
        "created_at": decision.created_at.isoformat() if decision.created_at else None,
    }
