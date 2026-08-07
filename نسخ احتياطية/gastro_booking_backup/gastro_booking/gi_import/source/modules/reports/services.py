"""
Service layer — Generic Endoscopy Reporting Engine (Sprint 3A).

Depends on frozen ProcedureSession / Procedure data but does not modify
those modules. Uses existing RBAC permissions:

- report:view — list and view reports
- report:draft — create reports and edit draft content
- report:sign — finalize, lock, and unlock reports
"""

from datetime import datetime, timezone

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.auth.models import User
from app.modules.department.models import Department
from app.modules.procedure_execution.models import ProcedureSession
from app.modules.reports.models import (
    ALL_SECTION_KEYS,
    SECTION_LABELS,
    STATUS_DRAFT,
    STATUS_FINALIZED,
    STATUS_LOCKED,
    Report,
    ReportNumberCounter,
    ReportSection,
)


def _utcnow():
    return datetime.now(timezone.utc)


def _department_id_for(acting_user, department_id=None):
    return department_id or getattr(acting_user, "department_id", None)


def _require_view(acting_user):
    permission_engine.require(acting_user, "report:view")


def _require_draft(acting_user, report: Report = None):
    ctx = {"target_type": "Report"}
    if report is not None:
        ctx["target_id"] = report.id
    permission_engine.require(acting_user, "report:draft", audit_context=ctx)


def _require_sign(acting_user, report: Report = None):
    ctx = {"target_type": "Report"}
    if report is not None:
        ctx["target_id"] = report.id
    permission_engine.require(acting_user, "report:sign", audit_context=ctx)


def _raise_if_not_editable(report: Report) -> None:
    if report.status != STATUS_DRAFT:
        raise ValidationError(
            f"Report is '{report.status}' — only draft reports can be edited. "
            "Unlock a locked report first if re-editing is required."
        )


def _generate_report_number(department: Department) -> str:
    counter = (
        ReportNumberCounter.query.filter_by(department_id=department.id)
        .with_for_update()
        .first()
    )
    if counter is None:
        counter = ReportNumberCounter(department_id=department.id, next_value=1)
        db.session.add(counter)
        db.session.flush()

    sequence_value = counter.next_value
    counter.next_value = sequence_value + 1
    db.session.commit()
    return f"RPT-{department.code}-{sequence_value:06d}"


def _resolve_session(procedure_session_id: int) -> ProcedureSession:
    session = ProcedureSession.query.get(procedure_session_id)
    if session is None or session.is_archived:
        raise NotFoundError(f"No procedure session with id {procedure_session_id}")
    if session.is_cancelled:
        raise ValidationError("Cannot create a report for a cancelled procedure session.")
    return session


def _resolve_consultant(user_id):
    if user_id is None:
        return None
    user = User.query.get(user_id)
    if user is None or user.is_archived or not user.is_active_account:
        raise ValidationError("Invalid supervising consultant.")
    return user


def _team_summary(session: ProcedureSession) -> str:
    parts = []
    mapping = [
        ("Endoscopist", session.endoscopist),
        ("Assistant", session.assistant),
        ("Nurse", session.nurse),
        ("Technician", session.technician),
        ("Anaesthetist", session.anaesthetist),
    ]
    for label, user in mapping:
        if user is not None:
            parts.append(f"{label}: {user.full_name}")
    return "; ".join(parts) if parts else "—"


def _sedation_label(value: str) -> str:
    if not value:
        return "—"
    return value.replace("_", " ").title()


def build_live_header(report: Report) -> dict:
    """Header for draft viewing — live data from linked clinical records."""
    session = report.procedure_session
    procedure = report.procedure
    patient = report.patient
    appointment = report.appointment
    endoscopist = session.endoscopist if session else None
    if endoscopist is None and procedure is not None:
        endoscopist = procedure.endoscopist

    return {
        "report_number": report.report_number,
        "patient_name": patient.full_name if patient else "—",
        "patient_mrn": patient.mrn if patient else "—",
        "procedure_type": procedure.procedure_type.name if procedure and procedure.procedure_type else "—",
        "procedure_date": appointment.scheduled_at if appointment else None,
        "room": procedure.room.name if procedure and procedure.room else "—",
        "endoscopist": endoscopist.full_name if endoscopist else "—",
        "team_summary": _team_summary(session) if session else "—",
        "sedation_category": _sedation_label(session.sedation_category if session else None),
        "author": report.author.full_name if report.author else "—",
        "supervising_consultant": (
            report.supervising_consultant.full_name if report.supervising_consultant else "—"
        ),
    }


