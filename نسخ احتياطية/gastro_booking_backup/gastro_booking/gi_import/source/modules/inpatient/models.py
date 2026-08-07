"""Inpatient ward bed management — separate from dept_ops endoscopy rooms."""

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

BED_AVAILABLE = "available"
BED_OCCUPIED = "occupied"
BED_CLEANING = "cleaning"
BED_ISOLATION = "isolation"
BED_RESERVED = "reserved"

MOVEMENT_ADMIT = "admit"
MOVEMENT_TRANSFER = "transfer"
MOVEMENT_DISCHARGE = "discharge"


class Ward(BaseModel):
    __tablename__ = "wards"

    code = db.Column(db.String(30), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    ward_type = db.Column(db.String(30), nullable=False, default="general", index=True)
    notes = db.Column(db.Text, nullable=True)

    rooms = db.relationship("WardRoom", back_populates="ward", order_by="WardRoom.name")


class WardRoom(BaseModel):
    __tablename__ = "ward_rooms"

    ward_id = db.Column(db.Integer, db.ForeignKey("wards.id"), nullable=False, index=True)
    name = db.Column(db.String(60), nullable=False)
    floor = db.Column(db.String(20), nullable=True)

    ward = db.relationship("Ward", back_populates="rooms")
    beds = db.relationship("Bed", back_populates="room", order_by="Bed.label")

    __table_args__ = (db.UniqueConstraint("ward_id", "name", name="uq_ward_room_name"),)


class Bed(BaseModel):
    __tablename__ = "beds"

    room_id = db.Column(db.Integer, db.ForeignKey("ward_rooms.id"), nullable=False, index=True)
    label = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=BED_AVAILABLE, index=True)
    notes = db.Column(db.Text, nullable=True)

    room = db.relationship("WardRoom", back_populates="beds")
    current_occupancy = db.relationship(
        "BedOccupancy",
        primaryjoin="and_(Bed.id==BedOccupancy.bed_id, BedOccupancy.discharged_at.is_(None))",
        uselist=False,
        viewonly=True,
    )

    __table_args__ = (db.UniqueConstraint("room_id", "label", name="uq_bed_room_label"),)


class BedOccupancy(BaseModel):
    __tablename__ = "bed_occupancies"

    bed_id = db.Column(db.Integer, db.ForeignKey("beds.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    admitted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    discharged_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    admitting_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    bed = db.relationship("Bed", foreign_keys=[bed_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    admitting_user = db.relationship("User", foreign_keys=[admitting_user_id])


class BedMovement(BaseModel):
    __tablename__ = "bed_movements"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    from_bed_id = db.Column(db.Integer, db.ForeignKey("beds.id"), nullable=True, index=True)
    to_bed_id = db.Column(db.Integer, db.ForeignKey("beds.id"), nullable=True, index=True)
    movement_type = db.Column(db.String(20), nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    moved_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    moved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    from_bed = db.relationship("Bed", foreign_keys=[from_bed_id])
    to_bed = db.relationship("Bed", foreign_keys=[to_bed_id])
    moved_by = db.relationship("User", foreign_keys=[moved_by_id])
