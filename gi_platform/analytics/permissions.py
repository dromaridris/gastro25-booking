"""Analytics RBAC."""

ANALYTICS_ROLES = frozenset({'admin', 'hod', 'consultant', 'specialist'})


def require_analytics_view(*, role: str | None) -> None:
    from gi_platform.clinical_ai.permissions import PermissionDeniedError
    if role not in ANALYTICS_ROLES:
        raise PermissionDeniedError('Analytics view denied.')
