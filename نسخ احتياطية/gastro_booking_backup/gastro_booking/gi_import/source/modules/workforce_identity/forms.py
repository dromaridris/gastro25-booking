"""Forms for Workforce Identity & Duty Management — Phase 7E."""

from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class InvitationForm(FlaskForm):
    role_code = SelectField(
        "Role",
        choices=[
            ("house_officer", "House Officer"),
            ("postgraduate_trainee", "Postgraduate Trainee"),
            ("senior_registrar", "Senior Registrar / Fellow"),
            ("visiting_trainee", "Visiting Trainee"),
        ],
        validators=[DataRequired()],
    )
    rotation_label = StringField("Rotation", validators=[Optional(), Length(max=120)])
    email = StringField("Email (optional pre-fill)", validators=[Optional(), Email(), Length(max=255)])
    start_date = DateField("Start Date", validators=[DataRequired()])
    expiry_date = DateField("Account Expiry Date", validators=[DataRequired()])
    maximum_validity_days = IntegerField("Link Validity (days)", default=14, validators=[Optional()])


class RegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=150)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired()])


class SwapRequestForm(FlaskForm):
    original_roster_entry_id = IntegerField("Your Duty Entry ID", validators=[DataRequired()])
    replacement_user_id = IntegerField("Replacement User ID", validators=[DataRequired()])
    requested_roster_entry_id = IntegerField("Requested Duty Entry ID (optional)", validators=[Optional()])
    reason = TextAreaField("Reason", validators=[DataRequired(), Length(max=2000)])
