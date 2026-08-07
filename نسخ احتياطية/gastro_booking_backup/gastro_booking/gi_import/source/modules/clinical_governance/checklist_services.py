"""Checklist compliance tracking — Sprint 7D."""

from __future__ import annotations

import json

from app.core.base_model import utcnow
from app.extensions import db
from app.engines import permission_engine
from app.modules.clinical_governance.constants import (
    ALL_CHECKLIST_TYPES,
    CHECKLIST_ENDOSCOPY_SAFETY,
    CHECKLIST_REPROCESSING,
    CHECKLIST_SEDATION,
    CHECKLIST_WHO,
)
from app.modules.clinical_governance.models import ChecklistComplianceRecord
from app.modules.dept_ops.models import ScopeReprocessingCycle
from app.modules.procedure_execution.models import ProcedureSession


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def _endoscopy_safety_complete(session: ProcedureSession) -> bool:
    return all([
        session.consent_confirmed,
        session.identity_confirmed,
        session.indication_confirmed,
        session.anticoagulants_reviewed,
    ])


def record_checklist(
    acting_user,
    checklist_type: str,
    reference_type: str,
    reference_id: int,
    *,
    is_complete: bool,
    items: dict | None = None,
) -> ChecklistComplianceRecord:
    _require(acting_user, "governance:checklist_complete")
    if checklist_type not in ALL_CHECKLIST_TYPES:
        from app.core.exceptions import ValidationError
        raise ValidationError(f"Invalid checklist type '{checklist_type}'.")
    existing = ChecklistComplianceRecord.query.filter_by(
        checklist_type=checklist_type,
        reference_type=reference_type,
        reference_id=reference_id,
        is_archived=False,
    ).first()
    if existing:
        existing.is_complete = is_complete
        existing.completed_at = utcnow() if is_complete else None
        existing.completed_by_id = acting_user.id if is_complete else None
        existing.items_json = json.dumps(items or {})
        db.session.commit()
        return existing
    record = ChecklistComplianceRecord(
        checklist_type=checklist_type,
        reference_type=reference_type,
        reference_id=reference_id,
        is_complete=is_complete,
        completed_at=utcnow() if is_complete else None,
        completed_by_id=acting_user.id if is_complete else None,
        items_json=json.dumps(items or {}),
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(record)
    db.session.commit()
    return record


def sync_endoscopy_safety_from_sessions() -> int:
    """Derive endoscopy safety checklist compliance from ProcedureSession booleans."""
    count = 0
    for session in ProcedureSession.query.filter_by(is_archived=False, is_cancelled=False).all():
        complete = _endoscopy_safety_complete(session)
        existing = ChecklistComplianceRecord.query.filter_by(
            checklist_type=CHECKLIST_ENDOSCOPY_SAFETY,
            reference_type="procedure_session",
            reference_id=session.id,
            is_archived=False,
        ).first()
        if existing:
            if existing.is_complete != complete:
                existing.is_complete = complete
                count += 1
        else:
            db.session.add(
                ChecklistComplianceRecord(
                    checklist_type=CHECKLIST_ENDOSCOPY_SAFETY,
                    reference_type="procedure_session",
                    reference_id=session.id,
                    is_complete=complete,
                    completed_at=session.procedure_start_at if complete else None,
                    department_id=session.department_id,
                )
            )
            count += 1
    db.session.commit()
    return count


def sync_reprocessing_checklists() -> int:
    count = 0
    for cycle in ScopeReprocessingCycle.query.filter_by(status="completed", is_archived=False).all():
        existing = ChecklistComplianceRecord.query.filter_by(
            checklist_type=CHECKLIST_REPROCESSING,
            reference_type="scope_reprocessing_cycle",
            reference_id=cycle.id,
            is_archived=False,
        ).first()
        if not existing:
            db.session.add(
                ChecklistComplianceRecord(
                    checklist_type=CHECKLIST_REPROCESSING,
                    reference_type="scope_reprocessing_cycle",
                    reference_id=cycle.id,
                    is_complete=True,
                    completed_at=cycle.completed_at,
                    department_id=cycle.department_id,
                )
            )
            count += 1
    db.session.commit()
    return count


def compliance_summary(acting_user) -> dict:
    _require(acting_user, "governance:view")
    sync_endoscopy_safety_from_sessions()
    sync_reprocessing_checklists()
    summary = {}
    for ctype in ALL_CHECKLIST_TYPES:
        records = ChecklistComplianceRecord.query.filter_by(checklist_type=ctype, is_archived=False).all()
        total = len(records)
        complete = sum(1 for r in records if r.is_complete)
        summary[ctype] = {
            "total": total,
            "complete": complete,
            "compliance_pct": round(complete * 100 / total, 1) if total else 100.0,
        }
    return summary
