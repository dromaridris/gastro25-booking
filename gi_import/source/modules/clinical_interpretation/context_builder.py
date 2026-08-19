"""Clinical context for interpretation — read-only integration."""

from __future__ import annotations

from typing import Any

from app.modules.clinical_assessment import services as assessment_services
from app.modules.clinical_history_ai.constants import DRAFT_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistoryDraft, GuidedHistorySession
from app.modules.clinical_intake.services import get_intake_for_encounter
from app.modules.clinical_reports.models import ClinicalReportDocument, WF_FINALIZE
from app.modules.encounters.models import ClinicalEncounter
from app.modules.investigation_planning import services as planning_services
from app.modules.investigations.models import (
    ImagingStudy,
    LabResultSet,
    LabResultValue,
    RESULT_STATUS_AVAILABLE,
    RESULT_STATUS_REVIEWED,
)
from app.modules.patients.models import Patient
from app.modules.reports.models import Report, STATUS_FINALIZED

from .evidence_linker import fetch_published_references


class InterpretationContextBuilder:
    """Assembles read-only clinical context from intake, history, assessment, and results."""

    def build(self, acting_user, encounter_id: int) -> dict[str, Any]:
        encounter = ClinicalEncounter.query.get(encounter_id)
        if encounter is None or encounter.is_archived:
            raise ValueError(f"No encounter with id {encounter_id}")

        patient = Patient.query.get(encounter.patient_id)
        intake = get_intake_for_encounter(acting_user, encounter_id)
        assessment = assessment_services.get_final_assessment(acting_user, encounter_id)
        plan_view = planning_services.get_plan_view(acting_user, encounter_id)

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

        lab_results = self._lab_results_for_patient(encounter.patient_id)
        imaging_results = self._imaging_results_for_patient(encounter.patient_id)
        procedure_reports = self._procedure_reports_for_patient(encounter.patient_id)

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

        data_sources = []
        for lab in lab_results:
            data_sources.append({"type": "laboratory", "id": lab["result_set_id"], "code": lab.get("test_code")})
        for img in imaging_results:
            data_sources.append({"type": "imaging", "id": img["study_id"], "code": img.get("catalogue_code")})
        for proc in procedure_reports:
            data_sources.append({"type": "procedure_report", "id": proc["document_id"], "code": proc.get("template_key")})

        return {
            "encounter_id": encounter.id,
            "patient_id": encounter.patient_id,
            "patient": {
                "mrn": patient.mrn if patient else None,
                "sex": patient.sex if patient else None,
            },
            "intake": {
                "chief_complaint": intake.chief_complaint if intake else None,
                "complaint_entry_code": history_session.complaint_entry_code if history_session else None,
            },
            "structured_findings": structured_findings,
            "differential_diagnoses": assessment.get("suggestions") or [],
            "physician_diagnosis_decisions": assessment.get("decisions") or [],
            "previous_differential_snapshot": assessment.get("suggestions") or [],
            "investigation_plan": plan_view.get("plan"),
            "investigation_suggestions": plan_view.get("suggestions") or [],
            "laboratory_results": lab_results,
            "imaging_results": imaging_results,
            "procedure_reports": procedure_reports,
            "clinical_data_sources": data_sources,
            "knowledge_references": knowledge_refs,
            "knowledge_sources": knowledge_sources,
        }

    @staticmethod
    def _lab_results_for_patient(patient_id: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        result_sets = LabResultSet.query.filter_by(patient_id=patient_id, is_archived=False).all()
        for result_set in result_sets:
            if result_set.status not in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
                continue
            for val in LabResultValue.query.filter_by(result_set_id=result_set.id).all():
                cat = val.catalogue_item
                results.append(
                    {
                        "result_set_id": result_set.id,
                        "encounter_id": result_set.encounter_id,
                        "test_code": val.test_code,
                        "test_name": cat.name if cat else val.test_code,
                        "numeric_value": float(val.numeric_value) if val.numeric_value is not None else None,
                        "text_value": val.text_value,
                        "unit": val.unit,
                        "reference_low": float(val.reference_low) if val.reference_low is not None else None,
                        "reference_high": float(val.reference_high) if val.reference_high is not None else None,
                        "abnormal_flag": val.abnormal_flag,
                        "status": result_set.status,
                        "resulted_at": result_set.resulted_at.isoformat() if result_set.resulted_at else None,
                    }
                )
        return results

    @staticmethod
    def _imaging_results_for_patient(patient_id: int) -> list[dict[str, Any]]:
        studies: list[dict[str, Any]] = []
        for study in ImagingStudy.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if study.status not in (RESULT_STATUS_AVAILABLE, RESULT_STATUS_REVIEWED):
                continue
            cat = study.catalogue_item
            studies.append(
                {
                    "study_id": study.id,
                    "encounter_id": study.encounter_id,
                    "catalogue_code": cat.code if cat else None,
                    "study_name": cat.name if cat else "Imaging study",
                    "body_region": study.body_region,
                    "findings_summary": study.findings_summary,
                    "impression": study.impression,
                    "study_date": study.study_date.isoformat() if study.study_date else None,
                    "status": study.status,
                }
            )
        return studies

    @staticmethod
    def _procedure_reports_for_patient(patient_id: int) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        finalized = Report.query.filter_by(patient_id=patient_id, status=STATUS_FINALIZED, is_archived=False).all()
        for report in finalized:
            doc = ClinicalReportDocument.query.filter_by(report_id=report.id, is_archived=False).first()
            if doc is None:
                continue
            payload = doc.get_payload()
            impression = payload.get("impression") or payload.get("synthesis", {}).get("impression")
            findings = payload.get("findings") or payload.get("synthesis", {}).get("findings")
            reports.append(
                {
                    "document_id": doc.id,
                    "report_id": report.id,
                    "template_key": doc.template_key,
                    "workflow_state": doc.workflow_state,
                    "impression": impression,
                    "findings": findings,
                    "is_finalized": doc.workflow_state == WF_FINALIZE or report.status == STATUS_FINALIZED,
                }
            )
        return reports
