from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.modules.auth.models import User


def _consultant_choices():
    choices = [("", "-- None --")]
    users = User.query.filter_by(is_archived=False, is_active_account=True).order_by(
        User.full_name.asc()
    )
    for user in users:
        role_name = user.role.name if user.role else "no role"
        choices.append((str(user.id), f"{user.full_name} ({role_name})"))
    return choices


class SectionEditForm(FlaskForm):
    content = TextAreaField("Content", validators=[Optional()])
    submit = SubmitField("Save Section")


class SupervisingConsultantForm(FlaskForm):
    supervising_consultant_id = SelectField(
        "Supervising Consultant", choices=[], validators=[Optional()]
    )
    submit = SubmitField("Save")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supervising_consultant_id.choices = _consultant_choices()


class ArchiveReportForm(FlaskForm):
    reason = StringField("Reason (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Archive Report")
