"""Medication forms."""

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional

from app.modules.medications.models import ALL_ENTRY_TYPES, ENTRY_TYPE_HOME


class MedicationEntryForm(FlaskForm):
    catalogue_item_id = SelectField("Medication", choices=[], coerce=int, validators=[DataRequired()])
    entry_type = SelectField(
        "Entry type",
        choices=[(t, t.replace("_", " ").title()) for t in ALL_ENTRY_TYPES],
        default=ENTRY_TYPE_HOME,
        validators=[DataRequired()],
    )
    dose_text = StringField("Dose", validators=[Optional()])
    route = StringField("Route", validators=[Optional()])
    frequency_text = StringField("Frequency", validators=[Optional()])
    indication = TextAreaField("Indication", validators=[Optional()])
    started_on = DateField("Started on", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save medication entry")
    save_as_draft = SubmitField("Save as draft")
