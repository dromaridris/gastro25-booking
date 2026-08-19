"""Quality metric definition model."""

from __future__ import annotations

import json

from app.core.base_model import BaseModel
from app.extensions import db

from app.modules.analytics.constants import METRIC_STATUS_ACTIVE

SCOPE_HOSPITAL = "hospital"
SCOPE_DEPARTMENT = "department"
SCOPE_SPECIALTY = "specialty"

ALL_SCOPES = (SCOPE_HOSPITAL, SCOPE_DEPARTMENT, SCOPE_SPECIALTY)


class QualityMetricDefinition(BaseModel):
    """Quality improvement and hospital KPI metric metadata."""

    __tablename__ = "quality_metric_definitions"

    metric_id = db.Column(db.String(80), nullable=False, unique=True, index=True)
    metric_definition_id = db.Column(
        db.Integer, db.ForeignKey("metric_definitions.id"), nullable=True, index=True
    )
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(40), nullable=False, index=True)
    scope_level = db.Column(db.String(20), nullable=False, default=SCOPE_DEPARTMENT, index=True)
    specialty = db.Column(db.String(60), nullable=True, index=True)
    quality_department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True, index=True)
    description = db.Column(db.Text, nullable=True)
    calculation_reference = db.Column(db.String(120), nullable=False)
    required_data_sources_json = db.Column(db.Text, nullable=False, default="[]")
    target_value = db.Column(db.Float, nullable=True)
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
