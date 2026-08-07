"""Analytics Foundation domain models."""

from __future__ import annotations

import json
import uuid

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

from .constants import METRIC_STATUS_ACTIVE, PERIOD_CUSTOM


class MetricDefinition(BaseModel):
    """Configurable metric definition — versioned and traceable."""

    __tablename__ = "metric_definitions"

    metric_id = db.Column(db.String(80), nullable=False, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    calculation_logic_ref = db.Column(db.String(120), nullable=False)
    data_sources_json = db.Column(db.Text, nullable=False, default="[]")
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default=METRIC_STATUS_ACTIVE, index=True)
    config_json = db.Column(db.Text, nullable=True)

    snapshots = db.relationship("AnalyticsSnapshot", back_populates="metric_definition", lazy="dynamic")

    @property
    def data_sources(self) -> list[str]:
        return json.loads(self.data_sources_json or "[]")

    @data_sources.setter
    def data_sources(self, value: list[str]) -> None:
        self.data_sources_json = json.dumps(value or [])

    @property
    def config(self) -> dict:
        return json.loads(self.config_json or "{}")

    @config.setter
    def config(self, value: dict) -> None:
        self.config_json = json.dumps(value or {})


class AnalyticsSnapshot(BaseModel):
    """Read-only cached metric result for a period."""

    __tablename__ = "analytics_snapshots"

    snapshot_uuid = db.Column(db.String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    metric_definition_id = db.Column(db.Integer, db.ForeignKey("metric_definitions.id"), nullable=False, index=True)
    metric_id = db.Column(db.String(80), nullable=False, index=True)
    period_type = db.Column(db.String(20), nullable=False, default=PERIOD_CUSTOM)
    period_start = db.Column(db.DateTime(timezone=True), nullable=False)
    period_end = db.Column(db.DateTime(timezone=True), nullable=False)
    filters_json = db.Column(db.Text, nullable=True)
    result_json = db.Column(db.Text, nullable=False)
    metric_version = db.Column(db.Integer, nullable=False, default=1)
    generated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    generated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    metric_definition = db.relationship("MetricDefinition", back_populates="snapshots")

    @property
    def filters(self) -> dict:
        return json.loads(self.filters_json or "{}")

    @filters.setter
    def filters(self, value: dict) -> None:
        self.filters_json = json.dumps(value or {})

    @property
    def result(self) -> dict:
        return json.loads(self.result_json or "{}")

    @result.setter
    def result(self, value: dict) -> None:
        self.result_json = json.dumps(value or {})
