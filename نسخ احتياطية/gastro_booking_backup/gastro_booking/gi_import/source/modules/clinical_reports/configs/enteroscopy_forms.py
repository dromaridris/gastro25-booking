from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import Optional

from app.modules.clinical_reports.vocabulary import vocabulary_choices

YES_NO_CHOICES = [
    ("", "-- Select --"),
    ("Yes", "Yes"),
    ("No", "No"),
    ("Unknown", "Unknown"),
]


FINDING_SEGMENT_KEYS = ("jejunum", "ileum")


class EnteroscopyContextForm(FlaskForm):
    indication_detail = TextAreaField("Indication detail", validators=[Optional()])
    urgency = SelectField("Urgency", choices=[], validators=[Optional()])
    consent_obtained = SelectField("Consent obtained", choices=[], validators=[Optional()])
    prior_surgery = SelectField("Prior GI surgery", choices=[], validators=[Optional()])
    estimated_location = StringField("Estimated lesion location", validators=[Optional()])
    submit = SubmitField("Save Context")

class EnteroscopyApproachForm(FlaskForm):
    approach_type = SelectField("Approach", choices=[], validators=[Optional()])
    device_type = SelectField("Device type", choices=[], validators=[Optional()])
    max_depth_reached = SelectField("Maximum depth reached", choices=[], validators=[Optional()])
    total_enteroscopy_achieved = SelectField("Total enteroscopy achieved", choices=[], validators=[Optional()])
    submit = SubmitField("Save Approach")

class EnteroscopyFindingsForm(FlaskForm):
    jejunum_normal = SelectField("Jejunum — normal", choices=[], validators=[Optional()])
    jejunum_detail = TextAreaField("Jejunum — detail", validators=[Optional()])
    ileum_normal = SelectField("Ileum — normal", choices=[], validators=[Optional()])
    ileum_detail = TextAreaField("Ileum — detail", validators=[Optional()])
    submit = SubmitField("Save Findings")

class EnteroscopyInterventionsForm(FlaskForm):
    submit = SubmitField("Save Interventions")

from app.modules.clinical_reports.configs.colonoscopy_v2_forms import extract_interventions_from_form

class EnteroscopyClosureForm(FlaskForm):
    procedure_completed = SelectField("Procedure completed as planned", choices=[], validators=[Optional()])
    immediate_complication = SelectField("Immediate complication", choices=[], validators=[Optional()])
    complication_detail = TextAreaField("Complication detail", validators=[Optional()])
    specimens_sent = SelectField("Specimens sent", choices=[], validators=[Optional()])
    specimen_details = TextAreaField("Specimen details", validators=[Optional()])
    submit = SubmitField("Save Closure")

class EnteroscopySynthesisForm(FlaskForm):
    impression_primary = TextAreaField("Primary impression", validators=[Optional()])
    clinical_plan = TextAreaField("Recommendations / clinical plan", validators=[Optional()])
    reenteroscopy_needed = SelectField("Re-enteroscopy needed", choices=[], validators=[Optional()])
    addendum_text = TextAreaField("Addendum", validators=[Optional()])
    submit = SubmitField("Save Synthesis")

class EnteroscopyTimelineForm(FlaskForm):
    submit = SubmitField("Save Timeline")


def populate_form_choices(form) -> None:
    for name, field in form._fields.items():
        if not isinstance(field, SelectField):
            continue
        vocab = _FIELD_VOCAB.get(name)
        if vocab:
            field.choices = vocabulary_choices(vocab)
        elif name.endswith("_normal") or name in _YES_NO_FIELDS:
            field.choices = YES_NO_CHOICES

_YES_NO_FIELDS = {
    "consent_obtained", "prior_surgery", "total_enteroscopy_achieved", "reenteroscopy_needed",
    "procedure_completed", "immediate_complication", "specimens_sent",
}

_FIELD_VOCAB = {
    "urgency": "procedure_urgency",
    "approach_type": "enteroscopy_approach",
    "device_type": "enteroscopy_device_type",
    "max_depth_reached": "enteroscopy_max_depth",
}

def bind_context_form(form: EnteroscopyContextForm, data: dict) -> None:
    populate_form_choices(form)
    form.indication_detail.data = data.get("indication_detail") or ""
    form.urgency.data = data.get("urgency") or ""
    form.consent_obtained.data = data.get("consent_obtained") or ""
    form.prior_surgery.data = data.get("prior_surgery") or ""
    form.estimated_location.data = data.get("estimated_location") or ""

def bind_approach_form(form: EnteroscopyApproachForm, data: dict) -> None:
    populate_form_choices(form)
    form.approach_type.data = data.get("approach_type") or ""
    form.device_type.data = data.get("device_type") or ""
    form.max_depth_reached.data = data.get("max_depth_reached") or ""
    form.total_enteroscopy_achieved.data = data.get("total_enteroscopy_achieved") or ""

def bind_findings_form(form: EnteroscopyFindingsForm, data: dict) -> None:
    for key in FINDING_SEGMENT_KEYS:
        if hasattr(form, f"{key}_normal"):
            getattr(form, f"{key}_normal").data = data.get(f"{key}_normal") or ""
        if hasattr(form, f"{key}_detail"):
            getattr(form, f"{key}_detail").data = data.get(f"{key}_detail") or ""

def bind_closure_form(form: EnteroscopyClosureForm, data: dict) -> None:
    populate_form_choices(form)
    form.procedure_completed.data = data.get("procedure_completed") or ""
    form.immediate_complication.data = data.get("immediate_complication") or ""
    form.complication_detail.data = data.get("complication_detail") or ""
    form.specimens_sent.data = data.get("specimens_sent") or ""
    form.specimen_details.data = data.get("specimen_details") or ""

def bind_synthesis_form(form: EnteroscopySynthesisForm, data: dict) -> None:
    populate_form_choices(form)
    form.impression_primary.data = data.get("impression_primary") or ""
    form.clinical_plan.data = data.get("clinical_plan") or ""
    form.reenteroscopy_needed.data = data.get("reenteroscopy_needed") or ""
    form.addendum_text.data = data.get("addendum_text") or ""
