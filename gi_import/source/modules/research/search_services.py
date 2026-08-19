"""Research study search — CDR and framework only."""

from __future__ import annotations

from app.modules.clinical_data_registry.service import get_clinical_data_registry
from app.modules.patients.models import Patient
from app.modules.research.catalogue_seed import REGISTRY_CONTEXT
from app.modules.research.models import ResearchVariableDefinition
from app.modules.research import variable_framework
from app.modules.research.study_models import ResearchCase, ResearchStudy


def search_cases(
    *,
    study_code: str | None = None,
    patient_id: int | None = None,
    case_status: str | None = None,
    diagnosis_source_key: str | None = None,
    lab_canonical_code: str | None = None,
    lab_operator: str = "exists",
    lab_value: str | None = None,
    date_from=None,
    date_to=None,
) -> list[ResearchCase]:
    query = ResearchCase.query.filter_by(is_archived=False)
    study = None
    if study_code:
        study = ResearchStudy.query.filter_by(study_code=study_code, is_archived=False).first()
        if study is None:
            return []
        query = query.filter_by(study_id=study.id)
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    if case_status:
        query = query.filter_by(case_status=case_status)
    if date_from:
        query = query.filter(ResearchCase.enrolled_at >= date_from)
    if date_to:
        query = query.filter(ResearchCase.enrolled_at <= date_to)

    cases = query.order_by(ResearchCase.enrolled_at.desc()).all()
    if not (diagnosis_source_key or lab_canonical_code):
        return cases

    registry = get_clinical_data_registry()
    filtered: list[ResearchCase] = []
    for case in cases:
        patient = case.patient
        study_obj = case.study
        if study_obj is None and case.study_id:
            study_obj = ResearchStudy.query.filter_by(id=case.study_id, is_archived=False).first()
        registry_code = study_obj.registry_code if study_obj else (study.registry_code if study else "")
        ctx = REGISTRY_CONTEXT.get(registry_code, {})

        if diagnosis_source_key:
            variable = ResearchVariableDefinition.query.filter_by(
                registry_code=registry_code,
                source_type="history_confirmed_diagnosis",
                is_archived=False,
            ).first()
            dx = None
            if variable:
                dx = variable_framework.resolve_variable_value(patient, variable, registry_context=ctx)
            if not dx or diagnosis_source_key.lower() not in str(dx).lower():
                continue

        if lab_canonical_code:
            ref = registry.resolve_latest(patient, canonical_code=lab_canonical_code)
            if lab_operator == "exists" and ref is None:
                continue
            if lab_operator == "lte" and ref and ref.value_numeric is not None and lab_value is not None:
                if float(ref.value_numeric) > float(lab_value):
                    continue
            if lab_operator == "gte" and ref and ref.value_numeric is not None and lab_value is not None:
                if float(ref.value_numeric) < float(lab_value):
                    continue

        filtered.append(case)
    return filtered
