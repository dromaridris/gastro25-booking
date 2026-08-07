"""Role-based navigation and module visibility — Gastro25 access rules."""

from __future__ import annotations

from gi_platform.constants import CLINICAL_STAFF_ROLES, FULL_ACCESS_ROLES, has_full_access

ADMIN_SPECIALIST = frozenset({'admin', 'specialist'})
RESEARCH_STATS_ROLES = frozenset({
    'admin', 'specialist', 'nurse_manager', 'hod', 'consultant', 'registrar',
})
RESEARCH_ERCP_ROLES = frozenset({'admin', 'specialist', 'nurse_manager', 'consultant', 'hod'})
RESEARCH_DILATATION_ROLES = RESEARCH_ERCP_ROLES
GI_RESEARCH_MODULE_ROLES = frozenset({'admin', 'specialist', 'hod'})
GOVERNANCE_LEADERS = frozenset({'admin', 'hod', 'consultant', 'specialist'})
MM_JC_ROLES = frozenset({'admin', 'hod', 'consultant', 'specialist', 'registrar'})
CLINICAL_NAV_ROLES = frozenset(CLINICAL_STAFF_ROLES) | frozenset({'nurse_manager', 'staff_nurse'})
SCHEDULING_ROLES = frozenset({'scheduler', 'endoscopy_staff'})
WARD_CLINICAL = frozenset({
    'admin', 'specialist', 'hod', 'consultant', 'registrar', 'house_officer',
    'pg_trainee', 'general_endoscopy', 'nurse_manager', 'staff_nurse',
})

MODULE_INTROS = {
    'booking': 'Book and manage endoscopy appointments — the department scheduling calendar.',
    'ward': 'Inpatient ward list, admissions, orders, and patient tasks.',
    'knowledge': 'Published clinical concepts, guidelines, and scores — admin & specialist only.',
    'research': 'Department research registries, variables, and patient enrollment — admin & specialist only.',
    'my_tasks': 'Personal items where you are @mentioned — presentations to deliver and research you lead.',
    'my_logbook': 'Your documented activities grouped by patient and procedure type.',
    'my_duties': 'Your on-call roster assignments for the month.',
    'staff_attendance': 'Department staff attendance overview — admin & specialist only (staff cannot see their own).',
    'governance': 'HOD dashboard: logbook oversight, quality KPIs, and trainee activity.',
    'mm': 'M&M meetings — flag important cases, assign training routes, and schedule presenters.',
    'journal_club': 'Schedule journal club sessions and assign responsible trainees.',
    'hod_research': 'Assign research projects to teams, approve variables, and track enrollment activity.',
    'import_manager': 'Import PDF guidelines into the Knowledge Library — staged for review before publishing.',
    'registry_map': 'Central clinical registry — patients, procedures, disease registries, and department activity.',
    'registry_dev_map': 'Developer-only module inventory and integration map.',
    'clinical_registry': 'Central clinical registry — patients, procedures, disease registries, and department activity.',
    'checklists': 'Safety and procedural checklists — track compliance for endoscopy and ward care.',
    'registrar_approvals': 'Review and approve trainee orders for endoscopy, ERCP, and imaging.',
    'governance_logbook': 'Department-wide logbook — monitor trainee activity and CanMEDS evaluations.',
    'roster': 'On-call rosters for PG trainees and house officers.',
    'research_capture': 'Enter study variables for an enrolled patient — auto-import fills known clinical data.',
    'user_accounts': 'Change staff roles and set account expiry — promote trainees or limit temporary access.',
    'login_promotions': 'Upload promotional images shown on the login page (Admin & HOD). Up to 4 visible; extras rotate daily.',
    'history_templates': 'LEGACY: disease-based history questions for ward/AI. Prefer Clinical Intelligence knowledge admin for new Bates templates.',
    'laboratory': 'Order and enter gastroenterology laboratory investigations with auto-scoring.',
    'unit_operations': 'Endoscopy unit operations — rooms, scopes, reprocessing, consumables, and waiting list.',
}


def _allow(role: str | None, allowed: frozenset[str] | set[str]) -> bool:
    if has_full_access(role):
        return True
    return role in allowed


def can_see_knowledge(role: str | None) -> bool:
    return _allow(role, ADMIN_SPECIALIST)


def can_see_research_module(role: str | None) -> bool:
    return _allow(role, GI_RESEARCH_MODULE_ROLES)


def can_see_statistics(role: str | None) -> bool:
    return _allow(role, RESEARCH_STATS_ROLES)


def can_see_ercp_research_registry(role: str | None) -> bool:
    return _allow(role, RESEARCH_ERCP_ROLES)


def can_see_dilatation_registry(role: str | None) -> bool:
    return _allow(role, RESEARCH_DILATATION_ROLES)


def can_see_upper_gi_registry(role: str | None) -> bool:
    return _allow(role, RESEARCH_ERCP_ROLES)


def can_see_colonoscopy_registry(role: str | None) -> bool:
    return _allow(role, RESEARCH_ERCP_ROLES)


def can_see_gi_research_module(role: str | None) -> bool:
    return _allow(role, GI_RESEARCH_MODULE_ROLES)


def can_see_research_dropdown(role: str | None) -> bool:
    if has_full_access(role):
        return True
    return (
        can_see_statistics(role)
        or can_see_ercp_research_registry(role)
        or can_see_dilatation_registry(role)
        or can_see_upper_gi_registry(role)
        or can_see_colonoscopy_registry(role)
        or can_see_gi_research_module(role)
        or can_assign_hod_research(role)
    )


def can_see_staff_attendance(role: str | None) -> bool:
    return _allow(role, ADMIN_SPECIALIST)


