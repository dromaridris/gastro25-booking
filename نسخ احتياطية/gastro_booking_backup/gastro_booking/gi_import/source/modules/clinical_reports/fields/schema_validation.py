"""Field Schema Document validation — fail fast at load time."""

from app.core.exceptions import ValidationError
from app.modules.clinical_reports.fields.measurements import UNIT_REGISTRY
from app.modules.clinical_reports.fields.schema_types import (
    FieldDef,
    FieldSchemaDocument,
    NarrativeBinding,
)
from app.modules.reports.models import ALL_SECTION_KEYS

ALLOWED_FIELD_TYPES = {
    "text",
    "long_text",
    "number",
    "date",
    "time",
    "datetime",
    "yes_no",
    "radio",
    "dropdown",
    "multi_select",
    "checkbox",
    "measurement",
    "unit_aware_measurement",
    "repeatable_group",
    "conditional_group",
}


def validate_fsd(fsd: FieldSchemaDocument) -> None:
    """Raise ValidationError when the FSD violates platform rules."""
    errors: list[str] = []
    prefix = f"{fsd.template_key}."

    top_level_ids: list[str] = []
    for section in fsd.sections:
        for field_def in section.fields:
            _collect_top_level_field_errors(field_def, prefix, top_level_ids, errors)

    id_set = set(top_level_ids)
    if len(id_set) != len(top_level_ids):
        seen = set()
        for fid in top_level_ids:
            if fid in seen:
                errors.append(f"Duplicate field_id: '{fid}'")
            seen.add(fid)

    for section in fsd.sections:
        for field_def in section.fields:
            _validate_field_refs(field_def, id_set, errors)
            _validate_field_constraints(field_def, errors)

    if not fsd.section_narratives:
        errors.append("Field Schema Document must define at least one section_narratives entry.")
    else:
        for aggregate in fsd.section_narratives:
            if aggregate.section not in ALL_SECTION_KEYS:
                errors.append(f"Invalid narrative section key: '{aggregate.section}'")
            if not aggregate.bindings and not aggregate.intro:
                errors.append(
                    f"section_narratives entry for '{aggregate.section}' has no bindings or intro."
                )
            for binding in aggregate.bindings:
                _validate_narrative_binding(binding, id_set, errors)

    if errors:
        raise ValidationError(
            "Invalid Field Schema Document for "
            f"'{fsd.template_key}': " + "; ".join(errors)
        )


def _collect_top_level_field_errors(
    field_def: FieldDef, prefix: str, top_level_ids: list[str], errors: list[str]
) -> None:
    if not field_def.id.startswith(prefix):
        errors.append(
            f"Stable field_id '{field_def.id}' must start with template prefix '{prefix}'"
        )
    top_level_ids.append(field_def.id)

    if field_def.type not in ALLOWED_FIELD_TYPES:
        errors.append(f"Unknown field type '{field_def.type}' on field '{field_def.id}'")

    if field_def.type == "repeatable_group":
        child_ids: list[str] = []
        for child in field_def.fields:
            if not child.id or child.id.startswith(prefix):
                errors.append(
                    f"Repeatable group '{field_def.id}' child fields must use short stable "
                    f"names, not template-prefixed ids (got '{child.id}')"
                )
            if child.id in child_ids:
                errors.append(
                    f"Duplicate child field_id '{child.id}' in repeatable group '{field_def.id}'"
                )
            child_ids.append(child.id)
            if child.type not in ALLOWED_FIELD_TYPES - {"repeatable_group", "conditional_group"}:
                errors.append(
                    f"Invalid child field type '{child.type}' in repeatable group '{field_def.id}'"
                )
        if field_def.max_rows is not None and field_def.max_rows < field_def.min_rows:
            errors.append(
                f"repeatable_group '{field_def.id}': max_rows cannot be less than min_rows"
            )


def _validate_field_refs(field_def: FieldDef, id_set: set[str], errors: list[str]) -> None:
    if field_def.visibility and field_def.visibility.field_id:
        if field_def.visibility.field_id not in id_set:
            errors.append(
                f"visibility on '{field_def.id}' references unknown field_id "
                f"'{field_def.visibility.field_id}'"
            )
    if field_def.narrative_binding and field_def.narrative_binding.field_id:
        if field_def.narrative_binding.field_id not in id_set:
            errors.append(
                f"narrative_binding on '{field_def.id}' references unknown field_id "
                f"'{field_def.narrative_binding.field_id}'"
            )
    if field_def.qi_flag and field_def.qi_mapping is None:
        errors.append(f"Field '{field_def.id}' has qi_flag without qi_mapping.")


def _validate_field_constraints(field_def: FieldDef, errors: list[str]) -> None:
    if field_def.unit and field_def.unit not in UNIT_REGISTRY:
        errors.append(f"Field '{field_def.id}' references unknown unit '{field_def.unit}'")


def _validate_narrative_binding(
    binding: NarrativeBinding, id_set: set[str], errors: list[str]
) -> None:
    modes_requiring_field = {"literal", "sentence", "list", "conditional"}
    if binding.mode in modes_requiring_field and not binding.field_id:
        errors.append(f"Narrative binding mode '{binding.mode}' requires field_id.")
    if binding.field_id and binding.field_id not in id_set:
        errors.append(
            f"Narrative binding references unknown field_id '{binding.field_id}'."
        )
    if binding.mode == "sentence" and not binding.template:
        errors.append(
            f"Narrative sentence binding for '{binding.field_id}' requires template."
        )
    if binding.mode == "list" and not binding.item_template:
        errors.append(f"Narrative list binding for '{binding.field_id}' requires item_template.")
    for child in binding.children:
        _validate_narrative_binding(child, id_set, errors)
