"""Branding forms — setup wizard and settings."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, HiddenField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.modules.branding.constants import THEME_MODES


class SetupWizardForm(FlaskForm):
    hospital_name = StringField("Hospital Name", validators=[DataRequired(), Length(max=200)])
    department_name = StringField("Department Name", validators=[DataRequired(), Length(max=200)])
    hospital_logo = FileField(
        "Hospital Logo",
        validators=[
            DataRequired(),
            FileAllowed(["png", "jpg", "jpeg", "gif", "webp", "svg"], "Images only"),
        ],
    )
    department_logo = FileField(
        "Department Logo (optional)",
        validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif", "webp", "svg"], "Images only")],
    )
    primary_color = StringField("Primary Colour", validators=[Optional(), Length(max=7)])
    secondary_color = StringField("Secondary Colour", validators=[Optional(), Length(max=7)])
    accent_color = StringField("Accent Colour", validators=[Optional(), Length(max=7)])
    slogan = TextAreaField("Hospital Slogan (optional)", validators=[Optional(), Length(max=255)])
    suggested_slogan = HiddenField()
    use_suggested_slogan = BooleanField("Use suggested slogan")
    submit = SubmitField("Complete Setup")


class BrandingSettingsForm(FlaskForm):
    hospital_name = StringField("Hospital Name", validators=[DataRequired(), Length(max=200)])
    department_name = StringField("Department Name", validators=[DataRequired(), Length(max=200)])
    hospital_logo = FileField(
        "Replace Hospital Logo",
        validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif", "webp", "svg"], "Images only")],
    )
    department_logo = FileField(
        "Replace Department Logo",
        validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif", "webp", "svg"], "Images only")],
    )
    remove_department_logo = BooleanField("Remove department logo")
    primary_color = StringField("Primary Colour", validators=[DataRequired(), Length(max=7)])
    secondary_color = StringField("Secondary Colour", validators=[DataRequired(), Length(max=7)])
    accent_color = StringField("Accent Colour", validators=[DataRequired(), Length(max=7)])
    slogan = TextAreaField("Slogan", validators=[Optional(), Length(max=255)])
    theme_mode = SelectField(
        "Theme Mode",
        choices=[(m, m.title()) for m in THEME_MODES],
        validators=[DataRequired()],
    )
    submit = SubmitField("Save Branding")
