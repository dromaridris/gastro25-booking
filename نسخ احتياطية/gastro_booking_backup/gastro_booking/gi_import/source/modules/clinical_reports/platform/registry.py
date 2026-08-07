"""Template configuration registry — loads bundles by report_template_key."""

import importlib

from app.core.exceptions import NotFoundError
from app.modules.clinical_reports.platform.bundle_types import TemplateBundle
from app.modules.clinical_reports.platform.template_schema import build_bundle_from_schema
from app.modules.procedures.models import REPORT_TEMPLATE_KEY_ERCP, STRUCTURED_CLINICAL_REPORT_TEMPLATE_KEYS

TEMPLATE_ERCP = REPORT_TEMPLATE_KEY_ERCP

TEMPLATE_LABELS = {
    TEMPLATE_ERCP: "ERCP Structured Clinical Report",
    "upper_gi_v2": "Upper GI Endoscopy — Structured Clinical Report",
    "colonoscopy_v2": "Colonoscopy — Structured Clinical Report",
    "flex_sig_v2": "Flexible Sigmoidoscopy — Structured Clinical Report",
    "proctoscopy_v2": "Proctoscopy — Structured Clinical Report",
    "eus": "EUS — Structured Clinical Report",
    "capsule": "Capsule Endoscopy — Structured Clinical Report",
    "enteroscopy": "Device-assisted Enteroscopy — Structured Clinical Report",
    "emr": "EMR — Structured Clinical Report",
    "esd": "ESD — Structured Clinical Report",
}

STRUCTURED_TEMPLATE_KEYS = STRUCTURED_CLINICAL_REPORT_TEMPLATE_KEYS


def _bundle_for(key: str) -> TemplateBundle:
    if not is_structured_template_key(key):
        raise NotFoundError(f"No clinical report template configuration for key '{key}'.")
    try:
        module = importlib.import_module(f"app.modules.clinical_reports.configs.{key}")
        if hasattr(module, "build_bundle"):
            return module.build_bundle()
    except ImportError:
        pass
    return build_bundle_from_schema(key)


def load_bundle(template_key: str) -> TemplateBundle:
    return _bundle_for(template_key)


def is_structured_template_key(template_key: str | None) -> bool:
    return template_key in STRUCTURED_TEMPLATE_KEYS


def resolve_structured_template_key(procedure_type) -> str | None:
    if procedure_type is None:
        return None
    key = getattr(procedure_type, "report_template_key", None)
    if is_structured_template_key(key):
        return key
    return None
