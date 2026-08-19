"""Upper GI v2 template — UI wiring (phase forms, labels, template context)."""

from flask import request

from app.modules.clinical_reports.configs import upper_gi_v2_forms
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
from app.modules.procedures.models import REPORT_TEMPLATE_KEY_UPPER_GI_V2

TEMPLATE_KEY = REPORT_TEMPLATE_KEY_UPPER_GI_V2

PHASE_FORMS = {
    WF_CONTEXT: ("context", upper_gi_v2_forms.UpperGiContextForm, upper_gi_v2_forms.bind_context_form),
    WF_ACCESS: ("procedure", upper_gi_v2_forms.UpperGiProcedureForm, upper_gi_v2_forms.bind_procedure_form),
    WF_IMAGING: ("findings", upper_gi_v2_forms.UpperGiFindingsForm, upper_gi_v2_forms.bind_findings_form),
    WF_THERAPY: ("interventions", upper_gi_v2_forms.UpperGiInterventionsForm, None),
    WF_CLOSURE: ("closure", upper_gi_v2_forms.UpperGiClosureForm, upper_gi_v2_forms.bind_closure_form),
    WF_SYNTHESIS: ("synthesis", upper_gi_v2_forms.UpperGiSynthesisForm, upper_gi_v2_forms.bind_synthesis_form),
}

_WORKFLOW_META_LABELS = {
    WF_REVIEW: "Review",
    WF_FINALIZE: "Finalize",
}


def phase_labels() -> dict[str, str]:
    fsd = get_fsd(TEMPLATE_KEY)
    return workflow_phase_labels(fsd, _WORKFLOW_META_LABELS)


EDITABLE_PHASE_STATES = list(PHASE_FORMS.keys())

TIMELINE_FORM = upper_gi_v2_forms.UpperGiTimelineForm


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
            "d2_reached": request.form.get("d2_reached", ""),
            "retroflexion_performed": request.form.get("retroflexion_performed", ""),
            "limited_exam": request.form.get("limited_exam", ""),
            "limited_exam_reason": request.form.get("limited_exam_reason", ""),
            "procedure_duration_min": request.form.get("procedure_duration_min", ""),
        }
    if phase_key == "findings":
        return {
            "oesophagus_normal": request.form.get("oesophagus_normal", ""),
            "oesophagus_findings": request.form.getlist("oesophagus_findings"),
            "oesophagus_detail": request.form.get("oesophagus_detail", ""),
            "ge_junction_normal": request.form.get("ge_junction_normal", ""),
            "ge_junction_findings": request.form.getlist("ge_junction_findings"),
            "ge_junction_detail": request.form.get("ge_junction_detail", ""),
            "stomach_normal": request.form.get("stomach_normal", ""),
            "stomach_findings": request.form.getlist("stomach_findings"),
            "stomach_detail": request.form.get("stomach_detail", ""),
            "duodenum_normal": request.form.get("duodenum_normal", ""),
            "duodenum_findings": request.form.getlist("duodenum_findings"),
            "duodenum_detail": request.form.get("duodenum_detail", ""),
        }
    if phase_key == "interventions":
        return {"interventions": upper_gi_v2_forms.extract_interventions_from_form(request.form)}
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
    return {
        "form": form,
        "report": report,
        "document": document,
        "phase_state": phase_state,
        "phase_label": labels[phase_state],
        "required_fields": legacy_keys_required_for_phase(fsd, phase_state),
        "indication_choices": vocabulary_choices("upper_gi_indication_category"),
        "selected_indications": sp.get_legacy_phase("context").get("indication_category") or [],
        "sedation_type_choices": vocabulary_choices("sedation_type"),
        "selected_sedation_types": sp.get_legacy_phase("procedure").get("sedation_type") or [],
        "finding_type_choices": vocabulary_choices("upper_gi_finding_type"),
        "selected_oesophagus_findings": sp.get_legacy_phase("findings").get("oesophagus_findings") or [],
        "selected_ge_junction_findings": sp.get_legacy_phase("findings").get("ge_junction_findings") or [],
        "selected_stomach_findings": sp.get_legacy_phase("findings").get("stomach_findings") or [],
        "selected_duodenum_findings": sp.get_legacy_phase("findings").get("duodenum_findings") or [],
        "complication_type_choices": vocabulary_choices("standard_complication_type"),
        "selected_complication_types": sp.get_legacy_phase("closure").get("complication_types") or [],
        "intervention_type_choices": vocabulary_choices("upper_gi_intervention_type"),
        "interventions": sp.get_legacy_phase("interventions").get("interventions") or [],
        "yes_no_choices": upper_gi_v2_forms.YES_NO_CHOICES,
        "show_anticoagulation_management": field_visible(
            fsd, sp, "upper_gi_v2.context.anticoagulation_management"
        ),
        "show_limited_exam_reason": field_visible(fsd, sp, "upper_gi_v2.procedure.limited_exam_reason"),
        "show_oesophagus_abnormal": field_visible(fsd, sp, "upper_gi_v2.findings.oesophagus_findings"),
        "show_ge_junction_abnormal": field_visible(fsd, sp, "upper_gi_v2.findings.ge_junction_findings"),
        "show_stomach_abnormal": field_visible(fsd, sp, "upper_gi_v2.findings.stomach_findings"),
        "show_duodenum_abnormal": field_visible(fsd, sp, "upper_gi_v2.findings.duodenum_findings"),
        "show_complication_types": field_visible(fsd, sp, "upper_gi_v2.closure.complication_types"),
        "show_complication_detail": field_visible(fsd, sp, "upper_gi_v2.closure.complication_detail"),
        "show_specimen_details": field_visible(fsd, sp, "upper_gi_v2.closure.specimen_details"),
    }
