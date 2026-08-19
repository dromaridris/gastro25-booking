"""Clinical Interpretation RBAC — reuses Clinical AI permissions."""

from app.modules.clinical_ai.permissions import require_use as require_interpretation_use
from app.modules.clinical_ai.permissions import require_view as require_interpretation_view


def require_clinical_interpretation_view(user) -> None:
    require_interpretation_view(user)


def require_clinical_interpretation_use(user) -> None:
    require_interpretation_use(user)
