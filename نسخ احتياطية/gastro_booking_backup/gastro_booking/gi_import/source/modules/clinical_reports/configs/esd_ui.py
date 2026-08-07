"""ESD — UI wiring."""

from flask import request

from app.modules.clinical_reports.configs import esd_forms
from app.modules.clinical_reports.fields.registry import get_fsd
from app.modules.clinical_reports.models import (
    WF_ACCESS,
    WF_CLOSURE,
    WF_CONTEXT,
    WF_FINALIZE,
    WF_IMAGING,
    WF_REVIEW,
    WF_SYNTHESIS,
    WF_THERAPY,
)
from app.modules.clinical_reports.platform.ui_helpers import (
    field_visible,
    legacy_keys_required_for_phase,
    workflow_phase_labels,
)
from app.modules.clinical_reports.vocabulary import vocabulary_choices
from app.modules.procedures.models import REPORT_TEMPLATE_KEY_ESD

TEMPLATE_KEY = REPORT_TEMPLATE_KEY_ESD

PHASE_FORMS = {
    WF_CONTEXT: ("context", esd_forms.EsdContextForm, esd_forms.bind_context_form),
    WF_ACCESS: ("access", esd_forms.EsdAccessForm, esd_forms.bind_access_form),
    WF_IMAGING: ("lesion", esd_forms.EsdLesionForm, esd_forms.bind_lesion_form),
    WF_THERAPY: ("resection", esd_forms.EsdResectionForm, esd_forms.bind_esd_resection_form),
    WF_CLOSURE: ("closure", esd_forms.EsdClosureForm, esd_forms.bind_closure_form),
    WF_SYNTHESIS: ("synthesis", esd_forms.EsdSynthesisForm, esd_forms.bind_synthesis_form),
}

EDITABLE_PHASE_STATES = list(PHASE_FORMS.keys())
TIMELINE_FORM = esd_forms.EsdTimelineForm


def phase_labels() -> dict[str, str]:
    return workflow_phase_labels(get_fsd(TEMPLATE_KEY), {WF_REVIEW: "Review", WF_FINALIZE: "Finalize"})


def extract_phase_data(phase_key: str) -> dict:
    if phase_key == "context":
        return {
            "indication_category": request.form.getlist("indication_category"),
            "indication_detail": request.form.get("indication_detail", ""),
            "urgency": request.form.get("urgency", ""),
            "consent_obtained": request.form.get("consent_obtained", ""),
            "anticoagulation": request.form.get("anticoagulation", ""),
            "anticoagulation_management": request.form.get("anticoagulation_management", ""),
            "prior_resection": request.form.get("prior_resection", ""),
            "prior_resection_detail": request.form.get("prior_resection_detail", ""),
        }
    if phase_key == "access":
        return {
            "sedation_type": request.form.getlist("sedation_type"),
            "organ": request.form.get("organ", ""),
            "scope_type": request.form.get("scope_type", ""),
            "cap_used": request.form.get("cap_used", ""),
            "anticoagulation_held": request.form.get("anticoagulation_held", ""),
        }
    if phase_key == "lesion":
        return {
            "segment": request.form.get("segment", ""),
            "location_detail": request.form.get("location_detail", ""),
            "size_mm": request.form.get("size_mm", ""),
            "paris_morphology": request.form.get("paris_morphology", ""),
            "nice_classification": request.form.get("nice_classification", ""),
            "jnet_classification": request.form.get("jnet_classification", ""),
            "tattoo_placed": request.form.get("tattoo_placed", ""),
            "lifting_assessment": request.form.get("lifting_assessment", ""),
            "lesion_description": request.form.get("lesion_description", ""),
        }
    if phase_key == "resection":
        return {
            "marking_method": request.form.get("marking_method", ""),
            "lift_solution": request.form.get("lift_solution", ""),
            "knife_type": request.form.get("knife_type", ""),
            "dissection_plane": request.form.get("dissection_plane", ""),
            "en_bloc": request.form.get("en_bloc", ""),
            "r0_resection": request.form.get("r0_resection", ""),
            "curative_resection_expected": request.form.get("curative_resection_expected", ""),
            "muscularis_exposure": request.form.get("muscularis_exposure", ""),
            "defect_size_mm": request.form.get("defect_size_mm", ""),
            "closure_method": request.form.get("closure_method", ""),
            "clips_count": request.form.get("clips_count", ""),
            "procedure_time_min": request.form.get("procedure_time_min", ""),
            "technique_notes": request.form.get("technique_notes", ""),
        }
    if phase_key == "closure":
        return {
            "procedure_completed": request.form.get("procedure_completed", ""),
            "immediate_complication": request.form.get("immediate_complication", ""),
            "complication_types": request.form.getlist("complication_types"),
            "complication_detail": request.form.get("complication_detail", ""),
            "hemostasis_required": request.form.get("hemostasis_required", ""),
            "hemostasis_method": request.form.get("hemostasis_method", ""),
            "specimens_sent": request.form.get("specimens_sent", ""),
            "specimen_details": request.form.get("specimen_details", ""),
        }
    if phase_key == "synthesis":
        return {
            "impression_primary": request.form.get("impression_primary", ""),
            "histology_expected": request.form.get("histology_expected", ""),
            "r_status_intraop": request.form.get("r_status_intraop", ""),
            "surveillance_interval": request.form.get("surveillance_interval", ""),
            "clinical_plan": request.form.get("clinical_plan", ""),
            "delayed_perforation_counseling": request.form.get("delayed_perforation_counseling", ""),
            "addendum_text": request.form.get("addendum_text", ""),
        }
    return {}


def phase_template_context(report, document, phase_state, sp, form=None) -> dict:
    fsd = get_fsd(TEMPLATE_KEY)
    ctx = {
        "form": form,
        "report": report,
        "document": document,
        "phase_state": phase_state,
        "phase_label": phase_labels()[phase_state],
        "required_fields": legacy_keys_required_for_phase(fsd, phase_state),
        "indication_choices": vocabulary_choices("emr_esd_indication_category"),
        "selected_indications": sp.get_legacy_phase("context").get("indication_category") or [],
        "complication_type_choices": vocabulary_choices("resection_complication_type"),
        "selected_complication_types": sp.get_legacy_phase("closure").get("complication_types") or [],
        "yes_no_choices": esd_forms.YES_NO_CHOICES,
        "show_complication_types": field_visible(fsd, sp, f"{TEMPLATE_KEY}.closure.complication_types"),
        "show_complication_detail": field_visible(fsd, sp, f"{TEMPLATE_KEY}.closure.complication_detail"),
        "show_specimen_details": field_visible(fsd, sp, f"{TEMPLATE_KEY}.closure.specimen_details"),
        "show_hemostasis_method": field_visible(fsd, sp, f"{TEMPLATE_KEY}.closure.hemostasis_method"),
        "show_anticoag_management": field_visible(fsd, sp, f"{TEMPLATE_KEY}.context.anticoagulation_management"),
        "show_prior_resection_detail": sp.get_legacy_phase("context").get("prior_resection") == "Yes",
        "sedation_type_choices": vocabulary_choices("sedation_type"),
        "selected_sedation_types": sp.get_legacy_phase("access").get("sedation_type") or [],
        "is_esd": True,
    }
    return ctx
