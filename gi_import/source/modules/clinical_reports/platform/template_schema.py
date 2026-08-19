"""
Unified template schema loader — Sprint 3E.

Loads a single Field Schema Document JSON file and exposes all template sections
(fields, workflow, validation, quick_fill, narrative, qi, timeline) for platform
engines and template bundles. Does not modify frozen Sprint 3D field runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from app.modules.clinical_reports.fields.loader import default_fields_from_fsd, parse_fsd_dict
from app.modules.clinical_reports.fields.payload import StructuredPayload, is_field_present
from app.modules.clinical_reports.platform.bundle_types import TemplateBundle

_SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


def load_raw_template_schema(template_key: str) -> dict:
    path = _SCHEMAS_DIR / f"{template_key}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No template schema for '{template_key}'.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def compile_validation_rule(spec: dict, template_key: str) -> Callable[[dict], bool]:
    """Compile a declarative validation rule spec into a payload check function."""
    rule_type = spec.get("type")
    if rule_type == "field_present":
        field_id = spec["field_id"]

        def check(payload: dict) -> bool:
            return is_field_present(
                StructuredPayload(payload, template_key=template_key).get_field(field_id)
            )

        return check

    if rule_type == "field_nonempty":
        field_id = spec["field_id"]

        def check(payload: dict) -> bool:
            value = StructuredPayload(payload, template_key=template_key).get_field(field_id)
            return isinstance(value, str) and bool(value.strip())

        return check

    if rule_type == "list_nonempty":
        field_id = spec["field_id"]

        def check(payload: dict) -> bool:
            value = StructuredPayload(payload, template_key=template_key).get_field(field_id)
            return isinstance(value, list) and len(value) > 0

        return check

    if rule_type == "field_in":
        field_id = spec["field_id"]
        allowed = set(spec.get("values") or [])

        def check(payload: dict) -> bool:
            value = StructuredPayload(payload, template_key=template_key).get_field(field_id)
            return value in allowed

        return check

    if rule_type == "when_field_equals":
        field_id = spec["field_id"]
        expected = spec.get("value")
        then_spec = spec.get("then")
        then_check = (
            compile_validation_rule(then_spec, template_key) if then_spec else lambda _p: True
        )

        def check(payload: dict) -> bool:
            sp = StructuredPayload(payload, template_key=template_key)
            if sp.get_field(field_id) != expected:
                return True
            return then_check(payload)

        return check

    if rule_type == "always":
        return lambda _payload: bool(spec.get("pass", True))

    raise ValueError(f"Unknown validation rule type: {rule_type!r}")


def compile_validation_rules(rules_spec: list[dict], template_key: str) -> list[dict]:
    compiled = []
    for rule in rules_spec:
        compiled.append(
            {
                "id": rule["id"],
                "severity": rule["severity"],
                "message": rule["message"],
                "check": compile_validation_rule(rule["rule"], template_key),
            }
        )
    return compiled


def build_bundle_from_schema(template_key: str) -> TemplateBundle:
    """Assemble a TemplateBundle from all sections of a unified template schema."""
    raw = load_raw_template_schema(template_key)
    fsd = parse_fsd_dict(raw)

    workflow = raw.get("workflow") or {}
    workflow_states = workflow.get("states") or []
    transitions = workflow.get("transitions") or {}

    validation_rules = compile_validation_rules(raw.get("validation") or [], template_key)
    quick_fill_profiles = raw.get("quick_fill") or {}

    qi_indicators = []
    for item in raw.get("qi") or []:
        metric_key = item["metric_key"]
        qi_indicators.append(
            {
                "key": metric_key,
                "label": item.get("label", metric_key),
            }
        )

    timeline_event_defs = [ev.key for ev in fsd.components.timeline]

    default_v2 = {
        "payload_version": "2",
        "fields": default_fields_from_fsd(fsd),
        "components": {"timeline": [], "images": [], "drawings": []},
        "meta": {"validation_acknowledgments": [], "manual_overrides": {}},
    }

    return TemplateBundle(
        template_key=template_key,
        label=raw.get("label") or template_key,
        workflow_states=workflow_states,
        transitions=transitions,
        mandatory_fields={},
        validation_rules=validation_rules,
        timeline_event_defs=timeline_event_defs,
        qi_indicators=qi_indicators,
        quick_fill_profiles=quick_fill_profiles,
        narrative_sections={},
        default_payload=default_v2,
        field_schema=fsd,
    )


def qi_labels_from_schema(template_key: str) -> dict[str, str]:
    """Return metric_key -> display label from the unified schema qi section."""
    raw = load_raw_template_schema(template_key)
    return {item["metric_key"]: item.get("label", item["metric_key"]) for item in raw.get("qi") or []}
