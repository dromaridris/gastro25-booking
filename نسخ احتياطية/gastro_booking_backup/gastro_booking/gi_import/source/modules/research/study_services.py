"""Research study registry services — Sprint 6C."""

from __future__ import annotations

import json

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.patients.models import Patient
from app.modules.research import services as legacy_research_services
from app.modules.research.cohort_engine import evaluate_criteria, find_eligible_patients
from app.modules.research.data_quality import assess_case_quality, refresh_case_completeness
from app.modules.research.export_engine import (
    build_study_dataset,
    create_snapshot,
    export_csv,
    export_xlsx,
    load_snapshot_data,
)
from app.modules.research.models import DiseaseRegistryDefinition
from app.modules.research.search_services import search_cases
from app.modules.research.study_constants import (
    ASSIGNMENT_PI,
    CASE_STATUS_ENROLLED,
    CASE_STATUS_EXCLUDED,
    CASE_STATUS_WITHDRAWN,
    EXPORT_FORMAT_CSV,
    EXPORT_FORMAT_XLSX,
    LOG_ACTION_ENROLLED,
    LOG_ACTION_EXCLUDED,
    LOG_ACTION_SCREENED,
    LOG_ACTION_WITHDRAWN,
    SCREENING_ELIGIBLE,
    SCREENING_INELIGIBLE,
    STUDY_STATUS_ARCHIVED,
    STUDY_STATUS_DRAFT,
    STUDY_STATUS_RECRUITING,
)
from app.modules.research.study_models import (
    EnrollmentLogEntry,
    ResearchCase,
    ResearchExportSnapshot,
    ResearchStudy,
    ScreeningLogEntry,
    StudyMemberAssignment,
)


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def _require_study_manage(user) -> None:
    _require(user, "research:study_manage")


def _require_study_view(user) -> None:
    _require(user, "research:view")


def _require_study_edit(user) -> None:
    _require(user, "research:edit")


def _require_export(user) -> None:
    _require(user, "research:export")


def _get_study(study_code: str) -> ResearchStudy:
    study = ResearchStudy.query.filter_by(study_code=study_code, is_archived=False).first()
    if study is None:
        raise NotFoundError(f"Study '{study_code}' not found.")
    return study


def _log_enrollment(study_id: int, patient_id: int, action: str, user, case_id: int | None = None, details: dict | None = None):
    db.session.add(
        EnrollmentLogEntry(
            study_id=study_id,
            case_id=case_id,
            patient_id=patient_id,
            action=action,
            details_json=json.dumps(details or {}),
            user_id=user.id,
            department_id=getattr(user, "department_id", 1) or 1,
            created_by_id=user.id,
        )
    )


def _ensure_registry(registry_code: str) -> None:
    legacy_research_services.ensure_catalogue_seeded()
    if DiseaseRegistryDefinition.query.filter_by(code=registry_code, is_archived=False).first() is None:
        raise ValidationError(f"Unknown variable registry '{registry_code}'.")


def _user_can_manage_study(user, study: ResearchStudy) -> bool:
    if permission_engine.check(user, "research:study_manage"):
        return True
    if permission_engine.check(user, "research:study_review"):
        return StudyMemberAssignment.query.filter_by(
            study_id=study.id, user_id=user.id, is_archived=False
        ).first() is not None
    return False


# ---------------------------------------------------------------------------
# Study CRUD
# ---------------------------------------------------------------------------


def create_study(
    acting_user,
    *,
    study_code: str,
    title: str,
    registry_code: str,
    description: str | None = None,
    principal_investigator_id: int | None = None,
    start_date=None,
    end_date=None,
    ethics_approval_number: str | None = None,
    inclusion_criteria: list | None = None,
    exclusion_criteria: list | None = None,
    auto_enroll_enabled: bool = False,
) -> ResearchStudy:
    _require_study_manage(acting_user)
    _ensure_registry(registry_code)
    code = study_code.strip()
    if ResearchStudy.query.filter_by(study_code=code, is_archived=False).first():
        raise ValidationError(f"Study code '{code}' already exists.")

    study = ResearchStudy(
        study_code=code,
        title=title.strip(),
        description=description,
        registry_code=registry_code,
        principal_investigator_id=principal_investigator_id or acting_user.id,
        status=STUDY_STATUS_DRAFT,
        start_date=start_date,
        end_date=end_date,
        ethics_approval_number=ethics_approval_number,
        inclusion_criteria_json=json.dumps(inclusion_criteria or []),
        exclusion_criteria_json=json.dumps(exclusion_criteria or []),
        auto_enroll_enabled=auto_enroll_enabled,
        version=1,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
        updated_by_id=acting_user.id,
    )
    db.session.add(study)
    db.session.flush()
    db.session.add(
        StudyMemberAssignment(
            study_id=study.id,
            user_id=study.principal_investigator_id,
            assignment_role=ASSIGNMENT_PI,
            department_id=study.department_id,
            created_by_id=acting_user.id,
        )
    )
    db.session.commit()
    audit_engine.log("research.study_created", user=acting_user, target_type="research_study", target_id=study.id, details={"study_code": code})
    return study


