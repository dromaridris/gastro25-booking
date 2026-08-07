"""Clinical context builder — intake, history, patient, knowledge."""

from __future__ import annotations

from typing import Any

from app.modules.clinical_history_ai.constants import DRAFT_STATUS_APPROVED
from app.modules.clinical_history_ai.models import GuidedHistoryAnswer, GuidedHistoryDraft, GuidedHistorySession
from app.modules.clinical_intake.services import get_intake_for_encounter
from app.modules.encounters.models import ClinicalEncounter
from app.modules.patients.models import Patient

from .knowledge_linker import fetch_published_references


class AssessmentContextBuilder:
    """Collects structured clinical context without modifying source modules."""

    def build(self, acting_user, encounter_id: int) -> dict[str, Any]:
        encounter = ClinicalEncounter.query.get(encounter_id)
        if encounter is None or encounter.is_archived:
            raise ValueError(f"No encounter with id {encounter_id}")

        patient = Patient.query.get(encounter.patient_id)
        intake = get_intake_for_encounter(acting_user, encounter_id)
        history_session = GuidedHistorySession.query.filter_by(
            encounter_id=encounter_id, is_archived=False
        ).first()

        structured_findings: list[dict] = []
        history_sections: dict[str, str | None] = {}
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
                history_sections = draft.sections
            else:
                answers = GuidedHistoryAnswer.query.filter_by(
                    session_id=history_session.id, is_archived=False
                ).all()
                structured_findings = [
                    {
                        "question_id": a.question_id,
                        "response": a.response_display or a.response_value,
                        "answer_id": a.id,
                    }
                    for a in answers
                ]

        answers_map = {
            item.get("question_id", ""): str(item.get("response", "")).lower()
            for item in structured_findings
            if item.get("question_id")
        }

        topic_keys: list[str] = []
        stable_ids: list[str] = []
        complaint_code = history_session.complaint_entry_code if history_session else None
        if complaint_code:
            from app.modules.clinical_assessment.models import DiagnosisRuleDefinition

            for rule in DiagnosisRuleDefinition.query.filter_by(
                complaint_code=complaint_code, status="active", is_archived=False
            ).all():
                if rule.knowledge_topic_key:
                    topic_keys.append(rule.knowledge_topic_key)
                if rule.knowledge_stable_id:
                    stable_ids.append(rule.knowledge_stable_id)

        knowledge_refs, knowledge_sources = fetch_published_references(
            topic_keys=topic_keys, stable_ids=stable_ids
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
                "normalized_complaint": intake.normalized_complaint if intake else None,
                "complaint_entry_code": history_session.complaint_entry_code if history_session else None,
            },
            "structured_findings": structured_findings,
            "history_sections": history_sections,
            "answers_map": answers_map,
            "knowledge_references": knowledge_refs,
            "knowledge_sources": knowledge_sources,
        }
