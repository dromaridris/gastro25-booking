"""
Procedure Execution — Sprint 2C.

One ProcedureSession per Procedure, recording team assignment, time
tracking, sedation category, safety checklist, and procedure outcome
during execution. No findings, diagnosis, recommendations, images, or
report generation — those belong to Phase 3 (Report Engine).

RoomOccupancyPeriod is deliberately NOT a BaseModel subclass: it is
internal interval bookkeeping for utilisation statistics, not clinical
data subject to archive/restore semantics.
"""

from app.core.base_model import BaseModel, utcnow
from app.extensions import db

# --- Sedation categories (Sprint 2C feature 6) ---
SEDATION_NO = "no_sedation"
SEDATION_CONSCIOUS = "conscious_sedation"
SEDATION_DEEP = "deep_sedation"
SEDATION_GENERAL = "general_anaesthesia"

ALL_SEDATION_CATEGORIES = [
    SEDATION_NO,
    SEDATION_CONSCIOUS,
    SEDATION_DEEP,
    SEDATION_GENERAL,
]

# --- Procedure outcomes (Sprint 2C feature 8 — NOT a medical report) ---
OUTCOME_COMPLETED = "completed"
OUTCOME_ABANDONED = "abandoned"
OUTCOME_DEFERRED = "deferred"

ALL_OUTCOMES = [OUTCOME_COMPLETED, OUTCOME_ABANDONED, OUTCOME_DEFERRED]


class ProcedureSession(BaseModel):
    """
    One execution session per Procedure (enforced by unique procedure_id).
    Links explicitly to Patient, Appointment, and Procedure for query
    convenience and future reporting — values are copied at session
    creation from the procedure graph and never change after that.
    """

    __tablename__ = "procedure_sessions"

    procedure_id = db.Column(
        db.Integer, db.ForeignKey("procedures.id"), nullable=False, unique=True, index=True
    )
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True
    )
    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), nullable=False, index=True
    )

    # Team assignment (Sprint 2C feature 2) — all optional, editable.
    endoscopist_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    assistant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    nurse_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    technician_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    anaesthetist_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Time tracking (Sprint 2C feature 3)
    patient_in_at = db.Column(db.DateTime(timezone=True), nullable=True)
    procedure_start_at = db.Column(db.DateTime(timezone=True), nullable=True)
    procedure_finish_at = db.Column(db.DateTime(timezone=True), nullable=True)
    patient_out_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Sedation (Sprint 2C feature 6)
    sedation_category = db.Column(db.String(30), nullable=True)

    # Safety checklist (Sprint 2C feature 7 — simple booleans, not a generic engine)
    consent_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    identity_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    indication_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    anticoagulants_reviewed = db.Column(db.Boolean, nullable=False, default=False)

    # Outcome (Sprint 2C feature 8)
    outcome = db.Column(db.String(20), nullable=True)

    # Execution-phase cancellation (Sprint 2C feature 5)
    is_cancelled = db.Column(db.Boolean, nullable=False, default=False, index=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    cancelled_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)

    procedure = db.relationship("Procedure", foreign_keys=[procedure_id])
    patient = db.relationship("Patient", foreign_keys=[patient_id])
    appointment = db.relationship("Appointment", foreign_keys=[appointment_id])
    endoscopist = db.relationship("User", foreign_keys=[endoscopist_id])
    assistant = db.relationship("User", foreign_keys=[assistant_id])
    nurse = db.relationship("User", foreign_keys=[nurse_id])
    technician = db.relationship("User", foreign_keys=[technician_id])
    anaesthetist = db.relationship("User", foreign_keys=[anaesthetist_id])
    cancelled_by = db.relationship("User", foreign_keys=[cancelled_by_id])
    occupancy_periods = db.relationship(
        "RoomOccupancyPeriod",
        back_populates="procedure_session",
        order_by="RoomOccupancyPeriod.occupied_from.asc()",
    )

    @property
    def is_active(self) -> bool:
        return not self.is_cancelled and self.outcome is None

    def __repr__(self):
        return f"<ProcedureSession {self.id} procedure={self.procedure_id}>"


class RoomOccupancyPeriod(db.Model):
    """
    Interval record for room utilisation during procedure execution
    (Sprint 2C feature 4). Supports future utilisation statistics by
    storing explicit occupied_from / occupied_until intervals rather
    than a single point-in-time snapshot.
    """

    __tablename__ = "room_occupancy_periods"

    id = db.Column(db.Integer, primary_key=True)
    procedure_session_id = db.Column(
        db.Integer, db.ForeignKey("procedure_sessions.id"), nullable=False, index=True
    )
    room_id = db.Column(
        db.Integer, db.ForeignKey("endoscopy_rooms.id"), nullable=False, index=True
    )
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False, index=True
    )
    occupied_from = db.Column(db.DateTime(timezone=True), nullable=False)
    occupied_until = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    procedure_session = db.relationship("ProcedureSession", back_populates="occupancy_periods")
    room = db.relationship("EndoscopyRoom")

    @property
    def is_open(self) -> bool:
        return self.occupied_until is None

    def __repr__(self):
        return f"<RoomOccupancyPeriod session={self.procedure_session_id} room={self.room_id}>"
