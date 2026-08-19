"""Proctoscopy v2 — UI wiring."""

from flask import request

from app.modules.clinical_reports.configs import proctoscopy_v2_forms
from app.modules.clinical_reports.configs.colonoscopy_v2_forms import extract_interventions_from_form
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
from app.modules.procedures.models import REPORT_TEMPLATE_KEY_PROCTOSCOPY_V2

TEMPLATE_KEY = REPORT_TEMPLATE_KEY_PROCTOSCOPY_V2

PHASE_FORMS = {
    WF_CONTEXT: ("context", proctoscopy_v2_forms.ProctoscopyContextForm, proctoscopy_v2_forms.bind_context_form),
    WF_ACCESS: ("procedure", proctoscopy_v2_forms.ProctoscopyProcedureForm, proctoscopy_v2_forms.bind_procedure_form),
    WF_IMAGING: ("findings", proctoscopy_v2_forms.ProctoscopyFindingsForm, proctoscopy_v2_forms.bind_findings_form),
    WF_THERAPY: ("interventions", proctoscopy_v2_forms.ProctoscopyInterventionsForm, None),
    WF_CLOSURE: ("closure", proctoscopy_v2_forms.ProctoscopyClosureForm, proctoscopy_v2_forms.bind_closure_form),
    WF_SYNTHESIS: ("synthesis", proctoscopy_v2_forms.ProctoscopySynthesisForm, proctoscopy_v2_forms.bind_synthesis_form),
}

FINDING_SEGMENT_LABELS = {"rectum": "Rectum", "anus": "Anus"}


def phase_labels() -> dict[str, str]:
    return workflow_phase_labels(get_fsd(TEMPLATE_KEY), {WF_REVIEW: "Review", WF_FINALIZE: "Finalize"})


EDITABLE_PHASE_STATES = list(PHASE_FORMS.keys())
TIMELINE_FORM = proctoscopy_v2_forms.ProctoscopyTimelineForm


def extract_phase_data(phase_key: str) -> dict:
    if phase_key == "context":
        return {
            "indication_category": request.form.getlist("indication_category"),
            "indication_detail": request.form.get("indication_detail", ""),
            "urgency": request.form.get("urgency", ""),
            "consent_obtained": request.form.get("consent_obtained", ""),
        }
    if phase_key == "procedure":
        return {
            "scope_type": request.form.get("scope_type", ""),
            "exam_completed": request.form.get("exam_completed", ""),
            "limited_exam": request.form.get("limited_exam", ""),
            "limited_exam_reason": request.form.get("limited_exam_reason", ""),
        }
    if phase_key == "findings":
        data = {}
        for key in proctoscopy_v2_forms.FINDING_SEGMENT_KEYS:
            data[f"{key}_normal"] = request.form.get(f"{key}_normal", "")
            data[f"{key}_findings"] = request.form.getlist(f"{key}_findings")
            data[f"{key}_detail"] = request.form.get(f"{key}_detail", "")
        return data
    if phase_key == "interventions":
        return {"interventions": extract_interventions_from_form(request.form)}
    if phase_key == "closure":
        return {
            "procedure_completed": request.form.get("procedure_completed", ""),
            "immediate_complication": request.form.get("immediate_complication", ""),
            "complication_types": request.form.getlist("complication_types"),
            "complication_detail": request.form.get("complication_detail", ""),
        }
    if phase_key == "synthesis":
        return {
            "impression_primary": request.form.get("impression_primary", ""),
            "clinical_plan": request.form.get("clinical_plan", ""),
            "addendum_text": request.form.get("addendum_text", ""),
        }
    return {}


def phase_template_context(report, document, phase_state, sp, form=None) -> dict:
    fsd = get_fsd(TEMPLATE_KEY)
    findings_data = sp.get_legacy_phase("findings")
    segment_ctx = []
    for key in proctoscopy_v2_forms.FINDING_SEGMENT_KEYS:
        segment_ctx.append(
            {
                "key": key,
                "label": FINDING_SEGMENT_LABELS[key],
                "selected_findings": findings_data.get(f"{key}_findings") or [],
                "show_abnormal": field_visible(fsd, sp, f"proctoscopy_v2.findings.{key}_findings"),
            }
        )
    return {
        "form": form,
        "report": report,
        "document": document,
        "phase_state": phase_state,
        "phase_label": phase_labels()[phase_state],
        "required_fields": legacy_keys_required_for_phase(fsd, phase_state),
        "indication_choices": vocabulary_choices("proctoscopy_indication_category"),
        "selected_indications": sp.get_legacy_phase("context").get("indication_category") or [],
        "finding_type_choices": vocabulary_choices("colonic_finding_type"),
        "finding_segments": segment_ctx,
        "complication_type_choices": vocabulary_choices("standard_complication_type"),
        "selected_complication_types": sp.get_legacy_phase("closure").get("complication_types") or [],
        "intervention_type_choices": vocabulary_choices("proctoscopy_intervention_type"),
        "interventions": sp.get_legacy_phase("interventions").get("interventions") or [],
        "yes_no_choices": proctoscopy_v2_forms.YES_NO_CHOICES,
        "show_limited_exam_reason": field_visible(fsd, sp, "proctoscopy_v2.procedure.limited_exam_reason"),
        "show_complication_types": field_visible(fsd, sp, "proctoscopy_v2.closure.complication_types"),
        "show_complication_detail": field_visible(fsd, sp, "proctoscopy_v2.closure.complication_detail"),
    }
