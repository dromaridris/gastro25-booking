"""ERCP template — WTForms and phase data extraction."""

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


class ErCpContextForm(FlaskForm):
    indication_detail = TextAreaField("Indication detail", validators=[Optional()])
    ercp_urgency = SelectField("Urgency", choices=[], validators=[Optional()])
    ascending_cholangitis_suspected = SelectField(
        "Ascending cholangitis suspected", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    prophylactic_antibiotics = SelectField(
        "Prophylactic antibiotics", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    antibiotic_agent = StringField("Antibiotic agent", validators=[Optional()])
    submit = SubmitField("Save Context")


class ErCpAccessForm(FlaskForm):
    ampulla_identified = SelectField("Ampulla identified", choices=YES_NO_CHOICES, validators=[Optional()])
    cannulation_success = SelectField(
        "Biliary cannulation successful", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    difficult_cannulation = SelectField(
        "Difficult cannulation", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    precut_performed = SelectField("Precut performed", choices=YES_NO_CHOICES, validators=[Optional()])
    submit = SubmitField("Save Access")


class ErCpImagingForm(FlaskForm):
    cholangiography_performed = SelectField(
        "Cholangiography performed", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    cbd_diameter_mm = StringField("CBD diameter (mm)", validators=[Optional()])
    filling_defects = StringField("Filling defects", validators=[Optional()])
    stone_burden = SelectField("Stone burden", choices=[], validators=[Optional()])
    stricture_present = SelectField("Stricture present", choices=YES_NO_CHOICES, validators=[Optional()])
    pancreatography_performed = SelectField(
        "Pancreatography performed", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    pancreatic_duct_findings = TextAreaField("Pancreatic duct findings", validators=[Optional()])
    submit = SubmitField("Save Imaging")


class ErCpTherapyForm(FlaskForm):
    submit = SubmitField("Save Therapy")


class ErCpClosureForm(FlaskForm):
    procedure_completed = SelectField(
        "Procedure completed as planned", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    clearance_achieved = SelectField(
        "Biliary clearance achieved", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    fluoroscopy_used = SelectField("Fluoroscopy used", choices=YES_NO_CHOICES, validators=[Optional()])
    immediate_complication = SelectField(
        "Immediate complication", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    pep_suspected = SelectField("PEP suspected", choices=YES_NO_CHOICES, validators=[Optional()])
    submit = SubmitField("Save Closure")


class ErCpSynthesisForm(FlaskForm):
    impression_primary = TextAreaField("Primary impression", validators=[Optional()])
    clinical_plan = TextAreaField("Clinical plan / recommendations", validators=[Optional()])
    repeat_ercp_planned = SelectField(
        "Repeat ERCP planned", choices=YES_NO_CHOICES, validators=[Optional()]
    )
    addendum_text = TextAreaField("Addendum", validators=[Optional()])
    submit = SubmitField("Save Synthesis")


class ErCpTimelineForm(FlaskForm):
    submit = SubmitField("Save Timeline")


def populate_form_choices(form) -> None:
    if hasattr(form, "ercp_urgency"):
        form.ercp_urgency.choices = vocabulary_choices("ercp_urgency")
    if hasattr(form, "stone_burden"):
        form.stone_burden.choices = vocabulary_choices("stone_burden")


def bind_context_form(form: ErCpContextForm, data: dict) -> None:
    populate_form_choices(form)
    form.indication_detail.data = data.get("indication_detail") or ""
    form.ercp_urgency.data = data.get("ercp_urgency") or ""
    form.ascending_cholangitis_suspected.data = data.get("ascending_cholangitis_suspected") or ""
    form.prophylactic_antibiotics.data = data.get("prophylactic_antibiotics") or ""
    form.antibiotic_agent.data = data.get("antibiotic_agent") or ""


def bind_access_form(form: ErCpAccessForm, data: dict) -> None:
    form.ampulla_identified.data = data.get("ampulla_identified") or ""
    form.cannulation_success.data = data.get("cannulation_success") or ""
    form.difficult_cannulation.data = data.get("difficult_cannulation") or ""
    form.precut_performed.data = data.get("precut_performed") or ""


def bind_imaging_form(form: ErCpImagingForm, data: dict) -> None:
    populate_form_choices(form)
    form.cholangiography_performed.data = data.get("cholangiography_performed") or ""
    form.cbd_diameter_mm.data = data.get("cbd_diameter_mm") or ""
    form.filling_defects.data = data.get("filling_defects") or ""
    form.stone_burden.data = data.get("stone_burden") or ""
    form.stricture_present.data = data.get("stricture_present") or ""
    form.pancreatography_performed.data = data.get("pancreatography_performed") or ""
    form.pancreatic_duct_findings.data = data.get("pancreatic_duct_findings") or ""


def bind_closure_form(form: ErCpClosureForm, data: dict) -> None:
    form.procedure_completed.data = data.get("procedure_completed") or ""
    form.clearance_achieved.data = data.get("clearance_achieved") or ""
    form.fluoroscopy_used.data = data.get("fluoroscopy_used") or ""
    form.immediate_complication.data = data.get("immediate_complication") or ""
    form.pep_suspected.data = data.get("pep_suspected") or ""


def bind_synthesis_form(form: ErCpSynthesisForm, data: dict) -> None:
    form.impression_primary.data = data.get("impression_primary") or ""
    form.clinical_plan.data = data.get("clinical_plan") or ""
    form.repeat_ercp_planned.data = data.get("repeat_ercp_planned") or ""
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
