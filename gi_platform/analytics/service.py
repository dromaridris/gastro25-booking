"""Analytics service — Gastro25."""

from __future__ import annotations

from gi_platform.analytics import metrics_registry
from gi_platform.analytics.permissions import require_analytics_view
from gi_platform.audit_service import log_event


def list_metrics(db, *, role) -> list[dict]:
    require_analytics_view(role=role)
    return metrics_registry.list_metrics()


def run_metric(db, *, role, user_id, metric_id: str) -> dict:
    require_analytics_view(role=role)
    result = metrics_registry.run_metric(db, metric_id)
    log_event(
        db, action='analytics.metric_executed',
        entity_type='metric', entity_id=None, user_id=user_id,
        details={'metric_id': metric_id, 'value': result['value']},
    )
    return result