def update_study(acting_user, study_code: str, **fields) -> ResearchStudy:
    _require_study_manage(acting_user)
    study = _get_study(study_code)
    mutable = {
        "title", "description", "status", "start_date", "end_date",
        "ethics_approval_number", "principal_investigator_id", "auto_enroll_enabled",
    }
    changed = False
    for key, value in fields.items():
        if key == "inclusion_criteria":
            study.inclusion_criteria_json = json.dumps(value or [])
            changed = True
        elif key == "exclusion_criteria":
            study.exclusion_criteria_json = json.dumps(value or [])
            changed = True
        elif key in mutable:
            setattr(study, key, value)
            changed = True
    if changed:
        study.version += 1
        study.updated_by_id = acting_user.id
        db.session.commit()
    return study


def archive_study(acting_user, study_code: str) -> ResearchStudy:
    _require_study_manage(acting_user)
    study = _get_study(study_code)
    study.status = STUDY_STATUS_ARCHIVED
    study.archive(acting_user.id, reason="Study archived")
    db.session.commit()
    return study


def list_studies(acting_user) -> list[ResearchStudy]:
    _require_study_view(acting_user)
    return ResearchStudy.query.filter_by(is_archived=False).order_by(ResearchStudy.created_at.desc()).all()


def get_study(acting_user, study_code: str) -> ResearchStudy:
    _require_study_view(acting_user)
    return _get_study(study_code)


