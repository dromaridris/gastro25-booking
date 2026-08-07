"""
Service layer for Patient Foundation (Sprint 1B). Deliberately scoped to
demographics/identifiers only — no scheduling (Appointments) or clinical
encounter data (Procedures), per explicit instruction those are separate,
later sprints.

Permission codes ("patient:view", "patient:edit") are string literals,
not imported constants — same reasoning as every other service module:
the set of roles/permissions is database data (app/modules/rbac/), not
Python. These two permissions already existed in the seeded RBAC data
from Sprint 1A (Nurse/Admin Staff/Research Coordinator get view-only;
Head of Department/Core Consultant/Consultant/Senior Registrar get edit)
— no new permission was needed for this sprint.
"""

from datetime import date

from sqlalchemy import or_

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.department.models import Department
from app.modules.patients.models import MRNCounter, Patient

_VALID_SEX_VALUES = {"female", "male", "other", "unknown"}


def _generate_mrn(department: Department) -> str:
    """Generates the next MRN for a department, e.g. "GASTRO-000001".
    Locks the counter row (SELECT ... FOR UPDATE on Postgres) so
    concurrent registrations don't race to the same number — see
    MRNCounter's docstring for the SQLite caveat (test-only, harmless)."""
    counter = (
        MRNCounter.query.filter_by(department_id=department.id).with_for_update().first()
    )
    if counter is None:
        counter = MRNCounter(department_id=department.id, next_value=1)
        db.session.add(counter)
        db.session.flush()  # assigns counter.id without ending the transaction

    sequence_value = counter.next_value
    counter.next_value = sequence_value + 1
    db.session.commit()
    return f"{department.code}-{sequence_value:06d}"


def _validate_demographics(first_name, last_name, date_of_birth, sex):
    if not first_name or not first_name.strip():
        raise ValidationError("First name is required.")
    if not last_name or not last_name.strip():
        raise ValidationError("Last name is required.")
    if date_of_birth is None:
        raise ValidationError("Date of birth is required.")
    if date_of_birth > date.today():
        raise ValidationError("Date of birth cannot be in the future.")
    if sex not in _VALID_SEX_VALUES:
        raise ValidationError(f"Invalid sex value: {sex}")