def build_print_header(report: Report) -> dict:
    """Header for print — snapshot after finalize, live header while draft."""
    if report.status == STATUS_DRAFT:
        return build_live_header(report)
    return {
        "report_number": report.report_number,
        "patient_name": report.header_patient_name or "—",
        "patient_mrn": report.header_patient_mrn or "—",
        "procedure_type": report.header_procedure_type or "—",
        "procedure_date": report.header_procedure_date,
        "room": report.header_room_name or "—",
        "endoscopist": report.header_endoscopist_name or "—",
        "team_summary": report.header_team_summary or "—",
        "sedation_category": _sedation_label(report.header_sedation_category),
        "author": report.author.full_name if report.author else "—",
        "supervising_consultant": (
            report.supervising_consultant.full_name if report.supervising_consultant else "—"
        ),
    }


def _snapshot_header(report: Report) -> None:
    live = build_live_header(report)
    report.header_patient_name = live["patient_name"]
    report.header_patient_mrn = live["patient_mrn"]
    report.header_procedure_type = live["procedure_type"]
    report.header_procedure_date = live["procedure_date"]
    report.header_room_name = live["room"]
    report.header_endoscopist_name = live["endoscopist"]
    report.header_team_summary = live["team_summary"]
    session = report.procedure_session
    report.header_sedation_category = session.sedation_category if session else None


def get_report(acting_user, report_id: int) -> Report:
    _require_view(acting_user)
    report = Report.query.get(report_id)
    if report is None:
        raise NotFoundError(f"No report with id {report_id}")
    return report


def get_report_for_session(acting_user, procedure_session_id: int) -> Report:
    _require_view(acting_user)
    report = Report.query.filter_by(procedure_session_id=procedure_session_id).first()
    if report is None:
        raise NotFoundError(f"No report for procedure session {procedure_session_id}")
    return report


def list_reports(acting_user, include_archived: bool = False):
    _require_view(acting_user)
    query = Report.query
    if not include_archived:
        query = query.filter_by(is_archived=False)
    return query.order_by(Report.created_at.desc()).all()


def create_report(
    acting_user,
    procedure_session_id: int,
    supervising_consultant_id: int = None,
    department_id: int = None,
) -> Report:
    _require_draft(acting_user)
    session = _resolve_session(procedure_session_id)

    existing = Report.query.filter_by(procedure_session_id=session.id).first()
    if existing is not None:
        raise ValidationError(
            f"Procedure session {session.id} already has report {existing.report_number}."
        )

    dept_id = _department_id_for(acting_user, department_id)
    department = Department.query.get(dept_id)
    if department is None:
        raise ValidationError("Invalid department.")

    consultant = _resolve_consultant(supervising_consultant_id)
    report_number = _generate_report_number(department)

    report = Report(
        report_number=report_number,
        procedure_session_id=session.id,
        patient_id=session.patient_id,
        appointment_id=session.appointment_id,
        procedure_id=session.procedure_id,
        status=STATUS_DRAFT,
        author_id=getattr(acting_user, "id", None),
        supervising_consultant_id=consultant.id if consultant else None,
        last_modified_by_id=getattr(acting_user, "id", None),
        department_id=department.id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(report)
    db.session.flush()

    for key in ALL_SECTION_KEYS:
        db.session.add(
            ReportSection(
                report_id=report.id,
                section_key=key,
                content="",
                department_id=department.id,
                created_by_id=getattr(acting_user, "id", None),
            )
        )

    db.session.commit()

    audit_engine.log(
        action="report.created",
        user=acting_user,
        target_type="Report",
        target_id=report.id,
        details={
            "report_number": report.report_number,
            "procedure_session_id": session.id,
            "procedure_id": session.procedure_id,
        },
    )
    return report


def get_or_create_report(acting_user, procedure_session_id: int) -> Report:
    try:
        return get_report_for_session(acting_user, procedure_session_id)
    except NotFoundError:
        return create_report(acting_user, procedure_session_id)


def update_supervising_consultant(
    acting_user, report: Report, supervising_consultant_id: int = None
) -> Report:
    _require_draft(acting_user, report)
    _raise_if_not_editable(report)

    before = report.supervising_consultant_id
    consultant = _resolve_consultant(supervising_consultant_id)
    report.supervising_consultant_id = consultant.id if consultant else None
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="report.supervising_consultant_updated",
        user=acting_user,
        target_type="Report",
        target_id=report.id,
        details={"before": before, "after": report.supervising_consultant_id},
    )
    return report


