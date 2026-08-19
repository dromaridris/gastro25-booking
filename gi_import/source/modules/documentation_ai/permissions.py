"""Clinical Documentation Intelligence RBAC."""

from app.engines import permission_engine
from app.modules.clinical_ai.permissions import require_use as require_ai_use
from app.modules.clinical_ai.permissions import require_view as require_ai_view


def require_documentation_view(user) -> None:
    require_ai_view(user)


def require_documentation_use(user) -> None:
    require_ai_use(user)


def require_documentation_sign(user) -> None:
    permission_engine.require(user, "report:sign", audit_context={"target_type": "ClinicalDocumentDraft"})
