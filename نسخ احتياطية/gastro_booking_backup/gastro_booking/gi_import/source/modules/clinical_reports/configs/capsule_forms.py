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


FINDING_SEGMENT_KEYS = ("oesophagus", "duodenum", "jejunum", "ileum", "colon")


class CapsuleContextForm(FlaskForm):
    indication_detail = TextAreaField("Indication detail", validators=[Optional()])
    urgency = SelectField("Urgency", choices=[], validators=[Optional()])
    consent_obtained = SelectField("Consent obtained", choices=[], validators=[Optional()])
    prior_gi_surgery = SelectField("Prior GI surgery", choices=[], validators=[Optional()])
    pacemaker_implant = SelectField("Pacemaker / implantable device", choices=[], validators=[Optional()])
    swallowing_difficulty = SelectField("Swallowing difficulty", choices=[], validators=[Optional()])
    submit = SubmitField("Save Context")

class CapsuleAcquisitionForm(FlaskForm):
    prep_regimen = SelectField("Bowel preparation regimen", choices=[], validators=[Optional()])
    prokinetic_given = SelectField("Prokinetic given", choices=[], validators=[Optional()])
    patency_result = SelectField("Patency capsule result", choices=[], validators=[Optional()])
    capsule_type = SelectField("Capsule type", choices=[], validators=[Optional()])
    completion_status = SelectField("Study completion", choices=[], validators=[Optional()])
    gastric_transit_hours = StringField("Gastric transit (hours)", validators=[Optional()])
    submit = SubmitField("Save Acquisition")

class CapsuleSupplementaryForm(FlaskForm):
    notes = TextAreaField("Supplementary notes", validators=[Optional()])
    submit = SubmitField("Save Supplementary")

class CapsuleFindingsForm(FlaskForm):
    oesophagus_normal = SelectField("Oesophagus — normal", choices=[], validators=[Optional()])
    oesophagus_detail = TextAreaField("Oesophagus — detail", validators=[Optional()])
    duodenum_normal = SelectField("Duodenum — normal", choices=[], validators=[Optional()])
    duodenum_detail = TextAreaField("Duodenum — detail", validators=[Optional()])
    jejunum_normal = SelectField("Jejunum — normal", choices=[], validators=[Optional()])
    jejunum_detail = TextAreaField("Jejunum — detail", validators=[Optional()])
    ileum_normal = SelectField("Ileum — normal", choices=[], validators=[Optional()])
    ileum_detail = TextAreaField("Ileum — detail", validators=[Optional()])
    colon_normal = SelectField("Colon — normal", choices=[], validators=[Optional()])
    colon_detail = TextAreaField("Colon — detail", validators=[Optional()])
    submit = SubmitField("Save Findings")

class CapsuleClosureForm(FlaskForm):
    procedure_completed = SelectField("Procedure completed as planned", choices=[], validators=[Optional()])
    immediate_complication = SelectField("Immediate complication", choices=[], validators=[Optional()])
    complication_detail = TextAreaField("Complication detail", validators=[Optional()])
    specimens_sent = SelectField("Specimens sent", choices=[], validators=[Optional()])
    specimen_details = TextAreaField("Specimen details", validators=[Optional()])
    retention_risk = SelectField("Capsule retention risk", choices=[], validators=[Optional()])
    submit = SubmitField("Save Closure")

class CapsuleSynthesisForm(FlaskForm):
    impression_primary = TextAreaField("Primary impression", validators=[Optional()])
    clinical_plan = TextAreaField("Recommendations / clinical plan", validators=[Optional()])
    addendum_text = TextAreaField("Addendum", validators=[Optional()])
    submit = SubmitField("Save Synthesis")

class CapsuleTimelineForm(FlaskForm):
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
    "consent_obtained", "prior_gi_surgery", "pacemaker_implant", "swallowing_difficulty",
    "prokinetic_given", "patency_result", "procedure_completed", "immediate_complication", "specimens_sent",
}

_FIELD_VOCAB = {
    "urgency": "procedure_urgency",
    "prep_regimen": "bowel_prep_regimen",
    "capsule_type": "capsule_type",
    "completion_status": "capsule_completion_status",
    "retention_risk": "capsule_retention_risk",
}

def bind_context_form(form: CapsuleContextForm, data: dict) -> None:
    populate_form_choices(form)
    form.indication_detail.data = data.get("indication_detail") or ""
    form.urgency.data = data.get("urgency") or ""
    form.consent_obtained.data = data.get("consent_obtained") or ""
    form.prior_gi_surgery.data = data.get("prior_gi_surgery") or ""
    form.pacemaker_implant.data = data.get("pacemaker_implant") or ""
    form.swallowing_difficulty.data = data.get("swallowing_difficulty") or ""

def bind_acquisition_form(form: CapsuleAcquisitionForm, data: dict) -> None:
    populate_form_choices(form)
    form.prep_regimen.data = data.get("prep_regimen") or ""
    form.prokinetic_given.data = data.get("prokinetic_given") or ""
    form.patency_result.data = data.get("patency_result") or ""
    form.capsule_type.data = data.get("capsule_type") or ""
    form.completion_status.data = data.get("completion_status") or ""
    form.gastric_transit_hours.data = data.get("gastric_transit_hours") or ""

def bind_supplementary_form(form: CapsuleSupplementaryForm, data: dict) -> None:
    populate_form_choices(form)
    form.notes.data = data.get("notes") or ""

def bind_findings_form(form: CapsuleFindingsForm, data: dict) -> None:
    for key in FINDING_SEGMENT_KEYS:
        if hasattr(form, f"{key}_normal"):
            getattr(form, f"{key}_normal").data = data.get(f"{key}_normal") or ""
        if hasattr(form, f"{key}_detail"):
            getattr(form, f"{key}_detail").data = data.get(f"{key}_detail") or ""

def bind_closure_form(form: CapsuleClosureForm, data: dict) -> None:
    populate_form_choices(form)
    form.procedure_completed.data = data.get("procedure_completed") or ""
    form.immediate_complication.data = data.get("immediate_complication") or ""
    form.complication_detail.data = data.get("complication_detail") or ""
    form.specimens_sent.data = data.get("specimens_sent") or ""
    form.specimen_details.data = data.get("specimen_details") or ""
    form.retention_risk.data = data.get("retention_risk") or ""

def bind_synthesis_form(form: CapsuleSynthesisForm, data: dict) -> None:
    populate_form_choices(form)
    form.impression_primary.data = data.get("impression_primary") or ""
    form.clinical_plan.data = data.get("clinical_plan") or ""
    form.addendum_text.data = data.get("addendum_text") or ""
