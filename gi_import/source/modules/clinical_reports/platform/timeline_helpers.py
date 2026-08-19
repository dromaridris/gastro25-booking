"""Timeline helpers for structured clinical reports."""

from datetime import date

from app.modules.reports.models import Report


def procedure_date_for_report(report: Report) -> date:
    """Calendar date used when persisting timeline event timestamps."""
    session = getattr(report, "procedure_session", None)
    if session is not None and session.procedure_start_at:
        return session.procedure_start_at.date()
    procedure = getattr(report, "procedure", None)
    if procedure is not None:
        appointment = getattr(procedure, "appointment", None)
        if appointment is not None and appointment.scheduled_at:
            return appointment.scheduled_at.date()
    return date.today()
