"""Global search aggregator."""

from app.engines import permission_engine
from app.modules.appointments.models import Appointment
from app.modules.patients.models import Patient
from app.modules.procedures.models import Procedure


def search(acting_user, query: str, *, limit: int = 20) -> dict:
    permission_engine.require(acting_user, "search:global")
    q = query.strip()
    if len(q) < 2:
        return {"patients": [], "appointments": [], "procedures": []}
    pattern = f"%{q}%"

    patients = (
        Patient.query.filter_by(is_archived=False)
        .filter(
            (Patient.first_name.ilike(pattern))
            | (Patient.last_name.ilike(pattern))
            | (Patient.mrn.ilike(pattern))
        )
        .order_by(Patient.last_name)
        .limit(limit)
        .all()
    )

    appointments = (
        Appointment.query.join(Patient, Appointment.patient_id == Patient.id)
        .filter(Appointment.is_archived.is_(False))
        .filter(
            (Patient.first_name.ilike(pattern))
            | (Patient.last_name.ilike(pattern))
            | (Patient.mrn.ilike(pattern))
        )
        .order_by(Appointment.scheduled_at.desc())
        .limit(limit)
        .all()
    )

    procedures = (
        Procedure.query.join(Appointment, Procedure.appointment_id == Appointment.id)
        .join(Patient, Appointment.patient_id == Patient.id)
        .filter(Procedure.is_archived.is_(False))
        .filter(
            (Patient.first_name.ilike(pattern))
            | (Patient.last_name.ilike(pattern))
            | (Patient.mrn.ilike(pattern))
        )
        .order_by(Procedure.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "patients": [
            {"id": p.id, "label": f"{p.full_name} ({p.mrn})", "url": f"/patients/{p.id}"}
            for p in patients
        ],
        "appointments": [
            {"id": a.id, "label": f"{a.patient.full_name} — {a.scheduled_at.strftime('%Y-%m-%d %H:%M')}", "url": f"/appointments/{a.id}"}
            for a in appointments
        ],
        "procedures": [
            {"id": pr.id, "label": f"{pr.patient.full_name} — {pr.procedure_type.name if pr.procedure_type else 'Procedure'}", "url": f"/procedures/{pr.id}"}
            for pr in procedures
        ],
    }
