"""EMR template — form aliases."""

from app.modules.clinical_reports.configs.therapeutic_resection_forms import (  # noqa: F401
    EmrResectionForm,
    TherapeuticAccessForm,
    TherapeuticClosureForm,
    TherapeuticContextForm,
    TherapeuticLesionForm,
    TherapeuticSynthesisForm,
    TherapeuticTimelineForm,
    bind_access_form,
    bind_closure_form,
    bind_context_form,
    bind_emr_resection_form,
    bind_lesion_form,
    bind_synthesis_form,
    populate_form_choices,
    YES_NO_CHOICES,
)

EmrContextForm = TherapeuticContextForm
EmrAccessForm = TherapeuticAccessForm
EmrLesionForm = TherapeuticLesionForm
EmrClosureForm = TherapeuticClosureForm
EmrSynthesisForm = TherapeuticSynthesisForm
EmrTimelineForm = TherapeuticTimelineForm
