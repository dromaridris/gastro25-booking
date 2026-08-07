"""Research variable value validation — Sprint 6B."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.core.exceptions import ValidationError
from app.modules.research.constants import (
    TYPE_BOOLEAN,
    TYPE_CALCULATED,
    TYPE_DATE,
    TYPE_DATETIME,
    TYPE_DECIMAL,
    TYPE_INTEGER,
    TYPE_MULTIPLE_CHOICE,
    TYPE_SINGLE_CHOICE,
    TYPE_TEXT,
)
from app.modules.research.models import ResearchVariableDefinition


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"yes", "true", "1", "y"}:
        return True
    if text in {"no", "false", "0", "n"}:
        return False
    raise ValidationError(f"Invalid boolean value: {value}")


def _parse_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value).strip())


def _parse_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def validate_variable_definition_payload(
    *,
    code: str,
    stable_id: str,
    name: str,
    data_type: str,
    source_type: str,
    source_key: str,
    value_origin: str,
    allowed_values: list | None = None,
) -> None:
    if not (code or "").strip():
        raise ValidationError("Variable code is required.")
    if not (stable_id or "").strip():
        raise ValidationError("Stable ID is required.")
    if not (name or "").strip():
        raise ValidationError("Variable name is required.")
    if data_type not in {
        TYPE_BOOLEAN,
        TYPE_INTEGER,
        TYPE_DECIMAL,
        TYPE_TEXT,
        TYPE_DATE,
        TYPE_DATETIME,
        TYPE_SINGLE_CHOICE,
        TYPE_MULTIPLE_CHOICE,
        TYPE_CALCULATED,
    }:
        raise ValidationError(f"Unsupported data type: {data_type}")
    if not (source_type or "").strip():
        raise ValidationError("Source type is required for module attachment.")
    if value_origin == "clinical_reference" and not (source_key or "").strip():
        raise ValidationError("Clinical reference variables require a source key.")
    if data_type in {TYPE_SINGLE_CHOICE, TYPE_MULTIPLE_CHOICE} and not allowed_values:
        raise ValidationError("Choice variables require allowed values.")


def validate_value_for_variable(variable: ResearchVariableDefinition, raw_value) -> dict:
    """
    Validate and normalise a value against variable metadata.

    Returns normalised dict: value_text, value_numeric, value_json (as applicable).
    """
    if variable.data_type == TYPE_CALCULATED:
        raise ValidationError("Calculated variables cannot accept manual entry yet.")

    if raw_value is None or raw_value == "":
        if variable.is_required:
            raise ValidationError(f"{variable.name} is required.")
        return {"value_text": None, "value_numeric": None, "value_json": None}

    rules = variable.validation_rules()
    allowed = variable.allowed_values()

    if variable.data_type == TYPE_BOOLEAN:
        normalised = _parse_bool(raw_value)
        return {"value_text": "yes" if normalised else "no", "value_numeric": None, "value_json": None}

    if variable.data_type == TYPE_INTEGER:
        try:
            num = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{variable.name} must be an integer.") from exc
        if "min" in rules and num < rules["min"]:
            raise ValidationError(f"{variable.name} must be >= {rules['min']}.")
        if "max" in rules and num > rules["max"]:
            raise ValidationError(f"{variable.name} must be <= {rules['max']}.")
        return {"value_text": str(num), "value_numeric": Decimal(num), "value_json": None}

    if variable.data_type == TYPE_DECIMAL:
        try:
            num = Decimal(str(raw_value))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"{variable.name} must be a number.") from exc
        if "min" in rules and num < Decimal(str(rules["min"])):
            raise ValidationError(f"{variable.name} must be >= {rules['min']}.")
        if "max" in rules and num > Decimal(str(rules["max"])):
            raise ValidationError(f"{variable.name} must be <= {rules['max']}.")
        return {"value_text": str(num), "value_numeric": num, "value_json": None}

    if variable.data_type == TYPE_DATE:
        parsed = _parse_date(raw_value)
        return {"value_text": parsed.isoformat(), "value_numeric": None, "value_json": None}

    if variable.data_type == TYPE_DATETIME:
        parsed = _parse_datetime(raw_value)
        return {"value_text": parsed.isoformat(), "value_numeric": None, "value_json": None}

    if variable.data_type == TYPE_SINGLE_CHOICE:
        text = str(raw_value).strip()
        if allowed and text not in allowed:
            raise ValidationError(f"{variable.name} must be one of: {', '.join(allowed)}.")
        return {"value_text": text, "value_numeric": None, "value_json": None}

    if variable.data_type == TYPE_MULTIPLE_CHOICE:
        if isinstance(raw_value, str):
            import json

            try:
                items = json.loads(raw_value)
            except json.JSONDecodeError:
                items = [v.strip() for v in raw_value.split(",") if v.strip()]
        elif isinstance(raw_value, list):
            items = raw_value
        else:
            raise ValidationError(f"{variable.name} must be a list of choices.")
        for item in items:
            if allowed and item not in allowed:
                raise ValidationError(f"Invalid choice '{item}' for {variable.name}.")
        import json

        return {"value_text": None, "value_numeric": None, "value_json": json.dumps(items)}

    text = str(raw_value)
    if "max_length" in rules and len(text) > int(rules["max_length"]):
        raise ValidationError(f"{variable.name} exceeds maximum length.")
    if "pattern" in rules:
        import re

        if not re.search(rules["pattern"], text):
            raise ValidationError(f"{variable.name} does not match required pattern.")
    return {"value_text": text, "value_numeric": None, "value_json": None}
