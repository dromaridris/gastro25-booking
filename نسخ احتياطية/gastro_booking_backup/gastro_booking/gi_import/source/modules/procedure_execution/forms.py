from flask_wtf import FlaskForm
from wtforms import BooleanField, DateTimeLocalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.modules.auth.models import User
from app.modules.procedure_execution.models import ALL_OUTCOMES, ALL_SEDATION_CATEGORIES


def _user_choices(include_empty=True):
    choices = []
    if include_empty:
        choices.append(("", "-- Unassigned --"))
    users = User.query.filter_by(is_archived=False, is_active_account=True).order_by(
        User.full_name.asc()
    )
    for user in users:
        role_name = user.role.name if user.role else "no role"
        choices.append((str(user.id), f"{user.full_name} ({role_name})"))
    return choices


def _endoscopist_choices():
    choices = [("", "-- Unassigned --")]
    endoscopists = User.query.filter_by(
        is_archived=False, is_active_account=True, is_provider=True
    ).order_by(User.full_name.asc())
    for user in endoscopists:
        role_name = user.role.name if user.role else "no role"
        choices.append((str(user.id), f"{user.full_name} ({role_name})"))
    return choices


def _sedation_choices():
    labels = {
        "no_sedation": "No Sedation",
        "conscious_sedation": "Conscious Sedation",
        "deep_sedation": "Deep Sedation",
        "general_anaesthesia": "General Anaesthesia",
    }
    return [("", "-- Not recorded --")] + [
        (value, labels.get(value, value.replace("_", " ").title()))
        for value in ALL_SEDATION_CATEGORIES
    ]


def _outcome_choices():
    labels = {
        "completed": "Completed",
        "abandoned": "Abandoned",
        "deferred": "Deferred",
    }
    return [("", "-- Not set --")] + [
        (value, labels.get(value, value.title())) for value in ALL_OUTCOMES
    ]


class TeamAssignmentForm(FlaskForm):
    endoscopist_id = SelectField("Endoscopist", choices=[], validators=[Optional()])
    assistant_id = SelectField("Assistant", choices=[], validators=[Optional()])
    nurse_id = SelectField("Nurse", choices=[], validators=[Optional()])
    technician_id = SelectField("Technician", choices=[], validators=[Optional()])
    anaesthetist_id = SelectField("Anaesthetist", choices=[], validators=[Optional()])
    submit = SubmitField("Save Team")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.endoscopist_id.choices = _endoscopist_choices()
        user_choices = _user_choices()
        self.assistant_id.choices = user_choices
        self.nurse_id.choices = user_choices
        self.technician_id.choices = user_choices
        self.anaesthetist_id.choices = user_choices


class TimeTrackingForm(FlaskForm):
    patient_in_at = DateTimeLocalField("Patient In", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    procedure_start_at = DateTimeLocalField(
        "Procedure Start", validators=[Optional()], format="%Y-%m-%dT%H:%M"
    )
    procedure_finish_at = DateTimeLocalField(
        "Procedure Finish", validators=[Optional()], format="%Y-%m-%dT%H:%M"
    )
    patient_out_at = DateTimeLocalField("Patient Out", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    submit = SubmitField("Save Times")


class SedationForm(FlaskForm):
    sedation_category = SelectField("Sedation Category", choices=[], validators=[Optional()])
    submit = SubmitField("Save Sedation")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sedation_category.choices = _sedation_choices()


class ChecklistForm(FlaskForm):
    consent_confirmed = BooleanField("Consent confirmed")
    identity_confirmed = BooleanField("Patient identity confirmed")
    indication_confirmed = BooleanField("Procedure indication confirmed")
    anticoagulants_reviewed = BooleanField("Anticoagulants reviewed")
    submit = SubmitField("Save Checklist")


class OutcomeForm(FlaskForm):
    outcome = SelectField("Procedure Outcome", choices=[], validators=[DataRequired()])
    submit = SubmitField("Set Outcome")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcome.choices = [(v, v.title()) for v in ALL_OUTCOMES]


class CancelSessionForm(FlaskForm):
    reason = TextAreaField("Cancellation Reason", validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField("Cancel Procedure")
