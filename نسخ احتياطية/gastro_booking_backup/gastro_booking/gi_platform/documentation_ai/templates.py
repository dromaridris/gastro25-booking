"""Document template definitions and seed — Gastro25 SQLite."""

from __future__ import annotations

import json

from gi_platform.documentation_ai.constants import (
    DOC_TYPE_ADMISSION, DOC_TYPE_DISCHARGE, DOC_TYPE_FOLLOW_UP, DOC_TYPE_PROGRESS, DOC_TYPE_REFERRAL,
)

DEFAULT_SPECIALTY = 'gastroenterology'

TEMPLATES = [
    {
        'template_key': 'doc.admission.gi',
        'document_type': DOC_TYPE_ADMISSION,
        'name': 'GI Admission Note',
        'sections': [
            {'key': 'chief_complaint', 'name': 'Chief Complaint', 'required': True, 'order': 1},
            {'key': 'history_presenting', 'name': 'History of Presenting Illness', 'required': True, 'order': 2},
            {'key': 'past_history', 'name': 'Past History', 'required': False, 'order': 3},
            {'key': 'examination', 'name': 'Examination', 'required': False, 'order': 4},
            {'key': 'investigations', 'name': 'Investigations', 'required': False, 'order': 5},
            {'key': 'assessment', 'name': 'Assessment', 'required': True, 'order': 6},
            {'key': 'plan', 'name': 'Plan', 'required': True, 'order': 7},
        ],
    },
    {
        'template_key': 'doc.progress.gi',
        'document_type': DOC_TYPE_PROGRESS,
        'name': 'GI Progress Note',
        'sections': [
            {'key': 'interval_events', 'name': 'Interval Events', 'required': True, 'order': 1},
            {'key': 'current_status', 'name': 'Current Status', 'required': True, 'order': 2},
            {'key': 'new_findings', 'name': 'New Findings', 'required': False, 'order': 3},
            {'key': 'assessment', 'name': 'Assessment', 'required': True, 'order': 4},
            {'key': 'plan', 'name': 'Plan', 'required': True, 'order': 5},
        ],
    },
    {
        'template_key': 'doc.discharge.gi',
        'document_type': DOC_TYPE_DISCHARGE,
        'name': 'GI Discharge Summary',
        'sections': [
            {'key': 'admission_reason', 'name': 'Admission Reason', 'required': True, 'order': 1},
            {'key': 'hospital_course', 'name': 'Hospital Course', 'required': True, 'order': 2},
            {'key': 'procedures', 'name': 'Procedures', 'required': False, 'order': 3},
            {'key': 'final_diagnosis', 'name': 'Final Diagnosis', 'required': True, 'order': 4},
            {'key': 'treatment', 'name': 'Treatment', 'required': True, 'order': 5},
            {'key': 'follow_up', 'name': 'Follow-up', 'required': True, 'order': 6},
        ],
    },
    {
        'template_key': 'doc.referral.gi',
        'document_type': DOC_TYPE_REFERRAL,
        'name': 'GI Referral Letter',
        'sections': [
            {'key': 'referral_reason', 'name': 'Referral Reason', 'required': True, 'order': 1},
            {'key': 'clinical_summary', 'name': 'Clinical Summary', 'required': True, 'order': 2},
            {'key': 'investigations', 'name': 'Investigations', 'required': False, 'order': 3},
            {'key': 'request', 'name': 'Request', 'required': True, 'order': 4},
        ],
    },
    {
        'template_key': 'doc.follow_up.gi',
        'document_type': DOC_TYPE_FOLLOW_UP,
        'name': 'GI Follow-up Note',
        'sections': [
            {'key': 'since_last_visit', 'name': 'Since Last Visit', 'required': True, 'order': 1},
            {'key': 'current_status', 'name': 'Current Status', 'required': True, 'order': 2},
            {'key': 'assessment', 'name': 'Assessment', 'required': True, 'order': 3},
            {'key': 'plan', 'name': 'Plan', 'required': True, 'order': 4},
        ],
    },
]


class TemplateRegistry:
    @staticmethod
    def get_by_key(db, template_key: str) -> dict | None:
        row = db.execute(
            """
            SELECT * FROM gi_documentation_template
            WHERE template_key = ? AND status = 'active'
            """,
            (template_key,),
        ).fetchone()
        return template_to_dict(row) if row else None

    @staticmethod
    def list_active(db) -> list[dict]:
        rows = db.execute(
            """
            SELECT * FROM gi_documentation_template
            WHERE status = 'active' ORDER BY document_type, name
            """,
        ).fetchall()
        return [template_to_dict(r) for r in rows]


def template_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'template_key': row['template_key'],
        'document_type': row['document_type'],
        'name': row['name'],
        'sections': json.loads(row['sections_json'] or '[]'),
        'version': row['version'],
    }


def seed_templates_if_empty(db) -> int:
    row = db.execute('SELECT COUNT(*) AS c FROM gi_documentation_template').fetchone()
    if row['c'] > 0:
        return 0
    for item in TEMPLATES:
        required = [s['key'] for s in item['sections'] if s.get('required')]
        optional = [s['key'] for s in item['sections'] if not s.get('required')]
        db.execute(
            """
            INSERT INTO gi_documentation_template (
                template_key, document_type, name, specialty_code,
                sections_json, required_fields_json, optional_fields_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item['template_key'], item['document_type'], item['name'], DEFAULT_SPECIALTY,
                json.dumps(item['sections']), json.dumps(required), json.dumps(optional),
            ),
        )
    db.commit()
    return len(TEMPLATES)
