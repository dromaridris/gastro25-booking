"""Generic UI helpers for structured report phase forms."""

from app.modules.clinical_reports.fields.conditions import evaluate_condition
from app.modules.clinical_reports.fields.legacy_map import legacy_field_key
from app.modules.clinical_reports.fields.payload import StructuredPayload
from app.modules.clinical_reports.fields.schema_types import FieldSchemaDocument


def legacy_keys_required_for_phase(fsd: FieldSchemaDocument, workflow_phase: str) -> set[str]:
    keys: set[str] = set()
    for field_def in fsd.all_fields():
        if not field_def.required:
            continue
        if field_def.workflow_phases and workflow_phase not in field_def.workflow_phases:
            continue
        keys.add(legacy_field_key(field_def.id))
    return keys


def field_visible(fsd: FieldSchemaDocument, sp: StructuredPayload, field_id: str) -> bool:
    field_def = fsd.field_by_id(field_id)
    if field_def is None or field_def.visibility is None:
        return True
    return evaluate_condition(field_def.visibility, sp)


def strip_hidden_phase_fields(
    fsd: FieldSchemaDocument,
    phase_key: str,
    phase_data: dict,
    payload_raw: dict,
) -> dict:
    """Clear values for fields hidden by FSD visibility rules after POST."""
    sp = StructuredPayload(payload_raw, template_key=fsd.template_key)
    sp.update_legacy_phase(phase_key, phase_data)
    cleared = dict(phase_data)
    section = next((s for s in fsd.sections if s.id == phase_key), None)
    if section is None:
        return cleared
    for field_def in section.fields:
        if field_def.visibility is None:
            continue
        if evaluate_condition(field_def.visibility, sp):
            continue
        key = legacy_field_key(field_def.id)
        if field_def.type == "multi_select":
            cleared[key] = []
        elif field_def.type == "repeatable_group":
            cleared[key] = []
        else:
            cleared[key] = ""
    return cleared


def workflow_phase_labels(fsd: FieldSchemaDocument, extra_labels: dict[str, str] | None = None) -> dict[str, str]:
    labels = {
        section.workflow_phase: section.label
        for section in fsd.sections
        if section.workflow_phase
    }
    if extra_labels:
        labels.update(extra_labels)
    return labels


def template_view_path(template_key: str, view_name: str) -> str:
    """Resolve Jinja template path for a structured report template."""
    return f"clinical_reports/{template_key}/{view_name}"
