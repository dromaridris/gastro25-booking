"""
Appointment — Sprint 2A "Appointment Core". Scheduling only: which
patient, which provider (optional), when. No procedure or clinical
encounter data lives here — that's the Procedure Engine, a later sprint
per the mandated build order. A future Procedure record will reference
an Appointment by ID, not add fields to this table.

Inherits BaseModel: department_id, audit fields, archive-not-delete.
Archiving here is reserved for correcting an erroneous/duplicate booking
(same convention as Patient) — a routine cancellation is a STATUS change
(see STATUS_CANCELLED below), not an archive, so cancelled appointments
remain visible in schedules/reports rather than disappearing.
"""

from datetime import timedelta

from app.core.base_model import BaseModel
from app.extensions import db

# --- Status workflow ---
# Exactly these seven, per explicit product decision for Sprint 2A — do
# not add further states without an explicit request.
STATUS_SCHEDULED = "scheduled"
STATUS_RESCHEDULED = "rescheduled"
STATUS_CHECKED_IN = "checked_in"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
STATUS_NO_SHOW = "no_show"

ALL_STATUSES = [
    STATUS_SCHEDULED,
    STATUS_RESCHEDULED,
    STATUS_CHECKED_IN,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    STATUS_NO_SHOW,
]

# Statuses that still "occupy" a provider's calendar for double-booking
# purposes. Cancelled appointments free up the slot; every other status
# (including completed/no-show, which already happened at that time)
# counts as occupying it.
CONFLICT_CHECK_STATUSES = [s for s in ALL_STATUSES if s != STATUS_CANCELLED]

DEFAULT_DURATION_MINUTES = 30


class Appointment(BaseModel):
    __tablename__ = "appointments"

    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True
    )

    # Nullable by explicit decision: an appointment can be booked as
    # "unassigned" (e.g. a department slot) and a provider assigned
    # later. Conflict detection (see services._raise_if_conflict) simply
    # does not apply when this is NULL — there is nothing to conflict
    # with.
    provider_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )

    # The CURRENT active scheduled time — updated on every reschedule.
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    # Set once at creation, never modified afterward — "the original
    # scheduled date/time" per the reschedule-history requirement. Full
    # reschedule-by-reschedule history (every old->new transition) lives
    # in the Audit Engine (action="appointment.rescheduled"), not as
    # additional rows here — reusing the existing audit trail rather than
    # building a second, parallel history mechanism.
    original_scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False)

    duration_minutes = db.Column(
        db.Integer, nullable=False, default=DEFAULT_DURATION_MINUTES
    )

    status = db.Column(db.String(20), nullable=False, default=STATUS_SCHEDULED, index=True)

    reason = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    is_capacity_override = db.Column(db.Boolean, nullable=False, default=False)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    # foreign_keys is required here -- BaseModel already gives this table
    # two other FKs to users.id (created_by_id, archived_by_id), so
    # SQLAlchemy can't infer which column this relationship should join
    # on without being told explicitly.
    provider = db.relationship("User", foreign_keys=[provider_id])

    @property
    def ends_at(self):
        return self.scheduled_at + timedelta(minutes=self.duration_minutes)

    @property
    def was_rescheduled(self) -> bool:
        return self.scheduled_at != self.original_scheduled_at

    def __repr__(self):
        return f"<Appointment {self.id} patient={self.patient_id} at={self.scheduled_at} status={self.status}>"
