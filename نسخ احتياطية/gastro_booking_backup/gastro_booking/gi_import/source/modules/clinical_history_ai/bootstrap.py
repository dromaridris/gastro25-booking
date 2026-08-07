"""Bootstrap Clinical History AI integrations."""

from flask import Flask

from app.modules.clinical_intake.hooks import register_intake_extension

from .services import on_complaint_selected


def init_clinical_history_ai(app: Flask) -> None:
    """Register intake hook — does not modify clinical_intake module."""
    _ = app
    register_intake_extension("complaint_selected", on_complaint_selected)
