"""Unified ward clinical encounter — specialty-agnostic staged workflow.

Physician surface of record: Ward Clinical Workflow.
Knowledge (GI first) lives in seeds/catalogue/CKP — not in engine hardcoding.
"""

from gi_platform.unified_encounter.service import (
    CURRENT_PROBLEMS,
    KNOWN_DISEASES,
    STAGE_LABELS,
    advance_stage,
    build_workflow_view,
    ensure_schema,
    get_state,
    handle_action,
    save_state,
)

__all__ = [
    'CURRENT_PROBLEMS',
    'KNOWN_DISEASES',
    'STAGE_LABELS',
    'advance_stage',
    'build_workflow_view',
    'ensure_schema',
    'get_state',
    'handle_action',
    'save_state',
]
