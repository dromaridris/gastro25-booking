"""Measurement unit registry and narrative formatting — Sprint 3D."""

UNIT_REGISTRY = {
    "mm": {"domain": "length", "display": "mm", "to_mm": 1.0},
    "cm": {"domain": "length", "display": "cm", "to_mm": 10.0},
    "Fr": {"domain": "gauge", "display": "Fr", "to_mm": None},
    "mL": {"domain": "volume", "display": "mL", "to_mm": None},
    "min": {"domain": "duration", "display": "min", "to_mm": None},
    "%": {"domain": "percentage", "display": "%", "to_mm": None},
}


def normalize_measurement(value, unit: str, target_unit: str = "mm") -> float | None:
    if value is None or unit not in UNIT_REGISTRY:
        return None
    spec = UNIT_REGISTRY[unit]
    if unit == target_unit:
        return float(value)
    if target_unit == "mm" and spec.get("to_mm"):
        return float(value) * spec["to_mm"]
    return None


def format_measurement(value, unit: str, style: str = "clinical") -> str:
    if value is None or value == "":
        return ""
    if style == "clinical" and unit:
        return f"{value} {UNIT_REGISTRY.get(unit, {}).get('display', unit)}"
    return str(value)


def format_field_value(field_type: str, value, unit: str | None = None) -> str:
    if value is None:
        return ""
    if field_type in ("measurement", "unit_aware_measurement"):
        u = unit or "mm"
        if isinstance(value, dict):
            return format_measurement(value.get("value"), value.get("unit") or u)
        return format_measurement(value, u)
    if isinstance(value, list):
        return ", ".join(str(v).replace("_", " ") for v in value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)
