"""Flex sig v2 — WTForms and phase data extraction."""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import Optional

from app.modules.clinical_reports.configs.colonoscopy_v2_forms import extract_interventions_from_form
from app.modules.clinical_reports.vocabulary import vocabulary_choices

YES_NO_CHOICES = [
    ("", "-- Select --"),
    ("Yes", "Yes"),
    ("No", "No"),
    ("Unknown", "Unknown"),
]

FINDING_SEGMENT_KEYS = ("descending", "sigmoid", "rectum")


class FlexSigContextForm(FlaskForm):
    indication_detail = TextAreaField("Indication detail", validators=[Optional()])
    urgency = SelectField("Urgency", choices=[], validators=[Optional()])
    consent_obtained = SelectField("Consent obtained", choices=YES_NO_CHOICES, validators=[Optional()])
    submit = SubmitField("Save Context")


class FlexSigProcedureForm(FlaskForm):
    scope_type = SelectField("Scope type", choices=[], validators=[Optional()])
    scope_limit_reached = SelectField("Scope limit reached", choices=[], validators=[Optional()])
    prep_regimen = SelectField("Bowel preparation regimen", choices=[], validators=[Optional()])
    limited_exam = SelectField("Limited examination", choices=YES_NO_CHOICES, validators=[Optional()])
    limited_exam_reason = TextAreaField("Reason for limited examination", validators=[Optional()])
    submit = SubmitField("Save Procedure")


class FlexSigFindingsForm(FlaskForm):
    descending_normal = SelectField("Descending colon — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    descending_detail = TextAreaField("Descending colon — detail", validators=[Optional()])
    sigmoid_normal = SelectField("Sigmoid colon — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    sigmoid_detail = TextAreaField("Sigmoid colon — detail", validators=[Optional()])
    rectum_normal = SelectField("Rectum — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    rectum_detail = TextAreaField("Rectum — detail", validators=[Optional()])
    submit = SubmitField("Save Findings")


class FlexSigInterventionsForm(FlaskForm):
    submit = SubmitField("Save Interventions")


class FlexSigClosureForm(FlaskForm):
    procedure_completed = SelectField("Procedure completed as planned", choices=YES_NO_CHOICES, validators=[Optional()])
    immediate_complication = SelectField("Immediate complication", choices=YES_NO_CHOICES, validators=[Optional()])
    complication_detail = TextAreaField("Complication detail", validators=[Optional()])
    specimens_sent = SelectField("Specimens sent to histology", choices=YES_NO_CHOICES, validators=[Optional()])
    specimen_details = TextAreaField("Specimen details", validators=[Optional()])
    submit = SubmitField("Save Closure")


class FlexSigSynthesisForm(FlaskForm):
    impression_primary = TextAreaField("Primary impression", validators=[Optional()])
    clinical_plan = TextAreaField("Recommendations / clinical plan", validators=[Optional()])
    surveillance_interval = SelectField("Surveillance interval", choices=[], validators=[Optional()])
    addendum_text = TextAreaField("Addendum", validators=[Optional()])
    submit = SubmitField("Save Synthesis")


class FlexSigTimelineForm(FlaskForm):
    submit = SubmitField("Save Timeline")


def populate_form_choices(form) -> None:
    if hasattr(form, "urgency"):
        form.urgency.choices = vocabulary_choices("procedure_urgency")
    if hasattr(form, "scope_type"):
        form.scope_type.choices = vocabulary_choices("flex_sig_scope_type")
    if hasattr(form, "scope_limit_reached"):
        form.scope_limit_reached.choices = vocabulary_choices("flex_sig_scope_limit")
    if hasattr(form, "prep_regimen"):
        form.prep_regimen.choices = vocabulary_choices("bowel_prep_regimen")
    if hasattr(form, "surveillance_interval"):
        form.surveillance_interval.choices = vocabulary_choices("surveillance_interval")


def bind_context_form(form: FlexSigContextForm, data: dict) -> None:
    populate_form_choices(form)
    form.indication_detail.data = data.get("indication_detail") or ""
    form.urgency.data = data.get("urgency") or ""
    form.consent_obtained.data = data.get("consent_obtained") or ""


def bind_procedure_form(form: FlexSigProcedureForm, data: dict) -> None:
    populate_form_choices(form)
    form.scope_type.data = data.get("scope_type") or ""
    form.scope_limit_reached.data = data.get("scope_limit_reached") or ""
    form.prep_regimen.data = data.get("prep_regimen") or ""
    form.limited_exam.data = data.get("limited_exam") or ""
    form.limited_exam_reason.data = data.get("limited_exam_reason") or ""


def bind_findings_form(form: FlexSigFindingsForm, data: dict) -> None:
    for key in FINDING_SEGMENT_KEYS:
        if hasattr(form, f"{key}_normal"):
            getattr(form, f"{key}_normal").data = data.get(f"{key}_normal") or ""
        if hasattr(form, f"{key}_detail"):
            getattr(form, f"{key}_detail").data = data.get(f"{key}_detail") or ""


def bind_closure_form(form: FlexSigClosureForm, data: dict) -> None:
    form.procedure_completed.data = data.get("procedure_completed") or ""
    form.immediate_complication.data = data.get("immediate_complication") or ""
    form.complication_detail.data = data.get("complication_detail") or ""
    form.specimens_sent.data = data.get("specimens_sent") or ""
    form.specimen_details.data = data.get("specimen_details") or ""


def bind_synthesis_form(form: FlexSigSynthesisForm, data: dict) -> None:
    populate_form_choices(form)
    form.impression_primary.data = data.get("impression_primary") or ""
    form.clinical_plan.data = data.get("clinical_plan") or ""
    form.surveillance_interval.data = data.get("surveillance_interval") or ""
    form.addendum_text.data = data.get("addendum_text") or ""
