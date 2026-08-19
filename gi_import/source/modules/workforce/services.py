"""Workforce services — verification, attendance adjustments, portfolio sync."""

from __future__ import annotations

from datetime import date

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.auth.models import User
from app.modules.workforce.analytics_engine import user_kpis
from app.modules.workforce.attendance_engine import attendance_score
from app.modules.workforce.constants import (
    ALL_ADJUSTMENT_TYPES,
    VERIFY_DEPARTMENT,
    VERIFY_DRAFT,
    VERIFY_LOCKED,
    VERIFY_SUPERVISOR,
)
from app.modules.workforce.models import AttendanceAdjustment, PortfolioEntry
from app.modules.workforce.competency_engine import competency_progress_for_user, seed_competency_standards
from app.modules.workforce.portfolio_engine import sync_portfolio


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def _get_entry(entry_id: int) -> PortfolioEntry:
    entry = PortfolioEntry.query.filter_by(id=entry_id, is_archived=False).first()
    if entry is None:
        raise NotFoundError("Portfolio entry not found.")
    return entry


def sync_user_portfolio(acting_user, user_id: int | None = None) -> dict:
    _require(acting_user, "workforce:view_own")
    target_id = user_id or acting_user.id
    if target_id != acting_user.id and not permission_engine.check(acting_user, "workforce:view_department"):
        raise PermissionDeniedError("Cannot sync another user's portfolio.")
    return sync_portfolio(target_id)


def list_portfolio(acting_user, user_id: int | None = None, *, limit: int = 100) -> list[PortfolioEntry]:
    _require(acting_user, "workforce:view_own")
    target_id = user_id or acting_user.id
    if target_id != acting_user.id:
        _require(acting_user, "workforce:view_department")
    sync_portfolio(target_id)
    return (
        PortfolioEntry.query.filter_by(user_id=target_id, is_archived=False)
        .order_by(PortfolioEntry.activity_at.desc())
        .limit(limit)
        .all()
    )


def verify_supervisor(acting_user, entry_id: int) -> PortfolioEntry:
    _require(acting_user, "workforce:supervise")
    entry = _get_entry(entry_id)
    if entry.verification_status not in {VERIFY_DRAFT, VERIFY_SUPERVISOR}:
        raise ValidationError("Entry cannot be supervisor-verified in its current state.")
    entry.verification_status = VERIFY_SUPERVISOR
    entry.supervisor_verified_by_id = acting_user.id
    entry.supervisor_verified_at = utcnow()
    db.session.commit()
    audit_engine.log("workforce.supervisor_verified", user=acting_user, target_type="portfolio_entry", target_id=entry.id)
    return entry


def verify_department(acting_user, entry_id: int) -> PortfolioEntry:
    _require(acting_user, "workforce:verify_department")
    entry = _get_entry(entry_id)
    if entry.verification_status not in {VERIFY_SUPERVISOR, VERIFY_DEPARTMENT}:
        raise ValidationError("Entry must be supervisor-verified before department verification.")
    entry.verification_status = VERIFY_DEPARTMENT
    entry.department_verified_by_id = acting_user.id
    entry.department_verified_at = utcnow()
    db.session.commit()
    audit_engine.log("workforce.department_verified", user=acting_user, target_type="portfolio_entry", target_id=entry.id)
    return entry


def lock_entry(acting_user, entry_id: int) -> PortfolioEntry:
    _require(acting_user, "workforce:verify_department")
    entry = _get_entry(entry_id)
    if entry.verification_status == VERIFY_DRAFT:
        raise ValidationError("Cannot lock an unverified entry.")
    entry.verification_status = VERIFY_LOCKED
    entry.locked_at = utcnow()
    db.session.commit()
    return entry


def create_attendance_adjustment(
    acting_user,
    *,
    user_id: int,
    adjustment_date: date,
    adjustment_type: str,
    hours: float = 8.0,
    notes: str | None = None,
) -> AttendanceAdjustment:
    _require(acting_user, "workforce:adjust_attendance")
    if adjustment_type not in ALL_ADJUSTMENT_TYPES:
        raise ValidationError(f"Invalid adjustment type '{adjustment_type}'.")
    adj = AttendanceAdjustment(
        user_id=user_id,
        adjustment_date=adjustment_date,
        adjustment_type=adjustment_type,
        hours=hours,
        notes=notes,
        approved_by_id=acting_user.id,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(adj)
    db.session.commit()
    audit_engine.log(
        "workforce.attendance_adjusted",
        user=acting_user,
        target_type="attendance_adjustment",
        target_id=adj.id,
        details={"user_id": user_id, "type": adjustment_type},
    )
    return adj


def get_performance(acting_user, user_id: int | None = None) -> dict:
    _require(acting_user, "workforce:view_own")
    target_id = user_id or acting_user.id
    if target_id != acting_user.id:
        _require(acting_user, "workforce:view_department")
    sync_portfolio(target_id)
    seed_competency_standards()
    return {
        "kpis": user_kpis(target_id),
        "competencies": competency_progress_for_user(target_id, official_only=True),
        "competency_summary": competency_progress_for_user(target_id, official_only=False),
        "procedure_totals": competency_progress_for_user(target_id, official_only=False),
        "attendance": attendance_score(target_id),
    }


def list_department_trainees(acting_user) -> list[User]:
    _require(acting_user, "workforce:view_department")
    from app.modules.workforce.constants import TRAINEE_ROLE_CODES

    users = User.query.filter_by(is_archived=False, department_id=acting_user.department_id or 1).all()
    return [u for u in users if u.role and u.role.code in TRAINEE_ROLE_CODES]
