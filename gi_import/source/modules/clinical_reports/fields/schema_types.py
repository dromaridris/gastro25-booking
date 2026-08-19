"""Field Schema Document types — Sprint 3D."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Condition:
    """Declarative visibility / requirement condition."""

    when: str = "field"
    field_id: str | None = None
    operator: str = "equals"
    value: Any = None
    conditions: list["Condition"] = field(default_factory=list)


@dataclass
class NarrativeBinding:
    section: str | None = None
    mode: str = "sentence"
    template: str | None = None
    empty_text: str | None = None
    item_template: str | None = None
    children: list["NarrativeBinding"] = field(default_factory=list)
    field_id: str | None = None
    label: str | None = None


@dataclass
class QiMapping:
    metric_key: str
    operator: str = "equals"
    value: Any = None


@dataclass
class FieldDef:
    id: str
    label: str
    type: str
    required: bool | None = False
    default: Any = None
    visibility: Condition | None = None
    printable: bool = True
    research_flag: bool = False
    qi_flag: bool = False
    qi_mapping: QiMapping | None = None
    unit: str | None = None
    vocabulary_source: str | None = None
    help_text: str | None = None
    workflow_phases: list[str] = field(default_factory=list)
    narrative_binding: NarrativeBinding | None = None
    deprecated: bool = False
    inactive: bool = False
    fields: list["FieldDef"] = field(default_factory=list)
    min_rows: int = 0
    max_rows: int | None = None
    reorderable: bool = True
    sort_order: int = 0


@dataclass
class SectionDef:
    id: str
    label: str
    workflow_phase: str | None = None
    fields: list[FieldDef] = field(default_factory=list)
    sort_order: int = 0


@dataclass
class TimelineEventDef:
    key: str
    label: str
    required: bool = False


@dataclass
class ComponentDefs:
    timeline: list[TimelineEventDef] = field(default_factory=list)


@dataclass
class SectionNarrativeAggregate:
    """Top-level narrative assembly for a 3A section key."""

    section: str
    mode: str = "section_aggregate"
    intro: str | None = None
    bindings: list[NarrativeBinding] = field(default_factory=list)


@dataclass
class FieldSchemaDocument:
    schema_version: str
    template_key: str
    sections: list[SectionDef] = field(default_factory=list)
    components: ComponentDefs = field(default_factory=ComponentDefs)
    section_narratives: list[SectionNarrativeAggregate] = field(default_factory=list)

    def all_fields(self) -> list[FieldDef]:
        out: list[FieldDef] = []
        for section in self.sections:
            out.extend(_flatten_fields(section.fields))
        return out

    def field_by_id(self, field_id: str) -> FieldDef | None:
        for f in self.all_fields():
            if f.id == field_id:
                return f
        return None

    def mandatory_for_phase(self, workflow_phase: str) -> list[str]:
        ids = []
        for f in self.all_fields():
            if f.inactive or f.deprecated:
                continue
            if f.required and workflow_phase in (f.workflow_phases or []):
                ids.append(f.id)
        return ids


def _flatten_fields(fields: list[FieldDef]) -> list[FieldDef]:
    out: list[FieldDef] = []
    for f in fields:
        out.append(f)
        if f.type == "repeatable_group" and f.fields:
            out.extend(f.fields)
    return out
