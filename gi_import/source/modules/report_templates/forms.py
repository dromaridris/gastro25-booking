from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import Length, Optional

from app.modules.reports.forms import SupervisingConsultantForm, _consultant_choices

YES_NO_CHOICES = [
    ("", "-- Select --"),
    ("Yes", "Yes"),
    ("No", "No"),
    ("Not attempted", "Not attempted"),
]

BBPS_CHOICES = [
    ("", "--"),
    ("0", "0"),
    ("1", "1"),
    ("2", "2"),
    ("3", "3"),
]


class TextSectionForm(FlaskForm):
    content = TextAreaField("Content", validators=[Optional()])
    submit = SubmitField("Save Section")


class ColonoscopyFindingsForm(FlaskForm):
    caecum_reached = SelectField("Caecum reached", choices=YES_NO_CHOICES, validators=[Optional()])
    ileum_intubated = SelectField(
        "Terminal ileum intubated", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    bbps_right = SelectField("BBPS — Right colon", choices=BBPS_CHOICES, validators=[Optional()])
    bbps_transverse = SelectField(
        "BBPS — Transverse colon", choices=BBPS_CHOICES, validators=[Optional()]
    )
    bbps_left = SelectField("BBPS — Left colon", choices=BBPS_CHOICES, validators=[Optional()])
    withdrawal_time_minutes = StringField(
        "Withdrawal time (minutes)", validators=[Optional(), Length(max=20)]
    )
    polyp_findings = TextAreaField("Polyp findings", validators=[Optional()])
    mucosal_findings = TextAreaField("Mucosal findings", validators=[Optional()])
    other_findings = TextAreaField("Other findings", validators=[Optional()])
    submit = SubmitField("Save Findings")


class UpperGiFindingsForm(FlaskForm):
    oesophagus_findings = TextAreaField("Oesophagus", validators=[Optional()])
    stomach_findings = TextAreaField("Stomach", validators=[Optional()])
    duodenum_findings = TextAreaField("Duodenum", validators=[Optional()])
    d2_reached = SelectField("D2 reached", choices=YES_NO_CHOICES, validators=[Optional()])
    other_findings = TextAreaField("Other findings", validators=[Optional()])
    submit = SubmitField("Save Findings")


__all__ = [
    "ColonoscopyFindingsForm",
    "SupervisingConsultantForm",
    "TextSectionForm",
    "UpperGiFindingsForm",
    "_consultant_choices",
]
