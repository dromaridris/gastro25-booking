"""Template UI registry — maps template_key to UI wiring modules."""

from app.modules.procedures.models import (
    REPORT_TEMPLATE_KEY_CAPSULE,
    REPORT_TEMPLATE_KEY_COLONOSCOPY_V2,
    REPORT_TEMPLATE_KEY_EMR,
    REPORT_TEMPLATE_KEY_ENTEROSCOPY,
    REPORT_TEMPLATE_KEY_ERCP,
    REPORT_TEMPLATE_KEY_ESD,
    REPORT_TEMPLATE_KEY_EUS,
    REPORT_TEMPLATE_KEY_FLEX_SIG_V2,
    REPORT_TEMPLATE_KEY_PROCTOSCOPY_V2,
    REPORT_TEMPLATE_KEY_UPPER_GI_V2,
)

_UI_MODULES = {
    REPORT_TEMPLATE_KEY_ERCP: "app.modules.clinical_reports.configs.ercp_ui",
    REPORT_TEMPLATE_KEY_UPPER_GI_V2: "app.modules.clinical_reports.configs.upper_gi_v2_ui",
    REPORT_TEMPLATE_KEY_COLONOSCOPY_V2: "app.modules.clinical_reports.configs.colonoscopy_v2_ui",
    REPORT_TEMPLATE_KEY_FLEX_SIG_V2: "app.modules.clinical_reports.configs.flex_sig_v2_ui",
    REPORT_TEMPLATE_KEY_PROCTOSCOPY_V2: "app.modules.clinical_reports.configs.proctoscopy_v2_ui",
    REPORT_TEMPLATE_KEY_EUS: "app.modules.clinical_reports.configs.eus_ui",
    REPORT_TEMPLATE_KEY_CAPSULE: "app.modules.clinical_reports.configs.capsule_ui",
    REPORT_TEMPLATE_KEY_ENTEROSCOPY: "app.modules.clinical_reports.configs.enteroscopy_ui",
    REPORT_TEMPLATE_KEY_EMR: "app.modules.clinical_reports.configs.emr_ui",
    REPORT_TEMPLATE_KEY_ESD: "app.modules.clinical_reports.configs.esd_ui",
}


def get_ui_module(template_key: str):
    import importlib

    module_path = _UI_MODULES.get(template_key)
    if module_path is None:
        raise KeyError(f"No UI module registered for template '{template_key}'.")
    return importlib.import_module(module_path)


def registered_template_keys() -> tuple[str, ...]:
    return tuple(_UI_MODULES.keys())
