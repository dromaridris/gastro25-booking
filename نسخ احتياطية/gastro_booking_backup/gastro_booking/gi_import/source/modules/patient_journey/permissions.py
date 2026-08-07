"""Patient Journey RBAC — reuses existing encounter and clinical AI permissions."""

from app.engines import permission_engine
from app.modules.clinical_ai.permissions import require_use as require_ai_use
from app.modules.clinical_ai.permissions import require_view as require_ai_view


def require_journey_view(user) -> None:
    permission_engine.require(user, "encounter:view", audit_context={"target_type": "PatientJourney"})


def require_journey_use(user) -> None:
    permission_engine.require(user, "encounter:create", audit_context={"target_type": "PatientJourney"})


def require_journey_ai_use(user) -> None:
    require_ai_use(user)


def require_journey_ai_view(user) -> None:
    require_ai_view(user)
