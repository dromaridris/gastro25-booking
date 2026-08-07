"""Session-based back navigation — shows the previous page name."""

from __future__ import annotations

from flask import has_request_context, request, session
from flask_login import current_user

from app.ui.navigation import NAV_GROUPS

_STACK_KEY = "gi_nav_stack"
_MAX_STACK = 20

# Friendly page names — plain language for clinicians and staff.
_ENDPOINT_LABELS: dict[str, str] = {
    "core.dashboard": "Home",
    "auth.login": "Log in",
    "auth.logout": "Log out",
    "branding.settings": "Branding settings",
    "branding.about": "About the platform",
    "branding.setup_wizard": "Initial setup",
}

_SKIP_ENDPOINT_PREFIXES = (
    "static.",
    "core.serve_file",
    "branding.platform_logo",
)


def _label_for_endpoint(endpoint: str | None) -> str:
    if not endpoint:
        return "Previous page"
    if endpoint in _ENDPOINT_LABELS:
        return _ENDPOINT_LABELS[endpoint]

    for group in NAV_GROUPS:
        for item in group["items"]:
            if item["endpoint"] == endpoint:
                return item["label"]

    if "." in endpoint:
        module, action = endpoint.split(".", 1)
        module_names = {
            "patients": "Patients",
            "appointments": "Appointments",
            "encounters": "Encounters",
            "procedures": "Procedures",
            "procedure_execution": "Procedure sessions",
            "reports": "Reports",
            "report_templates": "Report templates",
            "clinical_reports": "Clinical reports",
            "workforce": "Training & portfolio",
            "workforce_identity": "Duty schedule",
            "dept_ops": "Department unit",
            "clinical_governance": "Quality & governance",
            "research": "Research",
            "knowledge_library": "Guidelines library",
            "users": "User accounts",
            "audit": "Audit log",
            "investigations": "Investigations",
            "medications": "Medications",
            "clinical_history": "Clinical history",
            "branding": "Branding",
        }
        action_names = {
            "list_patients": "Patient list",
            "view_patient": "Patient record",
            "create_patient": "New patient",
            "list_encounters": "Encounter list",
            "list_procedures": "Procedure bookings",
            "list_appointments": "Appointment list",
            "home": "Dashboard",
            "settings": "Settings",
        }
        if action in action_names:
            return action_names[action]
        if module in module_names:
            readable = action.replace("_", " ").strip()
            return f"{module_names[module]} — {readable.title()}"

    return endpoint.replace("_", " ").replace(".", " — ").title()


def _should_track() -> bool:
    if not has_request_context() or request.method != "GET":
        return False
    if not getattr(current_user, "is_authenticated", False):
        return False
    endpoint = request.endpoint or ""
    if not endpoint or endpoint.startswith(_SKIP_ENDPOINT_PREFIXES):
        return False
    if endpoint.startswith("auth."):
        return False
    return True


def track_navigation_visit() -> None:
    """Record the current page for the back button on the next screen."""
    if not _should_track():
        return

    path = request.path
    endpoint = request.endpoint or ""
    label = _label_for_endpoint(endpoint)
    entry = {"path": path, "endpoint": endpoint, "label": label}

    stack: list[dict] = session.get(_STACK_KEY) or []

    if stack and stack[-1].get("path") == path:
        return

    for index, item in enumerate(stack):
        if item.get("path") == path:
            session[_STACK_KEY] = stack[: index + 1]
            return

    stack.append(entry)
    session[_STACK_KEY] = stack[-_MAX_STACK:]


def get_back_link() -> dict[str, str] | None:
    """Return the previous page in this session, if any."""
    if not has_request_context():
        return None

    stack: list[dict] = session.get(_STACK_KEY) or []
    if len(stack) < 2:
        return None

    previous = stack[-2]
    return {"url": previous.get("path", "/"), "label": previous.get("label", "Previous page")}
