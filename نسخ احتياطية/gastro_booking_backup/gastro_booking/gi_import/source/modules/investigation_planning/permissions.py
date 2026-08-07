"""Investigation Planning RBAC — reuses Clinical AI permissions."""

from app.modules.clinical_ai.permissions import require_use as require_planning_use
from app.modules.clinical_ai.permissions import require_view as require_planning_view


def require_investigation_plan_view(user) -> None:
    require_planning_view(user)


def require_investigation_plan_use(user) -> None:
    require_planning_use(user)
