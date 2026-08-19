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


FINDING_SEGMENT_KEYS = ("pancreas", "bile_duct", "mediastinal", "rectal")


class EusContextForm(FlaskForm):
    indication_detail = TextAreaField("Indication detail", validators=[Optional()])
    urgency = SelectField("Urgency", choices=[], validators=[Optional()])
    consent_obtained = SelectField("Consent obtained", choices=[], validators=[Optional()])
    anticoagulation = SelectField("Anticoagulation / antiplatelet therapy", choices=[], validators=[Optional()])
    targeted_lesion = TextAreaField("Targeted lesion description", validators=[Optional()])
    submit = SubmitField("Save Context")

class EusTechniqueForm(FlaskForm):
    scope_type = SelectField("Scope type", choices=[], validators=[Optional()])
    frequency = SelectField("Frequency", choices=[], validators=[Optional()])
    doppler_used = SelectField("Doppler used", choices=[], validators=[Optional()])
    contrast_used = SelectField("Contrast used", choices=[], validators=[Optional()])
    target_organ = SelectField("Target organ", choices=[], validators=[Optional()])
    lesion_location = StringField("Lesion location", validators=[Optional()])
    lesion_size_mm = StringField("Lesion size (mm)", validators=[Optional()])
    echo_layer = SelectField("Echo layer", choices=[], validators=[Optional()])
    submit = SubmitField("Save Technique")

class EusSamplingForm(FlaskForm):
    fna_performed = SelectField("FNA / FNB performed", choices=[], validators=[Optional()])
    needle_type = SelectField("Needle type", choices=[], validators=[Optional()])
    pass_count = StringField("Number of passes", validators=[Optional()])
    rose_performed = SelectField("ROSE performed", choices=[], validators=[Optional()])
    cytology_adequacy = SelectField("Cytology adequacy", choices=[], validators=[Optional()])
    submit = SubmitField("Save Sampling")

class EusFindingsForm(FlaskForm):
    pancreas_normal = SelectField("Pancreas — normal", choices=[], validators=[Optional()])
    pancreas_detail = TextAreaField("Pancreas — detail", validators=[Optional()])
    bile_duct_normal = SelectField("Bile duct — normal", choices=[], validators=[Optional()])
    bile_duct_detail = TextAreaField("Bile duct — detail", validators=[Optional()])
    mediastinal_normal = SelectField("Mediastinal — normal", choices=[], validators=[Optional()])
    mediastinal_detail = TextAreaField("Mediastinal — detail", validators=[Optional()])
    rectal_normal = SelectField("Rectal — normal", choices=[], validators=[Optional()])
    rectal_detail = TextAreaField("Rectal — detail", validators=[Optional()])
    submit = SubmitField("Save Findings")

class EusClosureForm(FlaskForm):
    procedure_completed = SelectField("Procedure completed as planned", choices=[], validators=[Optional()])
    immediate_complication = SelectField("Immediate complication", choices=[], validators=[Optional()])
    complication_detail = TextAreaField("Complication detail", validators=[Optional()])
    specimens_sent = SelectField("Specimens sent", choices=[], validators=[Optional()])
    specimen_details = TextAreaField("Specimen details", validators=[Optional()])
    submit = SubmitField("Save Closure")

class EusSynthesisForm(FlaskForm):
    impression_primary = TextAreaField("Primary impression", validators=[Optional()])
    clinical_plan = TextAreaField("Recommendations / clinical plan", validators=[Optional()])
    t_stage = SelectField("T stage (if applicable)", choices=[], validators=[Optional()])
    addendum_text = TextAreaField("Addendum", validators=[Optional()])
    submit = SubmitField("Save Synthesis")

class EusTimelineForm(FlaskForm):
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
    "consent_obtained", "doppler_used", "contrast_used", "fna_performed", "rose_performed",
    "procedure_completed", "immediate_complication", "specimens_sent",
    "prior_gi_surgery", "pacemaker_implant", "swallowing_difficulty", "prokinetic_given",
    "patency_result", "prior_surgery", "total_enteroscopy_achieved", "reenteroscopy_needed",
}

_FIELD_VOCAB = {
    "urgency": "procedure_urgency",
    "anticoagulation": "anticoagulation_status",
    "scope_type": "eus_scope_type",
    "frequency": "eus_frequency",
    "target_organ": "eus_target_organ",
    "echo_layer": "eus_echo_layer",
    "needle_type": "eus_needle_type",
    "cytology_adequacy": "eus_cytology_adequacy",
    "t_stage": "eus_t_stage",
}

def bind_context_form(form: EusContextForm, data: dict) -> None:
    populate_form_choices(form)
    form.indication_detail.data = data.get("indication_detail") or ""
    form.urgency.data = data.get("urgency") or ""
    form.consent_obtained.data = data.get("consent_obtained") or ""
    form.anticoagulation.data = data.get("anticoagulation") or ""
    form.targeted_lesion.data = data.get("targeted_lesion") or ""

def bind_technique_form(form: EusTechniqueForm, data: dict) -> None:
    populate_form_choices(form)
    form.scope_type.data = data.get("scope_type") or ""
    form.frequency.data = data.get("frequency") or ""
    form.doppler_used.data = data.get("doppler_used") or ""
    form.contrast_used.data = data.get("contrast_used") or ""
    form.target_organ.data = data.get("target_organ") or ""
    form.lesion_location.data = data.get("lesion_location") or ""
    form.lesion_size_mm.data = data.get("lesion_size_mm") or ""
    form.echo_layer.data = data.get("echo_layer") or ""

def bind_sampling_form(form: EusSamplingForm, data: dict) -> None:
    populate_form_choices(form)
    form.fna_performed.data = data.get("fna_performed") or ""
    form.needle_type.data = data.get("needle_type") or ""
    form.pass_count.data = data.get("pass_count") or ""
    form.rose_performed.data = data.get("rose_performed") or ""
    form.cytology_adequacy.data = data.get("cytology_adequacy") or ""

def bind_findings_form(form: EusFindingsForm, data: dict) -> None:
    for key in FINDING_SEGMENT_KEYS:
        if hasattr(form, f"{key}_normal"):
            getattr(form, f"{key}_normal").data = data.get(f"{key}_normal") or ""
        if hasattr(form, f"{key}_detail"):
            getattr(form, f"{key}_detail").data = data.get(f"{key}_detail") or ""

def bind_closure_form(form: EusClosureForm, data: dict) -> None:
    populate_form_choices(form)
    form.procedure_completed.data = data.get("procedure_completed") or ""
    form.immediate_complication.data = data.get("immediate_complication") or ""
    form.complication_detail.data = data.get("complication_detail") or ""
    form.specimens_sent.data = data.get("specimens_sent") or ""
    form.specimen_details.data = data.get("specimen_details") or ""

def bind_synthesis_form(form: EusSynthesisForm, data: dict) -> None:
    populate_form_choices(form)
    form.impression_primary.data = data.get("impression_primary") or ""
    form.clinical_plan.data = data.get("clinical_plan") or ""
    form.t_stage.data = data.get("t_stage") or ""
    form.addendum_text.data = data.get("addendum_text") or ""
