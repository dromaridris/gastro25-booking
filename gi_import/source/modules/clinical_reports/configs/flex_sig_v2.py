"""Flex sig v2 template bundle."""

from app.modules.clinical_reports.platform.template_schema import build_bundle_from_schema
from app.modules.procedures.models import REPORT_TEMPLATE_KEY_FLEX_SIG_V2

TEMPLATE_KEY = REPORT_TEMPLATE_KEY_FLEX_SIG_V2


def build_bundle():
    return build_bundle_from_schema(TEMPLATE_KEY)
