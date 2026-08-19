"""Shared WTForms for EMR and ESD structured clinical reports."""

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


class TherapeuticContextForm(FlaskForm):
    indication_detail = TextAreaField("Indication detail", validators=[Optional()])
    urgency = SelectField("Urgency", choices=[], validators=[Optional()])
    consent_obtained = SelectField("Consent obtained", choices=[], validators=[Optional()])
    anticoagulation = SelectField("Anticoagulation / antiplatelet therapy", choices=[], validators=[Optional()])
    anticoagulation_management = SelectField("Anticoagulation management", choices=[], validators=[Optional()])
    prior_resection = SelectField("Prior EMR / ESD / surgery at site", choices=[], validators=[Optional()])
    prior_resection_detail = TextAreaField("Prior resection detail", validators=[Optional()])
    submit = SubmitField("Save Context")


class TherapeuticAccessForm(FlaskForm):
    organ = SelectField("Target organ", choices=[], validators=[Optional()])
    scope_type = SelectField("Scope type", choices=[], validators=[Optional()])
    cap_used = SelectField("Distal attachment cap used", choices=[], validators=[Optional()])
    anticoagulation_held = SelectField("Anticoagulation held per protocol", choices=[], validators=[Optional()])
    submit = SubmitField("Save Access & Setup")


class TherapeuticLesionForm(FlaskForm):
    segment = SelectField("Anatomical segment", choices=[], validators=[Optional()])
    location_detail = StringField("Location detail (cm from landmark)", validators=[Optional()])
    size_mm = StringField("Lesion size (mm)", validators=[Optional()])
    paris_morphology = SelectField("Paris morphology", choices=[], validators=[Optional()])
    nice_classification = SelectField("NICE classification", choices=[], validators=[Optional()])
    jnet_classification = SelectField("JNET classification", choices=[], validators=[Optional()])
    tattoo_placed = SelectField("Tattoo placed", choices=[], validators=[Optional()])
    lifting_assessment = SelectField("Submucosal lifting assessment", choices=[], validators=[Optional()])
    lesion_description = TextAreaField("Lesion description", validators=[Optional()])
    submit = SubmitField("Save Lesion Assessment")


class EmrResectionForm(FlaskForm):
    lift_solution = SelectField("Submucosal lift solution", choices=[], validators=[Optional()])
    resection_technique = SelectField("Resection technique", choices=[], validators=[Optional()])
    snare_type = SelectField("Snare type", choices=[], validators=[Optional()])
    en_bloc = SelectField("En-bloc resection", choices=[], validators=[Optional()])
    piecemeal = SelectField("Piecemeal resection", choices=[], validators=[Optional()])
    defect_size_mm = StringField("Mucosal defect size (mm)", validators=[Optional()])
    closure_method = SelectField("Defect closure method", choices=[], validators=[Optional()])
    clips_count = StringField("Clips applied (count)", validators=[Optional()])
    procedure_time_min = StringField("Procedure time (minutes)", validators=[Optional()])
    technique_notes = TextAreaField("Technique notes", validators=[Optional()])
    submit = SubmitField("Save EMR Technique")


class EsdResectionForm(FlaskForm):
    marking_method = SelectField("Lesion marking method", choices=[], validators=[Optional()])
    lift_solution = SelectField("Submucosal lift solution", choices=[], validators=[Optional()])
    knife_type = SelectField("Dissection knife", choices=[], validators=[Optional()])
    dissection_plane = SelectField("Dissection plane", choices=[], validators=[Optional()])
    en_bloc = SelectField("En-bloc resection", choices=[], validators=[Optional()])
    r0_resection = SelectField("R0 resection (macroscopic)", choices=[], validators=[Optional()])
    curative_resection_expected = SelectField("Curative resection expected", choices=[], validators=[Optional()])
    muscularis_exposure = SelectField("Muscularis propria exposure", choices=[], validators=[Optional()])
    defect_size_mm = StringField("Mucosal defect size (mm)", validators=[Optional()])
    closure_method = SelectField("Defect closure method", choices=[], validators=[Optional()])
    clips_count = StringField("Clips / devices applied (count)", validators=[Optional()])
    procedure_time_min = StringField("Procedure time (minutes)", validators=[Optional()])
    technique_notes = TextAreaField("Technique notes", validators=[Optional()])
    submit = SubmitField("Save ESD Technique")


