"""Lightweight JSON Schema subset validator (no external jsonschema dependency).

Supports: type, required, properties, enum, pattern, minimum, minLength,
items, additionalProperties (bool only).
"""

from __future__ import annotations

import re
from typing import Any


def validate_against_schema(instance: Any, schema: dict, *, path: str = "$") -> list[str]:
    errors: list[str] = []
    _walk(instance, schema, path, errors)
    return errors


def _walk(instance: Any, schema: dict, path: str, errors: list[str]) -> None:
    if not schema:
        return
    expected = schema.get("type")
    if expected:
        types = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(instance, t) for t in types):
            errors.append(f"{path}: expected type {expected}, got {type(instance).__name__}")
            return

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} not in enum")

    if "pattern" in schema and isinstance(instance, str):
        if not re.search(schema["pattern"], instance):
            errors.append(f"{path}: does not match pattern {schema['pattern']}")

    if "minLength" in schema and isinstance(instance, str):
        if len(instance) < int(schema["minLength"]):
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")

    if "minimum" in schema and isinstance(instance, (int, float)):
        if instance < schema["minimum"]:
            errors.append(f"{path}: below minimum {schema['minimum']}")

    if schema.get("type") == "object" or (isinstance(instance, dict) and "properties" in schema):
        if not isinstance(instance, dict):
            return
        for req in schema.get("required") or []:
            if req not in instance:
                errors.append(f"{path}: missing required property '{req}'")
        props = schema.get("properties") or {}
        for key, val in instance.items():
            if key in props:
                _walk(val, props[key], f"{path}.{key}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: additional property '{key}' not allowed")

    if schema.get("type") == "array" or (isinstance(instance, list) and "items" in schema):
        if not isinstance(instance, list):
            return
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(instance):
                _walk(item, item_schema, f"{path}[{i}]", errors)


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True