def assign_member(acting_user, study_code: str, user_id: int, assignment_role: str) -> StudyMemberAssignment:
    _require_study_manage(acting_user)
    study = _get_study(study_code)
    row = StudyMemberAssignment(
        study_id=study.id,
        user_id=user_id,
        assignment_role=assignment_role,
        department_id=study.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(row)
    db.session.commit()
    return row


# ---------------------------------------------------------------------------
# Screening & enrolment
# ---------------------------------------------------------------------------


def screen_patient(acting_user, study_code: str, patient_id: int) -> ScreeningLogEntry:
    _require_study_edit(acting_user)
    study = _get_study(study_code)
    patient = Patient.query.filter_by(id=patient_id, is_archived=False).first()
    if patient is None:
        raise NotFoundError("Patient not found.")

    eligible, reason = evaluate_criteria(
        patient, study.inclusion_criteria(), study.exclusion_criteria(), study.registry_code
    )
    outcome = SCREENING_ELIGIBLE if eligible else SCREENING_INELIGIBLE
    entry = ScreeningLogEntry(
        study_id=study.id,
        patient_id=patient_id,
        outcome=outcome,
        reason=reason,
        screened_by_id=acting_user.id,
        department_id=study.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(entry)
    _log_enrollment(study.id, patient_id, LOG_ACTION_SCREENED, acting_user, details={"outcome": outcome, "reason": reason})
    db.session.commit()
    return entry


def enroll_case(
    acting_user,
    study_code: str,
    patient_id: int,
    *,
    encounter_id: int | None = None,
    procedure_id: int | None = None,
    skip_screening: bool = False,
) -> ResearchCase:
    _require_study_edit(acting_user)
    study = _get_study(study_code)
    patient = Patient.query.filter_by(id=patient_id, is_archived=False).first()
    if patient is None:
        raise NotFoundError("Patient not found.")

    existing = ResearchCase.query.filter_by(study_id=study.id, patient_id=patient_id, is_archived=False).first()
    if existing and existing.case_status not in {CASE_STATUS_WITHDRAWN, CASE_STATUS_EXCLUDED}:
        raise ValidationError("Duplicate enrolment: patient already enrolled in this study.")

    if not skip_screening:
        eligible, reason = evaluate_criteria(
            patient, study.inclusion_criteria(), study.exclusion_criteria(), study.registry_code
        )
        if not eligible:
            raise ValidationError(reason or "Patient does not meet study criteria.")

    enrollment = legacy_research_services.enroll_patient(
        acting_user, study.registry_code, patient_id, index_encounter_id=encounter_id
    )

    if existing:
        case = existing
        case.case_status = CASE_STATUS_ENROLLED
        case.encounter_id = encounter_id
        case.procedure_id = procedure_id
        case.registry_enrollment_id = enrollment.id
        case.enrolled_at = utcnow()
        case.enrolled_by_id = acting_user.id
    else:
        case = ResearchCase(
            study_id=study.id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            procedure_id=procedure_id,
            registry_enrollment_id=enrollment.id,
            case_status=CASE_STATUS_ENROLLED,
            enrolled_by_id=acting_user.id,
            department_id=patient.department_id,
            created_by_id=acting_user.id,
        )
        db.session.add(case)

    refresh_case_completeness(case)
    db.session.flush()
    _log_enrollment(study.id, patient_id, LOG_ACTION_ENROLLED, acting_user, case_id=case.id)
    db.session.commit()
    audit_engine.log("research.case_enrolled", user=acting_user, target_type="research_case", target_id=case.id, details={"study_code": study_code})
    from app.modules.workforce.portfolio_events import on_research_enrolled

    on_research_enrolled(case, acting_user)
    return case


def auto_enroll_candidates(acting_user, study_code: str, candidate_patient_ids: list[int]) -> list[ResearchCase]:
    _require_study_edit(acting_user)
    study = _get_study(study_code)
    eligible_ids = find_eligible_patients(
        candidate_patient_ids,
        study.inclusion_criteria(),
        study.exclusion_criteria(),
        study.registry_code,
    )
    enrolled = []
    for patient_id in eligible_ids:
        try:
            enrolled.append(enroll_case(acting_user, study_code, patient_id, skip_screening=True))
        except ValidationError:
            continue
    return enrolled


def withdraw_case(acting_user, case_id: int) -> ResearchCase:
    _require_study_edit(acting_user)
    case = ResearchCase.query.filter_by(id=case_id, is_archived=False).first()
    if case is None:
        raise NotFoundError("Case not found.")
    case.case_status = CASE_STATUS_WITHDRAWN
    _log_enrollment(case.study_id, case.patient_id, LOG_ACTION_WITHDRAWN, acting_user, case_id=case.id)
    db.session.commit()
    return case


def assign_reviewer(acting_user, case_id: int, reviewer_id: int) -> ResearchCase:
    if not (permission_engine.check(acting_user, "research:study_manage") or permission_engine.check(acting_user, "research:study_review")):
        raise PermissionDeniedError("User cannot assign reviewers.")
    case = ResearchCase.query.filter_by(id=case_id, is_archived=False).first()
    if case is None:
        raise NotFoundError("Case not found.")
    case.reviewer_id = reviewer_id
    db.session.commit()
    return case


def list_cases(acting_user, study_code: str) -> list[ResearchCase]:
    _require_study_view(acting_user)
    study = _get_study(study_code)
    return (
        ResearchCase.query.filter_by(study_id=study.id, is_archived=False)
        .order_by(ResearchCase.enrolled_at.desc())
        .all()
    )


def case_quality_report(acting_user, case_id: int) -> dict:
    _require_study_view(acting_user)
    case = ResearchCase.query.filter_by(id=case_id, is_archived=False).first()
    if case is None:
        raise NotFoundError("Case not found.")
    return assess_case_quality(case)


# ---------------------------------------------------------------------------
# Export & snapshots
# ---------------------------------------------------------------------------


def export_study(
    acting_user,
    study_code: str,
    *,
    export_format: str = EXPORT_FORMAT_CSV,
    variable_codes: list[str] | None = None,
    filters: dict | None = None,
    freeze_snapshot: bool = False,
    snapshot_name: str | None = None,
):
    _require_export(acting_user)
    study = _get_study(study_code)
    columns, rows = build_study_dataset(study, variable_codes=variable_codes, filters=filters)
    if freeze_snapshot:
        create_snapshot(
            acting_user,
            study,
            snapshot_name=snapshot_name or f"{study_code}_{utcnow().date().isoformat()}",
            export_format=export_format,
            variable_codes=variable_codes,
            filters=filters,
        )
    audit_engine.log("research.study_exported", user=acting_user, target_type="research_study", target_id=study.id, details={"study_code": study_code, "rows": len(rows)})
    if export_format == EXPORT_FORMAT_XLSX:
        return EXPORT_FORMAT_XLSX, export_xlsx(columns, rows)
    return EXPORT_FORMAT_CSV, export_csv(columns, rows)


def get_snapshot(acting_user, snapshot_id: int) -> ResearchExportSnapshot:
    _require_study_view(acting_user)
    snap = ResearchExportSnapshot.query.filter_by(id=snapshot_id, is_archived=False).first()
    if snap is None:
        raise NotFoundError("Snapshot not found.")
    return snap


def export_from_snapshot(acting_user, snapshot_id: int):
    _require_export(acting_user)
    snap = get_snapshot(acting_user, snapshot_id)
    columns, rows = load_snapshot_data(snap)
    if snap.export_format == EXPORT_FORMAT_XLSX:
        return EXPORT_FORMAT_XLSX, export_xlsx(columns, rows)
    return EXPORT_FORMAT_CSV, export_csv(columns, rows)


def search_study_cases(acting_user, **filters):
    _require_study_view(acting_user)
    return search_cases(**filters)
