"""Department Operations models — Sprint 7C."""

from app.core.base_model import BaseModel
from app.extensions import db


class RoomOperationsState(BaseModel):
    """Operational state for an endoscopy room — references frozen EndoscopyRoom by ID."""

    __tablename__ = "room_operations_states"

    room_id = db.Column(db.Integer, db.ForeignKey("endoscopy_rooms.id"), nullable=False, unique=True, index=True)
    room_type = db.Column(db.String(30), nullable=False, default="general", index=True)
    status = db.Column(db.String(30), nullable=False, default="available", index=True)
    current_procedure_id = db.Column(db.Integer, db.ForeignKey("procedures.id"), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)

    room = db.relationship("EndoscopyRoom", foreign_keys=[room_id])
    current_procedure = db.relationship("Procedure", foreign_keys=[current_procedure_id])


class RoomStaffAssignment(BaseModel):
    __tablename__ = "room_staff_assignments"

    room_id = db.Column(db.Integer, db.ForeignKey("endoscopy_rooms.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    assignment_date = db.Column(db.Date, nullable=False, index=True)
    role_label = db.Column(db.String(60), nullable=False, default="staff")

    room = db.relationship("EndoscopyRoom", foreign_keys=[room_id])
    user = db.relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        db.UniqueConstraint("room_id", "user_id", "assignment_date", "role_label", name="uq_room_staff_day"),
    )


class RoomScheduleSlot(BaseModel):
    __tablename__ = "room_schedule_slots"

    room_id = db.Column(db.Integer, db.ForeignKey("endoscopy_rooms.id"), nullable=False, index=True)
    procedure_id = db.Column(db.Integer, db.ForeignKey("procedures.id"), nullable=True, index=True)
    start_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    end_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    room = db.relationship("EndoscopyRoom", foreign_keys=[room_id])
    procedure = db.relationship("Procedure", foreign_keys=[procedure_id])


class Endoscope(BaseModel):
    __tablename__ = "endoscopes"

    scope_code = db.Column(db.String(40), nullable=False, unique=True, index=True)
    serial_number = db.Column(db.String(80), nullable=True)
    model = db.Column(db.String(120), nullable=True)
    manufacturer = db.Column(db.String(120), nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    scope_type = db.Column(db.String(30), nullable=False, index=True)
    current_location = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="available", index=True)
    assigned_room_id = db.Column(db.Integer, db.ForeignKey("endoscopy_rooms.id"), nullable=True, index=True)
    assigned_procedure_id = db.Column(db.Integer, db.ForeignKey("procedures.id"), nullable=True, index=True)
    assigned_technician_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    last_maintenance_at = db.Column(db.DateTime(timezone=True), nullable=True)
    next_maintenance_at = db.Column(db.DateTime(timezone=True), nullable=True)

    assigned_room = db.relationship("EndoscopyRoom", foreign_keys=[assigned_room_id])
    assigned_procedure = db.relationship("Procedure", foreign_keys=[assigned_procedure_id])
    assigned_technician = db.relationship("User", foreign_keys=[assigned_technician_id])


class ScopeMaintenanceRecord(BaseModel):
    __tablename__ = "scope_maintenance_records"

    scope_id = db.Column(db.Integer, db.ForeignKey("endoscopes.id"), nullable=False, index=True)
    record_type = db.Column(db.String(20), nullable=False, index=True)  # service | repair
    performed_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    performed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    next_due_at = db.Column(db.DateTime(timezone=True), nullable=True)

    scope = db.relationship("Endoscope", foreign_keys=[scope_id])
    performed_by = db.relationship("User", foreign_keys=[performed_by_id])


class ScopeReprocessingCycle(BaseModel):
    __tablename__ = "scope_reprocessing_cycles"

    scope_id = db.Column(db.Integer, db.ForeignKey("endoscopes.id"), nullable=False, index=True)
    procedure_session_id = db.Column(db.Integer, db.ForeignKey("procedure_sessions.id"), nullable=True, index=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    current_step = db.Column(db.String(40), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="in_progress", index=True)

    scope = db.relationship("Endoscope", foreign_keys=[scope_id])
    procedure_session = db.relationship("ProcedureSession", foreign_keys=[procedure_session_id])
    steps = db.relationship(
        "ScopeReprocessingStep",
        back_populates="cycle",
        order_by="ScopeReprocessingStep.completed_at.asc()",
    )


class ScopeReprocessingStep(BaseModel):
    __tablename__ = "scope_reprocessing_steps"

    cycle_id = db.Column(db.Integer, db.ForeignKey("scope_reprocessing_cycles.id"), nullable=False, index=True)
    step_code = db.Column(db.String(40), nullable=False, index=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    cycle = db.relationship("ScopeReprocessingCycle", back_populates="steps")
    completed_by = db.relationship("User", foreign_keys=[completed_by_id])


class ConsumableItem(BaseModel):
    __tablename__ = "consumable_items"

    name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    current_stock = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock = db.Column(db.Integer, nullable=False, default=0)
    unit = db.Column(db.String(20), nullable=False, default="each")


class ConsumableStockMovement(BaseModel):
    __tablename__ = "consumable_stock_movements"

    consumable_id = db.Column(db.Integer, db.ForeignKey("consumable_items.id"), nullable=False, index=True)
    movement_type = db.Column(db.String(20), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False)
    procedure_id = db.Column(db.Integer, db.ForeignKey("procedures.id"), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    consumable = db.relationship("ConsumableItem", foreign_keys=[consumable_id])
    procedure = db.relationship("Procedure", foreign_keys=[procedure_id])
    recorded_by = db.relationship("User", foreign_keys=[recorded_by_id])


class ProcedureConsumablePlan(BaseModel):
    """Consumables planned for a procedure — auto-deducted when procedure completes."""

    __tablename__ = "procedure_consumable_plans"

    procedure_id = db.Column(db.Integer, db.ForeignKey("procedures.id"), nullable=False, index=True)
    consumable_id = db.Column(db.Integer, db.ForeignKey("consumable_items.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    is_deducted = db.Column(db.Boolean, nullable=False, default=False)

    procedure = db.relationship("Procedure", foreign_keys=[procedure_id])
    consumable = db.relationship("ConsumableItem", foreign_keys=[consumable_id])

    __table_args__ = (
        db.UniqueConstraint("procedure_id", "consumable_id", name="uq_procedure_consumable"),
    )


class WaitingListEntry(BaseModel):
    __tablename__ = "waiting_list_entries"

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    procedure_type_id = db.Column(db.Integer, db.ForeignKey("procedure_types.id"), nullable=False, index=True)
    priority = db.Column(db.String(20), nullable=False, default="routine", index=True)
    consultant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    listed_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    scheduled_date = db.Column(db.Date, nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    procedure_id = db.Column(db.Integer, db.ForeignKey("procedures.id"), nullable=True, index=True)
    delay_alert_sent = db.Column(db.Boolean, nullable=False, default=False)

    patient = db.relationship("Patient", foreign_keys=[patient_id])
    procedure_type = db.relationship("ProcedureType", foreign_keys=[procedure_type_id])
    consultant = db.relationship("User", foreign_keys=[consultant_id])
    procedure = db.relationship("Procedure", foreign_keys=[procedure_id])


class DutyRosterEntry(BaseModel):
    __tablename__ = "duty_roster_entries"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    roster_date = db.Column(db.Date, nullable=False, index=True)
    shift_type = db.Column(db.String(20), nullable=False, index=True)
    shift_start = db.Column(db.Time, nullable=True)
    shift_end = db.Column(db.Time, nullable=True)
    is_on_call = db.Column(db.Boolean, nullable=False, default=False)
    is_leave = db.Column(db.Boolean, nullable=False, default=False)
    cover_for_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
    cover_for = db.relationship("User", foreign_keys=[cover_for_user_id])

    __table_args__ = (db.UniqueConstraint("user_id", "roster_date", "shift_type", name="uq_roster_user_day_shift"),)


class DepartmentAnnouncement(BaseModel):
    __tablename__ = "department_announcements"

    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, index=True)
    priority = db.Column(db.String(20), nullable=False, default="normal", index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    published_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    published_by = db.relationship("User", foreign_keys=[published_by_id])


class AnnouncementReadReceipt(BaseModel):
    __tablename__ = "announcement_read_receipts"

    announcement_id = db.Column(db.Integer, db.ForeignKey("department_announcements.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    read_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    announcement = db.relationship("DepartmentAnnouncement", foreign_keys=[announcement_id])
    user = db.relationship("User", foreign_keys=[user_id])

    __table_args__ = (db.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_read"),)


class InternalMessage(BaseModel):
    __tablename__ = "internal_messages"

    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    message_scope = db.Column(db.String(20), nullable=False, default="direct", index=True)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("internal_messages.id"), nullable=True, index=True)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)

    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])
    parent = db.relationship("InternalMessage", remote_side="InternalMessage.id")


class DepartmentResource(BaseModel):
    __tablename__ = "department_resources"

    name = db.Column(db.String(120), nullable=False, index=True)
    resource_type = db.Column(db.String(30), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="available", index=True)
    location = db.Column(db.String(120), nullable=True)
    assigned_room_id = db.Column(db.Integer, db.ForeignKey("endoscopy_rooms.id"), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    last_maintenance_at = db.Column(db.DateTime(timezone=True), nullable=True)
    next_maintenance_at = db.Column(db.DateTime(timezone=True), nullable=True)

    assigned_room = db.relationship("EndoscopyRoom", foreign_keys=[assigned_room_id])


class ResourceStatusLog(db.Model):
    """Audit trail for resource status changes — not archivable clinical data."""

    __tablename__ = "resource_status_logs"

    id = db.Column(db.Integer, primary_key=True)
    resource_type = db.Column(db.String(30), nullable=False, index=True)
    resource_id = db.Column(db.Integer, nullable=False, index=True)
    previous_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    changed_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False, default=1)

    changed_by = db.relationship("User", foreign_keys=[changed_by_id])
