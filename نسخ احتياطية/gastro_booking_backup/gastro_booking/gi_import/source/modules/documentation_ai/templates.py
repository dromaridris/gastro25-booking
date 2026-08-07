"""Document template definitions and seed."""

from __future__ import annotations

import json

from app.extensions import db
from app.modules.documentation_ai.constants import (
    DOC_TYPE_ADMISSION,
    DOC_TYPE_DISCHARGE,
    DOC_TYPE_FOLLOW_UP,
    DOC_TYPE_PROGRESS,
    DOC_TYPE_REFERRAL,
)
from app.modules.documentation_ai.models import DocumentationTemplate

DEFAULT_SPECIALTY = "gastroenterology"

TEMPLATES = [
    {
        "template_key": "doc.admission.gi",
        "document_type": DOC_TYPE_ADMISSION,
        "name": "GI Admission Note",
        "sections": [
            {"key": "chief_complaint", "name": "Chief Complaint", "required": True, "order": 1},
            {"key": "history_presenting", "name": "History of Presenting Illness", "required": True, "order": 2},
            {"key": "past_history", "name": "Past History", "required": False, "order": 3},
            {"key": "examination", "name": "Examination", "required": False, "order": 4},
            {"key": "investigations", "name": "Investigations", "required": False, "order": 5},
            {"key": "assessment", "name": "Assessment", "required": True, "order": 6},
            {"key": "plan", "name": "Plan", "required": True, "order": 7},
        ],
    },
    {
        "template_key": "doc.progress.gi",
        "document_type": DOC_TYPE_PROGRESS,
        "name": "GI Progress Note",
        "sections": [
            {"key": "interval_events", "name": "Interval Events", "required": True, "order": 1},
            {"key": "current_status", "name": "Current Status", "required": True, "order": 2},
            {"key": "new_findings", "name": "New Findings", "required": False, "order": 3},
            {"key": "assessment", "name": "Assessment", "required": True, "order": 4},
            {"key": "plan", "name": "Plan", "required": True, "order": 5},
        ],
    },
    {
        "template_key": "doc.discharge.gi",
        "document_type": DOC_TYPE_DISCHARGE,
        "name": "GI Discharge Summary",
        "sections": [
            {"key": "admission_reason", "name": "Admission Reason", "required": True, "order": 1},
            {"key": "hospital_course", "name": "Hospital Course", "required": True, "order": 2},
            {"key": "procedures", "name": "Procedures", "required": False, "order": 3},
            {"key": "final_diagnosis", "name": "Final Diagnosis", "required": True, "order": 4},
            {"key": "treatment", "name": "Treatment", "required": True, "order": 5},
            {"key": "follow_up", "name": "Follow-up", "required": True, "order": 6},
        ],
    },
    {
        "template_key": "doc.referral.gi",
        "document_type": DOC_TYPE_REFERRAL,
        "name": "GI Referral Letter",
        "sections": [
            {"key": "referral_reason", "name": "Referral Reason", "required": True, "order": 1},
            {"key": "clinical_summary", "name": "Clinical Summary", "required": True, "order": 2},
            {"key": "investigations", "name": "Investigations", "required": False, "order": 3},
            {"key": "request", "name": "Request", "required": True, "order": 4},
        ],
    },
    {
        "template_key": "doc.follow_up.gi",
        "document_type": DOC_TYPE_FOLLOW_UP,
        "name": "GI Follow-up Note",
        "sections": [
            {"key": "since_last_visit", "name": "Since Last Visit", "required": True, "order": 1},
            {"key": "current_status", "name": "Current Status", "required": True, "order": 2},
            {"key": "assessment", "name": "Assessment", "required": True, "order": 3},
            {"key": "plan", "name": "Plan", "required": True, "order": 4},
        ],
    },
]


class TemplateRegistry:
    """Loads and resolves documentation templates."""

    @staticmethod
    def get_by_key(template_key: str) -> DocumentationTemplate | None:
        return DocumentationTemplate.query.filter_by(
            template_key=template_key, status="active", is_archived=False
        ).first()

    @staticmethod
    def list_active() -> list[DocumentationTemplate]:
        return (
            DocumentationTemplate.query.filter_by(status="active", is_archived=False)
            .order_by(DocumentationTemplate.document_type, DocumentationTemplate.name)
            .all()
        )


def seed_templates_if_empty(specialty_code: str = DEFAULT_SPECIALTY) -> int:
    if DocumentationTemplate.query.first() is not None:
        return 0

    for item in TEMPLATES:
        required = [s["key"] for s in item["sections"] if s.get("required")]
        optional = [s["key"] for s in item["sections"] if not s.get("required")]
        db.session.add(
            DocumentationTemplate(
                template_key=item["template_key"],
                document_type=item["document_type"],
                name=item["name"],
                specialty_code=specialty_code,
                sections_json=json.dumps(item["sections"]),
                required_fields_json=json.dumps(required),
                optional_fields_json=json.dumps(optional),
                department_id=1,
            )
        )
    db.session.commit()
    return len(TEMPLATES)
