"""Specialty metric definition model."""

from __future__ import annotations

import json

from app.core.base_model import BaseModel
from app.extensions import db

from app.modules.analytics.constants import METRIC_STATUS_ACTIVE


class SpecialtyMetricDefinition(BaseModel):
    """Specialty-scoped metric metadata — registers through MetricDefinition."""

    __tablename__ = "specialty_metric_definitions"

    metric_id = db.Column(db.String(80), nullable=False, unique=True, index=True)
    metric_definition_id = db.Column(
        db.Integer, db.ForeignKey("metric_definitions.id"), nullable=True, index=True
    )
    specialty = db.Column(db.String(60), nullable=False, index=True)
    specialty_department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True, index=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    calculation_reference = db.Column(db.String(120), nullable=False)
    required_data_sources_json = db.Column(db.Text, nullable=False, default="[]")
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default=METRIC_STATUS_ACTIVE, index=True)
    configuration_json = db.Column(db.Text, nullable=True)

    metric_definition = db.relationship("MetricDefinition", foreign_keys=[metric_definition_id])

    @property
    def required_data_sources(self) -> list[str]:
        return json.loads(self.required_data_sources_json or "[]")

    @required_data_sources.setter
    def required_data_sources(self, value: list[str]) -> None:
        self.required_data_sources_json = json.dumps(value or [])

    @property
    def configuration(self) -> dict:
        return json.loads(self.configuration_json or "{}")

    @configuration.setter
    def configuration(self, value: dict) -> None:
        self.configuration_json = json.dumps(value or {})
