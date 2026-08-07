from flask_wtf import FlaskForm
from wtforms import BooleanField, DateTimeField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional, Length

from app.modules.auth.models import User

DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
]


def _provider_choices():
    """
    Queried at form-construction time (not module import time), same
    convention as UserCreateForm's role dropdown -- so a newly
    designated provider shows up without a restart.

    Deliberately keyed off User.is_provider -- a dedicated flag, NOT
    derived from report:draft/report:sign or any other permission. Per
    explicit correction: "who can sign a report" and "who is bookable
    as an appointment provider" are different questions, and coupling
    them meant a role's permission grants silently controlled
    scheduling eligibility. See User.is_provider's docstring.
    """
    choices = [("", "-- Unassigned --")]
    providers = User.query.filter_by(
        is_archived=False, is_active_account=True, is_provider=True
    ).order_by(User.full_name.asc())
    for user in providers:
        choices.append((str(user.id), f"{user.full_name} ({user.role.name if user.role else 'no role'})"))
    return choices


class AppointmentForm(FlaskForm):
    """
    Patient is deliberately NOT a field on this form -- Sprint 2A scope
    is scheduling for a single, already-identified patient (booked from
    that patient's own detail page), not a clinic-wide patient search
    widget. See app/modules/appointments/routes.py's new_appointment
    view: patient_id comes from the URL, not user input here.
    """

    provider_id = SelectField("Provider", validators=[Optional()])
    scheduled_at = DateTimeField(
        "Scheduled date/time", format=DATETIME_FORMATS, validators=[DataRequired()]
    )
    duration_minutes = IntegerField(
        "Duration (minutes)",
        default=30,
        validators=[DataRequired(), NumberRange(min=1, max=480)],
    )
    reason = StringField("Reason for visit", validators=[Optional(), Length(max=255)])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Book Appointment")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.provider_id.choices = _provider_choices()


class RescheduleForm(FlaskForm):
    new_scheduled_at = DateTimeField(
        "New scheduled date/time", format=DATETIME_FORMATS, validators=[DataRequired()]
    )
    reason = StringField("Reason for reschedule (optional)", validators=[Optional(), Length(max=255)])
    is_capacity_override = BooleanField(
        "Override endoscopy booking restrictions (consultant / HoD only)"
    )
    submit = SubmitField("Reschedule")


class CancelAppointmentForm(FlaskForm):
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Cancel Appointment")


class ArchiveAppointmentForm(FlaskForm):
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Archive")


class AppointmentSearchForm(FlaskForm):
    """GET-based filter -- no CSRF needed for a read-only query, same
    convention as PatientSearchForm."""

    class Meta:
        csrf = False

    date_from = DateTimeField(
        "From", format=DATETIME_FORMATS, validators=[Optional()]
    )
    date_to = DateTimeField("To", format=DATETIME_FORMATS, validators=[Optional()])
    status = SelectField("Status", validators=[Optional()])
    submit = SubmitField("Filter")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from app.modules.appointments.models import ALL_STATUSES

        self.status.choices = [("", "-- Any status --")] + [
            (s, s.replace("_", " ").title()) for s in ALL_STATUSES
        ]
