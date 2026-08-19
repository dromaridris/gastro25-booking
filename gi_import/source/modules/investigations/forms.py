"""Investigation forms."""

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from app.modules.investigations.models import ORDER_KIND_IMAGING, ORDER_KIND_LABORATORY


class LabOrderForm(FlaskForm):
    panel_id = SelectField("Panel (optional)", choices=[], coerce=int, validators=[Optional()])
    clinical_indication = TextAreaField("Clinical indication", validators=[Optional()])
    priority = SelectField(
        "Priority",
        choices=[("routine", "Routine"), ("urgent", "Urgent")],
        validators=[Optional()],
    )
    submit = SubmitField("Place laboratory order")


class ImagingOrderForm(FlaskForm):
    catalogue_item_id = SelectField("Imaging modality", choices=[], coerce=int, validators=[DataRequired()])
    clinical_indication = TextAreaField("Clinical indication", validators=[Optional()])
    priority = SelectField(
        "Priority",
        choices=[("routine", "Routine"), ("urgent", "Urgent")],
        validators=[Optional()],
    )
    submit = SubmitField("Place imaging order")


class LabResultForm(FlaskForm):
    submit = SubmitField("Save laboratory values")
    mark_available = SubmitField("Save and mark available")


class ImagingStudyForm(FlaskForm):
    catalogue_item_id = SelectField("Modality", choices=[], coerce=int, validators=[DataRequired()])
    study_date = DateField("Study date", validators=[DataRequired()])
    body_region = StringField("Body region", validators=[Optional()])
    findings_summary = TextAreaField("Findings summary", validators=[Optional()])
    impression = TextAreaField("Impression", validators=[Optional()])
    submit = SubmitField("Save imaging study")
    mark_available = SubmitField("Save and mark available")
