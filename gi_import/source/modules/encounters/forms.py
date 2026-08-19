"""Encounter forms."""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import Optional

from app.modules.encounters.models import ALL_ENCOUNTER_TYPES, ENCOUNTER_TYPE_OPD

ENCOUNTER_TYPE_CHOICES = [
    ("", "-- Select --"),
    *((t, t.replace("_", " ").title()) for t in ALL_ENCOUNTER_TYPES),
]


class EncounterForm(FlaskForm):
    encounter_type = SelectField(
        "Encounter type",
        choices=ENCOUNTER_TYPE_CHOICES,
        default=ENCOUNTER_TYPE_OPD,
        validators=[Optional()],
    )
    summary = StringField("Summary (optional)", validators=[Optional()])
    submit = SubmitField("Start encounter")
