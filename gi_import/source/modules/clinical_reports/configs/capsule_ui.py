"""Capsule — UI wiring."""

from flask import request

from app.modules.clinical_reports.configs import capsule_forms
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
from app.modules.procedures.models import REPORT_TEMPLATE_KEY_CAPSULE

TEMPLATE_KEY = REPORT_TEMPLATE_KEY_CAPSULE

PHASE_FORMS = {
    WF_CONTEXT: ("context", capsule_forms.CapsuleContextForm, capsule_forms.bind_context_form),
    WF_ACCESS: ("acquisition", capsule_forms.CapsuleAcquisitionForm, capsule_forms.bind_acquisition_form),
    WF_IMAGING: ("findings", capsule_forms.CapsuleFindingsForm, capsule_forms.bind_findings_form),
    WF_THERAPY: ("supplementary", capsule_forms.CapsuleSupplementaryForm, capsule_forms.bind_supplementary_form),
    WF_CLOSURE: ("closure", capsule_forms.CapsuleClosureForm, capsule_forms.bind_closure_form),
    WF_SYNTHESIS: ("synthesis", capsule_forms.CapsuleSynthesisForm, capsule_forms.bind_synthesis_form),
}

FINDING_SEGMENT_LABELS = {"oesophagus": "Oesophagus", "duodenum": "Duodenum", "jejunum": "Jejunum", "ileum": "Ileum", "colon": "Colon"}


def phase_labels() -> dict[str, str]:
    return workflow_phase_labels(get_fsd(TEMPLATE_KEY), {WF_REVIEW: "Review", WF_FINALIZE: "Finalize"})


EDITABLE_PHASE_STATES = list(PHASE_FORMS.keys())
TIMELINE_FORM = capsule_forms.CapsuleTimelineForm

def extract_phase_data(phase_key: str) -> dict:
    if phase_key == "context":
        return {
            "indication_category": request.form.getlist("indication_category"),
            "indication_detail": request.form.get("indication_detail", ""),
            "urgency": request.form.get("urgency", ""),
            "consent_obtained": request.form.get("consent_obtained", ""),
            "prior_gi_surgery": request.form.get("prior_gi_surgery", ""),
            "pacemaker_implant": request.form.get("pacemaker_implant", ""),
            "swallowing_difficulty": request.form.get("swallowing_difficulty", ""),
        }
    if phase_key == "acquisition":
        return {
            "prep_regimen": request.form.get("prep_regimen", ""),
            "prokinetic_given": request.form.get("prokinetic_given", ""),
            "patency_result": request.form.get("patency_result", ""),
            "capsule_type": request.form.get("capsule_type", ""),
            "completion_status": request.form.get("completion_status", ""),
            "gastric_transit_hours": request.form.get("gastric_transit_hours", ""),
        }
    if phase_key == "findings":
        data = {}
        for key in capsule_forms.FINDING_SEGMENT_KEYS:
            data[f"{key}_normal"] = request.form.get(f"{key}_normal", "")
            data[f"{key}_findings"] = request.form.getlist(f"{key}_findings")
            data[f"{key}_detail"] = request.form.get(f"{key}_detail", "")
        return data
    if phase_key == "supplementary":
        return {
            "notes": request.form.get("notes", ""),
        }
    if phase_key == "closure":
        return {
            "procedure_completed": request.form.get("procedure_completed", ""),
            "immediate_complication": request.form.get("immediate_complication", ""),
            "complication_types": request.form.getlist("complication_types"),
            "complication_detail": request.form.get("complication_detail", ""),
            "specimens_sent": request.form.get("specimens_sent", ""),
            "specimen_details": request.form.get("specimen_details", ""),
            "retention_risk": request.form.get("retention_risk", ""),
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
    for seg_key in capsule_forms.FINDING_SEGMENT_KEYS:
        segment_ctx.append(
            {
                "key": seg_key,
                "label": FINDING_SEGMENT_LABELS[seg_key],
                "selected_findings": findings_data.get(f"{seg_key}_findings") or [],
                "show_abnormal": field_visible(fsd, sp, f"{TEMPLATE_KEY}.findings.{seg_key}_findings"),
            }
        )
    ctx = {
        "form": form,
        "report": report,
        "document": document,
        "phase_state": phase_state,
        "phase_label": phase_labels()[phase_state],
        "required_fields": legacy_keys_required_for_phase(fsd, phase_state),
        "indication_choices": vocabulary_choices("capsule_indication_category"),
        "selected_indications": sp.get_legacy_phase("context").get("indication_category") or [],
        "finding_type_choices": vocabulary_choices("capsule_finding_type"),
        "finding_segments": segment_ctx,
        "complication_type_choices": vocabulary_choices("standard_complication_type"),
        "selected_complication_types": sp.get_legacy_phase("closure").get("complication_types") or [],
        "yes_no_choices": capsule_forms.YES_NO_CHOICES,
        "show_complication_types": field_visible(fsd, sp, f"{TEMPLATE_KEY}.closure.complication_types"),
        "show_complication_detail": field_visible(fsd, sp, f"{TEMPLATE_KEY}.closure.complication_detail"),
        "show_specimen_details": field_visible(fsd, sp, f"{TEMPLATE_KEY}.closure.specimen_details"),
    }
    return ctx
