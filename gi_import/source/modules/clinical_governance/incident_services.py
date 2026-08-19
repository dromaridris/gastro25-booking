"""Incident reporting services — Sprint 7D."""

from __future__ import annotations

from datetime import datetime

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.engines import audit_engine, permission_engine
from app.modules.clinical_governance.constants import (
    ALL_INCIDENT_CATEGORIES,
    ALL_INCIDENT_STATUSES,
    ALL_SEVERITIES,
    INCIDENT_OPEN,
    INCIDENT_UNDER_REVIEW,
)
from app.modules.clinical_governance.models import ClinicalIncident


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_incidents(acting_user, *, status: str | None = None) -> list[ClinicalIncident]:
    _require(acting_user, "governance:view")
    query = ClinicalIncident.query.filter_by(is_archived=False)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(ClinicalIncident.incident_date.desc()).all()


def create_incident(
    acting_user,
    *,
    incident_date: datetime,
    category: str,
    severity: str,
    description: str,
    patient_id: int | None = None,
    encounter_id: int | None = None,
    procedure_id: int | None = None,
    is_anonymous: bool = False,
) -> ClinicalIncident:
    _require(acting_user, "governance:incident_create")
    if category not in ALL_INCIDENT_CATEGORIES:
        raise ValidationError(f"Invalid incident category '{category}'.")
    if severity not in ALL_SEVERITIES:
        raise ValidationError(f"Invalid severity '{severity}'.")
    incident = ClinicalIncident(
        incident_date=incident_date,
        patient_id=None if is_anonymous else patient_id,
        encounter_id=encounter_id,
        procedure_id=procedure_id,
        is_anonymous=is_anonymous,
        category=category,
        severity=severity,
        description=description.strip(),
        status=INCIDENT_OPEN,
        reported_by_id=acting_user.id,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(incident)
    db.session.flush()
    audit_engine.log("governance.incident_created", user=acting_user, target_type="clinical_incident", target_id=incident.id)
    db.session.commit()
    return incident


def get_incident(acting_user, incident_id: int) -> ClinicalIncident:
    _require(acting_user, "governance:view")
    incident = ClinicalIncident.query.filter_by(id=incident_id, is_archived=False).first()
    if incident is None:
        raise NotFoundError("Incident not found.")
    return incident


def review_incident(
    acting_user,
    incident: ClinicalIncident,
    *,
    root_cause: str | None = None,
    corrective_action: str | None = None,
    preventive_action: str | None = None,
    status: str = INCIDENT_UNDER_REVIEW,
) -> ClinicalIncident:
    _require(acting_user, "governance:incident_review")
    if status not in ALL_INCIDENT_STATUSES:
        raise ValidationError(f"Invalid status '{status}'.")
    incident.reviewer_id = acting_user.id
    incident.root_cause = root_cause
    incident.corrective_action = corrective_action
    incident.preventive_action = preventive_action
    incident.status = status
    audit_engine.log("governance.incident_reviewed", user=acting_user, target_type="clinical_incident", target_id=incident.id)
    db.session.commit()
    return incident


def close_incident(acting_user, incident: ClinicalIncident) -> ClinicalIncident:
    return review_incident(acting_user, incident, status="closed")
