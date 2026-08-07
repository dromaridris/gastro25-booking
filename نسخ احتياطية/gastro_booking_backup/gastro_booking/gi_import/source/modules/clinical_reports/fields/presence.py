"""Field-level validation and workflow presence — Sprint 3D."""

from app.modules.clinical_reports.fields.conditions import evaluate_condition
from app.modules.clinical_reports.fields.payload import StructuredPayload, is_field_present
from app.modules.clinical_reports.fields.schema_types import FieldDef, FieldSchemaDocument


def is_field_satisfied(
    field_def: FieldDef, payload: StructuredPayload, workflow_phase: str | None = None
) -> bool:
    if field_def.inactive or field_def.deprecated:
        return True
    if workflow_phase and field_def.workflow_phases and workflow_phase not in field_def.workflow_phases:
        return True
    if not field_def.required:
        return True
    if not evaluate_condition(field_def.visibility, payload):
        return True
    value = payload.get_field(field_def.id)
    return is_field_present(value)


def missing_mandatory_fields(
    fsd: FieldSchemaDocument, payload: StructuredPayload, workflow_phase: str
) -> list[str]:
    missing = []
    for field_def in fsd.all_fields():
        if not field_def.required:
            continue
        if field_def.workflow_phases and workflow_phase not in field_def.workflow_phases:
            continue
        if not is_field_satisfied(field_def, payload, workflow_phase):
            missing.append(field_def.id)
    return missing


def qi_metrics_from_fsd(fsd: FieldSchemaDocument, payload: StructuredPayload) -> dict[str, str]:
    results = {}
    for field_def in fsd.all_fields():
        if not field_def.qi_flag or not field_def.qi_mapping:
            continue
        value = payload.get_field(field_def.id)
        mapping = field_def.qi_mapping
        matched = False
        if mapping.operator == "equals":
            matched = value == mapping.value
        elif mapping.operator == "not_empty":
            matched = is_field_present(value)
        results[mapping.metric_key] = str(matched)
    return results
