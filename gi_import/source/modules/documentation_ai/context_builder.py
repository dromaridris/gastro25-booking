"""Documentation context assembly — read-only integration."""

from __future__ import annotations

from typing import Any

from app.modules.clinical_assessment import services as assessment_services
from app.modules.clinical_history_ai.constants import DRAFT_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistoryDraft, GuidedHistorySession
from app.modules.clinical_intake.services import get_intake_for_encounter
from app.modules.clinical_interpretation import services as interpretation_services
from app.modules.encounters.models import ClinicalEncounter
from app.modules.investigation_planning import services as planning_services
from app.modules.investigations.models import ImagingStudy, LabResultSet, LabResultValue, RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED
from app.modules.management_plan_ai import services as management_services
from app.modules.patient_journey import services as journey_services
from app.modules.documentation_ai.guideline_linker import fetch_published_references
from app.modules.patients.models import Patient
from app.modules.procedure_execution.models import ProcedureSession
from app.modules.reports.models import Report, STATUS_FINALIZED


class DocumentationContextBuilder:
    """Builds read-only documentation context from all clinical intelligence modules."""

    SOURCE_MODULES = [
        "patients",
        "clinical_intake",
        "clinical_history_ai",
        "clinical_assessment",
        "investigation_planning",
        "investigations",
        "clinical_interpretation",
        "management_plan_ai",
        "patient_journey",
        "procedure_execution",
        "reports",
    ]

    def build(self, acting_user, encounter_id: int) -> dict[str, Any]:
        encounter = ClinicalEncounter.query.get(encounter_id)
        if encounter is None or encounter.is_archived:
            raise ValueError(f"No encounter with id {encounter_id}")

        patient = Patient.query.get(encounter.patient_id)
        intake = get_intake_for_encounter(acting_user, encounter_id)
        assessment = assessment_services.get_final_assessment(acting_user, encounter_id)
        investigation_plan = planning_services.get_plan_view(acting_user, encounter_id)
        interpretation = interpretation_services.get_interpretation_view(acting_user, encounter_id)
        management_plan = management_services.get_plan_view(acting_user, encounter_id)
        journey = journey_services.get_journey_view(acting_user, encounter.patient_id, encounter_id=encounter_id)

        history_session = GuidedHistorySession.query.filter_by(
            encounter_id=encounter_id, is_archived=False
        ).first()
        structured_findings: list[dict] = []
        approved_history_text = ""
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
                sections = draft.sections or {}
                approved_history_text = draft.physician_edited_text or sections.get("narrative") or sections.get("history") or ""

        working_diagnoses = self._working_diagnoses(assessment)
        lab_results = self._lab_results(encounter.patient_id)
        imaging_results = self._imaging_results(encounter.patient_id)
        procedures = self._procedures(encounter.patient_id)
        reports = self._reports(encounter.patient_id)

        topic_keys: list[str] = []
        for suggestion in (assessment.get("suggestions") or []) + (management_plan.get("suggestions") or []):
            for ref in suggestion.get("knowledge_references") or []:
                if ref.get("topic_key"):
                    topic_keys.append(ref["topic_key"])

        knowledge_refs, knowledge_sources = fetch_published_references(
            topic_keys=list(dict.fromkeys(topic_keys))
        )

        sources_used = []
        if intake:
            sources_used.append("clinical_intake")
        if structured_findings:
            sources_used.append("clinical_history_ai")
        if assessment.get("run"):
            sources_used.append("clinical_assessment")
        if investigation_plan.get("plan"):
            sources_used.append("investigation_planning")
        if lab_results or imaging_results:
            sources_used.append("investigations")
        if interpretation.get("run"):
            sources_used.append("clinical_interpretation")
        if management_plan.get("plan"):
            sources_used.append("management_plan_ai")
        if journey.get("follow_up_plans"):
            sources_used.append("patient_journey")
        if procedures:
            sources_used.append("procedure_execution")
        if reports:
            sources_used.append("reports")

        return {
            "encounter_id": encounter.id,
            "patient_id": encounter.patient_id,
            "patient": {
                "mrn": patient.mrn if patient else None,
                "sex": patient.sex if patient else None,
                "date_of_birth": patient.date_of_birth.isoformat() if patient and patient.date_of_birth else None,
            },
            "encounter": {
                "type": encounter.encounter_type,
                "status": encounter.status,
                "summary": encounter.summary,
            },
            "intake": {"chief_complaint": intake.chief_complaint if intake else None},
            "structured_findings": structured_findings,
            "approved_history_text": approved_history_text,
            "assessment": assessment,
            "working_diagnoses": working_diagnoses,
            "investigation_plan": investigation_plan,
            "interpretation": interpretation,
            "management_plan": management_plan,
            "patient_journey": journey,
            "laboratory_results": lab_results,
            "imaging_results": imaging_results,
            "procedures": procedures,
            "reports": reports,
            "knowledge_references": knowledge_refs,
            "knowledge_sources": knowledge_sources,
            "source_modules_used": sources_used,
        }

    @staticmethod
    def _working_diagnoses(assessment: dict) -> list[str]:
        names: list[str] = []
        for decision in assessment.get("decisions") or []:
            if decision.get("physician_status") in ("confirmed", "suspected", "accepted", "manual", "modified"):
                name = decision.get("diagnosis_name")
                if name and name not in names:
                    names.append(name)
        if not names:
            for s in assessment.get("suggestions") or []:
                name = s.get("diagnosis_name")
                if name and name not in names:
                    names.append(name)
        return names

    @staticmethod
    def _lab_results(patient_id: int) -> list[dict]:
        results: list[dict] = []
        for rs in LabResultSet.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if rs.status not in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
                continue
            for val in LabResultValue.query.filter_by(result_set_id=rs.id).all():
                results.append(
                    {
                        "test_code": val.test_code,
                        "value": float(val.numeric_value) if val.numeric_value is not None else val.text_value,
                        "abnormal_flag": val.abnormal_flag,
                        "unit": val.unit,
                    }
                )
        return results

    @staticmethod
    def _imaging_results(patient_id: int) -> list[dict]:
        items: list[dict] = []
        for study in ImagingStudy.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if study.status in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
                items.append(
                    {"impression": study.impression, "findings_summary": study.findings_summary}
                )
        return items

    @staticmethod
    def _procedures(patient_id: int) -> list[dict]:
        return [
            {"session_id": s.id, "outcome": s.outcome}
            for s in ProcedureSession.query.filter_by(patient_id=patient_id, is_archived=False).all()
        ]

    @staticmethod
    def _reports(patient_id: int) -> list[dict]:
        return [
            {"report_number": r.report_number, "status": r.status}
            for r in Report.query.filter_by(patient_id=patient_id, status=STATUS_FINALIZED, is_archived=False).all()
        ]
