"""Read-only research value extraction via Clinical Data Registry."""

from __future__ import annotations

from app.modules.clinical_data_registry.service import get_clinical_data_registry
from app.modules.patients.models import Patient


def extract_variable_value(patient: Patient, source_type: str, source_key: str, registry_context: dict = None):
    """
    Resolve a research variable through CDR.

    Research must never query owning module tables directly.
    """
    registry = get_clinical_data_registry()
    return registry.resolve_display_value(
        patient,
        source_type=source_type,
        source_key=source_key,
        registry_context=registry_context,
    )
