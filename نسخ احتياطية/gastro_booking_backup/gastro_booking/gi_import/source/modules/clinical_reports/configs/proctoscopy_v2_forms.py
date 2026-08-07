"""Proctoscopy v2 — WTForms and phase data extraction."""

from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, TextAreaField
from wtforms.validators import Optional

from app.modules.clinical_reports.configs.colonoscopy_v2_forms import extract_interventions_from_form
from app.modules.clinical_reports.vocabulary import vocabulary_choices

YES_NO_CHOICES = [
    ("", "-- Select --"),
    ("Yes", "Yes"),
    ("No", "No"),
    ("Unknown", "Unknown"),
]

FINDING_SEGMENT_KEYS = ("rectum", "anus")


class ProctoscopyContextForm(FlaskForm):
    indication_detail = TextAreaField("Indication detail", validators=[Optional()])
    urgency = SelectField("Urgency", choices=[], validators=[Optional()])
    consent_obtained = SelectField("Consent obtained", choices=YES_NO_CHOICES, validators=[Optional()])
    submit = SubmitField("Save Context")


class ProctoscopyProcedureForm(FlaskForm):
    scope_type = SelectField("Scope type", choices=[], validators=[Optional()])
    exam_completed = SelectField("Examination completed as planned", choices=YES_NO_CHOICES, validators=[Optional()])
    limited_exam = SelectField("Limited examination", choices=YES_NO_CHOICES, validators=[Optional()])
    limited_exam_reason = TextAreaField("Reason for limited examination", validators=[Optional()])
    submit = SubmitField("Save Procedure")


class ProctoscopyFindingsForm(FlaskForm):
    rectum_normal = SelectField("Rectum — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    rectum_detail = TextAreaField("Rectum — detail", validators=[Optional()])
    anus_normal = SelectField("Anus — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    anus_detail = TextAreaField("Anus — detail", validators=[Optional()])
    submit = SubmitField("Save Findings")


class ProctoscopyInterventionsForm(FlaskForm):
    submit = SubmitField("Save Interventions")


class ProctoscopyClosureForm(FlaskForm):
    procedure_completed = SelectField("Procedure completed as planned", choices=YES_NO_CHOICES, validators=[Optional()])
    immediate_complication = SelectField("Immediate complication", choices=YES_NO_CHOICES, validators=[Optional()])
    complication_detail = TextAreaField("Complication detail", validators=[Optional()])
    submit = SubmitField("Save Closure")


class ProctoscopySynthesisForm(FlaskForm):
    impression_primary = TextAreaField("Primary impression", validators=[Optional()])
    clinical_plan = TextAreaField("Recommendations / clinical plan", validators=[Optional()])
    addendum_text = TextAreaField("Addendum", validators=[Optional()])
    submit = SubmitField("Save Synthesis")


class ProctoscopyTimelineForm(FlaskForm):
    submit = SubmitField("Save Timeline")


def populate_form_choices(form) -> None:
    if hasattr(form, "urgency"):
        form.urgency.choices = vocabulary_choices("procedure_urgency")
    if hasattr(form, "scope_type"):
        form.scope_type.choices = vocabulary_choices("proctoscopy_scope_type")


def bind_context_form(form: ProctoscopyContextForm, data: dict) -> None:
    populate_form_choices(form)
    form.indication_detail.data = data.get("indication_detail") or ""
    form.urgency.data = data.get("urgency") or ""
    form.consent_obtained.data = data.get("consent_obtained") or ""


def bind_procedure_form(form: ProctoscopyProcedureForm, data: dict) -> None:
    populate_form_choices(form)
    form.scope_type.data = data.get("scope_type") or ""
    form.exam_completed.data = data.get("exam_completed") or ""
    form.limited_exam.data = data.get("limited_exam") or ""
    form.limited_exam_reason.data = data.get("limited_exam_reason") or ""


def bind_findings_form(form: ProctoscopyFindingsForm, data: dict) -> None:
    form.rectum_normal.data = data.get("rectum_normal") or ""
    form.rectum_detail.data = data.get("rectum_detail") or ""
    form.anus_normal.data = data.get("anus_normal") or ""
    form.anus_detail.data = data.get("anus_detail") or ""


def bind_closure_form(form: ProctoscopyClosureForm, data: dict) -> None:
    form.procedure_completed.data = data.get("procedure_completed") or ""
    form.immediate_complication.data = data.get("immediate_complication") or ""
    form.complication_detail.data = data.get("complication_detail") or ""


def bind_synthesis_form(form: ProctoscopySynthesisForm, data: dict) -> None:
    form.impression_primary.data = data.get("impression_primary") or ""
    form.clinical_plan.data = data.get("clinical_plan") or ""
    form.addendum_text.data = data.get("addendum_text") or ""
