"""Catalog of imported GastroIntelligence modules and ward clinical workflow sections."""

from __future__ import annotations

import os

GI_SOURCE_ROOT = os.path.join(os.path.dirname(__file__), '..', 'gi_import', 'source')

IMPORTED_MODULE_NAMES = (
    'knowledge_library',
    'clinical_history',
    'clinical_history_ai',
    'clinical_intake',
    'clinical_assessment',
    'clinical_interpretation',
    'investigation_planning',
    'investigations',
    'management_plan_ai',
    'documentation_ai',
    'clinical_ai',
    'decision_support',
    'clinical_data_registry',
    'research',
    'global_search',
    'patient_journey',
    'analytics',
    'medications',
    'clinical_documents',
    'encounters',
    'inpatient',
)

GI_MODULE_STATUS = {}
for name in IMPORTED_MODULE_NAMES:
    path = os.path.join(GI_SOURCE_ROOT, 'modules', name)
    GI_MODULE_STATUS[name] = os.path.isdir(path)


def clinical_workflow_sections(*, ward_patient_id: int | None = None, db=None):
    """Single unified inpatient clinical workflow entry."""
    if not ward_patient_id:
        return []
    return [
        {
            'id': 'clinical',
            'title': 'Clinical workflow',
            'modules': [
                'clinical_history', 'clinical_assessment', 'investigations',
                'documentation_ai', 'management_plan_ai', 'decision_support',
            ],
            'url': f'/ward/patient/{ward_patient_id}/clinical',
            'hint': 'History → Examination → Investigations → Summary → Plan',
        },
    ]
