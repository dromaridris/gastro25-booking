"""Structured payload contract — v1 legacy nested ↔ v2 field-id document."""

import copy
import uuid

from app.modules.clinical_reports.fields.legacy_map import get_legacy_phase_field_map

PAYLOAD_VERSION_V2 = "2"

_DEFAULT_TEMPLATE_KEY = "ercp"


def normalize_payload(raw: dict | None, template_key: str = _DEFAULT_TEMPLATE_KEY) -> dict:
    """Ensure v2 payload shape; migrate legacy 3C nested dict on read."""
    if raw is None:
        raw = {}
    if _is_v2(raw):
        return copy.deepcopy(raw)
    return _migrate_v1_to_v2(raw, template_key)


def _is_v2(raw: dict) -> bool:
    return raw.get("payload_version") == PAYLOAD_VERSION_V2 and "fields" in raw


def _migrate_v1_to_v2(raw: dict, template_key: str) -> dict:
    legacy_map = get_legacy_phase_field_map(template_key)
    fields: dict = {}
    for (phase, key), field_id in legacy_map.items():
        phase_data = raw.get(phase)
        if isinstance(phase_data, dict) and key in phase_data:
            value = copy.deepcopy(phase_data[key])
            field_def_id = field_id
            if _is_repeatable_group_field(template_key, field_def_id) and isinstance(value, list):
                value = [_ensure_row_id(row) for row in value]
            fields[field_def_id] = value
    meta = {
        "validation_acknowledgments": raw.get("validation_acknowledgments") or [],
        "manual_overrides": {},
    }
    if raw.get("impression_edited_manually"):
        meta["manual_overrides"]["impression"] = True
    return {
        "payload_version": PAYLOAD_VERSION_V2,
        "fields": fields,
        "components": raw.get("components") or {"timeline": [], "images": [], "drawings": []},
        "meta": meta,
    }


def _is_repeatable_group_field(template_key: str, field_id: str) -> bool:
    from app.modules.clinical_reports.fields.registry import get_fsd

    field_def = get_fsd(template_key).field_by_id(field_id)
    return field_def is not None and field_def.type == "repeatable_group"


def _ensure_row_id(row: dict) -> dict:
    if not isinstance(row, dict):
        return row
    out = copy.deepcopy(row)
    if "_row_id" not in out:
        out["_row_id"] = str(uuid.uuid4())
    return out


class StructuredPayload:
    """Field-id keyed payload with legacy phase access for transitional UI."""

    def __init__(self, raw: dict | None = None, template_key: str = _DEFAULT_TEMPLATE_KEY):
        self._template_key = template_key
        self._legacy_map = get_legacy_phase_field_map(template_key)
        self._data = normalize_payload(raw, template_key)

    @property
    def data(self) -> dict:
        return self._data

    def get_field(self, field_id: str):
        return self._data.get("fields", {}).get(field_id)

    def set_field(self, field_id: str, value) -> None:
        self._data.setdefault("fields", {})[field_id] = copy.deepcopy(value)

    def get_legacy_phase(self, phase: str) -> dict:
        out = {}
        for (p, key), field_id in self._legacy_map.items():
            if p == phase:
                out[key] = self.get_field(field_id)
        return out

    def update_legacy_phase(self, phase: str, phase_data: dict) -> None:
        for key, value in (phase_data or {}).items():
            field_id = self._legacy_map.get((phase, key))
            if field_id:
                if _is_repeatable_group_field(self._template_key, field_id) and isinstance(value, list):
                    value = [_ensure_row_id(row) for row in value]
                self.set_field(field_id, value)

    def legacy_dict(self) -> dict:
        """Nested phase dict for backward-compatible narrative/validation during transition."""
        result = {}
        for (phase, key), field_id in self._legacy_map.items():
            result.setdefault(phase, {})[key] = self.get_field(field_id)
        result["validation_acknowledgments"] = self.meta.get("validation_acknowledgments") or []
        return result

    @property
    def meta(self) -> dict:
        return self._data.setdefault("meta", {})

    @property
    def components(self) -> dict:
        return self._data.setdefault("components", {})

    def validation_acknowledgments(self) -> list:
        return list(self.meta.get("validation_acknowledgments") or [])

    def set_validation_acknowledgments(self, rule_ids: list[str]) -> None:
        self.meta["validation_acknowledgments"] = sorted(set(rule_ids))


def is_field_present(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, dict):
        return len(value) > 0
    return True
