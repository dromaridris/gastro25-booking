"""Legacy phase key ↔ stable field-id mapping derived from FSD sections."""

from app.modules.clinical_reports.fields.schema_types import FieldSchemaDocument

_LEGACY_MAP_CACHE: dict[str, dict[tuple[str, str], str]] = {}


def legacy_field_key(field_id: str) -> str:
    """Short form field name used in transitional UI POST/bindings."""
    return field_id.rsplit(".", 1)[-1]


def build_legacy_phase_field_map(fsd: FieldSchemaDocument) -> dict[tuple[str, str], str]:
    """Map (section_id, legacy_key) → stable field id from a Field Schema Document."""
    mapping: dict[tuple[str, str], str] = {}
    for section in fsd.sections:
        for field_def in section.fields:
            mapping[(section.id, legacy_field_key(field_def.id))] = field_def.id
    return mapping


def get_legacy_phase_field_map(template_key: str) -> dict[tuple[str, str], str]:
    if template_key not in _LEGACY_MAP_CACHE:
        from app.modules.clinical_reports.fields.registry import get_fsd

        _LEGACY_MAP_CACHE[template_key] = build_legacy_phase_field_map(get_fsd(template_key))
    return _LEGACY_MAP_CACHE[template_key]
