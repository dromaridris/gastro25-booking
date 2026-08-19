"""Research Platform services — Sprint 5A-RES."""

import csv
import io

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.patients.models import Patient
from app.modules.research.catalogue_seed import REGISTRY_CONTEXT
from app.modules.research.catalogue_seed import seed_research_catalogue_if_empty
from app.modules.research.models import (
    ENROLLMENT_STATUS_ACTIVE,
    ENROLLMENT_STATUS_WITHDRAWN,
    DiseaseRegistryDefinition,
    RegistryEnrollment,
    ResearchVariableDefinition,
)
from app.modules.research import variable_framework


def _require(user, permission: str):
    permission_engine.require(user, permission)


def ensure_catalogue_seeded() -> int:
    created = seed_research_catalogue_if_empty()
    variable_framework.backfill_legacy_variable_metadata()
    return created


def list_registries(acting_user) -> list[DiseaseRegistryDefinition]:
    _require(acting_user, "research:view")
    ensure_catalogue_seeded()
    return (
        DiseaseRegistryDefinition.query.filter_by(is_archived=False, is_active=True)
        .order_by(DiseaseRegistryDefinition.sort_order)
        .all()
    )


def get_registry(acting_user, registry_code: str) -> DiseaseRegistryDefinition:
    _require(acting_user, "research:view")
    ensure_catalogue_seeded()
    reg = DiseaseRegistryDefinition.query.filter_by(code=registry_code, is_archived=False).first()
    if reg is None:
        raise NotFoundError(f"Registry '{registry_code}' not found.")
    return reg


def list_variables(acting_user, registry_code: str) -> list[ResearchVariableDefinition]:
    get_registry(acting_user, registry_code)
    return (
        ResearchVariableDefinition.query.filter_by(registry_code=registry_code, is_archived=False)
        .order_by(ResearchVariableDefinition.sort_order)
        .all()
    )


def list_enrollments(acting_user, registry_code: str) -> list[RegistryEnrollment]:
    get_registry(acting_user, registry_code)
    return (
        RegistryEnrollment.query.filter_by(
            registry_code=registry_code,
            status=ENROLLMENT_STATUS_ACTIVE,
            is_archived=False,
        )
        .order_by(RegistryEnrollment.enrolled_at.desc())
        .all()
    )


def enroll_patient(acting_user, registry_code: str, patient_id: int, index_encounter_id: int = None, notes: str = None):
    _require(acting_user, "research:edit")
    get_registry(acting_user, registry_code)
    patient = Patient.query.filter_by(id=patient_id, is_archived=False).first()
    if patient is None:
        raise NotFoundError("Patient not found.")

    existing = RegistryEnrollment.query.filter_by(
        registry_code=registry_code,
        patient_id=patient_id,
        is_archived=False,
    ).first()
    if existing and existing.status == ENROLLMENT_STATUS_ACTIVE:
        raise ValidationError("Patient is already enrolled in this registry.")

    if existing and existing.status == ENROLLMENT_STATUS_WITHDRAWN:
        existing.status = ENROLLMENT_STATUS_ACTIVE
        existing.enrolled_at = utcnow()
        existing.enrolled_by_id = acting_user.id
        existing.index_encounter_id = index_encounter_id
        existing.notes = notes
        db.session.commit()
        audit_engine.log(
            "research.enrollment_reactivated",
            user=acting_user,
            target_type="registry_enrollment",
            target_id=existing.id,
            details={"registry": registry_code, "patient_id": patient_id},
        )
        return existing

    enrollment = RegistryEnrollment(
        registry_code=registry_code,
        patient_id=patient_id,
        index_encounter_id=index_encounter_id,
        enrolled_by_id=acting_user.id,
        notes=notes,
        department_id=patient.department_id,
    )
    db.session.add(enrollment)
    db.session.commit()
    audit_engine.log(
        "research.enrollment_created",
        user=acting_user,
        target_type="registry_enrollment",
        target_id=enrollment.id,
        details={"registry": registry_code, "patient_id": patient_id},
    )
    return enrollment


def withdraw_enrollment(acting_user, enrollment_id: int):
    _require(acting_user, "research:edit")
    enrollment = RegistryEnrollment.query.filter_by(id=enrollment_id, is_archived=False).first()
    if enrollment is None:
        raise NotFoundError("Enrollment not found.")
    enrollment.status = ENROLLMENT_STATUS_WITHDRAWN
    db.session.commit()
    audit_engine.log(
        "research.enrollment_withdrawn",
        user=acting_user,
        target_type="registry_enrollment",
        target_id=enrollment.id,
        details={"registry": enrollment.registry_code, "patient_id": enrollment.patient_id},
    )
    return enrollment


def build_dataset(acting_user, registry_code: str) -> tuple[list[str], list[dict]]:
    _require(acting_user, "research:view")
    variables = list_variables(acting_user, registry_code)
    enrollments = list_enrollments(acting_user, registry_code)
    context = REGISTRY_CONTEXT.get(registry_code, {})

    columns = ["patient_id", "mrn"] + [v.code for v in variables]
    rows = []
    for enrollment in enrollments:
        patient = enrollment.patient
        row = {
            "patient_id": patient.id,
            "mrn": patient.mrn,
        }
        for var in variables:
            row[var.code] = variable_framework.resolve_variable_value(
                patient,
                var,
                enrollment_id=enrollment.id,
                registry_context=context,
            )
        rows.append(row)
    return columns, rows


def export_dataset_csv(acting_user, registry_code: str) -> str:
    _require(acting_user, "research:export")
    columns, rows = build_dataset(acting_user, registry_code)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    audit_engine.log(
        "research.dataset_exported",
        user=acting_user,
        target_type="disease_registry",
        details={"registry": registry_code, "row_count": len(rows)},
    )
    return buf.getvalue()
