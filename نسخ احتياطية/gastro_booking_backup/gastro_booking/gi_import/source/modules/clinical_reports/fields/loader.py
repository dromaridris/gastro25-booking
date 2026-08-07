"""Load Field Schema Documents from JSON files."""

import json
from pathlib import Path

from app.core.exceptions import NotFoundError

from app.modules.clinical_reports.fields.schema_validation import validate_fsd
from app.modules.clinical_reports.fields.schema_types import (
    ComponentDefs,
    Condition,
    FieldDef,
    FieldSchemaDocument,
    NarrativeBinding,
    QiMapping,
    SectionDef,
    SectionNarrativeAggregate,
    TimelineEventDef,
)

_SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


def _parse_condition(data: dict | None) -> Condition | None:
    if not data:
        return None
    return Condition(
        when=data.get("when", "field"),
        field_id=data.get("field_id"),
        operator=data.get("operator", "equals"),
        value=data.get("value"),
        conditions=[_parse_condition(c) for c in data.get("conditions", []) if c],
    )


def _parse_narrative_binding(data: dict | None) -> NarrativeBinding | None:
    if not data:
        return None
    return NarrativeBinding(
        section=data.get("section"),
        mode=data.get("mode", "sentence"),
        template=data.get("template"),
        empty_text=data.get("empty_text"),
        item_template=data.get("item_template"),
        field_id=data.get("field_id"),
        label=data.get("label"),
        children=[_parse_narrative_binding(c) for c in data.get("children", []) if c],
    )


def _parse_qi_mapping(data: dict | None) -> QiMapping | None:
    if not data:
        return None
    return QiMapping(
        metric_key=data["metric_key"],
        operator=data.get("operator", "equals"),
        value=data.get("value"),
    )


def _parse_field(data: dict) -> FieldDef:
    return FieldDef(
        id=data["id"],
        label=data["label"],
        type=data["type"],
        required=data.get("required", False),
        default=data.get("default"),
        visibility=_parse_condition(data.get("visibility")),
        printable=data.get("printable", True),
        research_flag=data.get("research_flag", False),
        qi_flag=data.get("qi_flag", False),
        qi_mapping=_parse_qi_mapping(data.get("qi_mapping")),
        unit=data.get("unit"),
        vocabulary_source=data.get("vocabulary_source"),
        help_text=data.get("help_text"),
        workflow_phases=data.get("workflow_phases") or [],
        narrative_binding=_parse_narrative_binding(data.get("narrative_binding")),
        deprecated=data.get("deprecated", False),
        inactive=data.get("inactive", False),
        fields=[_parse_field(f) for f in data.get("fields", [])],
        min_rows=data.get("min_rows", 0),
        max_rows=data.get("max_rows"),
        reorderable=data.get("reorderable", True),
        sort_order=data.get("sort_order", 0),
    )


def parse_fsd_dict(data: dict) -> FieldSchemaDocument:
    sections = []
    for s in data.get("sections", []):
        sections.append(
            SectionDef(
                id=s["id"],
                label=s["label"],
                workflow_phase=s.get("workflow_phase"),
                fields=[_parse_field(f) for f in s.get("fields", [])],
                sort_order=s.get("sort_order", 0),
            )
        )
    timeline = []
    for ev in data.get("components", {}).get("timeline", []):
        timeline.append(
            TimelineEventDef(key=ev["key"], label=ev["label"], required=ev.get("required", False))
        )
    section_narratives = []
    for sn in data.get("section_narratives", []):
        section_narratives.append(
            SectionNarrativeAggregate(
                section=sn["section"],
                mode=sn.get("mode", "section_aggregate"),
                intro=sn.get("intro"),
                bindings=[_parse_narrative_binding(b) for b in sn.get("bindings", []) if b],
            )
        )
    fsd = FieldSchemaDocument(
        schema_version=data.get("schema_version", "1"),
        template_key=data["template_key"],
        sections=sections,
        components=ComponentDefs(timeline=timeline),
        section_narratives=section_narratives,
    )
    validate_fsd(fsd)
    return fsd


def load_fsd(template_key: str) -> FieldSchemaDocument:
    path = _SCHEMAS_DIR / f"{template_key}.json"
    if not path.is_file():
        raise NotFoundError(f"No Field Schema Document for template '{template_key}'.")
    with open(path, encoding="utf-8") as fh:
        return parse_fsd_dict(json.load(fh))


def default_fields_from_fsd(fsd: FieldSchemaDocument) -> dict:
    fields = {}
    for field_def in fsd.all_fields():
        if field_def.type == "repeatable_group":
            fields[field_def.id] = []
        elif field_def.default is not None:
            fields[field_def.id] = field_def.default
        elif field_def.type == "multi_select":
            fields[field_def.id] = []
        elif field_def.type in ("yes_no", "radio", "dropdown", "text", "long_text"):
            fields[field_def.id] = ""
        else:
            fields[field_def.id] = None
    return fields