def can_see_my_attendance(role: str | None) -> bool:
    return False


def can_see_clinical_menu(role: str | None) -> bool:
    if has_full_access(role):
        return True
    return role in CLINICAL_NAV_ROLES and role not in SCHEDULING_ROLES


def can_see_my_logbook(role: str | None) -> bool:
    if has_full_access(role):
        return True
    return role in CLINICAL_NAV_ROLES and role not in SCHEDULING_ROLES


def can_see_governance(role: str | None) -> bool:
    return _allow(role, GOVERNANCE_LEADERS)


def can_see_mm_journal_club(role: str | None) -> bool:
    return _allow(role, MM_JC_ROLES)


def can_see_history_templates(role: str | None) -> bool:
    return _allow(role, frozenset({'admin', 'hod', 'consultant', 'specialist'}))


def can_see_unit_operations(role: str | None) -> bool:
    """Endoscopy unit operations dashboard and tools."""
    if has_full_access(role):
        return True
    return role in frozenset({
        'hod', 'consultant', 'specialist', 'nurse_manager',
        'endoscopy_staff', 'scheduler', 'staff_nurse', 'registrar',
    })


def can_manage_unit_operations(role: str | None) -> bool:
    if has_full_access(role):
        return True
    return role in frozenset({'hod', 'nurse_manager', 'endoscopy_staff'})


def can_see_unit_ops_topnav(role: str | None) -> bool:
    """Standalone top-nav Unit Ops only when Admin menu is not available."""
    return can_see_unit_operations(role) and not can_see_admin_menu(role)


def can_manage_mm_training(role: str | None) -> bool:
    """Legacy role check — prefer can_assign_mm_presenters(db, user_id, role)."""
    return _allow(role, MM_JC_ROLES)


def can_assign_mm_presenters(db, user_id: int | None, role: str | None) -> bool:
    """Schedule M&M / journal club presenters — roster managers, admin, and HOD."""
    if has_full_access(role):
        return True
    from gi_platform.constants import ROSTER_PERMISSIONS
    from gi_platform.permission_service import has_permission
    return any(has_permission(db, user_id, perm) for perm in ROSTER_PERMISSIONS)


def can_assign_hod_research(role: str | None) -> bool:
    return _allow(role, FULL_ACCESS_ROLES)


def can_review_hod_research(role: str | None) -> bool:
    return _allow(role, frozenset({'admin', 'specialist', 'hod'}))


def can_manage_user_accounts(role: str | None) -> bool:
    return _allow(role, FULL_ACCESS_ROLES)


def can_see_import_manager(role: str | None) -> bool:
    return _allow(role, FULL_ACCESS_ROLES)


def can_see_registry_map(role: str | None) -> bool:
    """GI Clinical Registry dashboard — central department navigation."""
    if has_full_access(role):
        return True
    return role in frozenset({
        'hod', 'consultant', 'registrar', 'nurse_manager', 'house_officer',
        'pg_trainee', 'general_endoscopy', 'staff_nurse',
    })


def can_see_clinical_registry(role: str | None) -> bool:
    return can_see_registry_map(role)


def dev_map_enabled() -> bool:
    """Internal migration inventory — off in production unless GASTRO25_DEV_MAP=1."""
    import os
    return os.environ.get('GASTRO25_DEV_MAP', '').strip().lower() in ('1', 'true', 'yes')


def can_see_registry_dev_map(role: str | None) -> bool:
    if not dev_map_enabled():
        return False
    return _allow(role, ADMIN_SPECIALIST)


def can_see_patient_search(role: str | None) -> bool:
    return _allow(role, frozenset({'admin', 'specialist', 'nurse_manager'}))


def can_see_registrar_approvals(role: str | None) -> bool:
    return _allow(role, frozenset({'admin', 'hod', 'consultant', 'specialist', 'registrar'}))


def can_see_my_tasks(role: str | None) -> bool:
    if has_full_access(role):
        return True
    return role in WARD_CLINICAL and role not in SCHEDULING_ROLES


def can_see_my_duties(role: str | None) -> bool:
    if has_full_access(role):
        return True
    return role in WARD_CLINICAL and role not in SCHEDULING_ROLES


def can_see_incidents(role: str | None) -> bool:
    if has_full_access(role):
        return True
    return role in GOVERNANCE_LEADERS or role in frozenset({'registrar', 'nurse_manager'})


def can_see_admin_panel(role: str | None) -> bool:
    return _allow(role, frozenset({'admin', 'specialist', 'hod', 'consultant'}))


def can_see_booking_admin(role: str | None) -> bool:
    return _allow(role, ADMIN_SPECIALIST)


def can_see_roster_permissions(role: str | None) -> bool:
    return _allow(role, frozenset({'admin', 'specialist', 'hod'}))


def can_manage_login_promos(role: str | None) -> bool:
    return _allow(role, FULL_ACCESS_ROLES)


def can_see_admin_menu(role: str | None) -> bool:
    if has_full_access(role):
        return True
    if not role or role in SCHEDULING_ROLES:
        return False
    return (
        can_see_admin_panel(role)
        or can_see_booking_admin(role)
        or can_see_my_duties(role)
        or can_see_staff_attendance(role)
        or can_see_governance(role)
        or can_see_mm_journal_club(role)
        or can_see_incidents(role)
        or can_manage_user_accounts(role)
        or can_see_roster_permissions(role)
        or can_see_import_manager(role)
        or can_manage_login_promos(role)
    )


def scheduling_only_nav(role: str | None) -> bool:
    return role in SCHEDULING_ROLES


def intro(key: str) -> str:
    return MODULE_INTROS.get(key, '')