class TherapeuticClosureForm(FlaskForm):
    procedure_completed = SelectField("Procedure completed as planned", choices=[], validators=[Optional()])
    immediate_complication = SelectField("Immediate complication", choices=[], validators=[Optional()])
    complication_detail = TextAreaField("Complication detail", validators=[Optional()])
    hemostasis_required = SelectField("Hemostasis required", choices=[], validators=[Optional()])
    hemostasis_method = SelectField("Hemostasis method", choices=[], validators=[Optional()])
    specimens_sent = SelectField("Specimens sent to histology", choices=[], validators=[Optional()])
    specimen_details = TextAreaField("Specimen details (jars / orientation)", validators=[Optional()])
    submit = SubmitField("Save Closure")


class TherapeuticSynthesisForm(FlaskForm):
    impression_primary = TextAreaField("Primary impression", validators=[Optional()])
    histology_expected = SelectField("Expected histology", choices=[], validators=[Optional()])
    r_status_intraop = SelectField("Resection margin status (intra-procedure)", choices=[], validators=[Optional()])
    surveillance_interval = SelectField("Surveillance interval", choices=[], validators=[Optional()])
    clinical_plan = TextAreaField("Recommendations / clinical plan", validators=[Optional()])
    delayed_perforation_counseling = SelectField(
        "Delayed perforation counseling documented", choices=[], validators=[Optional()]
    )
    addendum_text = TextAreaField("Addendum", validators=[Optional()])
    submit = SubmitField("Save Synthesis")


class TherapeuticTimelineForm(FlaskForm):
    submit = SubmitField("Save Timeline")


_YES_NO_FIELDS = {
    "consent_obtained",
    "prior_resection",
    "cap_used",
    "anticoagulation_held",
    "tattoo_placed",
    "en_bloc",
    "piecemeal",
    "r0_resection",
    "curative_resection_expected",
    "muscularis_exposure",
    "procedure_completed",
    "immediate_complication",
    "hemostasis_required",
    "specimens_sent",
    "delayed_perforation_counseling",
}

_FIELD_VOCAB = {
    "urgency": "procedure_urgency",
    "anticoagulation": "anticoagulation_status",
    "anticoagulation_management": "anticoagulation_management",
    "organ": "emr_esd_organ",
    "scope_type": "emr_esd_scope_type",
    "segment": "emr_esd_segment",
    "paris_morphology": "paris_morphology",
    "nice_classification": "nice_classification",
    "jnet_classification": "jnet_classification",
    "lifting_assessment": "lifting_assessment",
    "lift_solution": "lift_solution",
    "resection_technique": "emr_resection_technique",
    "snare_type": "emr_snare_type",
    "marking_method": "esd_marking_method",
    "knife_type": "esd_knife_type",
    "dissection_plane": "esd_dissection_plane",
    "closure_method": "defect_closure_method",
    "hemostasis_method": "hemostasis_method",
    "histology_expected": "expected_histology",
    "r_status_intraop": "r_resection_status",
    "surveillance_interval": "surveillance_interval",
}


def populate_form_choices(form) -> None:
    for name, field in form._fields.items():
        if not isinstance(field, SelectField):
            continue
        vocab = _FIELD_VOCAB.get(name)
        if vocab:
            field.choices = vocabulary_choices(vocab)
        elif name in _YES_NO_FIELDS:
            field.choices = YES_NO_CHOICES


def bind_context_form(form: TherapeuticContextForm, data: dict) -> None:
    populate_form_choices(form)
    form.indication_detail.data = data.get("indication_detail") or ""
    form.urgency.data = data.get("urgency") or ""
    form.consent_obtained.data = data.get("consent_obtained") or ""
    form.anticoagulation.data = data.get("anticoagulation") or ""
    form.anticoagulation_management.data = data.get("anticoagulation_management") or ""
    form.prior_resection.data = data.get("prior_resection") or ""
    form.prior_resection_detail.data = data.get("prior_resection_detail") or ""


