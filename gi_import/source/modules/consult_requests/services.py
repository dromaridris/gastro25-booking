"""Consult request services."""

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.consult_requests.models import (
    STATUS_ACCEPTED,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_PENDING,
    STATUS_REJECTED,
    ConsultRequest,
)
from app.modules.notifications import services as notification_services


def _require(user, code: str, target_id=None):
    permission_engine.require(user, code, audit_context={"target_type": "ConsultRequest", "target_id": target_id})


def list_requests(acting_user, *, status: str | None = None) -> list[ConsultRequest]:
    _require(acting_user, "consult:view")
    q = ConsultRequest.query.filter_by(is_archived=False)
    if status:
        q = q.filter_by(status=status)
    return q.order_by(ConsultRequest.created_at.desc()).all()


def get_request(acting_user, request_id: int) -> ConsultRequest:
    _require(acting_user, "consult:view", request_id)
    req = ConsultRequest.query.get(request_id)
    if req is None or req.is_archived:
        raise NotFoundError(f"No consult request with id {request_id}")
    return req


def create(acting_user, *, patient_id: int, specialty: str, clinical_question: str,
           urgency: str = "routine", encounter_id: int | None = None) -> ConsultRequest:
    _require(acting_user, "consult:request")
    req = ConsultRequest(
        patient_id=patient_id,
        encounter_id=encounter_id,
        requesting_user_id=acting_user.id,
        specialty=specialty.strip(),
        clinical_question=clinical_question.strip(),
        urgency=urgency,
        created_by_id=acting_user.id,
    )
    db.session.add(req)
    db.session.commit()
    audit_engine.log("consult.create", user=acting_user, target_type="consult_request", target_id=req.id)
    return req


def accept(acting_user, request_id: int) -> ConsultRequest:
    _require(acting_user, "consult:respond", request_id)
    req = get_request(acting_user, request_id)
    if req.status != STATUS_PENDING:
        raise ValidationError("Only pending requests can be accepted.")
    req.status = STATUS_ACCEPTED
    req.assigned_user_id = acting_user.id
    db.session.commit()
    notification_services.create_for_user(
        req.requesting_user_id,
        title=f"Consult accepted: {req.specialty}",
        body=f"Your consult request has been accepted.",
        link_url=f"/consult-requests/{req.id}",
        source_module="consult_requests",
        source_id=req.id,
    )
    audit_engine.log("consult.accept", user=acting_user, target_type="consult_request", target_id=req.id)
    return req


def complete(acting_user, request_id: int, *, response_notes: str) -> ConsultRequest:
    _require(acting_user, "consult:respond", request_id)
    req = get_request(acting_user, request_id)
    if req.status not in (STATUS_PENDING, STATUS_ACCEPTED):
        raise ValidationError("Request cannot be completed in current status.")
    req.status = STATUS_COMPLETED
    req.response_notes = response_notes.strip()
    req.responded_at = utcnow()
    req.assigned_user_id = req.assigned_user_id or acting_user.id
    db.session.commit()
    notification_services.create_for_user(
        req.requesting_user_id,
        title=f"Consult completed: {req.specialty}",
        body=response_notes[:200],
        link_url=f"/consult-requests/{req.id}",
        source_module="consult_requests",
        source_id=req.id,
    )
    audit_engine.log("consult.complete", user=acting_user, target_type="consult_request", target_id=req.id)
    return req


def reject(acting_user, request_id: int, *, reason: str) -> ConsultRequest:
    _require(acting_user, "consult:respond", request_id)
    req = get_request(acting_user, request_id)
    if req.status != STATUS_PENDING:
        raise ValidationError("Only pending requests can be rejected.")
    req.status = STATUS_REJECTED
    req.response_notes = reason.strip()
    req.responded_at = utcnow()
    db.session.commit()
    audit_engine.log("consult.reject", user=acting_user, target_type="consult_request", target_id=req.id)
    return req


def cancel(acting_user, request_id: int) -> ConsultRequest:
    req = get_request(acting_user, request_id)
    if req.requesting_user_id != acting_user.id:
        _require(acting_user, "consult:respond", request_id)
    if req.status in (STATUS_COMPLETED, STATUS_CANCELLED):
        raise ValidationError("Request cannot be cancelled.")
    req.status = STATUS_CANCELLED
    db.session.commit()
    audit_engine.log("consult.cancel", user=acting_user, target_type="consult_request", target_id=req.id)
    return req
