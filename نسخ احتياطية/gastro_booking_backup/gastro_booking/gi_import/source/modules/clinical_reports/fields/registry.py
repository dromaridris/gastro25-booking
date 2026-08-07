"""Field Schema Document registry."""

from app.modules.clinical_reports.fields.loader import load_fsd
from app.modules.clinical_reports.fields.schema_types import FieldSchemaDocument
from app.modules.procedures.models import STRUCTURED_CLINICAL_REPORT_TEMPLATE_KEYS

_fsd_cache: dict[str, FieldSchemaDocument] = {}


def get_fsd(template_key: str) -> FieldSchemaDocument:
    if template_key not in _fsd_cache:
        _fsd_cache[template_key] = load_fsd(template_key)
    return _fsd_cache[template_key]


def has_fsd(template_key: str) -> bool:
    return template_key in STRUCTURED_CLINICAL_REPORT_TEMPLATE_KEYS


def clear_fsd_cache() -> None:
    _fsd_cache.clear()
