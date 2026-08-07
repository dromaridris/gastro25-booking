"""Seed built-in metric definitions."""

from __future__ import annotations

from app.extensions import db

from .constants import METRIC_STATUS_ACTIVE
from .metrics import BUILTIN_METRIC_DEFINITIONS
from .models import MetricDefinition


def seed_metrics_if_empty() -> int:
    """Register foundation metrics. Returns count of newly created definitions."""
    created = 0
    for spec in BUILTIN_METRIC_DEFINITIONS:
        existing = MetricDefinition.query.filter_by(metric_id=spec["metric_id"]).first()
        if existing:
            continue
        metric = MetricDefinition(
            metric_id=spec["metric_id"],
            name=spec["name"],
            description=spec.get("description"),
            category=spec["category"],
            calculation_logic_ref=spec["calculation_logic_ref"],
            status=METRIC_STATUS_ACTIVE,
            version=1,
        )
        metric.data_sources = spec.get("data_sources", [])
        db.session.add(metric)
        created += 1
    if created:
        db.session.commit()
    return created
