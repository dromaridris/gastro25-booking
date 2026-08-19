"""Colonoscopy v2 template — UI wiring."""

from flask import request

from app.modules.clinical_reports.configs import colonoscopy_v2_forms
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
from app.modules.procedures.models import REPORT_TEMPLATE_KEY_COLONOSCOPY_V2

TEMPLATE_KEY = REPORT_TEMPLATE_KEY_COLONOSCOPY_V2

PHASE_FORMS = {
    WF_CONTEXT: ("context", colonoscopy_v2_forms.ColonoscopyContextForm, colonoscopy_v2_forms.bind_context_form),
    WF_ACCESS: ("procedure", colonoscopy_v2_forms.ColonoscopyProcedureForm, colonoscopy_v2_forms.bind_procedure_form),
    WF_IMAGING: ("findings", colonoscopy_v2_forms.ColonoscopyFindingsForm, colonoscopy_v2_forms.bind_findings_form),
    WF_THERAPY: ("interventions", colonoscopy_v2_forms.ColonoscopyInterventionsForm, None),
    WF_CLOSURE: ("closure", colonoscopy_v2_forms.ColonoscopyClosureForm, colonoscopy_v2_forms.bind_closure_form),
    WF_SYNTHESIS: ("synthesis", colonoscopy_v2_forms.ColonoscopySynthesisForm, colonoscopy_v2_forms.bind_synthesis_form),
}

_WORKFLOW_META_LABELS = {WF_REVIEW: "Review", WF_FINALIZE: "Finalize"}

FINDING_SEGMENT_LABELS = {
    "terminal_ileum": "Terminal ileum",
    "caecum": "Caecum",
    "ascending": "Ascending colon",
    "transverse": "Transverse colon",
    "descending": "Descending colon",
    "sigmoid": "Sigmoid colon",
    "rectum": "Rectum",
    "anus": "Anus",
}


def phase_labels() -> dict[str, str]:
    fsd = get_fsd(TEMPLATE_KEY)
    return workflow_phase_labels(fsd, _WORKFLOW_META_LABELS)


EDITABLE_PHASE_STATES = list(PHASE_FORMS.keys())
TIMELINE_FORM = colonoscopy_v2_forms.ColonoscopyTimelineForm


def extract_phase_data(phase_key: str) -> dict:
    if phase_key == "context":
        return {
            "indication_category": request.form.getlist("indication_category"),
            "indication_detail": request.form.get("indication_detail", ""),
            "urgency": request.form.get("urgency", ""),
            "consent_obtained": request.form.get("consent_obtained", ""),
            "anticoagulation": request.form.get("anticoagulation", ""),
            "anticoagulation_management": request.form.get("anticoagulation_management", ""),
            "asa_class": request.form.get("asa_class", ""),
        }
    if phase_key == "procedure":
        return {
            "sedation_type": request.form.getlist("sedation_type"),
            "scope_type": request.form.get("scope_type", ""),
            "caecum_reached": request.form.get("caecum_reached", ""),
            "ti_intubated": request.form.get("ti_intubated", ""),
            "withdrawal_time_min": request.form.get("withdrawal_time_min", ""),
            "bbps_right": request.form.get("bbps_right", ""),
            "bbps_transverse": request.form.get("bbps_transverse", ""),
            "bbps_left": request.form.get("bbps_left", ""),
            "prep_regimen": request.form.get("prep_regimen", ""),
            "limited_exam": request.form.get("limited_exam", ""),
            "limited_exam_reason": request.form.get("limited_exam_reason", ""),
        }
    if phase_key == "findings":
        data = {}
        for key in colonoscopy_v2_forms.FINDING_SEGMENT_KEYS:
            data[f"{key}_normal"] = request.form.get(f"{key}_normal", "")
            data[f"{key}_findings"] = request.form.getlist(f"{key}_findings")
            data[f"{key}_detail"] = request.form.get(f"{key}_detail", "")
        return data
    if phase_key == "interventions":
        return {"interventions": colonoscopy_v2_forms.extract_interventions_from_form(request.form)}
    if phase_key == "closure":
        return {
            "procedure_completed": request.form.get("procedure_completed", ""),
            "immediate_complication": request.form.get("immediate_complication", ""),
            "complication_types": request.form.getlist("complication_types"),
            "complication_detail": request.form.get("complication_detail", ""),
            "specimens_sent": request.form.get("specimens_sent", ""),
            "specimen_details": request.form.get("specimen_details", ""),
        }
    if phase_key == "synthesis":
        return {
            "impression_primary": request.form.get("impression_primary", ""),
            "clinical_plan": request.form.get("clinical_plan", ""),
            "surveillance_interval": request.form.get("surveillance_interval", ""),
            "follow_up_procedure": request.form.get("follow_up_procedure", ""),
            "addendum_text": request.form.get("addendum_text", ""),
        }
    return {}


def phase_template_context(report, document, phase_state, sp, form=None) -> dict:
    fsd = get_fsd(TEMPLATE_KEY)
    labels = phase_labels()
    findings_data = sp.get_legacy_phase("findings")
    segment_ctx = []
    for key in colonoscopy_v2_forms.FINDING_SEGMENT_KEYS:
        segment_ctx.append(
            {
                "key": key,
                "label": FINDING_SEGMENT_LABELS[key],
                "selected_findings": findings_data.get(f"{key}_findings") or [],
                "show_abnormal": field_visible(fsd, sp, f"colonoscopy_v2.findings.{key}_findings"),
            }
        )
    return {
        "form": form,
        "report": report,
        "document": document,
        "phase_state": phase_state,
        "phase_label": labels[phase_state],
        "required_fields": legacy_keys_required_for_phase(fsd, phase_state),
        "indication_choices": vocabulary_choices("colonoscopy_indication_category"),
        "selected_indications": sp.get_legacy_phase("context").get("indication_category") or [],
        "sedation_type_choices": vocabulary_choices("sedation_type"),
        "selected_sedation_types": sp.get_legacy_phase("procedure").get("sedation_type") or [],
        "finding_type_choices": vocabulary_choices("colonic_finding_type"),
        "finding_segments": segment_ctx,
        "complication_type_choices": vocabulary_choices("standard_complication_type"),
        "selected_complication_types": sp.get_legacy_phase("closure").get("complication_types") or [],
        "intervention_type_choices": vocabulary_choices("colonoscopy_intervention_type"),
        "interventions": sp.get_legacy_phase("interventions").get("interventions") or [],
        "yes_no_choices": colonoscopy_v2_forms.YES_NO_CHOICES,
        "show_anticoagulation_management": field_visible(
            fsd, sp, "colonoscopy_v2.context.anticoagulation_management"
        ),
        "show_limited_exam_reason": field_visible(fsd, sp, "colonoscopy_v2.procedure.limited_exam_reason"),
        "show_complication_types": field_visible(fsd, sp, "colonoscopy_v2.closure.complication_types"),
        "show_complication_detail": field_visible(fsd, sp, "colonoscopy_v2.closure.complication_detail"),
        "show_specimen_details": field_visible(fsd, sp, "colonoscopy_v2.closure.specimen_details"),
    }
