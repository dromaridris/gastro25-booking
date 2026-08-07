"""Colonoscopy v2 template — WTForms and phase data extraction."""

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

FINDING_SEGMENT_KEYS = (
    "terminal_ileum",
    "caecum",
    "ascending",
    "transverse",
    "descending",
    "sigmoid",
    "rectum",
    "anus",
)


class ColonoscopyContextForm(FlaskForm):
    indication_detail = TextAreaField("Indication detail", validators=[Optional()])
    urgency = SelectField("Urgency", choices=[], validators=[Optional()])
    consent_obtained = SelectField("Consent obtained", choices=YES_NO_CHOICES, validators=[Optional()])
    anticoagulation = SelectField("Anticoagulation / antiplatelet", choices=[], validators=[Optional()])
    anticoagulation_management = SelectField(
        "Anticoagulation management", choices=[], validators=[Optional()]
    )
    asa_class = SelectField("ASA class", choices=[], validators=[Optional()])
    submit = SubmitField("Save Context")


class ColonoscopyProcedureForm(FlaskForm):
    scope_type = SelectField("Scope type", choices=[], validators=[Optional()])
    caecum_reached = SelectField("Caecum reached", choices=YES_NO_CHOICES, validators=[Optional()])
    ti_intubated = SelectField("Terminal ileum intubated", choices=YES_NO_CHOICES, validators=[Optional()])
    withdrawal_time_min = StringField("Withdrawal time (minutes)", validators=[Optional()])
    bbps_right = SelectField("BBPS — right colon", choices=[], validators=[Optional()])
    bbps_transverse = SelectField("BBPS — transverse colon", choices=[], validators=[Optional()])
    bbps_left = SelectField("BBPS — left colon", choices=[], validators=[Optional()])
    prep_regimen = SelectField("Bowel preparation regimen", choices=[], validators=[Optional()])
    limited_exam = SelectField("Limited examination", choices=YES_NO_CHOICES, validators=[Optional()])
    limited_exam_reason = TextAreaField("Reason for limited examination", validators=[Optional()])
    submit = SubmitField("Save Procedure")


class ColonoscopyFindingsForm(FlaskForm):
    terminal_ileum_normal = SelectField("Terminal ileum — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    terminal_ileum_detail = TextAreaField("Terminal ileum — detail", validators=[Optional()])
    caecum_normal = SelectField("Caecum — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    caecum_detail = TextAreaField("Caecum — detail", validators=[Optional()])
    ascending_normal = SelectField("Ascending colon — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    ascending_detail = TextAreaField("Ascending colon — detail", validators=[Optional()])
    transverse_normal = SelectField("Transverse colon — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    transverse_detail = TextAreaField("Transverse colon — detail", validators=[Optional()])
    descending_normal = SelectField("Descending colon — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    descending_detail = TextAreaField("Descending colon — detail", validators=[Optional()])
    sigmoid_normal = SelectField("Sigmoid colon — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    sigmoid_detail = TextAreaField("Sigmoid colon — detail", validators=[Optional()])
    rectum_normal = SelectField("Rectum — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    rectum_detail = TextAreaField("Rectum — detail", validators=[Optional()])
    anus_normal = SelectField("Anus — normal", choices=YES_NO_CHOICES, validators=[Optional()])
    anus_detail = TextAreaField("Anus — detail", validators=[Optional()])
    submit = SubmitField("Save Findings")


class ColonoscopyInterventionsForm(FlaskForm):
    submit = SubmitField("Save Interventions")


class ColonoscopyClosureForm(FlaskForm):
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


class ColonoscopySynthesisForm(FlaskForm):
    impression_primary = TextAreaField("Primary impression", validators=[Optional()])
    clinical_plan = TextAreaField("Recommendations / clinical plan", validators=[Optional()])
    surveillance_interval = SelectField("Surveillance interval", choices=[], validators=[Optional()])
    follow_up_procedure = SelectField("Follow-up procedure planned", choices=[], validators=[Optional()])
    addendum_text = TextAreaField("Addendum", validators=[Optional()])
    submit = SubmitField("Save Synthesis")


class ColonoscopyTimelineForm(FlaskForm):
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
        form.scope_type.choices = vocabulary_choices("colonoscopy_scope_type")
    for attr in ("bbps_right", "bbps_transverse", "bbps_left"):
        if hasattr(form, attr):
            getattr(form, attr).choices = vocabulary_choices("bbps_score")
    if hasattr(form, "prep_regimen"):
        form.prep_regimen.choices = vocabulary_choices("bowel_prep_regimen")
    if hasattr(form, "surveillance_interval"):
        form.surveillance_interval.choices = vocabulary_choices("surveillance_interval")
    if hasattr(form, "follow_up_procedure"):
        form.follow_up_procedure.choices = vocabulary_choices("follow_up_procedure")


def bind_context_form(form: ColonoscopyContextForm, data: dict) -> None:
    populate_form_choices(form)
    form.indication_detail.data = data.get("indication_detail") or ""
    form.urgency.data = data.get("urgency") or ""
    form.consent_obtained.data = data.get("consent_obtained") or ""
    form.anticoagulation.data = data.get("anticoagulation") or ""
    form.anticoagulation_management.data = data.get("anticoagulation_management") or ""
    form.asa_class.data = data.get("asa_class") or ""


def bind_procedure_form(form: ColonoscopyProcedureForm, data: dict) -> None:
    populate_form_choices(form)
    form.scope_type.data = data.get("scope_type") or ""
    form.caecum_reached.data = data.get("caecum_reached") or ""
    form.ti_intubated.data = data.get("ti_intubated") or ""
    form.withdrawal_time_min.data = data.get("withdrawal_time_min") or ""
    form.bbps_right.data = data.get("bbps_right") or ""
    form.bbps_transverse.data = data.get("bbps_transverse") or ""
    form.bbps_left.data = data.get("bbps_left") or ""
    form.prep_regimen.data = data.get("prep_regimen") or ""
    form.limited_exam.data = data.get("limited_exam") or ""
    form.limited_exam_reason.data = data.get("limited_exam_reason") or ""


def bind_findings_form(form: ColonoscopyFindingsForm, data: dict) -> None:
    for key in FINDING_SEGMENT_KEYS:
        normal_attr = f"{key}_normal"
        detail_attr = f"{key}_detail"
        if hasattr(form, normal_attr):
            getattr(form, normal_attr).data = data.get(normal_attr) or ""
        if hasattr(form, detail_attr):
            getattr(form, detail_attr).data = data.get(detail_attr) or ""


def bind_closure_form(form: ColonoscopyClosureForm, data: dict) -> None:
    form.procedure_completed.data = data.get("procedure_completed") or ""
    form.immediate_complication.data = data.get("immediate_complication") or ""
    form.complication_detail.data = data.get("complication_detail") or ""
    form.specimens_sent.data = data.get("specimens_sent") or ""
    form.specimen_details.data = data.get("specimen_details") or ""


def bind_synthesis_form(form: ColonoscopySynthesisForm, data: dict) -> None:
    populate_form_choices(form)
    form.impression_primary.data = data.get("impression_primary") or ""
    form.clinical_plan.data = data.get("clinical_plan") or ""
    form.surveillance_interval.data = data.get("surveillance_interval") or ""
    form.follow_up_procedure.data = data.get("follow_up_procedure") or ""
    form.addendum_text.data = data.get("addendum_text") or ""


def extract_interventions_from_form(form_data) -> list[dict]:
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
            {"intervention_type": itype, "success": success, "details": details}
        )
    return interventions
