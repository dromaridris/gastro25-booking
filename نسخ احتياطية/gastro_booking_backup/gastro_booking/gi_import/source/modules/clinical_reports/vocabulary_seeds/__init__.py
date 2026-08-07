"""Aggregated vocabulary seeds from template-specific seed modules."""

from app.modules.clinical_reports.vocabulary_seeds.emr_esd import EMR_ESD_VOCABULARY_SEED
from app.modules.clinical_reports.vocabulary_seeds.advanced_endoscopy import (
    CAPSULE_VOCABULARY_SEED,
    ENTEROSCOPY_VOCABULARY_SEED,
    EUS_VOCABULARY_SEED,
)
from app.modules.clinical_reports.vocabulary_seeds.colonoscopy_v2 import COLONOSCOPY_V2_VOCABULARY_SEED
from app.modules.clinical_reports.vocabulary_seeds.ercp import ERCP_VOCABULARY_SEED
from app.modules.clinical_reports.vocabulary_seeds.flex_proctoscopy_v2 import (
    FLEX_SIG_V2_VOCABULARY_SEED,
    PROCTOSCOPY_V2_VOCABULARY_SEED,
)
from app.modules.clinical_reports.vocabulary_seeds.shared_standard import SHARED_STANDARD_VOCABULARY_SEED
from app.modules.clinical_reports.vocabulary_seeds.upper_gi_v2 import UPPER_GI_V2_VOCABULARY_SEED

SHARED_VOCABULARY_SEED = {
    "yes_no_unknown": [
        ("Yes", "Yes", 10),
        ("No", "No", 20),
        ("Unknown", "Unknown", 30),
    ],
}

VOCABULARY_SEED = {
    **ERCP_VOCABULARY_SEED,
    **SHARED_STANDARD_VOCABULARY_SEED,
    **UPPER_GI_V2_VOCABULARY_SEED,
    **COLONOSCOPY_V2_VOCABULARY_SEED,
    **FLEX_SIG_V2_VOCABULARY_SEED,
    **PROCTOSCOPY_V2_VOCABULARY_SEED,
    **EUS_VOCABULARY_SEED,
    **CAPSULE_VOCABULARY_SEED,
    **ENTEROSCOPY_VOCABULARY_SEED,
    **EMR_ESD_VOCABULARY_SEED,
    **SHARED_VOCABULARY_SEED,
}
