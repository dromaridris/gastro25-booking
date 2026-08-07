"""Analytics Foundation services."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.engines import audit_engine
from app.extensions import db

from .constants import (
    AUDIT_CONFIG_CHANGE,
    AUDIT_DASHBOARD_ACCESS,
    AUDIT_EXPORT_REQUEST,
    AUDIT_METRIC_EXECUTION,
    METRIC_STATUS_ACTIVE,
    METRIC_STATUS_INACTIVE,
    PERIOD_CUSTOM,
)
from .metric_seed import seed_metrics_if_empty
from .models import AnalyticsSnapshot, MetricDefinition
from .permissions import require_configure, require_export, require_view
from .query_engine import AnalyticsQueryEngine

_engine = AnalyticsQueryEngine()


def init_analytics_module() -> None:
    """Lazy seeding happens on first analytics service call."""
    return None


def ensure_metrics_seeded() -> int:
    created = seed_metrics_if_empty()
    from .specialty_metrics.registry import ensure_specialty_metrics_seeded
    from .quality_metrics.registry import ensure_quality_metrics_seeded

    created += ensure_specialty_metrics_seeded()
    created += ensure_quality_metrics_seeded()
    return created


def list_metrics(user) -> list[dict[str, Any]]:
    require_view(user)
    ensure_metrics_seeded()
    _audit_dashboard_access(user, action="list_metrics")
    metrics = MetricDefinition.query.filter_by(is_archived=False).order_by(MetricDefinition.metric_id).all()
    return [metric_to_dict(m) for m in metrics]


def get_metric(user, metric_id: str) -> MetricDefinition | None:
    require_view(user)
    return MetricDefinition.query.filter_by(metric_id=metric_id, is_archived=False).first()


def run_metric(
    user,
    metric_id: str,
    *,
    period_type: str = PERIOD_CUSTOM,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    department_id: int | None = None,
    physician_id: int | None = None,
    role_code: str | None = None,
    procedure_type_id: int | None = None,
    diagnosis_category: str | None = None,
    create_snapshot: bool = False,
) -> dict[str, Any]:
    require_view(user)
    ensure_metrics_seeded()
    metric = MetricDefinition.query.filter_by(metric_id=metric_id, is_archived=False).first()
    if metric is None:
        raise ValueError(f"Unknown metric: {metric_id}")

    payload = _engine.execute_metric(
        metric,
        period_type=period_type,
        date_from=date_from,
        date_to=date_to,
        department_id=department_id,
        physician_id=physician_id,
        role_code=role_code,
        procedure_type_id=procedure_type_id,
        diagnosis_category=diagnosis_category,
    )

    audit_engine.log(
        action=AUDIT_METRIC_EXECUTION,
        user=user,
        target_type="MetricDefinition",
        target_id=metric.id,
        details={
            "metric_id": metric_id,
            "filters": payload.get("filters"),
            "period": payload.get("period"),
        },
    )

    if create_snapshot:
        snapshot = _create_snapshot(user, metric, payload)
        payload["snapshot"] = snapshot_to_dict(snapshot)

    return payload


def list_snapshots(
    user,
    *,
    metric_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    require_view(user)
    _audit_dashboard_access(user, action="list_snapshots", metric_id=metric_id)
    query = AnalyticsSnapshot.query.filter_by(is_archived=False).order_by(AnalyticsSnapshot.generated_at.desc())
    if metric_id:
        query = query.filter_by(metric_id=metric_id)
    snapshots = query.limit(limit).all()
    return [snapshot_to_dict(s) for s in snapshots]


def configure_metric(user, metric_id: str, *, status: str | None = None, config: dict | None = None) -> dict[str, Any]:
    require_configure(user)
    metric = MetricDefinition.query.filter_by(metric_id=metric_id, is_archived=False).first()
    if metric is None:
        raise ValueError(f"Unknown metric: {metric_id}")

    changes: dict[str, Any] = {}
    if status is not None:
        if status not in (METRIC_STATUS_ACTIVE, METRIC_STATUS_INACTIVE):
            raise ValueError(f"Invalid status: {status}")
        changes["status"] = status
        metric.status = status

    if config is not None:
        merged = dict(metric.config)
        merged.update(config)
        changes["config"] = config
        metric.config = merged

    if changes:
        metric.version += 1
        db.session.commit()
        audit_engine.log(
            action=AUDIT_CONFIG_CHANGE,
            user=user,
            target_type="MetricDefinition",
            target_id=metric.id,
            details={"metric_id": metric_id, "changes": changes, "version": metric.version},
        )

    return metric_to_dict(metric)


def export_metric_result(user, metric_id: str, **run_kwargs) -> dict[str, Any]:
    require_export(user)
    metric = MetricDefinition.query.filter_by(metric_id=metric_id, is_archived=False).first()
    result = run_metric(user, metric_id, **run_kwargs)
    audit_engine.log(
        action=AUDIT_EXPORT_REQUEST,
        user=user,
        target_type="MetricDefinition",
        target_id=metric.id if metric else None,
        details={"metric_id": metric_id, "filters": result.get("filters")},
    )
    result["exported"] = True
    return result


def metric_to_dict(metric: MetricDefinition) -> dict[str, Any]:
    return {
        "id": metric.id,
        "metric_id": metric.metric_id,
        "name": metric.name,
        "description": metric.description,
        "category": metric.category,
        "calculation_logic_ref": metric.calculation_logic_ref,
        "data_sources": metric.data_sources,
        "version": metric.version,
        "status": metric.status,
        "config": metric.config,
    }


def snapshot_to_dict(snapshot: AnalyticsSnapshot) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot.snapshot_uuid,
        "metric_id": snapshot.metric_id,
        "period_type": snapshot.period_type,
        "period_start": snapshot.period_start.isoformat() if snapshot.period_start else None,
        "period_end": snapshot.period_end.isoformat() if snapshot.period_end else None,
        "generated_at": snapshot.generated_at.isoformat() if snapshot.generated_at else None,
        "generated_by_id": snapshot.generated_by_id,
        "filters": snapshot.filters,
        "result": snapshot.result,
        "version": snapshot.metric_version,
    }


def _create_snapshot(user, metric: MetricDefinition, payload: dict[str, Any]) -> AnalyticsSnapshot:
    period = payload["period"]
    snapshot = AnalyticsSnapshot(
        metric_definition_id=metric.id,
        metric_id=metric.metric_id,
        period_type=period["period_type"],
        period_start=datetime.fromisoformat(period["start"]),
        period_end=datetime.fromisoformat(period["end"]),
        metric_version=metric.version,
        generated_by_id=user.id,
    )
    snapshot.filters = payload.get("filters", {})
    snapshot.result = payload.get("result", {})
    db.session.add(snapshot)
    db.session.commit()
    return snapshot


def _audit_dashboard_access(user, *, action: str, metric_id: str | None = None) -> None:
    audit_engine.log(
        action=AUDIT_DASHBOARD_ACCESS,
        user=user,
        target_type="AnalyticsDashboard",
        details={"action": action, "metric_id": metric_id},
    )
