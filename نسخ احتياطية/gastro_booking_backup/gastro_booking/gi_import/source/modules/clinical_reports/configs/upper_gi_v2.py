"""Upper GI v2 template bundle — assembled from schemas/upper_gi_v2.json."""

from app.modules.clinical_reports.platform.template_schema import build_bundle_from_schema
from app.modules.procedures.models import REPORT_TEMPLATE_KEY_UPPER_GI_V2

TEMPLATE_KEY = REPORT_TEMPLATE_KEY_UPPER_GI_V2


def build_bundle():
    return build_bundle_from_schema(TEMPLATE_KEY)
