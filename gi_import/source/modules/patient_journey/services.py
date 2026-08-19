"""Patient Journey orchestration services."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.encounters import services as encounter_services
from app.modules.encounters.models import ClinicalEncounter, ENCOUNTER_STATUS_OPEN
from app.modules.management_plan_ai import services as management_services
from app.modules.management_plan_ai.models import ManagementPlan
from app.modules.patient_journey.catalogue_seed import seed_follow_up_rules_if_empty
from app.modules.patient_journey.constants import (
    AUDIT_PREFIX,
    FOLLOWUP_STATUS_ACTIVE,
    FOLLOWUP_STATUS_CANCELLED,
    FOLLOWUP_STATUS_COMPLETED,
    FOLLOWUP_STATUS_MISSED,
    FOLLOWUP_STATUS_PLANNED,
    NEXT_ACTION_CLOSE,
    SUMMARY_STATUS_APPROVED,
    SUMMARY_STATUS_DRAFT,
    SUMMARY_STATUS_REJECTED,
)
from app.modules.patient_journey.context_builder import JourneyContextBuilder
from app.modules.patient_journey.followup_engine import FollowUpEngine, FollowUpSummaryGenerator
from app.modules.patient_journey.models import (
    ClinicalOutcomeRecord,
    FollowUpEvent,
    FollowUpPlan,
    JourneySummaryDraft,
)
from app.modules.patient_journey.outcome_tracker import OutcomeTracker
from app.modules.patient_journey.permissions import require_journey_use, require_journey_view
from app.modules.patient_journey.timeline import PatientTimelineAggregator


def ensure_rules_seeded() -> int:
    return seed_follow_up_rules_if_empty()


def get_patient_timeline(acting_user, patient_id: int) -> list[dict[str, Any]]:
    require_journey_view(acting_user)
    timeline = PatientTimelineAggregator().build(acting_user, patient_id)
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.timeline_accessed",
        user=acting_user,
        target_type="Patient",
        target_id=patient_id,
        details={"event_count": len(timeline)},
    )
    return timeline


def create_follow_up_plan(
    acting_user,
    encounter_id: int,
    *,
    related_condition: str | None = None,
    recommended_interval_days: int | None = None,
    recommended_interval_text: str | None = None,
    reason: str | None = None,
    responsible_physician_id: int | None = None,
) -> FollowUpPlan:
    require_journey_use(acting_user)
    ensure_rules_seeded()

    encounter = encounter_services.get_encounter(acting_user, encounter_id)
    mgmt_plan = management_services.get_latest_plan_for_encounter(acting_user, encounter_id)
    if mgmt_plan is None:
        raise ValidationError("Management plan is required before creating follow-up plan.")

    context = JourneyContextBuilder().build_for_encounter(acting_user, encounter_id)
    suggestions = FollowUpEngine().suggest(context)

    if related_condition is None and suggestions:
        related_condition = suggestions[0].get("related_condition")
    if recommended_interval_days is None and suggestions:
        recommended_interval_days = suggestions[0].get("recommended_interval_days")
    if recommended_interval_text is None and suggestions:
        recommended_interval_text = suggestions[0].get("recommended_interval_text")
    if reason is None and suggestions:
        reason = suggestions[0].get("reason")

    knowledge_refs = suggestions[0].get("knowledge_references", []) if suggestions else []

    plan = FollowUpPlan(
        patient_id=encounter.patient_id,
        encounter_id=encounter.id,
        management_plan_id=mgmt_plan.id,
        related_condition=related_condition,
        responsible_physician_id=responsible_physician_id or acting_user.id,
        recommended_interval_days=recommended_interval_days,
        recommended_interval_text=recommended_interval_text,
        reason=reason,
        status=FOLLOWUP_STATUS_PLANNED,
        knowledge_references=knowledge_refs,
        department_id=encounter.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(plan)
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.follow_up_created",
        user=acting_user,
        target_type="FollowUpPlan",
        target_id=plan.id,
        details={
            "encounter_id": encounter.id,
            "related_condition": related_condition,
            "knowledge_references": knowledge_refs,
        },
    )
    return plan


def update_follow_up_status(acting_user, plan_id: int, *, status: str) -> FollowUpPlan:
    require_journey_use(acting_user)
    if status not in (
        FOLLOWUP_STATUS_PLANNED,
        FOLLOWUP_STATUS_ACTIVE,
        FOLLOWUP_STATUS_COMPLETED,
        FOLLOWUP_STATUS_CANCELLED,
        FOLLOWUP_STATUS_MISSED,
    ):
        raise ValidationError(f"Invalid follow-up status: {status}")

    plan = _get_follow_up_plan(acting_user, plan_id)
    plan.status = status
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.follow_up_status_changed",
        user=acting_user,
        target_type="FollowUpPlan",
        target_id=plan.id,
        details={"status": status, "encounter_id": plan.encounter_id},
    )
    return plan


def record_follow_up_event(
    acting_user,
    plan_id: int,
    *,
    clinical_update: str | None = None,
    new_findings: list[str] | None = None,
    symptoms_status: str | None = None,
    investigation_updates: list[str] | None = None,
    physician_assessment: str | None = None,
    next_action: str | None = None,
    encounter_id: int | None = None,
) -> FollowUpEvent:
    require_journey_use(acting_user)
    plan = _get_follow_up_plan(acting_user, plan_id)

    event = FollowUpEvent(
        plan_id=plan.id,
        patient_id=plan.patient_id,
        encounter_id=encounter_id or plan.encounter_id,
        clinical_update=clinical_update,
        new_findings=new_findings or [],
        symptoms_status=symptoms_status,
        investigation_updates=investigation_updates or [],
        physician_assessment=physician_assessment,
        next_action=next_action,
        department_id=getattr(acting_user, "department_id", 1),
        created_by_id=acting_user.id,
    )
    db.session.add(event)

    if plan.status == FOLLOWUP_STATUS_PLANNED:
        plan.status = FOLLOWUP_STATUS_ACTIVE

    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.follow_up_event_recorded",
        user=acting_user,
        target_type="FollowUpEvent",
        target_id=event.id,
        details={"plan_id": plan.id, "next_action": next_action},
    )
    return event


def record_outcome(
    acting_user,
    encounter_id: int,
    *,
    outcome: str,
    notes: str | None = None,
    follow_up_plan_id: int | None = None,
    follow_up_event_id: int | None = None,
) -> ClinicalOutcomeRecord:
    require_journey_use(acting_user)
    encounter = encounter_services.get_encounter(acting_user, encounter_id)
    prepared = OutcomeTracker.prepare_record(outcome=outcome, notes=notes, physician_confirmed=True)

    record = ClinicalOutcomeRecord(
        patient_id=encounter.patient_id,
        encounter_id=encounter.id,
        follow_up_plan_id=follow_up_plan_id,
        follow_up_event_id=follow_up_event_id,
        outcome=prepared["outcome"],
        outcome_notes=prepared["outcome_notes"],
        physician_confirmed=True,
        recorded_by_id=acting_user.id,
        department_id=encounter.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(record)
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.outcome_recorded",
        user=acting_user,
        target_type="ClinicalOutcomeRecord",
        target_id=record.id,
        details={"outcome": outcome, "encounter_id": encounter.id},
    )
    return record


def generate_summary_draft(acting_user, encounter_id: int) -> JourneySummaryDraft:
    require_journey_use(acting_user)
    encounter = encounter_services.get_encounter(acting_user, encounter_id)
    context = JourneyContextBuilder().build_for_encounter(acting_user, encounter_id)

    ai_result = FollowUpSummaryGenerator().generate(
        acting_user,
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        clinical_context=context,
    )

    follow_up = (
        FollowUpPlan.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(FollowUpPlan.created_at.desc())
        .first()
    )

    draft = JourneySummaryDraft(
        patient_id=encounter.patient_id,
        encounter_id=encounter.id,
        follow_up_plan_id=follow_up.id if follow_up else None,
        ai_session_uuid=ai_result["ai_session_uuid"],
        provider_key=ai_result["provider_key"],
        model_name=ai_result["model_name"],
        draft_text=ai_result["draft_text"],
        status=SUMMARY_STATUS_DRAFT,
        knowledge_references=ai_result.get("knowledge_references") or [],
        missing_information=ai_result.get("missing_information") or [],
        department_id=encounter.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(draft)
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.summary_generated",
        user=acting_user,
        target_type="JourneySummaryDraft",
        target_id=draft.id,
        details={
            "encounter_id": encounter.id,
            "ai_session_uuid": draft.ai_session_uuid,
            "knowledge_references": draft.knowledge_references,
        },
    )
    return draft


def approve_summary(acting_user, draft_id: int, *, approved_text: str | None = None) -> JourneySummaryDraft:
    require_journey_use(acting_user)
    draft = _get_summary_draft(acting_user, draft_id)
    draft.approved_text = approved_text or draft.draft_text
    draft.status = SUMMARY_STATUS_APPROVED
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.summary_approved",
        user=acting_user,
        target_type="JourneySummaryDraft",
        target_id=draft.id,
        details={"encounter_id": draft.encounter_id},
    )
    return draft


def reject_summary(acting_user, draft_id: int, *, reason: str | None = None) -> JourneySummaryDraft:
    draft = _get_summary_draft(acting_user, draft_id)
    draft.status = SUMMARY_STATUS_REJECTED
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.summary_rejected",
        user=acting_user,
        target_type="JourneySummaryDraft",
        target_id=draft.id,
        details={"reason": reason},
    )
    return draft


def physician_close_encounter(acting_user, encounter_id: int, *, notes: str | None = None) -> ClinicalEncounter:
    """Explicit physician action to close encounter — never automatic."""
    require_journey_use(acting_user)
    encounter = encounter_services.get_encounter(acting_user, encounter_id)
    if encounter.status != ENCOUNTER_STATUS_OPEN:
        raise ValidationError("Encounter is not open.")

    closed = encounter_services.close_encounter(acting_user, encounter)
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.encounter_closed_by_physician",
        user=acting_user,
        target_type="ClinicalEncounter",
        target_id=encounter.id,
        details={"notes": notes},
    )
    return closed


def get_journey_view(acting_user, patient_id: int, *, encounter_id: int | None = None) -> dict[str, Any]:
    require_journey_view(acting_user)
    focus = encounter_id
    context = JourneyContextBuilder().build_for_patient(acting_user, patient_id, focus_encounter_id=focus)
    timeline = PatientTimelineAggregator().build(acting_user, patient_id)

    follow_ups = (
        FollowUpPlan.query.filter_by(patient_id=patient_id, is_archived=False)
        .order_by(FollowUpPlan.created_at.desc())
        .all()
    )
    outcomes = (
        ClinicalOutcomeRecord.query.filter_by(patient_id=patient_id, is_archived=False)
        .order_by(ClinicalOutcomeRecord.created_at.desc())
        .all()
    )

    return {
        "context": context,
        "timeline": timeline,
        "follow_up_plans": [follow_up_to_dict(p) for p in follow_ups],
        "outcomes": [outcome_to_dict(o) for o in outcomes],
    }


def _get_follow_up_plan(acting_user, plan_id: int) -> FollowUpPlan:
    require_journey_view(acting_user)
    plan = FollowUpPlan.query.get(plan_id)
    if plan is None or plan.is_archived:
        raise NotFoundError(f"No follow-up plan with id {plan_id}")
    return plan


def _get_summary_draft(acting_user, draft_id: int) -> JourneySummaryDraft:
    require_journey_view(acting_user)
    draft = JourneySummaryDraft.query.get(draft_id)
    if draft is None or draft.is_archived:
        raise NotFoundError(f"No journey summary draft with id {draft_id}")
    return draft


def follow_up_to_dict(plan: FollowUpPlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "patient_id": plan.patient_id,
        "encounter_id": plan.encounter_id,
        "management_plan_id": plan.management_plan_id,
        "related_condition": plan.related_condition,
        "responsible_physician_id": plan.responsible_physician_id,
        "recommended_interval_days": plan.recommended_interval_days,
        "recommended_interval_text": plan.recommended_interval_text,
        "reason": plan.reason,
        "status": plan.status,
        "knowledge_references": plan.knowledge_references,
        "version": plan.version,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
    }


def event_to_dict(event: FollowUpEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "plan_id": event.plan_id,
        "encounter_id": event.encounter_id,
        "clinical_update": event.clinical_update,
        "new_findings": event.new_findings,
        "symptoms_status": event.symptoms_status,
        "investigation_updates": event.investigation_updates,
        "physician_assessment": event.physician_assessment,
        "next_action": event.next_action,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def outcome_to_dict(record: ClinicalOutcomeRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "patient_id": record.patient_id,
        "encounter_id": record.encounter_id,
        "outcome": record.outcome,
        "outcome_notes": record.outcome_notes,
        "physician_confirmed": record.physician_confirmed,
        "recorded_by_id": record.recorded_by_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def summary_to_dict(draft: JourneySummaryDraft) -> dict[str, Any]:
    return {
        "id": draft.id,
        "patient_id": draft.patient_id,
        "encounter_id": draft.encounter_id,
        "ai_session_uuid": draft.ai_session_uuid,
        "draft_text": draft.draft_text,
        "approved_text": draft.approved_text,
        "status": draft.status,
        "knowledge_references": draft.knowledge_references,
        "missing_information": draft.missing_information,
        "created_at": draft.created_at.isoformat() if draft.created_at else None,
    }
