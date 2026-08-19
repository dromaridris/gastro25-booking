"""Clinical documents and consent services."""

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.clinical_documents.consent_seed import seed_consent_templates_if_empty
from app.modules.clinical_documents.models import CONSENT_DRAFT, CONSENT_SIGNED, ConsentRecord, ConsentTemplate


def _require(user, code: str, target_id=None):
    permission_engine.require(user, code, audit_context={"target_type": "ClinicalDocument", "target_id": target_id})


def ensure_templates_seeded() -> None:
    seed_consent_templates_if_empty()


def list_templates(acting_user) -> list[ConsentTemplate]:
    _require(acting_user, "consent:view")
    ensure_templates_seeded()
    return ConsentTemplate.query.filter_by(is_active=True, is_archived=False).order_by(ConsentTemplate.title).all()


def list_consents_for_patient(acting_user, patient_id: int) -> list[ConsentRecord]:
    _require(acting_user, "consent:view")
    return (
        ConsentRecord.query.filter_by(patient_id=patient_id, is_archived=False)
        .order_by(ConsentRecord.created_at.desc())
        .all()
    )


def get_consent(acting_user, record_id: int) -> ConsentRecord:
    _require(acting_user, "consent:view", record_id)
    rec = ConsentRecord.query.get(record_id)
    if rec is None or rec.is_archived:
        raise NotFoundError(f"No consent record with id {record_id}")
    return rec


def create_consent(acting_user, *, template_id: int, patient_id: int,
                   encounter_id: int | None = None, procedure_id: int | None = None) -> ConsentRecord:
    _require(acting_user, "consent:sign")
    template = ConsentTemplate.query.get(template_id)
    if template is None or not template.is_active:
        raise NotFoundError("Consent template not found.")
    rec = ConsentRecord(
        template_id=template_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        procedure_id=procedure_id,
        rendered_html=template.body_html,
        created_by_id=acting_user.id,
    )
    db.session.add(rec)
    db.session.commit()
    audit_engine.log("consent.create", user=acting_user, target_type="consent_record", target_id=rec.id)
    return rec


def sign_consent(acting_user, record_id: int, *, witness_name: str | None = None) -> ConsentRecord:
    _require(acting_user, "consent:sign", record_id)
    rec = get_consent(acting_user, record_id)
    if rec.status == CONSENT_SIGNED:
        raise ValidationError("Consent already signed.")
    rec.status = CONSENT_SIGNED
    rec.signed_at = utcnow()
    rec.signed_by_user_id = acting_user.id
    rec.witness_name = witness_name
    db.session.commit()
    audit_engine.log("consent.sign", user=acting_user, target_type="consent_record", target_id=rec.id)
    return rec
