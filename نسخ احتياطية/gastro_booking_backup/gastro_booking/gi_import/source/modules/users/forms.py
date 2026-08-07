from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional

from app.modules.rbac import services as rbac_services

def _role_choices():
    return rbac_services.role_choices_for_forms()


class UserCreateForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=150)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    role = SelectField("Role", validators=[DataRequired()])
    submit = SubmitField("Create User")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role.choices = _role_choices()


class UserEditForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=150)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    submit = SubmitField("Save Changes")


class ChangeRoleForm(FlaskForm):
    role = SelectField("Role", validators=[DataRequired()])
    submit = SubmitField("Change Role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role.choices = _role_choices()


class DeactivateForm(FlaskForm):
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Deactivate")


class AppointmentLimitForm(FlaskForm):
    """Sprint 2A: per-user daily appointment-creation cap. Left blank =
    unlimited (NumberRange only applies when a value is actually
    entered, since the field itself is Optional)."""

    daily_appointment_limit = IntegerField(
        "Daily appointment booking limit (leave blank for unlimited)",
        validators=[Optional(), NumberRange(min=0)],
    )
    submit = SubmitField("Save Limit")


class ProviderFlagForm(FlaskForm):
    """Sprint 2A correction: dedicated toggle for appointment-provider
    eligibility, deliberately independent of role/permissions."""

    is_provider = BooleanField("Eligible to be selected as an appointment provider")
    submit = SubmitField("Save")
