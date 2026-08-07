"""Navigation structure and active-state detection — presentation only."""

from __future__ import annotations

from flask import request

NAV_GROUPS = [
    {
        "id": "platform",
        "label": "Platform",
        "items": [
            {"label": "Ward bed board", "endpoint": "inpatient.board", "permission": "inpatient:view"},
            {"label": "Consult requests", "endpoint": "consult_requests.list_requests", "permission": "consult:view"},
            {"label": "Notifications", "endpoint": "notifications.inbox", "permission": "notification:view"},
            {"label": "Department calendar", "endpoint": "calendar_hub.week_view", "permission": "calendar:view"},
            {"label": "Education activities", "endpoint": "education.list_activities", "permission": "education:view"},
            {"label": "Data export", "endpoint": "data_exchange.index", "permission": "data:export"},
            {"label": "Archive storage", "endpoint": "archive_storage.index", "permission": "archive_storage:view"},
        ],
    },
    {
        "id": "clinical",
        "label": "Patient care",
        "items": [
            {"label": "Patient list", "endpoint": "patients.list_patients", "permission": "patient:view"},
            {"label": "Appointments", "endpoint": "appointments.list_appointments", "permission": "appointment:view"},
            {"label": "Clinical encounters", "endpoint": "encounters.list_encounters", "permission": "encounter:view"},
            {"label": "Endoscopy bookings", "endpoint": "procedures.list_procedures", "permission": "procedure:view"},
            {"label": "Procedures in progress", "endpoint": "procedure_execution.list_sessions", "permission": "procedure_execution:view"},
        ],
    },
    {
        "id": "reporting",
        "label": "Reports",
        "items": [
            {"label": "Endoscopy reports", "endpoint": "reports.list_reports", "permission": "report:view"},
            {"label": "Colonoscopy & upper GI reports", "endpoint": "report_templates.list_template_reports", "permission": "report:view"},
            {"label": "Clinical report forms", "endpoint": "clinical_reports.list_reports", "permission": "report:view"},
        ],
    },
    {
        "id": "operations",
        "label": "Department",
        "items": [
            {"label": "Training & portfolio", "endpoint": "workforce.home", "permission": "workforce:view_own"},
            {"label": "Unit operations", "endpoint": "dept_ops.home", "permission": "dept_ops:view"},
            {"label": "Endoscopy rooms", "endpoint": "dept_ops.rooms", "permission": "dept_ops:view"},
            {"label": "Scope inventory", "endpoint": "dept_ops.scopes", "permission": "dept_ops:view"},
            {"label": "Waiting list", "endpoint": "dept_ops.waiting_list", "permission": "dept_ops:waiting_list"},
            {"label": "Duty roster", "endpoint": "dept_ops.roster", "permission": "dept_ops:roster_manage"},
            {"label": "Department messages", "endpoint": "dept_ops.messages", "permission": "dept_ops:message"},
            {"label": "My duty schedule", "endpoint": "workforce_identity.my_duties", "permission": "workforce_identity:duty_view"},
            {"label": "Quality & safety", "endpoint": "clinical_governance.home", "permission": "governance:view"},
        ],
    },
    {
        "id": "intelligence",
        "label": "Research",
        "items": [
            {"label": "Research registry", "endpoint": "research.list_registries", "permission": "research:view"},
        ],
    },
    {
        "id": "admin",
        "label": "Settings",
        "items": [
            {"label": "Training accounts", "endpoint": "workforce_identity.hod_dashboard", "permission": "workforce_identity:dashboard_view"},
            {"label": "Invite trainee / house officer", "endpoint": "workforce_identity.list_invitations", "permission": "workforce_identity:invite_manage"},
            {"label": "User accounts", "endpoint": "users.list_users", "permission": "user:manage"},
            {"label": "Hospital branding", "endpoint": "branding.settings", "permission": "branding:manage"},
            {"label": "Educational banner", "endpoint": "branding.pharma_banner_manage", "permission": "pharma_banner:manage"},
            {"label": "Clinical guidelines (admin)", "endpoint": "knowledge_library.index", "permission": "knowledge_library:edit"},
            {"label": "System audit log", "endpoint": "audit.list_logs", "permission": "audit_log:view"},
        ],
    },
]

_ENDPOINT_PREFIXES = {
    "inpatient": "inpatient.",
    "consult_requests": "consult_requests.",
    "notifications": "notifications.",
    "calendar_hub": "calendar_hub.",
    "education": "education.",
    "data_exchange": "data_exchange.",
    "archive_storage": "archive_storage.",
    "global_search": "global_search.",
    "patient_documents": "patient_documents.",
    "clinical_documents": "clinical_documents.",
    "patients": "patients.",
    "appointments": "appointments.",
    "encounters": "encounters.",
    "procedures": "procedures.",
    "procedure_execution": "procedure_execution.",
    "reports": "reports.",
    "report_templates": "report_templates.",
    "clinical_reports": "clinical_reports.",
    "workforce": "workforce.",
    "workforce_identity": "workforce_identity.",
    "dept_ops": "dept_ops.",
    "clinical_governance": "clinical_governance.",
    "research": "research.",
    "knowledge_library": "knowledge_library.",
    "users": "users.",
    "branding": "branding.",
    "audit": "audit.",
}


def is_nav_active(item_endpoint: str) -> bool:
    current = request.endpoint or ""
    if current == item_endpoint:
        return True
    prefix = item_endpoint.split(".")[0] if "." in item_endpoint else item_endpoint
    group_prefix = _ENDPOINT_PREFIXES.get(prefix, f"{prefix}.")
    return current.startswith(group_prefix)


def visible_nav_groups(can_fn) -> list[dict]:
    groups = []
    for group in NAV_GROUPS:
        items = [item for item in group["items"] if can_fn(item["permission"])]
        if items:
            groups.append({**group, "items": items})
    return groups
