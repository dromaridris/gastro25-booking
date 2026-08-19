"""Clinical History forms."""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional


class ChiefComplaintForm(FlaskForm):
    complaint_code = SelectField("Chief complaint", choices=[], validators=[DataRequired()])
    submit = SubmitField("Start adaptive interview")


class HistoryAnswerForm(FlaskForm):
    submit = SubmitField("Save and continue")


class NarrativeSectionForm(FlaskForm):
    text = TextAreaField("Text", validators=[DataRequired()])
    submit = SubmitField("Save section")


class ConfirmDiagnosisForm(FlaskForm):
    diagnosis_code = SelectField("Working diagnosis (consultant confirmation)", choices=[], validators=[DataRequired()])
    submit = SubmitField("Confirm diagnosis")


class FollowUpForm(FlaskForm):
    narrative_text = TextAreaField("Follow-up note", validators=[DataRequired()])
    submit = SubmitField("Record follow-up")
