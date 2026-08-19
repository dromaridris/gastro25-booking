"""Declarative narrative generation from FSD bindings — Sprint 3D."""

from app.modules.clinical_reports.fields.conditions import evaluate_condition
from app.modules.clinical_reports.fields.measurements import format_field_value
from app.modules.clinical_reports.fields.payload import StructuredPayload, is_field_present
from app.modules.clinical_reports.fields.schema_types import (
    FieldDef,
    FieldSchemaDocument,
    NarrativeBinding,
    SectionNarrativeAggregate,
)


def generate_narrative_from_fsd(fsd: FieldSchemaDocument, raw_payload: dict) -> dict[str, str]:
    payload = StructuredPayload(raw_payload, template_key=fsd.template_key)
    sections: dict[str, str] = {}
    for aggregate in fsd.section_narratives:
        text = _render_section_aggregate(aggregate, payload, fsd)
        if text.strip():
            sections[aggregate.section] = text
    return sections


def _render_section_aggregate(
    aggregate: SectionNarrativeAggregate, payload: StructuredPayload, fsd: FieldSchemaDocument
) -> str:
    lines = []
    if aggregate.intro:
        lines.append(aggregate.intro)
    for binding in aggregate.bindings:
        clause = render_binding(binding, payload, fsd)
        if clause:
            lines.append(clause)
    return "\n".join(lines)


def render_binding(
    binding: NarrativeBinding, payload: StructuredPayload, fsd: FieldSchemaDocument
) -> str:
    if binding.mode == "section_aggregate" and binding.children:
        parts = [render_binding(c, payload, fsd) for c in binding.children]
        return "\n".join(p for p in parts if p)

    field_def = fsd.field_by_id(binding.field_id) if binding.field_id else None
    if field_def and not evaluate_condition(field_def.visibility, payload):
        return ""

    if binding.mode == "list" and binding.field_id:
        return _render_list(binding, payload, field_def)

    if binding.mode == "sentence" and binding.template and binding.field_id:
        value = payload.get_field(binding.field_id)
        if not is_field_present(value):
            return ""
        formatted = _format_value(field_def, value)
        return binding.template.replace("{value}", formatted)

    if binding.mode == "paragraph":
        parts = []
        for child in binding.children:
            part = render_binding(child, payload, fsd)
            if part:
                parts.append(part)
        return "\n".join(parts)

    if binding.mode == "literal" and binding.field_id:
        value = payload.get_field(binding.field_id)
        if not is_field_present(value):
            return binding.empty_text or ""
        label = binding.label or (field_def.label if field_def else binding.field_id)
        formatted = _format_value(field_def, value)
        return f"{label}: {formatted}"

    return ""


def _format_value(field_def: FieldDef | None, value) -> str:
    if field_def is None:
        if isinstance(value, list):
            return ", ".join(str(v).replace("_", " ") for v in value)
        return str(value)
    return format_field_value(field_def.type, value, field_def.unit)


def _render_list(binding: NarrativeBinding, payload: StructuredPayload, field_def: FieldDef | None) -> str:
    rows = payload.get_field(binding.field_id) or []
    if not rows:
        return binding.empty_text or ""
    lines = []
    template = binding.item_template or "{index}. {value}"
    for idx, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        line = template
        for key, val in row.items():
            if key == "_row_id":
                continue
            placeholder = "{" + key + "}"
            formatted = str(val).replace("_", " ") if val else "—"
            line = line.replace(placeholder, formatted)
        line = line.replace("{index}", str(idx))
        lines.append(line)
    return "\n".join(lines)
