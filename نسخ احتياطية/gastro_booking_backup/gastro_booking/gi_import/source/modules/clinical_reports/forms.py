"""Backward-compatible re-exports — ERCP forms live in configs/ercp_forms.py."""

from app.modules.clinical_reports.configs.ercp_forms import (  # noqa: F401
    YES_NO_CHOICES,
    ErCpAccessForm,
    ErCpClosureForm,
    ErCpContextForm,
    ErCpImagingForm,
    ErCpSynthesisForm,
    ErCpTherapyForm,
    ErCpTimelineForm,
    bind_access_form,
    bind_closure_form,
    bind_context_form,
    bind_imaging_form,
    bind_synthesis_form,
    extract_interventions_from_form,
    populate_form_choices,
)

# Legacy alias
populate_ercp_form_choices = populate_form_choices
