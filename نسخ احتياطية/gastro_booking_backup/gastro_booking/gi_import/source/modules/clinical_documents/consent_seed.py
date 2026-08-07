"""Consent template seed data."""

from app.extensions import db
from app.modules.clinical_documents.models import ConsentTemplate

DEFAULT_TEMPLATES = [
    ("endoscopy", "Upper GI Endoscopy Consent", "endoscopy"),
    ("colonoscopy", "Colonoscopy Consent", "colonoscopy"),
    ("ercp", "ERCP Consent", "ercp"),
    ("eus", "Endoscopic Ultrasound Consent", "eus"),
    ("liver_biopsy", "Liver Biopsy Consent", "liver_biopsy"),
    ("peg", "PEG Tube Insertion Consent", "peg"),
]

_BODY = """
<p>I consent to the proposed procedure. Risks, benefits, and alternatives have been explained.</p>
<p>I understand I may withdraw consent at any time before the procedure begins.</p>
"""


def seed_consent_templates_if_empty() -> None:
    if ConsentTemplate.query.first():
        return
    for code, title, proc_type in DEFAULT_TEMPLATES:
        db.session.add(
            ConsentTemplate(
                code=code,
                title=title,
                procedure_type=proc_type,
                body_html=_BODY.strip(),
                version=1,
                is_active=True,
            )
        )
    db.session.commit()