def update_section(acting_user, report: Report, section_key: str, content: str) -> ReportSection:
    _require_draft(acting_user, report)
    _raise_if_not_editable(report)

    if section_key not in ALL_SECTION_KEYS:
        raise ValidationError(f"Invalid section key: {section_key}")

    section = ReportSection.query.filter_by(report_id=report.id, section_key=section_key).first()
    if section is None:
        raise NotFoundError(f"Section '{section_key}' not found on this report.")

    before = section.content
    section.content = content or ""
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="report.section_updated",
        user=acting_user,
        target_type="Report",
        target_id=report.id,
        details={
            "section_key": section_key,
            "section_label": SECTION_LABELS.get(section_key, section_key),
            "before_length": len(before or ""),
            "after_length": len(section.content or ""),
        },
    )
    return section


def get_section(report: Report, section_key: str) -> ReportSection:
    section = ReportSection.query.filter_by(report_id=report.id, section_key=section_key).first()
    if section is None:
        raise NotFoundError(f"Section '{section_key}' not found.")
    return section


def finalize_report(acting_user, report: Report) -> Report:
    _require_sign(acting_user, report)
    if report.status != STATUS_DRAFT:
        raise ValidationError(f"Only draft reports can be finalized (current: '{report.status}').")

    _snapshot_header(report)
    now = _utcnow()
    report.status = STATUS_FINALIZED
    report.finalized_by_id = getattr(acting_user, "id", None)
    report.finalized_at = now
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="report.finalized",
        user=acting_user,
        target_type="Report",
        target_id=report.id,
        details={"report_number": report.report_number, "finalized_at": now.isoformat()},
    )
    from app.modules.workforce.portfolio_events import on_report_finalized

    on_report_finalized(report, acting_user)
    return report


def lock_report(acting_user, report: Report) -> Report:
    _require_sign(acting_user, report)
    if report.status != STATUS_FINALIZED:
        raise ValidationError(
            f"Only finalized reports can be locked (current: '{report.status}')."
        )

    now = _utcnow()
    report.status = STATUS_LOCKED
    report.locked_by_id = getattr(acting_user, "id", None)
    report.locked_at = now
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="report.locked",
        user=acting_user,
        target_type="Report",
        target_id=report.id,
        details={"report_number": report.report_number, "locked_at": now.isoformat()},
    )
    return report


def unlock_report(acting_user, report: Report) -> Report:
    _require_sign(acting_user, report)
    if report.status != STATUS_LOCKED:
        raise ValidationError(f"Only locked reports can be unlocked (current: '{report.status}').")

    old_status = report.status
    report.status = STATUS_DRAFT
    report.locked_by_id = None
    report.locked_at = None
    report.finalized_by_id = None
    report.finalized_at = None
    report.last_modified_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="report.unlocked",
        user=acting_user,
        target_type="Report",
        target_id=report.id,
        details={"report_number": report.report_number, "previous_status": old_status},
    )
    return report


def archive_report(acting_user, report: Report, reason: str = None) -> Report:
    _require_sign(acting_user, report)
    report.archive(by_user_id=getattr(acting_user, "id", None), reason=reason)
    db.session.commit()

    audit_engine.log(
        action="report.archived",
        user=acting_user,
        target_type="Report",
        target_id=report.id,
        details={"reason": reason},
    )
    return report


def restore_report(acting_user, report: Report) -> Report:
    _require_sign(acting_user, report)
    report.restore()
    db.session.commit()

    audit_engine.log(
        action="report.restored",
        user=acting_user,
        target_type="Report",
        target_id=report.id,
    )
    return report
