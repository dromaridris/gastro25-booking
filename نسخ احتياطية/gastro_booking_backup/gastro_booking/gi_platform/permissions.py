"""Map Gastro25 session roles to GI capability flags."""

from __future__ import annotations

_ALL_CLINICAL = {
    'knowledge.read', 'clinical_history.read', 'clinical_history.write',
    'cds.run', 'ward.manage', 'tasks.view',
}

ROLE_CAPABILITIES: dict[str, set[str]] = {
    'admin': {
        'knowledge.read', 'knowledge.write', 'knowledge.review', 'knowledge.activate',
        'research.read', 'research.write', 'research.enroll',
        'clinical_history.read', 'clinical_history.write',
        'cds.run', 'ai.use', 'import.run', 'ward.manage', 'tasks.manage', 'tasks.view',
    },
    'hod': {
        'knowledge.read', 'knowledge.write', 'knowledge.review', 'knowledge.activate',
        'research.read', 'research.write', 'research.enroll',
        'clinical_history.read', 'clinical_history.write',
        'cds.run', 'ai.use', 'import.run', 'ward.manage', 'tasks.manage', 'tasks.view',
    },
    'consultant': {
        'knowledge.read', 'research.read', 'research.enroll',
        'clinical_history.read', 'clinical_history.write',
        'cds.run', 'ai.use', 'ward.manage', 'tasks.manage', 'tasks.view',
    },
    'specialist': {
        'knowledge.read', 'knowledge.write', 'knowledge.review',
        'research.read', 'research.write', 'research.enroll',
        'clinical_history.read', 'clinical_history.write',
        'cds.run', 'ai.use', 'ward.manage', 'tasks.manage', 'tasks.view',
    },
    'registrar': {
        'knowledge.read', 'research.read', 'research.enroll',
        'clinical_history.read', 'clinical_history.write',
        'cds.run', 'ward.manage', 'tasks.view', 'tasks.manage',
    },
    'general_endoscopy': {
        'knowledge.read', 'clinical_history.read', 'cds.run', 'ward.manage', 'tasks.view',
    },
    'house_officer': {
        'knowledge.read', 'clinical_history.read', 'clinical_history.write',
        'cds.run', 'ward.manage', 'tasks.view',
    },
    'pg_trainee': {
        'knowledge.read', 'clinical_history.read', 'clinical_history.write',
        'cds.run', 'ai.use', 'ward.manage', 'tasks.view',
    },
    'nurse_manager': {
        'knowledge.read', 'research.read', 'research.enroll',
        'clinical_history.read', 'clinical_history.write',
        'cds.run', 'ward.manage', 'tasks.view',
    },
    'staff_nurse': {
        'knowledge.read', 'clinical_history.read', 'ward.manage', 'tasks.view',
    },
    'oncall_doctor': {  # legacy — same as pg_trainee
        'knowledge.read', 'clinical_history.read', 'clinical_history.write',
        'cds.run', 'ai.use', 'ward.manage', 'tasks.view',
    },
    'scheduler': {'knowledge.read', 'clinical_history.read', 'tasks.view'},
    'endoscopy_staff': {'knowledge.read', 'clinical_history.read', 'tasks.view'},
}


def role_has_capability(role: str, capability: str) -> bool:
    return capability in ROLE_CAPABILITIES.get(role or '', set())
