"""Shared types for template configuration bundles."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.clinical_reports.fields.schema_types import FieldSchemaDocument


@dataclass
class TemplateBundle:
    template_key: str
    label: str
    workflow_states: list
    transitions: dict
    mandatory_fields: dict
    validation_rules: list
    timeline_event_defs: list
    qi_indicators: list
    quick_fill_profiles: dict
    narrative_sections: dict
    default_payload: dict = field(default_factory=dict)
    field_schema: "FieldSchemaDocument | None" = None
