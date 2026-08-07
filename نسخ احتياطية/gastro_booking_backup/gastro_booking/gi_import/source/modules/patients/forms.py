from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

SEX_CHOICES = [
    ("female", "Female"),
    ("male", "Male"),
    ("other", "Other"),
    ("unknown", "Unknown"),
]


class PatientForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired(), Length(max=100)])
    last_name = StringField("Last name", validators=[DataRequired(), Length(max=100)])
    date_of_birth = DateField("Date of birth", validators=[DataRequired()])
    sex = SelectField("Sex", choices=SEX_CHOICES, validators=[DataRequired()])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=255)])
    address = StringField("Address", validators=[Optional(), Length(max=255)])
    national_id = StringField("National ID (optional)", validators=[Optional(), Length(max=50)])
    emergency_contact_name = StringField(
        "Emergency contact name", validators=[Optional(), Length(max=150)]
    )
    emergency_contact_phone = StringField(
        "Emergency contact phone", validators=[Optional(), Length(max=30)]
    )
    submit = SubmitField("Save")


class PatientSearchForm(FlaskForm):
    """GET-based search — no CSRF needed for a read-only query, but kept
    as a FlaskForm for consistent validation/rendering with the rest of
    the app."""

    class Meta:
        csrf = False

    q = StringField("Search by name or MRN", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Search")


class ArchivePatientForm(FlaskForm):
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Archive")