def bind_access_form(form: TherapeuticAccessForm, data: dict) -> None:
    populate_form_choices(form)
    form.organ.data = data.get("organ") or ""
    form.scope_type.data = data.get("scope_type") or ""
    form.cap_used.data = data.get("cap_used") or ""
    form.anticoagulation_held.data = data.get("anticoagulation_held") or ""


def bind_lesion_form(form: TherapeuticLesionForm, data: dict) -> None:
    populate_form_choices(form)
    form.segment.data = data.get("segment") or ""
    form.location_detail.data = data.get("location_detail") or ""
    form.size_mm.data = data.get("size_mm") or ""
    form.paris_morphology.data = data.get("paris_morphology") or ""
    form.nice_classification.data = data.get("nice_classification") or ""
    form.jnet_classification.data = data.get("jnet_classification") or ""
    form.tattoo_placed.data = data.get("tattoo_placed") or ""
    form.lifting_assessment.data = data.get("lifting_assessment") or ""
    form.lesion_description.data = data.get("lesion_description") or ""


def bind_emr_resection_form(form: EmrResectionForm, data: dict) -> None:
    populate_form_choices(form)
    form.lift_solution.data = data.get("lift_solution") or ""
    form.resection_technique.data = data.get("resection_technique") or ""
    form.snare_type.data = data.get("snare_type") or ""
    form.en_bloc.data = data.get("en_bloc") or ""
    form.piecemeal.data = data.get("piecemeal") or ""
    form.defect_size_mm.data = data.get("defect_size_mm") or ""
    form.closure_method.data = data.get("closure_method") or ""
    form.clips_count.data = data.get("clips_count") or ""
    form.procedure_time_min.data = data.get("procedure_time_min") or ""
    form.technique_notes.data = data.get("technique_notes") or ""


def bind_esd_resection_form(form: EsdResectionForm, data: dict) -> None:
    populate_form_choices(form)
    form.marking_method.data = data.get("marking_method") or ""
    form.lift_solution.data = data.get("lift_solution") or ""
    form.knife_type.data = data.get("knife_type") or ""
    form.dissection_plane.data = data.get("dissection_plane") or ""
    form.en_bloc.data = data.get("en_bloc") or ""
    form.r0_resection.data = data.get("r0_resection") or ""
    form.curative_resection_expected.data = data.get("curative_resection_expected") or ""
    form.muscularis_exposure.data = data.get("muscularis_exposure") or ""
    form.defect_size_mm.data = data.get("defect_size_mm") or ""
    form.closure_method.data = data.get("closure_method") or ""
    form.clips_count.data = data.get("clips_count") or ""
    form.procedure_time_min.data = data.get("procedure_time_min") or ""
    form.technique_notes.data = data.get("technique_notes") or ""


def bind_closure_form(form: TherapeuticClosureForm, data: dict) -> None:
    populate_form_choices(form)
    form.procedure_completed.data = data.get("procedure_completed") or ""
    form.immediate_complication.data = data.get("immediate_complication") or ""
    form.complication_detail.data = data.get("complication_detail") or ""
    form.hemostasis_required.data = data.get("hemostasis_required") or ""
    form.hemostasis_method.data = data.get("hemostasis_method") or ""
    form.specimens_sent.data = data.get("specimens_sent") or ""
    form.specimen_details.data = data.get("specimen_details") or ""


def bind_synthesis_form(form: TherapeuticSynthesisForm, data: dict) -> None:
    populate_form_choices(form)
    form.impression_primary.data = data.get("impression_primary") or ""
    form.histology_expected.data = data.get("histology_expected") or ""
    form.r_status_intraop.data = data.get("r_status_intraop") or ""
    form.surveillance_interval.data = data.get("surveillance_interval") or ""
    form.clinical_plan.data = data.get("clinical_plan") or ""
    form.delayed_perforation_counseling.data = data.get("delayed_perforation_counseling") or ""
    form.addendum_text.data = data.get("addendum_text") or ""
