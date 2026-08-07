"""Management Plan Assistant RBAC — reuses Clinical AI permissions."""

from app.modules.clinical_ai.permissions import require_use as require_management_plan_use
from app.modules.clinical_ai.permissions import require_view as require_management_plan_view


def require_management_plan_ai_view(user) -> None:
    require_management_plan_view(user)


def require_management_plan_ai_use(user) -> None:
    require_management_plan_use(user)