def create_patient(
    acting_user,
    first_name: str,
    last_name: str,
    date_of_birth,
    sex: str,
    phone: str = None,
    email: str = None,
    address: str = None,
    national_id: str = None,
    emergency_contact_name: str = None,
    emergency_contact_phone: str = None,
    department_id: int = None,
) -> Patient:
    permission_engine.require(
        acting_user, "patient:edit", audit_context={"target_type": "Patient"}
    )

    _validate_demographics(first_name, last_name, date_of_birth, sex)

    resolved_department_id = department_id or getattr(acting_user, "department_id", None)
    department = Department.query.get(resolved_department_id)
    if department is None:
        raise ValidationError("Invalid department.")

    mrn = _generate_mrn(department)

    patient = Patient(
        mrn=mrn,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        date_of_birth=date_of_birth,
        sex=sex,
        phone=(phone or "").strip() or None,
        email=(email or "").strip().lower() or None,
        address=(address or "").strip() or None,
        national_id=(national_id or "").strip() or None,
        emergency_contact_name=(emergency_contact_name or "").strip() or None,
        emergency_contact_phone=(emergency_contact_phone or "").strip() or None,
        department_id=department.id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(patient)
    db.session.commit()

    audit_engine.log(
        action="patient.created",
        user=acting_user,
        target_type="Patient",
        target_id=patient.id,
        details={"mrn": patient.mrn},
    )
    return patient


def get_patient(acting_user, patient_id: int) -> Patient:
    permission_engine.require(acting_user, "patient:view")
    patient = Patient.query.get(patient_id)
    if patient is None:
        raise NotFoundError(f"No patient with id {patient_id}")
    return patient


def get_patient_by_mrn(acting_user, mrn: str) -> Patient:
    permission_engine.require(acting_user, "patient:view")
    patient = Patient.query.filter_by(mrn=mrn).first()
    if patient is None:
        raise NotFoundError(f"No patient with MRN {mrn}")
    return patient


def search_patients(acting_user, query: str = None, include_archived: bool = False):
    """Simple substring search over MRN/name — NOT the future cross-module
    Search Engine mentioned in the project's architecture rules (that's a
    later, dedicated sprint spanning multiple entity types). This is
    Patient-specific and intentionally minimal for Sprint 1B."""
    permission_engine.require(acting_user, "patient:view")

    patient_query = Patient.query
    if not include_archived:
        patient_query = patient_query.filter_by(is_archived=False)

    if query:
        like_query = f"%{query.strip()}%"
        patient_query = patient_query.filter(
            or_(
                Patient.mrn.ilike(like_query),
                Patient.first_name.ilike(like_query),
                Patient.last_name.ilike(like_query),
            )
        )

    return patient_query.order_by(Patient.last_name.asc(), Patient.first_name.asc()).all()


def update_patient(
    acting_user,
    target_patient: Patient,
    first_name: str,
    last_name: str,
    date_of_birth,
    sex: str,
    phone: str = None,
    email: str = None,
    address: str = None,
    national_id: str = None,
    emergency_contact_name: str = None,
    emergency_contact_phone: str = None,
) -> Patient:
    permission_engine.require(
        acting_user,
        "patient:edit",
        audit_context={"target_type": "Patient", "target_id": target_patient.id},
    )

    _validate_demographics(first_name, last_name, date_of_birth, sex)

    before = {
        "first_name": target_patient.first_name,
        "last_name": target_patient.last_name,
        "date_of_birth": target_patient.date_of_birth.isoformat(),
        "sex": target_patient.sex,
    }

    target_patient.first_name = first_name.strip()
    target_patient.last_name = last_name.strip()
    target_patient.date_of_birth = date_of_birth
    target_patient.sex = sex
    target_patient.phone = (phone or "").strip() or None
    target_patient.email = (email or "").strip().lower() or None
    target_patient.address = (address or "").strip() or None
    target_patient.national_id = (national_id or "").strip() or None
    target_patient.emergency_contact_name = (emergency_contact_name or "").strip() or None
    target_patient.emergency_contact_phone = (emergency_contact_phone or "").strip() or None
    db.session.commit()

    audit_engine.log(
        action="patient.updated",
        user=acting_user,
        target_type="Patient",
        target_id=target_patient.id,
        details={
            "before": before,
            "after": {
                "first_name": target_patient.first_name,
                "last_name": target_patient.last_name,
                "date_of_birth": target_patient.date_of_birth.isoformat(),
                "sex": target_patient.sex,
            },
        },
    )
    return target_patient


def archive_patient(acting_user, target_patient: Patient, reason: str = None) -> Patient:
    """Archive, never delete — a patient record must never be hard-deleted
    even for a duplicate/erroneous registration, since a future Procedure
    or Report may already reference it. Use for merging duplicates or
    correcting a mis-registration, not as a routine action."""
    permission_engine.require(
        acting_user,
        "patient:edit",
        audit_context={"target_type": "Patient", "target_id": target_patient.id},
    )

    target_patient.archive(by_user_id=getattr(acting_user, "id", None), reason=reason)
    db.session.commit()

    audit_engine.log(
        action="patient.archived",
        user=acting_user,
        target_type="Patient",
        target_id=target_patient.id,
        details={"reason": reason},
    )
    return target_patient


def restore_patient(acting_user, target_patient: Patient) -> Patient:
    permission_engine.require(
        acting_user,
        "patient:edit",
        audit_context={"target_type": "Patient", "target_id": target_patient.id},
    )

    target_patient.restore()
    db.session.commit()

    audit_engine.log(
        action="patient.restored",
        user=acting_user,
        target_type="Patient",
        target_id=target_patient.id,
    )
    return target_patient
