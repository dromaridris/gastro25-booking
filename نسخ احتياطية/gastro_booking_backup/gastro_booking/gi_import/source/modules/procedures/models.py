"""
Procedure Engine core -- Sprint 2B "Procedure Scheduling & Endoscopy
Workflow". Booking and workflow only: which patient/appointment, which
procedure type, which room, which endoscopist (optional), what priority,
what stage of the daily workflow it's at. No findings, diagnosis,
recommendations, images, or report generation here -- that's the Report
Engine, a later sprint per the mandated build order; a future Report
record will reference a Procedure by ID, not add fields to this table.

Three tables:
- ProcedureType -- administrator-managed catalogue (Upper GI Endoscopy,
  Colonoscopy, ERCP, ...). Never hardcoded; see requires_special_authorization below.
- EndoscopyRoom -- administrator-managed room list (Room 1, ERCP Room,
  ...). Never hardcoded.
- Procedure -- one booking, linking an existing Appointment to a
  ProcedureType, with an optional EndoscopyRoom and endoscopist.

All three inherit BaseModel (department_id, audit fields,
archive-not-delete) -- the catalogue/room admin verbs the brief asks for
("Add, Edit, Archive, Restore") are exactly BaseModel's existing
archive()/restore() vocabulary, not a new is_active-style mechanism.
"""

from app.core.base_model import BaseModel
from app.extensions import db

# --- Priority ---
PRIORITY_ROUTINE = "routine"
PRIORITY_URGENT = "urgent"
PRIORITY_EMERGENCY = "emergency"

ALL_PRIORITIES = [PRIORITY_ROUTINE, PRIORITY_URGENT, PRIORITY_EMERGENCY]

# --- Status workflow ---
# Exactly these six, per explicit product decision for Sprint 2B -- do
# not add further states without an explicit request.
STATUS_BOOKED = "booked"
STATUS_WAITING = "waiting"
STATUS_READY = "ready"
STATUS_IN_ROOM = "in_room"
STATUS_FINISHED = "finished"
STATUS_CANCELLED = "cancelled"

ALL_STATUSES = [
    STATUS_BOOKED,
    STATUS_WAITING,
    STATUS_READY,
    STATUS_IN_ROOM,
    STATUS_FINISHED,
    STATUS_CANCELLED,
]

# Statuses that mean "this case is over" -- no further workflow action
# (waitlist/ready/in-room/finished/cancel/endoscopist/room/type/priority
# change) is allowed on it. Archive/restore are still allowed, same as
# any BaseModel record.
TERMINAL_STATUSES = {STATUS_FINISHED, STATUS_CANCELLED}


# --- Report template category (Sprint 3B) ---
# Stable catalogue key for standard endoscopy report template selection.
# NULL = no standard template (use generic Sprint 3A report only).
# Independent of display name — administrators may rename ProcedureType.name
# without changing template behaviour.
REPORT_TEMPLATE_KEY_COLONOSCOPY = "colonoscopy"
REPORT_TEMPLATE_KEY_UPPER_GI = "upper_gi"
REPORT_TEMPLATE_KEY_ERCP = "ercp"
REPORT_TEMPLATE_KEY_UPPER_GI_V2 = "upper_gi_v2"
REPORT_TEMPLATE_KEY_COLONOSCOPY_V2 = "colonoscopy_v2"
REPORT_TEMPLATE_KEY_FLEX_SIG_V2 = "flex_sig_v2"
REPORT_TEMPLATE_KEY_PROCTOSCOPY_V2 = "proctoscopy_v2"
REPORT_TEMPLATE_KEY_EUS = "eus"
REPORT_TEMPLATE_KEY_CAPSULE = "capsule"
REPORT_TEMPLATE_KEY_ENTEROSCOPY = "enteroscopy"
REPORT_TEMPLATE_KEY_EMR = "emr"
REPORT_TEMPLATE_KEY_ESD = "esd"

# Sprint 3B standard templates (frozen module reads this tuple — do not add structured keys here).
ALL_REPORT_TEMPLATE_KEYS = (
    REPORT_TEMPLATE_KEY_COLONOSCOPY,
    REPORT_TEMPLATE_KEY_UPPER_GI,
)

# Structured clinical report templates (Sprint 3C+).
STRUCTURED_CLINICAL_REPORT_TEMPLATE_KEYS = (
    REPORT_TEMPLATE_KEY_ERCP,
    REPORT_TEMPLATE_KEY_UPPER_GI_V2,
    REPORT_TEMPLATE_KEY_COLONOSCOPY_V2,
    REPORT_TEMPLATE_KEY_FLEX_SIG_V2,
    REPORT_TEMPLATE_KEY_PROCTOSCOPY_V2,
    REPORT_TEMPLATE_KEY_EUS,
    REPORT_TEMPLATE_KEY_CAPSULE,
    REPORT_TEMPLATE_KEY_ENTEROSCOPY,
    REPORT_TEMPLATE_KEY_EMR,
    REPORT_TEMPLATE_KEY_ESD,
)

# Full ProcedureType catalogue validation set.
CATALOGUE_REPORT_TEMPLATE_KEYS = ALL_REPORT_TEMPLATE_KEYS + STRUCTURED_CLINICAL_REPORT_TEMPLATE_KEYS

