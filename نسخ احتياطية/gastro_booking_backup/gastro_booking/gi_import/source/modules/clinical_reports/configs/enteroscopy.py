"""enteroscopy template bundle."""

from app.modules.clinical_reports.platform.template_schema import build_bundle_from_schema
from app.modules.procedures.models import REPORT_TEMPLATE_KEY_ENTEROSCOPY

TEMPLATE_KEY = REPORT_TEMPLATE_KEY_ENTEROSCOPY


def build_bundle():
    return build_bundle_from_schema(TEMPLATE_KEY)
