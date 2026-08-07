"""Clinical History AI permissions — reuse existing RBAC."""

from __future__ import annotations

from app.engines import permission_engine
from app.modules.clinical_ai.permissions import require_use as require_clinical_ai_use


def require_history_view(user, *, session_id: int | None = None) -> None:
    permission_engine.require(
        user,
        "history:view",
        audit_context={"target_type": "GuidedHistorySession", "target_id": session_id},
    )


def require_history_document(user, *, session_id: int | None = None) -> None:
    permission_engine.require(
        user,
        "history:document",
        audit_context={"target_type": "GuidedHistorySession", "target_id": session_id},
    )


def require_ai_generation(user) -> None:
    require_clinical_ai_use(user)
