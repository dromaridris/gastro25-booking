"""Branded email template rendering — outbound delivery deferred to future sprint."""

from __future__ import annotations

from flask import render_template

from app.modules.branding_integration.cache import get_cached_template_context

EMAIL_TEMPLATES = {
    "appointment_confirmation": "email/appointment_confirmation.html",
    "password_reset": "email/password_reset.html",
    "account_activation": "email/account_activation.html",
    "notification": "email/notification.html",
    "announcement": "email/announcement.html",
    "report_ready": "email/report_ready.html",
}


def render_email(template_key: str, **extra) -> str:
    if template_key not in EMAIL_TEMPLATES:
        raise ValueError(f"Unknown email template: {template_key}")
    ctx = get_cached_template_context()
    ctx.update(extra)
    return render_template(EMAIL_TEMPLATES[template_key], **ctx)


def render_email_subject(template_key: str, **extra) -> str:
    branding = get_cached_template_context()["branding"]
    subjects = {
        "appointment_confirmation": f"Appointment confirmed — {branding.hospital_name}",
        "password_reset": f"Password reset — {branding.hospital_name}",
        "account_activation": f"Activate your account — {branding.hospital_name}",
        "notification": f"Notification — {branding.hospital_name}",
        "announcement": f"Announcement — {branding.department_name}",
        "report_ready": f"Report ready — {branding.hospital_name}",
    }
    return subjects.get(template_key, branding.display_title)
