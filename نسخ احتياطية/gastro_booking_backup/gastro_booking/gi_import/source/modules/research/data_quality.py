"""Research case data quality and completeness — Sprint 6C."""

from __future__ import annotations

from decimal import Decimal

from app.modules.research import variable_framework
from app.modules.research.catalogue_seed import REGISTRY_CONTEXT
from app.modules.research.constants import ORIGIN_MANUAL_ENTRY
from app.modules.research.models import ResearchVariableDefinition
from app.modules.research.study_constants import CASE_STATUS_EXCLUDED, CASE_STATUS_WITHDRAWN
from app.modules.research.study_models import ResearchCase
from app.modules.research.validation import validate_value_for_variable


def assess_case_quality(case: ResearchCase) -> dict:
    study = case.study
    if study is None and case.study_id:
        from app.modules.research.study_models import ResearchStudy

        study = ResearchStudy.query.filter_by(id=case.study_id, is_archived=False).first()
    if study is None:
        return {
            "case_id": case.id,
            "completeness_pct": 0.0,
            "missing_variables": [],
            "issues": [{"type": "error", "message": "Study not found for case."}],
            "duplicate_enrollment": False,
        }
    patient = case.patient
    variables = (
        ResearchVariableDefinition.query.filter_by(
            registry_code=study.registry_code,
            is_archived=False,
            is_active=True,
        )
        .order_by(ResearchVariableDefinition.sort_order)
        .all()
    )
    context = REGISTRY_CONTEXT.get(study.registry_code, {})
    issues: list[dict] = []
    missing: list[str] = []
    required_total = 0
    required_filled = 0

    for variable in variables:
        value = variable_framework.resolve_variable_value(
            patient,
            variable,
            enrollment_id=case.registry_enrollment_id,
            registry_context=context,
        )
        if variable.is_required:
            required_total += 1
            if value is None or value == "":
                missing.append(variable.code)
                issues.append({"type": "missing", "variable_code": variable.code, "message": f"Required variable {variable.name} is missing"})
            else:
                required_filled += 1

        if value is not None and value != "" and variable.value_origin == ORIGIN_MANUAL_ENTRY:
            try:
                validate_value_for_variable(variable, value)
            except Exception as exc:
                issues.append({"type": "validation_failure", "variable_code": variable.code, "message": str(exc)})

        if value is not None and value != "":
            rules = variable.validation_rules()
            num = None
            try:
                num = Decimal(str(value))
            except Exception:
                num = None
            if num is not None:
                if "min" in rules and num < Decimal(str(rules["min"])):
                    issues.append({"type": "out_of_range", "variable_code": variable.code, "message": f"{variable.name} below minimum"})
                if "max" in rules and num > Decimal(str(rules["max"])):
                    issues.append({"type": "out_of_range", "variable_code": variable.code, "message": f"{variable.name} above maximum"})

    completeness = Decimal("100") if required_total == 0 else Decimal(required_filled * 100 / required_total).quantize(Decimal("0.01"))
    duplicate = (
        ResearchCase.query.filter(
            ResearchCase.study_id == case.study_id,
            ResearchCase.patient_id == case.patient_id,
            ResearchCase.is_archived.is_(False),
            ResearchCase.id != case.id,
            ResearchCase.case_status.notin_([CASE_STATUS_WITHDRAWN, CASE_STATUS_EXCLUDED]),
        ).count()
        > 0
    )
    if duplicate:
        issues.append({"type": "duplicate_enrollment", "message": "Duplicate active enrolment for this patient in the study."})
    return {
        "case_id": case.id,
        "completeness_pct": float(completeness),
        "missing_variables": missing,
        "issues": issues,
        "duplicate_enrollment": duplicate,
    }


def refresh_case_completeness(case: ResearchCase) -> ResearchCase:
    report = assess_case_quality(case)
    case.completeness_pct = report["completeness_pct"]
    return case
