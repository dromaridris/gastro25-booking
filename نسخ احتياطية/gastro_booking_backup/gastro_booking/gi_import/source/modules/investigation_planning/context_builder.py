"""Clinical context for investigation planning — read-only integration."""

from __future__ import annotations

from typing import Any

from app.modules.clinical_assessment import services as assessment_services
from app.modules.clinical_history_ai.constants import DRAFT_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistoryDraft, GuidedHistorySession
from app.modules.clinical_intake.services import get_intake_for_encounter
from app.modules.encounters.models import ClinicalEncounter
from app.modules.investigation_planning.evidence_linker import fetch_published_references
from app.modules.investigation_planning.models import InvestigationLibraryEntry
from app.modules.investigations.models import (
    InvestigationCatalogueItem,
    InvestigationOrder,
    InvestigationOrderItem,
    LabResultSet,
    ORDER_STATUS_REVIEWED,
    RESULT_STATUS_REVIEWED,
)
from app.modules.patients.models import Patient


class InvestigationContextBuilder:
    """Builds work-up context from intake, history, assessment, and existing data."""

    def build(self, acting_user, encounter_id: int) -> dict[str, Any]:
        encounter = ClinicalEncounter.query.get(encounter_id)
        if encounter is None or encounter.is_archived:
            raise ValueError(f"No encounter with id {encounter_id}")

        patient = Patient.query.get(encounter.patient_id)
        intake = get_intake_for_encounter(acting_user, encounter_id)
        assessment = assessment_services.get_final_assessment(acting_user, encounter_id)

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

        differential = assessment.get("suggestions") or []
        physician_decisions = assessment.get("decisions") or []

        existing_codes = self._existing_investigation_codes(encounter.patient_id)
        existing_results = self._existing_result_codes(encounter.patient_id)

        topic_keys: list[str] = []
        stable_ids: list[str] = []
        for entry in InvestigationLibraryEntry.query.filter_by(status="active", is_archived=False).all():
            if entry.knowledge_topic_key:
                topic_keys.append(entry.knowledge_topic_key)
            if entry.knowledge_stable_id:
                stable_ids.append(entry.knowledge_stable_id)

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
            },
            "intake": {
                "chief_complaint": intake.chief_complaint if intake else None,
                "complaint_entry_code": history_session.complaint_entry_code if history_session else None,
            },
            "structured_findings": structured_findings,
            "differential_diagnoses": differential,
            "physician_diagnosis_decisions": physician_decisions,
            "existing_investigation_codes": sorted(existing_codes),
            "existing_result_codes": sorted(existing_results),
            "knowledge_references": knowledge_refs,
            "knowledge_sources": knowledge_sources,
        }

    @staticmethod
    def _existing_investigation_codes(patient_id: int) -> set[str]:
        codes: set[str] = set()
        orders = InvestigationOrder.query.filter_by(patient_id=patient_id, is_archived=False).all()
        for order in orders:
            if order.status == ORDER_STATUS_REVIEWED or order.status in ("available", "reviewed"):
                for item in InvestigationOrderItem.query.filter_by(order_id=order.id, is_archived=False).all():
                    cat = InvestigationCatalogueItem.query.get(item.catalogue_item_id)
                    if cat:
                        codes.add(cat.code)
        return codes

    @staticmethod
    def _existing_result_codes(patient_id: int) -> set[str]:
        codes: set[str] = set()
        for result_set in LabResultSet.query.filter_by(patient_id=patient_id, is_archived=False).all():
            if result_set.status == RESULT_STATUS_REVIEWED:
                for val in result_set.values:
                    codes.add(val.test_code)
        return codes
