"""Platform — Generic Reporting Workflow Engine."""

from app.core.exceptions import ValidationError
from app.modules.clinical_reports.platform.bundle_types import TemplateBundle
from app.modules.clinical_reports.platform.registry import load_bundle


def allowed_next_states(bundle: TemplateBundle, current_state: str) -> list[str]:
    return list(bundle.transitions.get(current_state, []))


def can_transition(bundle: TemplateBundle, from_state: str, to_state: str) -> bool:
    return to_state in allowed_next_states(bundle, from_state)


def validate_mandatory_fields(
    bundle: TemplateBundle, state: str, payload: dict, template_key: str | None = None
) -> list[str]:
    """Return list of missing field paths for the given workflow state."""
    if bundle.field_schema is not None:
        from app.modules.clinical_reports.fields.payload import StructuredPayload
        from app.modules.clinical_reports.fields.presence import missing_mandatory_fields

        sp = StructuredPayload(
            payload,
            template_key=template_key or bundle.field_schema.template_key,
        )
        return missing_mandatory_fields(bundle.field_schema, sp, state)

    required = bundle.mandatory_fields.get(state, [])
    missing = []
    for field_path in required:
        if not _field_present(payload, field_path):
            missing.append(field_path)
    return missing


def validate_transition(
    template_key: str, from_state: str, to_state: str, payload: dict
) -> None:
    bundle = load_bundle(template_key)
    if not can_transition(bundle, from_state, to_state):
        raise ValidationError(
            f"Transition from '{from_state}' to '{to_state}' is not allowed for template '{template_key}'."
        )
    missing = validate_mandatory_fields(bundle, from_state, payload, template_key=template_key)
    if missing:
        raise ValidationError(
            "Cannot leave current phase — required fields missing: "
            + ", ".join(missing)
        )


def _field_present(payload: dict, field_path: str) -> bool:
    parts = field_path.split(".")
    node = payload
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    if node is None:
        return False
    if isinstance(node, str):
        return bool(node.strip())
    if isinstance(node, list):
        return len(node) > 0
    if isinstance(node, dict):
        return len(node) > 0
    return True
