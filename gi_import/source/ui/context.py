"""UI template context — presentation layer only."""

from __future__ import annotations

from flask import has_request_context, request

from app.ui.navigation import is_nav_active, visible_nav_groups
from app.ui.navigation_history import get_back_link
from app.ui.quick_actions import visible_quick_actions

_CLINICAL_WORKFLOW_PREFIXES = (
    "/encounters",
    "/patients",
    "/investigations",
    "/clinical-history",
    "/medications",
    "/clinical-reports",
    "/clinical-documents",
    "/clinical-assessment",
    "/clinical-intake",
    "/investigation-planning",
    "/documentation-ai",
    "/procedures",
    "/appointments",
)


def _is_clinical_workflow_page() -> bool:
    if not has_request_context():
        return False
    path = request.path.rstrip("/") or "/"
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in _CLINICAL_WORKFLOW_PREFIXES)


def get_ui_context() -> dict:
    from flask_login import current_user

    can_fn = lambda perm: False
    if getattr(current_user, "is_authenticated", False):
        from app.engines import permission_engine

        can_fn = lambda perm: permission_engine.check(current_user, perm)

    return {
        "gi_nav_groups": visible_nav_groups(can_fn) if has_request_context() else [],
        "gi_nav_active": is_nav_active,
        "gi_page_path": request.path if has_request_context() else "",
        "gi_back_link": get_back_link() if has_request_context() else None,
        "gi_quick_actions": visible_quick_actions(can_fn) if has_request_context() else [],
        "gi_pharma_slides": _pharma_slides() if has_request_context() else [],
        "gi_footer_show_platform": not _is_clinical_workflow_page() if has_request_context() else True,
    }


def _pharma_slides() -> list:
    try:
        from app.modules.branding.pharma_banner_service import list_active_slides
        return list_active_slides()
    except Exception:
        return []
