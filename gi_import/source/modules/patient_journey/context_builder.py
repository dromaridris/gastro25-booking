"""Journey context assembly — read-only integration."""

from __future__ import annotations

from typing import Any

from app.modules.clinical_assessment import services as assessment_services
from app.modules.clinical_history_ai.constants import DRAFT_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistoryDraft, GuidedHistorySession
from app.modules.clinical_intake.services import get_intake_for_encounter
from app.modules.clinical_interpretation import services as interpretation_services
from app.modules.encounters import services as encounter_services
from app.modules.encounters.models import ClinicalEncounter
from app.modules.investigation_planning import services as planning_services
from app.modules.investigations.models import ImagingStudy, LabResultSet, RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED
from app.modules.management_plan_ai import services as management_services
from app.modules.patient_journey.guideline_linker import fetch_published_references
from app.modules.patients.models import Patient
from app.modules.procedure_execution.models import ProcedureSession
from app.modules.reports.models import Report, STATUS_FINALIZED


class JourneyContextBuilder:
    """Builds read-only journey context without duplicating clinical records."""

    def build_for_encounter(self, acting_user, encounter_id: int) -> dict[str, Any]:
        encounter = ClinicalEncounter.query.get(encounter_id)
        if encounter is None or encounter.is_archived:
            raise ValueError(f"No encounter with id {encounter_id}")
        return self.build_for_patient(acting_user, encounter.patient_id, focus_encounter_id=encounter_id)

    def build_for_patient(
        self, acting_user, patient_id: int, *, focus_encounter_id: int | None = None
    ) -> dict[str, Any]:
        patient = Patient.query.get(patient_id)
        if patient is None or patient.is_archived:
            raise ValueError(f"No patient with id {patient_id}")

        encounters = encounter_services.list_encounters_for_patient(acting_user, patient_id)
        focus_id = focus_encounter_id or (encounters[0].id if encounters else None)

        intake = None
        assessment = {"run": None, "suggestions": [], "decisions": []}
        investigation_plan = {"plan": None, "suggestions": []}
        interpretation = {"run": None, "findings": [], "differential_updates": []}
        management_plan = {"plan": None, "suggestions": [], "decisions": []}
        structured_findings: list[dict] = []

        if focus_id:
            intake = get_intake_for_encounter(acting_user, focus_id)
            assessment = assessment_services.get_final_assessment(acting_user, focus_id)
            investigation_plan = planning_services.get_plan_view(acting_user, focus_id)
            interpretation = interpretation_services.get_interpretation_view(acting_user, focus_id)
            management_plan = management_services.get_plan_view(acting_user, focus_id)

            history_session = GuidedHistorySession.query.filter_by(
                encounter_id=focus_id, is_archived=False
            ).first()
            if history_session:
                draft = (
                    GuidedHistoryDraft.query.filter_by(
                        session_id=history_session.id,
                        status=DRAFT_STATUS_APPROVED,
                        is_archived=False,
                    )
                    .order_by(GuidedHistoryDraft.created_at.desc())
                    .first()
                )
                if draft:
                    structured_findings = draft.structured_findings

        topic_keys: list[str] = []
        for suggestion in assessment.get("suggestions") or []:
            for ref in suggestion.get("knowledge_references") or []:
                if ref.get("topic_key"):
                    topic_keys.append(ref["topic_key"])
        for suggestion in management_plan.get("suggestions") or []:
            for ref in suggestion.get("knowledge_references") or []:
                if ref.get("topic_key"):
                    topic_keys.append(ref["topic_key"])

        knowledge_refs, knowledge_sources = fetch_published_references(
            topic_keys=list(dict.fromkeys(topic_keys))
        )

        return {
            "patient_id": patient.id,
            "focus_encounter_id": focus_id,
            "patient": {
                "mrn": patient.mrn,
                "sex": patient.sex,
                "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            },
            "encounters": [
                {
                    "id": e.id,
                    "encounter_type": e.encounter_type,
                    "status": e.status,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "closed_at": e.closed_at.isoformat() if e.closed_at else None,
                    "summary": e.summary,
                }
                for e in encounters
            ],
            "intake": {"chief_complaint": intake.chief_complaint if intake else None},
            "structured_findings": structured_findings,
            "assessment": assessment,
            "investigation_plan": investigation_plan,
            "interpretation": interpretation,
            "management_plan": management_plan,
            "laboratory_summary": self._lab_summary(patient_id),
            "imaging_summary": self._imaging_summary(patient_id),
            "procedures_summary": self._procedures_summary(patient_id),
            "reports_summary": self._reports_summary(patient_id),
            "working_diagnoses": self._working_diagnoses(assessment),
            "knowledge_references": knowledge_refs,
            "knowledge_sources": knowledge_sources,
        }

    @staticmethod
    def _working_diagnoses(assessment: dict) -> list[str]:
        names: list[str] = []
        for decision in assessment.get("decisions") or []:
            if decision.get("physician_status") in ("confirmed", "suspected", "accepted", "manual", "modified"):
                name = decision.get("diagnosis_name")
                if name and name not in names:
                    names.append(name)
        return names

    @staticmethod
    def _lab_summary(patient_id: int) -> list[dict]:
        items: list[dict] = []
        for rs in LabResultSet.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if rs.status in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
                items.append({"result_set_id": rs.id, "encounter_id": rs.encounter_id, "status": rs.status})
        return items

    @staticmethod
    def _imaging_summary(patient_id: int) -> list[dict]:
        items: list[dict] = []
        for study in ImagingStudy.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if study.status in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
                items.append({"study_id": study.id, "encounter_id": study.encounter_id, "impression": study.impression})
        return items

    @staticmethod
    def _procedures_summary(patient_id: int) -> list[dict]:
        items: list[dict] = []
        for session in ProcedureSession.query.filter_by(patient_id=patient_id, is_archived=False).all():
            items.append({"session_id": session.id, "outcome": session.outcome})
        return items

    @staticmethod
    def _reports_summary(patient_id: int) -> list[dict]:
        items: list[dict] = []
        for report in Report.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if report.status == STATUS_FINALIZED:
                items.append({"report_id": report.id, "report_number": report.report_number, "status": report.status})
        return items
