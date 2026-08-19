"""Unified patient timeline — reference-only aggregation."""

from __future__ import annotations

from typing import Any

from app.modules.clinical_assessment.models import ClinicalAssessmentRun
from app.modules.clinical_interpretation.models import ClinicalInterpretationRun
from app.modules.encounters import services as encounter_services
from app.modules.investigations.models import ImagingStudy, LabResultSet, RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED
from app.modules.management_plan_ai.models import ManagementPlan
from app.modules.patient_journey.constants import (
    TIMELINE_ASSESSMENT,
    TIMELINE_ENCOUNTER,
    TIMELINE_FOLLOWUP,
    TIMELINE_INTERPRETATION,
    TIMELINE_INVESTIGATION,
    TIMELINE_MANAGEMENT_PLAN,
    TIMELINE_OUTCOME,
    TIMELINE_PROCEDURE,
    TIMELINE_REPORT,
)
from app.modules.patient_journey.models import ClinicalOutcomeRecord, FollowUpEvent, FollowUpPlan
from app.modules.procedure_execution.models import ProcedureSession
from app.modules.reports.models import Report, STATUS_FINALIZED


class PatientTimelineAggregator:
    """Builds unified timeline from source module references — no data duplication."""

    def build(self, acting_user, patient_id: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        for enc in encounter_services.list_encounters_for_patient(acting_user, patient_id):
            events.append(
                {
                    "event_type": TIMELINE_ENCOUNTER,
                    "reference_type": "ClinicalEncounter",
                    "reference_id": enc.id,
                    "encounter_id": enc.id,
                    "timestamp": enc.started_at.isoformat() if enc.started_at else None,
                    "title": f"Encounter ({enc.encounter_type})",
                    "status": enc.status,
                    "summary": enc.summary,
                }
            )

        for run in ClinicalAssessmentRun.query.filter_by(patient_id=patient_id, is_archived=False).all():
            events.append(
                {
                    "event_type": TIMELINE_ASSESSMENT,
                    "reference_type": "ClinicalAssessmentRun",
                    "reference_id": run.id,
                    "encounter_id": run.encounter_id,
                    "timestamp": run.created_at.isoformat() if run.created_at else None,
                    "title": "Clinical assessment",
                    "status": run.status,
                }
            )

        for rs in LabResultSet.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if rs.status in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
                events.append(
                    {
                        "event_type": TIMELINE_INVESTIGATION,
                        "reference_type": "LabResultSet",
                        "reference_id": rs.id,
                        "encounter_id": rs.encounter_id,
                        "timestamp": rs.resulted_at.isoformat() if rs.resulted_at else None,
                        "title": "Laboratory results",
                        "status": rs.status,
                    }
                )

        for study in ImagingStudy.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if study.status in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
                events.append(
                    {
                        "event_type": TIMELINE_INVESTIGATION,
                        "reference_type": "ImagingStudy",
                        "reference_id": study.id,
                        "encounter_id": study.encounter_id,
                        "timestamp": study.study_date.isoformat() if study.study_date else None,
                        "title": "Imaging study",
                        "status": study.status,
                    }
                )

        for session in ProcedureSession.query.filter_by(patient_id=patient_id, is_archived=False).all():
            events.append(
                {
                    "event_type": TIMELINE_PROCEDURE,
                    "reference_type": "ProcedureSession",
                    "reference_id": session.id,
                    "encounter_id": None,
                    "timestamp": session.created_at.isoformat() if session.created_at else None,
                    "title": "Procedure session",
                    "status": session.outcome or ("cancelled" if session.is_cancelled else "active"),
                }
            )

        for report in Report.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if report.status == STATUS_FINALIZED:
                events.append(
                    {
                        "event_type": TIMELINE_REPORT,
                        "reference_type": "Report",
                        "reference_id": report.id,
                        "encounter_id": None,
                        "timestamp": report.finalized_at.isoformat() if report.finalized_at else None,
                        "title": f"Report {report.report_number}",
                        "status": report.status,
                    }
                )

        for plan in ManagementPlan.query.filter_by(patient_id=patient_id, is_archived=False).all():
            events.append(
                {
                    "event_type": TIMELINE_MANAGEMENT_PLAN,
                    "reference_type": "ManagementPlan",
                    "reference_id": plan.id,
                    "encounter_id": plan.encounter_id,
                    "timestamp": plan.created_at.isoformat() if plan.created_at else None,
                    "title": "Management plan",
                    "status": plan.status,
                }
            )

        for run in ClinicalInterpretationRun.query.filter_by(patient_id=patient_id, is_archived=False).all():
            events.append(
                {
                    "event_type": TIMELINE_INTERPRETATION,
                    "reference_type": "ClinicalInterpretationRun",
                    "reference_id": run.id,
                    "encounter_id": run.encounter_id,
                    "timestamp": run.created_at.isoformat() if run.created_at else None,
                    "title": "Clinical interpretation",
                    "status": run.status,
                }
            )

        for plan in FollowUpPlan.query.filter_by(patient_id=patient_id, is_archived=False).all():
            events.append(
                {
                    "event_type": TIMELINE_FOLLOWUP,
                    "reference_type": "FollowUpPlan",
                    "reference_id": plan.id,
                    "encounter_id": plan.encounter_id,
                    "timestamp": plan.created_at.isoformat() if plan.created_at else None,
                    "title": f"Follow-up: {plan.related_condition or 'plan'}",
                    "status": plan.status,
                }
            )

        for outcome in ClinicalOutcomeRecord.query.filter_by(patient_id=patient_id, is_archived=False).all():
            events.append(
                {
                    "event_type": TIMELINE_OUTCOME,
                    "reference_type": "ClinicalOutcomeRecord",
                    "reference_id": outcome.id,
                    "encounter_id": outcome.encounter_id,
                    "timestamp": outcome.created_at.isoformat() if outcome.created_at else None,
                    "title": f"Outcome: {outcome.outcome}",
                    "status": "confirmed" if outcome.physician_confirmed else "pending",
                }
            )

        events.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
        return events
