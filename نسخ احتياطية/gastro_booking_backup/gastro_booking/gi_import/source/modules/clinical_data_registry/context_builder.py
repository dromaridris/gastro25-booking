"""Build Decision Support assessment context from CDR reads."""

from __future__ import annotations

from app.modules.clinical_data_registry.canonical_codes import CANONICAL_REGISTRY
from app.modules.clinical_data_registry.constants import SOURCE_TYPE_LAB_RESULT
from app.modules.clinical_data_registry.service import get_clinical_data_registry
from app.modules.decision_support.context import AssessmentContext
from app.modules.patients.models import Patient


def lab_values_for_patient(patient_id: int | None) -> dict[str, str | float]:
    """
    Populate CDS lab_values using canonical codes.

    Keys use legacy lab test codes (source_key) for compatibility with KL score
    definitions while values are resolved through CDR.
    """
    if not patient_id:
        return {}
    patient = Patient.query.get(patient_id)
    if patient is None:
        return {}

    registry = get_clinical_data_registry()
    values: dict[str, str | float] = {}
    for definition in CANONICAL_REGISTRY.values():
        if definition.source_type != SOURCE_TYPE_LAB_RESULT:
            continue
        ref = registry.resolve_latest(patient, canonical_code=definition.code)
        if ref is None:
            continue
        key = ref.source_key
        if ref.value_numeric is not None:
            values[key] = ref.value_numeric
        elif ref.value_text is not None:
            values[key] = ref.value_text
    return values


def enrich_assessment_context(context: AssessmentContext) -> AssessmentContext:
    """Merge CDR-resolved lab values into an existing assessment context."""
    if not context.patient_id:
        return context
    resolved = lab_values_for_patient(context.patient_id)
    merged = dict(resolved)
    merged.update(context.lab_values or {})
    context.lab_values = merged
    return context
