"""Cohort inclusion/exclusion evaluation via CDR and Research Variables Framework."""

from __future__ import annotations

from decimal import Decimal

from app.modules.clinical_data_registry.service import get_clinical_data_registry
from app.modules.patients.models import Patient
from app.modules.research import variable_framework
from app.modules.research.catalogue_seed import REGISTRY_CONTEXT
from app.modules.research.models import ResearchVariableDefinition


def _normalize(value) -> str:
    return str(value or "").strip().lower()


def _coerce_number(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _resolve_rule_value(patient: Patient, rule: dict, registry_code: str) -> str | None:
    if rule.get("type") == "cdr":
        registry = get_clinical_data_registry()
        ref = registry.resolve_latest(
            patient,
            canonical_code=rule.get("canonical_code"),
            source_type=rule.get("source_type"),
            source_key=rule.get("source_key"),
            registry_context=REGISTRY_CONTEXT.get(registry_code, {}),
        )
        return ref.display_value if ref else None

    variable_code = rule.get("variable_code")
    if variable_code:
        variable = ResearchVariableDefinition.query.filter_by(code=variable_code, is_archived=False).first()
        if variable:
            return variable_framework.resolve_variable_value(
                patient,
                variable,
                registry_context=REGISTRY_CONTEXT.get(registry_code, {}),
            )

    source_type = rule.get("source_type")
    source_key = rule.get("source_key")
    if source_type and source_key:
        return get_clinical_data_registry().resolve_display_value(
            patient,
            source_type=source_type,
            source_key=source_key,
            registry_context=REGISTRY_CONTEXT.get(registry_code, {}),
        )
    return None


def _rule_matches(patient: Patient, rule: dict, registry_code: str) -> bool:
    actual_raw = _resolve_rule_value(patient, rule, registry_code)
    operator = rule.get("operator", "exists")
    expected = rule.get("value")

    if operator == "exists":
        return actual_raw is not None and actual_raw != ""
    if operator == "eq":
        return _normalize(actual_raw) == _normalize(expected)
    if operator == "neq":
        return _normalize(actual_raw) != _normalize(expected)

    actual_num = _coerce_number(actual_raw)
    expected_num = _coerce_number(expected)
    if actual_num is None:
        return False
    if operator == "gte":
        return actual_num >= (expected_num or Decimal("0"))
    if operator == "lte":
        return actual_num <= (expected_num or Decimal("0"))
    if operator == "gt":
        return actual_num > (expected_num or Decimal("0"))
    if operator == "lt":
        return actual_num < (expected_num or Decimal("0"))
    return False


def evaluate_criteria(patient: Patient, inclusion: list, exclusion: list, registry_code: str) -> tuple[bool, str | None]:
    for rule in inclusion or []:
        if not _rule_matches(patient, rule, registry_code):
            return False, rule.get("reason") or f"Inclusion not met: {rule.get('label') or rule}"

    for rule in exclusion or []:
        if _rule_matches(patient, rule, registry_code):
            return False, rule.get("reason") or f"Exclusion met: {rule.get('label') or rule}"

    return True, None


def find_eligible_patients(patient_ids: list[int], inclusion: list, exclusion: list, registry_code: str) -> list[int]:
    eligible: list[int] = []
    for patient_id in patient_ids:
        patient = Patient.query.filter_by(id=patient_id, is_archived=False).first()
        if patient is None:
            continue
        ok, _ = evaluate_criteria(patient, inclusion, exclusion, registry_code)
        if ok:
            eligible.append(patient_id)
    return eligible
