"""
Patient — the first clinical-data entity in the system, and per the
project's core philosophy, the center of it: every other clinical module
(Procedures, Reports, Research) will eventually hang off Patient records.

Inherits BaseModel: department_id, audit fields, and archive-not-delete
— a patient record is NEVER hard-deleted, only archived (e.g. for a
duplicate-record merge or an erroneous registration), preserving
referential integrity for any future Procedure/Report that references it.

Scope note (Sprint 1B — "Patient Foundation" only, per explicit
instruction not to start Appointments or Procedures): this model holds
demographics and identifiers only. No scheduling, procedure, or clinical
encounter data lives here — those are separate future modules that will
reference Patient by ID, not fields added to this table.
"""

from app.core.base_model import BaseModel
from app.extensions import db


class Patient(BaseModel):
    __tablename__ = "patients"

    # Medical Record Number — the primary clinical identifier, distinct
    # from the database's internal `id`. Auto-generated (see
    # services.py's _generate_mrn), never user-typed, so it can't collide
    # or be malformed. Format: "<DEPARTMENT_CODE>-<6-digit sequence>",
    # e.g. "GASTRO-000001".
    mrn = db.Column(db.String(30), nullable=False, unique=True, index=True)

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)

    # Free-form string rather than a DB-level enum: sex/gender categories
    # used in intake forms vary by institution and can change over time;
    # a string column means adding/renaming a category is a form-layer
    # change, not a migration. Validated at the form layer
    # (app/modules/patients/forms.py), not constrained here.
    sex = db.Column(db.String(20), nullable=False)

    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    # Optional external identifier (national ID / passport / etc.) —
    # deliberately NOT unique-constrained: two patients can legitimately
    # share a missing/placeholder value, and cross-border or undocumented
    # patients may have none at all. MRN is the system's unique identifier;
    # this is supplementary.
    national_id = db.Column(db.String(50), nullable=True)

    emergency_contact_name = db.Column(db.String(150), nullable=True)
    emergency_contact_phone = db.Column(db.String(30), nullable=True)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Patient {self.mrn} {self.full_name}>"


class MRNCounter(db.Model):
    """
    One row per department, tracking the next MRN sequence number for
    that department. Not a BaseModel subclass — this is internal
    bookkeeping, not clinical data; it has no meaningful "archive" state.

    Concurrency note: _generate_mrn() in services.py locks this row with
    SELECT ... FOR UPDATE before incrementing, so concurrent patient
    registrations on real Postgres serialize correctly instead of
    racing to the same MRN. SQLite (unit tests only — never production,
    per the hybrid testing strategy) does not honor row-level locking,
    but unit tests run single-threaded, so this doesn't affect
    correctness there.
    """

    __tablename__ = "mrn_counters"

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer, db.ForeignKey("departments.id"), nullable=False, unique=True
    )
    next_value = db.Column(db.Integer, nullable=False, default=1)
