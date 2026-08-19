"""
Service layer — Standard Endoscopy Report Templates (Sprint 3B).

Uses the frozen Sprint 3A reporting engine for persistence and lifecycle.
This module adds template resolution, scaffolds, structured findings editors,
and procedure-specific print layouts only.
"""

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.modules.report_templates import serializers
from app.modules.report_templates.definitions import (
    TEMPLATE_COLONOSCOPY,
    TEMPLATE_UPPER_GI,
    resolve_template_key,
    scaffold_for,
)
from app.modules.reports import services as report_services
from app.modules.reports.models import (
    ALL_SECTION_KEYS,
    SECTION_FINDINGS,
    SECTION_LABELS,
    Report,
)


def get_template_key_for_report(report: Report) -> str | None:
    procedure = report.procedure
    if procedure is None or procedure.procedure_type is None:
        return None
    return resolve_template_key(procedure.procedure_type)


def require_supported_template(report: Report) -> str:
    template_key = get_template_key_for_report(report)
    if template_key is None:
        raise ValidationError(
            "This procedure type has no standard report template assigned in the "
            "ProcedureType catalogue (report_template_key is unset)."
        )
    return template_key


def open_report_for_session(acting_user, procedure_session_id: int) -> Report:
    report = report_services.get_or_create_report(acting_user, procedure_session_id)
    template_key = require_supported_template(report)
    apply_scaffolds_if_empty(acting_user, report, template_key)
    return report


def apply_scaffolds_if_empty(acting_user, report: Report, template_key: str) -> bool:
    """Populate empty section content with template scaffolds (draft only)."""
    if not report.is_editable:
        return False

    applied = False
    for section_key in ALL_SECTION_KEYS:
        section = report_services.get_section(report, section_key)
        if section.content and section.content.strip():
            continue
        scaffold = scaffold_for(template_key, section_key)
        if not scaffold:
            continue
        report_services.update_section(acting_user, report, section_key, scaffold)
        applied = True

    if applied:
        audit_engine.log(
            action="report_template.scaffolds_applied",
            user=acting_user,
            target_type="Report",
            target_id=report.id,
            details={"template_key": template_key},
        )
    return applied


def get_report(acting_user, report_id: int) -> Report:
    report = report_services.get_report(acting_user, report_id)
    require_supported_template(report)
    return report


def list_supported_reports(acting_user):
    reports = report_services.list_reports(acting_user)
    return [r for r in reports if get_template_key_for_report(r) is not None]


def update_text_section(acting_user, report: Report, section_key: str, content: str):
    if section_key not in SECTION_LABELS:
        raise ValidationError(f"Invalid section key: {section_key}")
    return report_services.update_section(acting_user, report, section_key, content)


def update_findings_section(acting_user, report: Report, template_key: str, data: dict):
    content = serializers.format_findings(template_key, data)
    return report_services.update_section(acting_user, report, SECTION_FINDINGS, content)


def get_findings_data(report: Report, template_key: str) -> dict:
    section = report_services.get_section(report, SECTION_FINDINGS)
    return serializers.parse_findings(template_key, section.content)


def print_template_name(template_key: str) -> str:
    if template_key == TEMPLATE_COLONOSCOPY:
        return "report_templates/print/colonoscopy.html"
    if template_key == TEMPLATE_UPPER_GI:
        return "report_templates/print/upper_gi.html"
    raise NotFoundError(f"No print template for key '{template_key}'")
