"""Upper GI v2 template — WTForms and phase data extraction."""

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


class UpperGiContextForm(FlaskForm):
    indication_detail = TextAreaField("Indication detail", validators=[Optional()])
    urgency = SelectField("Urgency", choices=[], validators=[Optional()])
    consent_obtained = SelectField("Consent obtained", choices=YES_NO_CHOICES, validators=[Optional()])
    anticoagulation = SelectField("Anticoagulation / antiplatelet", choices=[], validators=[Optional()])
    anticoagulation_management = SelectField(
        "Anticoagulation management", choices=[], validators=[Optional()]
    )
    asa_class = SelectField("ASA class", choices=[], validators=[Optional()])
    submit = SubmitField("Save Context")


class UpperGiProcedureForm(FlaskForm):
    scope_type = SelectField("Scope type", choices=[], validators=[Optional()])
    d2_reached = SelectField("D2 reached", choices=YES_NO_CHOICES, validators=[Optional()])
    retroflexion_performed = SelectField(
        "Retroflexion in stomach performed", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    limited_exam = SelectField("Limited examination", choices=YES_NO_CHOICES, validators=[Optional()])
    limited_exam_reason = TextAreaField("Reason for limited examination", validators=[Optional()])
    procedure_duration_min = StringField("Procedure duration (minutes)", validators=[Optional()])
    submit = SubmitField("Save Procedure")


class UpperGiFindingsForm(FlaskForm):
    oesophagus_normal = SelectField("Oesophagus — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    oesophagus_detail = TextAreaField("Oesophagus — detail", validators=[Optional()])
    ge_junction_normal = SelectField(
        "Gastro-oesophageal junction — normal", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    ge_junction_detail = TextAreaField("GE junction — detail", validators=[Optional()])
    stomach_normal = SelectField("Stomach — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    stomach_detail = TextAreaField("Stomach — detail", validators=[Optional()])
    duodenum_normal = SelectField("Duodenum — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    duodenum_detail = TextAreaField("Duodenum — detail", validators=[Optional()])
    submit = SubmitField("Save Findings")


class UpperGiInterventionsForm(FlaskForm):
    submit = SubmitField("Save Interventions")


class UpperGiClosureForm(FlaskForm):
    procedure_completed = SelectField(
        "Procedure completed as planned", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    immediate_complication = SelectField(
        "Immediate complication", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    complication_detail = TextAreaField("Complication detail", validators=[Optional()])
    specimens_sent = SelectField(
        "Specimens sent to histology", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    specimen_details = TextAreaField("Specimen details", validators=[Optional()])
    submit = SubmitField("Save Closure")


class UpperGiSynthesisForm(FlaskForm):
    impression_primary = TextAreaField("Primary impression", validators=[Optional()])
    clinical_plan = TextAreaField("Recommendations / clinical plan", validators=[Optional()])
    surveillance_interval = SelectField("Surveillance interval", choices=[], validators=[Optional()])
    follow_up_procedure = SelectField("Follow-up procedure planned", choices=[], validators=[Optional()])
    addendum_text = TextAreaField("Addendum", validators=[Optional()])
    submit = SubmitField("Save Synthesis")


class UpperGiTimelineForm(FlaskForm):
    submit = SubmitField("Save Timeline")


def populate_form_choices(form) -> None:
    if hasattr(form, "urgency"):
        form.urgency.choices = vocabulary_choices("procedure_urgency")
    if hasattr(form, "anticoagulation"):
        form.anticoagulation.choices = vocabulary_choices("anticoagulation_status")
    if hasattr(form, "anticoagulation_management"):
        form.anticoagulation_management.choices = vocabulary_choices("anticoagulation_management")
    if hasattr(form, "asa_class"):
        form.asa_class.choices = vocabulary_choices("asa_class")
    if hasattr(form, "scope_type"):
        form.scope_type.choices = vocabulary_choices("upper_gi_scope_type")
    if hasattr(form, "surveillance_interval"):
        form.surveillance_interval.choices = vocabulary_choices("surveillance_interval")
    if hasattr(form, "follow_up_procedure"):
        form.follow_up_procedure.choices = vocabulary_choices("follow_up_procedure")


def bind_context_form(form: UpperGiContextForm, data: dict) -> None:
    populate_form_choices(form)
    form.indication_detail.data = data.get("indication_detail") or ""
    form.urgency.data = data.get("urgency") or ""
    form.consent_obtained.data = data.get("consent_obtained") or ""
    form.anticoagulation.data = data.get("anticoagulation") or ""
    form.anticoagulation_management.data = data.get("anticoagulation_management") or ""
    form.asa_class.data = data.get("asa_class") or ""


def bind_procedure_form(form: UpperGiProcedureForm, data: dict) -> None:
    populate_form_choices(form)
    form.scope_type.data = data.get("scope_type") or ""
    form.d2_reached.data = data.get("d2_reached") or ""
    form.retroflexion_performed.data = data.get("retroflexion_performed") or ""
    form.limited_exam.data = data.get("limited_exam") or ""
    form.limited_exam_reason.data = data.get("limited_exam_reason") or ""
    form.procedure_duration_min.data = data.get("procedure_duration_min") or ""


def bind_findings_form(form: UpperGiFindingsForm, data: dict) -> None:
    form.oesophagus_normal.data = data.get("oesophagus_normal") or ""
    form.oesophagus_detail.data = data.get("oesophagus_detail") or ""
    form.ge_junction_normal.data = data.get("ge_junction_normal") or ""
    form.ge_junction_detail.data = data.get("ge_junction_detail") or ""
    form.stomach_normal.data = data.get("stomach_normal") or ""
    form.stomach_detail.data = data.get("stomach_detail") or ""
    form.duodenum_normal.data = data.get("duodenum_normal") or ""
    form.duodenum_detail.data = data.get("duodenum_detail") or ""


def bind_closure_form(form: UpperGiClosureForm, data: dict) -> None:
    form.procedure_completed.data = data.get("procedure_completed") or ""
    form.immediate_complication.data = data.get("immediate_complication") or ""
    form.complication_detail.data = data.get("complication_detail") or ""
    form.specimens_sent.data = data.get("specimens_sent") or ""
    form.specimen_details.data = data.get("specimen_details") or ""


def bind_synthesis_form(form: UpperGiSynthesisForm, data: dict) -> None:
    populate_form_choices(form)
    form.impression_primary.data = data.get("impression_primary") or ""
    form.clinical_plan.data = data.get("clinical_plan") or ""
    form.surveillance_interval.data = data.get("surveillance_interval") or ""
    form.follow_up_procedure.data = data.get("follow_up_procedure") or ""
    form.addendum_text.data = data.get("addendum_text") or ""


def extract_interventions_from_form(form_data) -> list[dict]:
    """Parse repeatable intervention rows from POST data."""
    row_indices = set()
    for key in form_data:
        if key.startswith("intervention_type_"):
            try:
                row_indices.add(int(key.rsplit("_", 1)[-1]))
            except ValueError:
                continue
    interventions = []
    for idx in sorted(row_indices):
        itype = form_data.get(f"intervention_type_{idx}", "").strip()
        success = form_data.get(f"success_{idx}", "").strip()
        details = form_data.get(f"details_{idx}", "").strip()
        if not itype and not success and not details:
            continue
        interventions.append(
            {
                "intervention_type": itype,
                "success": success,
                "details": details,
            }
        )
    return interventions
