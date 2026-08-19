"""History Composer — structured answers to clinical documentation."""

from __future__ import annotations

from typing import Any

from app.modules.clinical_history_ai.constants import COMPOSER_SECTIONS
from app.modules.clinical_history_ai.models import GuidedHistoryAnswer, GuidedHistoryQuestion, GuidedHistorySession


CATEGORY_TO_SECTION = {
    "history_of_present_illness": "history_of_present_illness",
    "associated_symptoms": "associated_symptoms",
    "negative_findings": "relevant_negative_findings",
    "red_flags": "relevant_negative_findings",
    "past_medical_history": "past_medical_history",
    "medication_history": "medication_history",
    "allergy_history": "medication_history",
    "family_history": "family_history",
    "social_history": "social_history",
    "risk_factors": "risk_factors",
    "review_of_systems": "associated_symptoms",
}


class HistoryComposer:
    """
    Converts structured answers into professional documentation sections.

    Uses only recorded answers — never invents missing information.
    """

    def compose(
        self,
        session: GuidedHistorySession,
        answers: list[GuidedHistoryAnswer],
        *,
        chief_complaint: str | None = None,
    ) -> dict[str, Any]:
        question_map = self._load_question_map([a.question_id for a in answers])
        grouped: dict[str, list[str]] = {section: [] for section in COMPOSER_SECTIONS}
        structured_findings: list[dict[str, Any]] = []
        answered_ids: list[int] = []

        for answer in answers:
            answered_ids.append(answer.id)
            question = question_map.get(answer.question_id)
            category = question.category if question else "history_of_present_illness"
            section_key = CATEGORY_TO_SECTION.get(category, "history_of_present_illness")
            display = answer.response_display or answer.response_value
            line = self._format_line(question, display)
            grouped.setdefault(section_key, []).append(line)
            structured_findings.append(
                {
                    "question_id": answer.question_id,
                    "question_text": question.question_text if question else answer.question_id,
                    "category": category,
                    "response": display,
                    "answer_id": answer.id,
                }
            )

        sections: dict[str, str | None] = {}
        missing: list[str] = []
        cc = chief_complaint or session.chief_complaint or session.normalized_complaint
        sections["chief_complaint"] = cc

        for section_key in COMPOSER_SECTIONS:
            if section_key == "chief_complaint":
                continue
            lines = grouped.get(section_key) or []
            if lines:
                sections[section_key] = "\n".join(lines)
            else:
                sections[section_key] = None
                missing.append(section_key.replace("_", " "))

        learning_notes = {
            "structured_findings_visible": True,
            "generated_phrasing_visible": True,
            "missing_information": missing,
        }
        return {
            "sections": sections,
            "source_answer_ids": answered_ids,
            "missing_information": missing,
            "structured_findings": structured_findings,
            "learning_notes": learning_notes,
        }

    @staticmethod
    def _load_question_map(question_ids: list[str]) -> dict[str, GuidedHistoryQuestion]:
        if not question_ids:
            return {}
        rows = GuidedHistoryQuestion.query.filter(
            GuidedHistoryQuestion.question_id.in_(question_ids),
            GuidedHistoryQuestion.is_archived.is_(False),
        ).all()
        return {row.question_id: row for row in rows}

    @staticmethod
    def _format_line(question: GuidedHistoryQuestion | None, display: str) -> str:
        if question is None:
            return display
        if question.question_type == "boolean":
            normalized = display.strip().lower()
            if normalized in {"yes", "true", "1"}:
                return f"{question.question_text}: Present."
            if normalized in {"no", "false", "0"}:
                return f"{question.question_text}: Denied."
        return f"{question.question_text}: {display}."
