"""Aggregate all GI complaint intelligence bundles for seeding."""

from app.modules.clinical_history.catalogue_bundles_bleeding import BLEEDING_BUNDLES
from app.modules.clinical_history.catalogue_bundles_hepatobiliary import HEPATOBILIARY_BUNDLES
from app.modules.clinical_history.catalogue_bundles_luminal import LUMINAL_BUNDLES
from app.modules.clinical_history.catalogue_diarrhea_intelligence import DIARRHEA_BUNDLE

ALL_INTELLIGENCE_BUNDLES = (
    [DIARRHEA_BUNDLE]
    + BLEEDING_BUNDLES
    + LUMINAL_BUNDLES
    + HEPATOBILIARY_BUNDLES
)
