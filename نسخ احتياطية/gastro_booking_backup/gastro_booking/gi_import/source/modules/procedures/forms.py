from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, Optional

from app.modules.auth.models import User
from app.modules.procedures.models import (
    ALL_PRIORITIES,
    ALL_STATUSES,
    REPORT_TEMPLATE_KEY_CHOICES,
    EndoscopyRoom,
    ProcedureType,
)


def _procedure_type_choices(acting_user=None):
    """Show only procedure types the current user is allowed to book."""
    from flask_login import current_user

    from app.engines import permission_engine

    user = acting_user or current_user
    can_book_advanced = permission_engine.check(user, "procedure:special_authorization")
    types = ProcedureType.query.filter_by(is_archived=False).order_by(ProcedureType.name.asc())
    choices = []
    for procedure_type in types:
        if procedure_type.requires_special_authorization and not can_book_advanced:
            continue
        label = procedure_type.name
        if procedure_type.requires_special_authorization:
            label += " (Advanced procedure)"
        choices.append((str(procedure_type.id), label))
    if choices:
        choices = [("", "-- Select procedure type --")] + choices
    else:
        choices = [("", "— No procedure types configured (ask HoD to add them) —")]
    return choices


def _all_procedure_type_choices():
    types = ProcedureType.query.filter_by(is_archived=False).order_by(ProcedureType.name.asc())
    return [
        (
            str(procedure_type.id),
            f"{procedure_type.name}{' (Advanced procedure)' if procedure_type.requires_special_authorization else ''}",
        )
        for procedure_type in types
    ]


def _room_choices():
    choices = [("", "-- No room assigned yet --")]
    rooms = EndoscopyRoom.query.filter_by(is_archived=False).order_by(EndoscopyRoom.name.asc())
    for room in rooms:
        choices.append((str(room.id), room.name))
    return choices


def _endoscopist_choices():
    """
    Deliberately keyed off User.is_provider -- the same dedicated flag
    Sprint 2A introduced for appointment providers, reused here by
    explicit decision rather than adding a second flag. See
    Procedure.endoscopist_id's docstring.
    """
    choices = [("", "-- Unassigned --")]
    endoscopists = User.query.filter_by(
        is_archived=False, is_active_account=True, is_provider=True
    ).order_by(User.full_name.asc())
    for user in endoscopists:
        choices.append((str(user.id), f"{user.full_name} ({user.role.name if user.role else 'no role'})"))
    return choices


class ProcedureTypeForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    requires_special_authorization = BooleanField(
        "Advanced procedure — only Consultant level and above can book this type"
    )
    report_template_key = SelectField(
        "Standard report template",
        choices=REPORT_TEMPLATE_KEY_CHOICES,
        validators=[Optional()],
        description="Which standard report form applies when documenting this procedure type.",
    )
    description = TextAreaField("Description (optional)", validators=[Optional()])
    submit = SubmitField("Save")


class ArchiveProcedureTypeForm(FlaskForm):
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Archive")


class RoomForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description (optional)", validators=[Optional()])
    submit = SubmitField("Save")


class ArchiveRoomForm(FlaskForm):
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Archive")


class ProcedureForm(FlaskForm):
    """
    Appointment is deliberately NOT a field on this form -- same
    convention as AppointmentForm's patient field: a procedure is booked
    from that appointment's own detail page (appointment_id comes from
    the URL, see routes.py's new_procedure view), not a clinic-wide
    appointment search widget.
    """

    procedure_type_id = SelectField("Procedure type", validators=[DataRequired()])
    room_id = SelectField("Room (optional)", validators=[Optional()])
    endoscopist_id = SelectField("Endoscopist (optional)", validators=[Optional()])
    priority = SelectField("Priority", validators=[DataRequired()])
    notes = TextAreaField("Notes", validators=[Optional()])
    is_capacity_override = BooleanField(
        "Override capacity / holiday / Sunday restrictions (consultant / HoD only)"
    )
    submit = SubmitField("Save booking")

    def __init__(self, *args, acting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.procedure_type_id.choices = _procedure_type_choices(acting_user)
        self.room_id.choices = _room_choices()
        self.endoscopist_id.choices = _endoscopist_choices()
        self.priority.choices = [(p, p.title()) for p in ALL_PRIORITIES]


class AssignEndoscopistForm(FlaskForm):
    endoscopist_id = SelectField("Endoscopist", validators=[Optional()])
    submit = SubmitField("Assign")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endoscopist_id.choices = _endoscopist_choices()


class AssignRoomForm(FlaskForm):
    room_id = SelectField("Room", validators=[Optional()])
    submit = SubmitField("Assign")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id.choices = _room_choices()


class ChangeProcedureTypeForm(FlaskForm):
    procedure_type_id = SelectField("Type of procedure", validators=[DataRequired()])
    submit = SubmitField("Update procedure type")

    def __init__(self, *args, acting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.procedure_type_id.choices = _procedure_type_choices(acting_user)


class PriorityForm(FlaskForm):
    priority = SelectField("Priority", validators=[DataRequired()])
    submit = SubmitField("Update Priority")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.priority.choices = [(p, p.title()) for p in ALL_PRIORITIES]


class WaitlistForm(FlaskForm):
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Move to Waiting List")


class CancelProcedureForm(FlaskForm):
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Cancel Procedure")


class ArchiveProcedureForm(FlaskForm):
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Archive")


class DailyListFilterForm(FlaskForm):
    """GET-based filter -- no CSRF needed for a read-only query, same
    convention as AppointmentSearchForm/PatientSearchForm."""

    class Meta:
        csrf = False

    date = DateField("Date", validators=[Optional()])
    room_id = SelectField("Room", validators=[Optional()])
    procedure_type_id = SelectField("Procedure type", validators=[Optional()])
    endoscopist_id = SelectField("Endoscopist", validators=[Optional()])
    status = SelectField("Status", validators=[Optional()])
    priority = SelectField("Priority", validators=[Optional()])
    submit = SubmitField("Filter")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id.choices = [("", "-- Any room --")] + _room_choices()[1:]
        self.procedure_type_id.choices = [("", "-- Any type --")] + _all_procedure_type_choices()
        self.endoscopist_id.choices = [("", "-- Any endoscopist --")] + _endoscopist_choices()[1:]
        self.status.choices = [("", "-- Any status --")] + [
            (s, s.replace("_", " ").title()) for s in ALL_STATUSES
        ]
        self.priority.choices = [("", "-- Any priority --")] + [
            (p, p.title()) for p in ALL_PRIORITIES
        ]
