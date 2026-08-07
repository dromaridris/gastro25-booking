"""ESD template — form aliases."""

from app.modules.clinical_reports.configs.therapeutic_resection_forms import (  # noqa: F401
    EsdResectionForm,
    TherapeuticAccessForm,
    TherapeuticClosureForm,
    TherapeuticContextForm,
    TherapeuticLesionForm,
    TherapeuticSynthesisForm,
    TherapeuticTimelineForm,
    bind_access_form,
    bind_closure_form,
    bind_context_form,
    bind_esd_resection_form,
    bind_lesion_form,
    bind_synthesis_form,
    populate_form_choices,
    YES_NO_CHOICES,
)

EsdContextForm = TherapeuticContextForm
EsdAccessForm = TherapeuticAccessForm
EsdLesionForm = TherapeuticLesionForm
EsdClosureForm = TherapeuticClosureForm
EsdSynthesisForm = TherapeuticSynthesisForm
EsdTimelineForm = TherapeuticTimelineForm
