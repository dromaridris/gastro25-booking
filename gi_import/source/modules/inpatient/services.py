"""Inpatient services — ward bed board."""

from __future__ import annotations

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.inpatient.models import (
    BED_AVAILABLE,
    BED_CLEANING,
    BED_ISOLATION,
    BED_OCCUPIED,
    BED_RESERVED,
    MOVEMENT_ADMIT,
    MOVEMENT_DISCHARGE,
    MOVEMENT_TRANSFER,
    Bed,
    BedMovement,
    BedOccupancy,
    Ward,
    WardRoom,
)
from app.modules.patients.models import Patient


def _require(user, code: str, target_id=None):
    permission_engine.require(user, code, audit_context={"target_type": "Inpatient", "target_id": target_id})


def list_board(acting_user, *, ward_id: int | None = None) -> list[dict]:
    _require(acting_user, "inpatient:view")
    q = Ward.query.filter_by(is_archived=False)
    if ward_id:
        q = q.filter_by(id=ward_id)
    wards = q.order_by(Ward.name).all()
    board = []
    for ward in wards:
        rooms_data = []
        for room in WardRoom.query.filter_by(ward_id=ward.id, is_archived=False).order_by(WardRoom.name):
            beds_data = []
            for bed in Bed.query.filter_by(room_id=room.id, is_archived=False).order_by(Bed.label):
                occ = (
                    BedOccupancy.query.filter_by(bed_id=bed.id, is_archived=False)
                    .filter(BedOccupancy.discharged_at.is_(None))
                    .first()
                )
                beds_data.append({"bed": bed, "occupancy": occ})
            rooms_data.append({"room": room, "beds": beds_data})
        board.append({"ward": ward, "rooms": rooms_data})
    return board


def _get_bed(acting_user, bed_id: int) -> Bed:
    bed = Bed.query.get(bed_id)
    if bed is None or bed.is_archived:
        raise NotFoundError(f"No bed with id {bed_id}")
    return bed


def _active_occupancy(bed_id: int) -> BedOccupancy | None:
    return (
        BedOccupancy.query.filter_by(bed_id=bed_id, is_archived=False)
        .filter(BedOccupancy.discharged_at.is_(None))
        .first()
    )


def admit(acting_user, *, bed_id: int, patient_id: int, notes: str | None = None) -> BedOccupancy:
    _require(acting_user, "inpatient:manage", bed_id)
    bed = _get_bed(acting_user, bed_id)
    if bed.status not in (BED_AVAILABLE, BED_RESERVED):
        raise ValidationError(f"Bed is not available (status: {bed.status}).")
    if _active_occupancy(bed_id):
        raise ValidationError("Bed already has an active occupancy.")
    patient = Patient.query.get(patient_id)
    if patient is None or patient.is_archived:
        raise NotFoundError(f"No patient with id {patient_id}")
    occ = BedOccupancy(
        bed_id=bed_id,
        patient_id=patient_id,
        admitting_user_id=acting_user.id,
        created_by_id=acting_user.id,
    )
    bed.status = BED_OCCUPIED
    movement = BedMovement(
        patient_id=patient_id,
        to_bed_id=bed_id,
        movement_type=MOVEMENT_ADMIT,
        notes=notes,
        moved_by_id=acting_user.id,
        created_by_id=acting_user.id,
    )
    db.session.add_all([occ, movement])
    db.session.commit()
    audit_engine.log("inpatient.admit", user=acting_user, target_type="bed", target_id=bed_id, details={"patient_id": patient_id})
    return occ


def transfer(acting_user, *, from_bed_id: int, to_bed_id: int, notes: str | None = None) -> BedOccupancy:
    _require(acting_user, "inpatient:manage", to_bed_id)
    from_bed = _get_bed(acting_user, from_bed_id)
    to_bed = _get_bed(acting_user, to_bed_id)
    if to_bed.status not in (BED_AVAILABLE, BED_RESERVED):
        raise ValidationError("Destination bed is not available.")
    occ = _active_occupancy(from_bed_id)
    if occ is None:
        raise ValidationError("Source bed has no active patient.")
    if _active_occupancy(to_bed_id):
        raise ValidationError("Destination bed is occupied.")
    occ.bed_id = to_bed_id
    occ.discharged_at = None
    from_bed.status = BED_CLEANING
    to_bed.status = BED_OCCUPIED
    movement = BedMovement(
        patient_id=occ.patient_id,
        from_bed_id=from_bed_id,
        to_bed_id=to_bed_id,
        movement_type=MOVEMENT_TRANSFER,
        notes=notes,
        moved_by_id=acting_user.id,
        created_by_id=acting_user.id,
    )
    db.session.add(movement)
    db.session.commit()
    audit_engine.log("inpatient.transfer", user=acting_user, target_type="bed", target_id=to_bed_id)
    return occ


def discharge(acting_user, *, bed_id: int, notes: str | None = None) -> None:
    _require(acting_user, "inpatient:manage", bed_id)
    bed = _get_bed(acting_user, bed_id)
    occ = _active_occupancy(bed_id)
    if occ is None:
        raise ValidationError("Bed has no active patient.")
    occ.discharged_at = utcnow()
    bed.status = BED_CLEANING
    movement = BedMovement(
        patient_id=occ.patient_id,
        from_bed_id=bed_id,
        movement_type=MOVEMENT_DISCHARGE,
        notes=notes,
        moved_by_id=acting_user.id,
        created_by_id=acting_user.id,
    )
    db.session.add(movement)
    db.session.commit()
    audit_engine.log("inpatient.discharge", user=acting_user, target_type="bed", target_id=bed_id)


def set_bed_status(acting_user, bed_id: int, status: str) -> Bed:
    _require(acting_user, "inpatient:manage", bed_id)
    if status not in (BED_AVAILABLE, BED_CLEANING, BED_ISOLATION, BED_RESERVED):
        raise ValidationError(f"Invalid bed status: {status}")
    bed = _get_bed(acting_user, bed_id)
    if status == BED_AVAILABLE and _active_occupancy(bed_id):
        raise ValidationError("Cannot mark occupied bed as available.")
    bed.status = status
    db.session.commit()
    audit_engine.log("inpatient.bed_status", user=acting_user, target_type="bed", target_id=bed_id, details={"status": status})
    return bed
