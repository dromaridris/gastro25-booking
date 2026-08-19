"""Clinical context for management planning — read-only integration."""

from __future__ import annotations

from typing import Any

from app.modules.clinical_assessment import services as assessment_services
from app.modules.clinical_history_ai.constants import DRAFT_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistoryDraft, GuidedHistorySession
from app.modules.clinical_intake.services import get_intake_for_encounter
from app.modules.clinical_interpretation import services as interpretation_services
from app.modules.encounters.models import ClinicalEncounter
from app.modules.investigation_planning import services as planning_services
from app.modules.investigations.models import (
    ImagingStudy,
    LabResultSet,
    LabResultValue,
    RESULT_STATUS_AVAILABLE,
    RESULT_STATUS_REVIEWED,
)
from app.modules.management_plan_ai.constants import WORKING_DIAGNOSIS_STATUSES
from app.modules.management_plan_ai.guideline_linker import fetch_published_references
from app.modules.patients.models import Patient


class ManagementContextBuilder:
    """Builds management context from intake, history, assessment, results, and interpretation."""

    def build(self, acting_user, encounter_id: int) -> dict[str, Any]:
        encounter = ClinicalEncounter.query.get(encounter_id)
        if encounter is None or encounter.is_archived:
            raise ValueError(f"No encounter with id {encounter_id}")

        patient = Patient.query.get(encounter.patient_id)
        intake = get_intake_for_encounter(acting_user, encounter_id)
        assessment = assessment_services.get_final_assessment(acting_user, encounter_id)
        plan_view = planning_services.get_plan_view(acting_user, encounter_id)
        interpretation_view = interpretation_services.get_interpretation_view(acting_user, encounter_id)

        history_session = GuidedHistorySession.query.filter_by(
            encounter_id=encounter_id, is_archived=False
        ).first()
        structured_findings: list[dict] = []
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

        working_diagnoses = self._working_diagnoses(assessment)
        lab_results = self._lab_results(encounter.patient_id)
        imaging_results = self._imaging_results(encounter.patient_id)

        topic_keys: list[str] = []
        stable_ids: list[str] = []
        for suggestion in assessment.get("suggestions") or []:
            for ref in suggestion.get("knowledge_references") or []:
                if ref.get("topic_key"):
                    topic_keys.append(ref["topic_key"])
                if ref.get("stable_id"):
                    stable_ids.append(ref["stable_id"])

        knowledge_refs, knowledge_sources = fetch_published_references(
            topic_keys=list(dict.fromkeys(topic_keys)),
            stable_ids=list(dict.fromkeys(stable_ids)),
        )

        return {
            "encounter_id": encounter.id,
            "patient_id": encounter.patient_id,
            "patient": {
                "mrn": patient.mrn if patient else None,
                "sex": patient.sex if patient else None,
                "date_of_birth": patient.date_of_birth.isoformat() if patient and patient.date_of_birth else None,
            },
            "intake": {
                "chief_complaint": intake.chief_complaint if intake else None,
                "complaint_entry_code": history_session.complaint_entry_code if history_session else None,
            },
            "structured_findings": structured_findings,
            "differential_diagnoses": assessment.get("suggestions") or [],
            "physician_diagnosis_decisions": assessment.get("decisions") or [],
            "working_diagnoses": working_diagnoses,
            "investigation_plan": plan_view.get("plan"),
            "investigation_suggestions": plan_view.get("suggestions") or [],
            "interpretation": interpretation_view.get("run"),
            "interpretation_findings": interpretation_view.get("findings") or [],
            "differential_updates": interpretation_view.get("differential_updates") or [],
            "laboratory_results": lab_results,
            "imaging_results": imaging_results,
            "knowledge_references": knowledge_refs,
            "knowledge_sources": knowledge_sources,
        }

    @staticmethod
    def _working_diagnoses(assessment: dict[str, Any]) -> list[str]:
        names: list[str] = []
        for decision in assessment.get("decisions") or []:
            status = decision.get("physician_status")
            name = decision.get("diagnosis_name")
            if status in WORKING_DIAGNOSIS_STATUSES and name and name not in names:
                names.append(name)
        return names

    @staticmethod
    def _lab_results(patient_id: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for result_set in LabResultSet.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if result_set.status not in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
                continue
            for val in LabResultValue.query.filter_by(result_set_id=result_set.id).all():
                if val.abnormal_flag in ("low", "high"):
                    results.append(
                        {
                            "test_code": val.test_code,
                            "abnormal_flag": val.abnormal_flag,
                            "numeric_value": float(val.numeric_value) if val.numeric_value is not None else None,
                        }
                    )
        return results

    @staticmethod
    def _imaging_results(patient_id: int) -> list[dict[str, Any]]:
        studies: list[dict[str, Any]] = []
        for study in ImagingStudy.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if study.status in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
                studies.append(
                    {
                        "study_id": study.id,
                        "impression": study.impression,
                        "findings_summary": study.findings_summary,
                    }
                )
        return studies
