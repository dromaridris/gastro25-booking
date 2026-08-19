"""
Master registry — every GastroIntelligence branch mapped to its Gastro25 home.

Conflict policy: Gastro25 logic wins for booking, auth, roles, ERCP, SQLite runtime.
GI source retained under gi_import/source/ as reference; runtime uses gi_platform/* adapters.

NOT user-facing: /gi-registry/dev-map reads this file for developer inventory only.
Enable with env GASTRO25_DEV_MAP=1 (hidden from Admin nav in production).
"""

from __future__ import annotations

import os

GI_SOURCE_ROOT = os.path.join(os.path.dirname(__file__), '..', 'gi_import', 'source')
GI_MODULES_ROOT = os.path.join(GI_SOURCE_ROOT, 'modules')

# branch_id -> metadata
BRANCH_REGISTRY: dict[str, dict] = {
    'booking': {
        'title': 'Booking',
        'gi_modules': [],
        'g25_owner': 'app.py',
        'route_prefix': '/',
        'status': 'native',
        'notes': 'Gastro25 authoritative — GI appointments module NOT mounted (conflict resolved).',
    },
    'ward': {
        'title': 'Ward',
        'gi_modules': ['inpatient'],
        'g25_owner': 'ward/',
        'route_prefix': '/ward',
        'status': 'native_adapted',
        'notes': 'GI inpatient ORM replaced with SQLite ward_* tables; Gastro25 roles.',
    },
    'knowledge_library': {
        'title': 'Knowledge Library',
        'gi_modules': ['knowledge_library'],
        'g25_owner': 'gi_platform/knowledge_service.py',
        'route_prefix': '/knowledge-library',
        'status': 'sqlite_adapter',
        'tables': ['gi_knowledge_object', 'gi_knowledge_link'],
    },
    'knowledge_pipeline': {
        'title': 'Knowledge Pipeline / Authoring',
        'gi_modules': ['knowledge_library'],
        'g25_owner': 'gi_platform/knowledge_service.py',
        'route_prefix': '/knowledge-library/admin',
        'status': 'sqlite_adapter',
        'notes': 'Draft/review/publish lifecycle on gi_knowledge_object.status',
    },
    'import_manager': {
        'title': 'Import Manager',
        'gi_modules': ['data_exchange'],
        'g25_owner': 'gi_platform/import_service.py',
        'route_prefix': '/data-exchange',
        'status': 'sqlite_adapter',
        'tables': ['gi_import_job'],
    },
    'ai_engine': {
        'title': 'AI Engine',
        'gi_modules': ['clinical_ai', 'clinical_history_ai', 'clinical_assessment',
                       'investigation_planning', 'clinical_interpretation',
                       'management_plan_ai', 'documentation_ai', 'patient_journey', 'analytics'],
        'g25_owner': 'gi_platform/ai_service.py',
        'route_prefix': '/clinical-ai',
        'status': 'sqlite_adapter',
        'tables': ['gi_ai_session', 'gi_ai_request_log'],
        'notes': 'Null/provider stub; audit trail persisted. Full LLM wiring optional via env.',
    },
    'history_builder': {
        'title': 'History Builder',
        'gi_modules': ['clinical_history', 'clinical_intake', 'clinical_history_ai'],
        'g25_owner': 'gi_platform/history_service.py',
        'route_prefix': '/clinical-history',
        'status': 'sqlite_adapter',
        'tables': ['gi_history_session', 'gi_history_answer', 'gi_history_narrative'],
    },
    'clinical_decision_support': {
        'title': 'Clinical Decision Support',
        'gi_modules': ['decision_support'],
        'g25_owner': 'gi_platform/cds_service.py',
        'route_prefix': '/clinical-history/cds',
        'status': 'ported_logic',
        'notes': 'Deterministic CDS over SQLite knowledge; GI orchestrator logic ported.',
    },
    'differential_diagnosis': {
        'title': 'Differential Diagnosis',
        'gi_modules': ['decision_support', 'clinical_assessment'],
        'g25_owner': 'gi_platform/cds_service.py',
        'route_prefix': '/clinical-history/cds',
        'status': 'ported_logic',
    },
    'investigation_suggestions': {
        'title': 'Investigation Suggestions',
        'gi_modules': ['investigation_planning', 'investigations', 'decision_support'],
        'g25_owner': 'gi_platform/cds_service.py',
        'route_prefix': '/clinical-history/investigations',
        'status': 'sqlite_adapter',
        'tables': ['gi_investigation_suggestion'],
    },
    'guideline_engine': {
        'title': 'Guideline Recommendation Engine',
        'gi_modules': ['decision_support', 'knowledge_library'],
        'g25_owner': 'gi_platform/cds_service.py',
        'route_prefix': '/knowledge-library/guidelines',
        'status': 'sqlite_adapter',
    },
    'medical_scores': {
        'title': 'Medical Scores',
        'gi_modules': ['clinical_assessment', 'knowledge_library'],
        'g25_owner': 'gi_platform/cds_service.py',
        'route_prefix': '/clinical-history/scores',
        'status': 'sqlite_adapter',
        'tables': ['gi_clinical_score_result'],
    },
    'research_module': {
        'title': 'Research Module',
        'gi_modules': ['research', 'clinical_data_registry'],
        'g25_owner': 'gi_platform/research_service.py',
        'route_prefix': '/research',
        'status': 'sqlite_adapter',
        'tables': ['gi_research_registry', 'gi_research_variable', 'gi_research_enrollment'],
    },
    'search_engine': {
        'title': 'Search Engine',
        'gi_modules': ['global_search'],
        'g25_owner': 'app.py:/search + gi_routes/search.py',
        'route_prefix': '/search',
        'status': 'extended_native',
        'notes': 'Extended Gastro25 search with ward + knowledge hits; GI ILIKE logic adapted for SQLite.',
    },
    'knowledge_registry': {
        'title': 'Knowledge Registry',
        'gi_modules': ['knowledge_library', 'clinical_data_registry'],
        'g25_owner': 'gi_platform/knowledge_service.py',
        'route_prefix': '/knowledge-library/registry',
        'status': 'sqlite_adapter',
    },
    'knowledge_review': {
        'title': 'Knowledge Review System',
        'gi_modules': ['knowledge_library'],
        'g25_owner': 'gi_platform/knowledge_service.py',
        'route_prefix': '/knowledge-library/review',
        'status': 'sqlite_adapter',
        'notes': 'Status workflow: draft -> review -> published -> archived',
    },
    'knowledge_activation': {
        'title': 'Knowledge Activation Workflow',
        'gi_modules': ['knowledge_library'],
        'g25_owner': 'gi_platform/knowledge_service.py',
        'route_prefix': '/knowledge-library/activation',
        'status': 'sqlite_adapter',
        'tables': ['gi_knowledge_activation'],
    },
    'medications': {
        'title': 'Medication History',
        'gi_modules': ['medications'],
        'g25_owner': 'gi_platform/history_service.py',
        'route_prefix': '/clinical-history/medications',
        'status': 'sqlite_adapter',
        'tables': ['gi_medication_entry'],
    },
    'encounters': {
        'title': 'Clinical Encounters',
        'gi_modules': ['encounters'],
        'g25_owner': 'gi_platform/history_service.py',
        'route_prefix': '/clinical-history',
        'status': 'sqlite_adapter',
        'notes': 'Linked to ward_patient_id; GI encounter model adapted.',
    },
    'endoscopy_procedures_gi': {
        'title': 'GI Procedure Catalogue (non-ERCP)',
        'gi_modules': ['procedures', 'procedure_execution', 'clinical_reports'],
        'g25_owner': 'procedure_extensions.py + booking',
        'route_prefix': '/dashboard',
        'status': 'native_extended',
        'notes': 'ERCP untouched; new procedure labels in booking only.',
    },
}


def list_branches(*, status: str | None = None) -> list[dict]:
    items = []
    for branch_id, meta in BRANCH_REGISTRY.items():
        row = {'id': branch_id, **meta}
        if status and meta.get('status') != status:
            continue
        row['gi_source_present'] = all(
            os.path.isdir(os.path.join(GI_MODULES_ROOT, m.split('/')[0]))
            for m in meta.get('gi_modules', []) if m
        ) if meta.get('gi_modules') else True
        items.append(row)
    return items


def get_branch(branch_id: str) -> dict | None:
    meta = BRANCH_REGISTRY.get(branch_id)
    if not meta:
        return None
    return {'id': branch_id, **meta}


def gi_module_inventory() -> dict[str, bool]:
    """All copied GI module folders and whether present on disk."""
    if not os.path.isdir(GI_MODULES_ROOT):
        return {}
    return {
        name: os.path.isdir(os.path.join(GI_MODULES_ROOT, name))
        for name in os.listdir(GI_MODULES_ROOT)
        if os.path.isdir(os.path.join(GI_MODULES_ROOT, name))
    }
