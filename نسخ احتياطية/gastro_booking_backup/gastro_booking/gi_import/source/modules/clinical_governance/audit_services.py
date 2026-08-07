"""Departmental audit project framework — Sprint 7D."""

from __future__ import annotations

import json
from datetime import date

from app.core.exceptions import NotFoundError, ValidationError
from app.extensions import db
from app.engines import audit_engine, permission_engine
from app.modules.clinical_governance.constants import ALL_AUDIT_STATUSES, AUDIT_PLANNED, AUDIT_IN_PROGRESS
from app.modules.clinical_governance.models import AuditProject


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_audits(acting_user, *, status: str | None = None) -> list[AuditProject]:
    _require(acting_user, "governance:view")
    query = AuditProject.query.filter_by(is_archived=False)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(AuditProject.created_at.desc()).all()


def create_audit(
    acting_user,
    *,
    title: str,
    objective: str,
    methodology: str | None = None,
    inclusion_criteria: str | None = None,
    variables: list[str] | None = None,
    timeline_start: date | None = None,
    timeline_end: date | None = None,
    investigator_id: int | None = None,
    research_study_id: int | None = None,
) -> AuditProject:
    _require(acting_user, "governance:audit_manage")
    audit = AuditProject(
        title=title.strip(),
        objective=objective.strip(),
        methodology=methodology,
        inclusion_criteria=inclusion_criteria,
        variables_json=json.dumps(variables or []),
        timeline_start=timeline_start,
        timeline_end=timeline_end,
        status=AUDIT_PLANNED,
        investigator_id=investigator_id or acting_user.id,
        research_study_id=research_study_id,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(audit)
    audit_engine.log("governance.audit_created", user=acting_user, target_type="audit_project", target_id=audit.id)
    db.session.commit()
    return audit


def get_audit(acting_user, audit_id: int) -> AuditProject:
    _require(acting_user, "governance:view")
    audit = AuditProject.query.filter_by(id=audit_id, is_archived=False).first()
    if audit is None:
        raise NotFoundError("Audit project not found.")
    return audit


def update_audit_status(
    acting_user, audit: AuditProject, status: str, findings_summary: str | None = None
) -> AuditProject:
    _require(acting_user, "governance:audit_manage")
    if status not in ALL_AUDIT_STATUSES:
        raise ValidationError(f"Invalid audit status '{status}'.")
    audit.status = status
    if findings_summary:
        audit.findings_summary = findings_summary
    db.session.commit()
    return audit


def link_research_study(acting_user, audit: AuditProject, research_study_id: int) -> AuditProject:
    """Reuse Research Framework for audit variable collection."""
    _require(acting_user, "governance:audit_manage")
    audit.research_study_id = research_study_id
    if audit.status == AUDIT_PLANNED:
        audit.status = AUDIT_IN_PROGRESS
    db.session.commit()
    return audit