REPORT_TEMPLATE_KEY_CHOICES = [
    ("", "None (generic report only)"),
    (REPORT_TEMPLATE_KEY_COLONOSCOPY, "Colonoscopy"),
    (REPORT_TEMPLATE_KEY_UPPER_GI, "Upper GI Endoscopy"),
    (REPORT_TEMPLATE_KEY_ERCP, "ERCP (structured clinical report)"),
    (REPORT_TEMPLATE_KEY_UPPER_GI_V2, "Upper GI Endoscopy (structured clinical report)"),
    (REPORT_TEMPLATE_KEY_COLONOSCOPY_V2, "Colonoscopy (structured clinical report)"),
    (REPORT_TEMPLATE_KEY_FLEX_SIG_V2, "Flexible Sigmoidoscopy (structured clinical report)"),
    (REPORT_TEMPLATE_KEY_PROCTOSCOPY_V2, "Proctoscopy (structured clinical report)"),
    (REPORT_TEMPLATE_KEY_EUS, "EUS (structured clinical report)"),
    (REPORT_TEMPLATE_KEY_CAPSULE, "Capsule endoscopy (structured clinical report)"),
    (REPORT_TEMPLATE_KEY_ENTEROSCOPY, "Device-assisted enteroscopy (structured clinical report)"),
    (REPORT_TEMPLATE_KEY_EMR, "EMR — endoscopic mucosal resection (structured clinical report)"),
    (REPORT_TEMPLATE_KEY_ESD, "ESD — endoscopic submucosal dissection (structured clinical report)"),
]


class ProcedureType(BaseModel):
    """
    Administrator-managed catalogue entry (Sprint 2B feature 2). The
    catalogue is deliberately NOT hardcoded -- an administrator with
    procedure_catalogue:manage adds/edits/archives/restores rows here
    (see app/modules/procedures/services.py), the running application
    never assumes a specific name exists.
    """

    __tablename__ = "procedure_types"

    name = db.Column(db.String(120), nullable=False, unique=True)

    # Sprint 2B explicit product decision: this is a pure AUTHORIZATION
    # POLICY flag, not a clinical-complexity judgment -- it says nothing
    # about whether a procedure is medically "advanced", only whether
    # booking it (and deciding its endoscopist) requires the
    # "procedure:special_authorization" permission (see
    # app/modules/procedures/services.py) instead of plain
    # "procedure:edit". The Procedure Catalogue -- i.e. an administrator,
    # per row -- is entirely what decides this; it is never hardcoded by
    # name (e.g. never `if name == "ERCP"`) or inferred from any notion
    # of procedure complexity in code.
    requires_special_authorization = db.Column(db.Boolean, nullable=False, default=False)

    report_template_key = db.Column(db.String(40), nullable=True, index=True)

    description = db.Column(db.String(255), nullable=True)

    # Optional bucket for endoscopy daily-cap counting (upper_gi, colonoscopy, peg, ercp, special, none).
    capacity_category = db.Column(db.String(30), nullable=True, index=True)

    def __repr__(self):
        return f"<ProcedureType {self.name}>"


class EndoscopyRoom(BaseModel):
    """Administrator-managed procedure room (Sprint 2B feature 3). Never
    hardcoded -- see app/modules/procedures/services.py for
    add/edit/archive/restore."""

    __tablename__ = "endoscopy_rooms"

    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<EndoscopyRoom {self.name}>"


class Procedure(BaseModel):
    """
    One procedure booking. Always linked to an existing Appointment
    (feature 1) -- patient_id is deliberately NOT duplicated here: the
    appointment's patient never changes after booking (Sprint 2A,
    frozen), so it's derived via the `patient` property below rather than
    denormalized into a second column that could drift out of sync.
    """

    __tablename__ = "procedures"

    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), nullable=False, index=True
    )
    procedure_type_id = db.Column(
        db.Integer, db.ForeignKey("procedure_types.id"), nullable=False, index=True
    )

    # Nullable: a procedure can be booked before a room is secured (e.g.
    # while on the waiting list) and assigned/changed later -- same
    # optionality pattern as Appointment.provider_id in Sprint 2A.
    room_id = db.Column(
        db.Integer, db.ForeignKey("endoscopy_rooms.id"), nullable=True, index=True
    )

    # Endoscopist assignment is OPTIONAL and may be set/changed later
    # (Sprint 2B feature 4). Deliberately a plain FK to users.id, gated
    # in the service layer by the SAME dedicated User.is_provider flag
    # Sprint 2A introduced for appointment providers -- explicit decision
    # (see app/modules/procedures/services.py) not to add a second,
    # separate "is_endoscopist" flag: is_provider already means "eligible
    # to be assigned to a bookable clinical slot", which an endoscopy
    # procedure is. Never linked to report:draft/report:sign or any other
    # permission.
    endoscopist_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )

    priority = db.Column(
        db.String(20), nullable=False, default=PRIORITY_ROUTINE, index=True
    )
    status = db.Column(db.String(20), nullable=False, default=STATUS_BOOKED, index=True)

    notes = db.Column(db.Text, nullable=True)

    is_capacity_override = db.Column(db.Boolean, nullable=False, default=False)

    appointment = db.relationship("Appointment")
    procedure_type = db.relationship("ProcedureType")
    room = db.relationship("EndoscopyRoom")
    # foreign_keys is required here -- BaseModel already gives this table
    # two other FKs to users.id (created_by_id, archived_by_id), so
    # SQLAlchemy can't infer which column this relationship should join
    # on without being told explicitly (same reasoning as
    # Appointment.provider in Sprint 2A).
    endoscopist = db.relationship("User", foreign_keys=[endoscopist_id])

    @property
    def patient(self):
        return self.appointment.patient if self.appointment else None

    def __repr__(self):
        return f"<Procedure {self.id} appointment={self.appointment_id} status={self.status}>"
