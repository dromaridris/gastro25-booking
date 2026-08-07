"""ERCP template — UI wiring (phase forms, labels, template context)."""

from flask import request

from app.modules.clinical_reports.configs import ercp_forms
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
from app.modules.procedures.models import REPORT_TEMPLATE_KEY_ERCP

TEMPLATE_KEY = REPORT_TEMPLATE_KEY_ERCP

PHASE_FORMS = {
    WF_CONTEXT: ("context", ercp_forms.ErCpContextForm, ercp_forms.bind_context_form),
    WF_ACCESS: ("access", ercp_forms.ErCpAccessForm, ercp_forms.bind_access_form),
    WF_IMAGING: ("imaging", ercp_forms.ErCpImagingForm, ercp_forms.bind_imaging_form),
    WF_THERAPY: ("therapy", ercp_forms.ErCpTherapyForm, None),
    WF_CLOSURE: ("closure", ercp_forms.ErCpClosureForm, ercp_forms.bind_closure_form),
    WF_SYNTHESIS: ("synthesis", ercp_forms.ErCpSynthesisForm, ercp_forms.bind_synthesis_form),
}

_WORKFLOW_META_LABELS = {
    WF_REVIEW: "Review",
    WF_FINALIZE: "Finalize",
}


def phase_labels() -> dict[str, str]:
    fsd = get_fsd(TEMPLATE_KEY)
    return workflow_phase_labels(fsd, _WORKFLOW_META_LABELS)


EDITABLE_PHASE_STATES = list(PHASE_FORMS.keys())

TIMELINE_FORM = ercp_forms.ErCpTimelineForm


def extract_phase_data(phase_key: str) -> dict:
    if phase_key == "context":
        return {
            "indication_category": request.form.getlist("indication_category"),
            "indication_detail": request.form.get("indication_detail", ""),
            "ercp_urgency": request.form.get("ercp_urgency", ""),
            "ascending_cholangitis_suspected": request.form.get("ascending_cholangitis_suspected", ""),
            "prophylactic_antibiotics": request.form.get("prophylactic_antibiotics", ""),
            "antibiotic_agent": request.form.get("antibiotic_agent", ""),
        }
    if phase_key == "access":
        return {
            "ampulla_identified": request.form.get("ampulla_identified", ""),
            "cannulation_method": request.form.getlist("cannulation_method"),
            "cannulation_success": request.form.get("cannulation_success", ""),
            "difficult_cannulation": request.form.get("difficult_cannulation", ""),
            "precut_performed": request.form.get("precut_performed", ""),
            "pep_prophylaxis": request.form.getlist("pep_prophylaxis"),
        }
    if phase_key == "imaging":
        return {
            "cholangiography_performed": request.form.get("cholangiography_performed", ""),
            "cbd_diameter_mm": request.form.get("cbd_diameter_mm", ""),
            "filling_defects": request.form.get("filling_defects", ""),
            "stone_burden": request.form.get("stone_burden", ""),
            "stricture_present": request.form.get("stricture_present", ""),
            "pancreatography_performed": request.form.get("pancreatography_performed", ""),
            "pancreatic_duct_findings": request.form.get("pancreatic_duct_findings", ""),
        }
    if phase_key == "therapy":
        return {"interventions": ercp_forms.extract_interventions_from_form(request.form)}
    if phase_key == "closure":
        return {
            "procedure_completed": request.form.get("procedure_completed", ""),
            "clearance_achieved": request.form.get("clearance_achieved", ""),
            "fluoroscopy_used": request.form.get("fluoroscopy_used", ""),
            "immediate_complication": request.form.get("immediate_complication", ""),
            "complication_types": request.form.getlist("complication_types"),
            "pep_suspected": request.form.get("pep_suspected", ""),
        }
    if phase_key == "synthesis":
        return {
            "impression_primary": request.form.get("impression_primary", ""),
            "clinical_plan": request.form.get("clinical_plan", ""),
            "repeat_ercp_planned": request.form.get("repeat_ercp_planned", ""),
            "addendum_text": request.form.get("addendum_text", ""),
        }
    return {}


def phase_template_context(report, document, phase_state, sp, form=None) -> dict:
    fsd = get_fsd(TEMPLATE_KEY)
    labels = phase_labels()
    return {
        "form": form,
        "report": report,
        "document": document,
        "phase_state": phase_state,
        "phase_label": labels[phase_state],
        "required_fields": legacy_keys_required_for_phase(fsd, phase_state),
        "indication_choices": vocabulary_choices("ercp_indication_category"),
        "selected_indications": sp.get_legacy_phase("context").get("indication_category") or [],
        "cannulation_method_choices": vocabulary_choices("cannulation_method"),
        "selected_cannulation_methods": sp.get_legacy_phase("access").get("cannulation_method") or [],
        "pep_prophylaxis_choices": vocabulary_choices("pep_prophylaxis"),
        "selected_pep_prophylaxis": sp.get_legacy_phase("access").get("pep_prophylaxis") or [],
        "complication_type_choices": vocabulary_choices("complication_type"),
        "selected_complication_types": sp.get_legacy_phase("closure").get("complication_types") or [],
        "intervention_type_choices": vocabulary_choices("intervention_type"),
        "interventions": sp.get_legacy_phase("therapy").get("interventions") or [],
        "yes_no_choices": ercp_forms.YES_NO_CHOICES,
        "show_antibiotic_agent": field_visible(fsd, sp, "ercp.context.antibiotic_agent"),
        "show_complication_types": field_visible(fsd, sp, "ercp.closure.complication_types"),
    }
