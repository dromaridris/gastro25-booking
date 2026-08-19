"""Clinical Assessment RBAC — reuses Clinical AI permissions."""

from __future__ import annotations

from app.modules.clinical_ai.permissions import require_use as require_clinical_ai_use
from app.modules.clinical_ai.permissions import require_view as require_clinical_ai_view


def require_assessment_view(user) -> None:
    require_clinical_ai_view(user)


def require_assessment_use(user) -> None:
    require_clinical_ai_use(user)
