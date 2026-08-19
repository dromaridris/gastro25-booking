"""Shift swap workflow — Phase 7E."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.dept_ops.models import DutyRosterEntry
from app.modules.workforce_identity.constants import (
    SWAP_APPROVED,
    SWAP_CANCELLED,
    SWAP_PENDING,
    SWAP_REJECTED,
)
from app.modules.workforce_identity.models import DutySwapRequest
from app.modules.workforce_identity.roster_integration import apply_swap_to_roster, roster_entry_snapshot


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def create_swap_request(
    acting_user,
    *,
    replacement_user_id: int,
    original_roster_entry_id: int,
    requested_roster_entry_id: int | None = None,
    reason: str,
) -> DutySwapRequest:
    _require(acting_user, "workforce_identity:swap_request")
    original = DutyRosterEntry.query.get(original_roster_entry_id)
    if original is None or original.is_archived:
        raise NotFoundError("Original duty entry not found.")
    if original.user_id != acting_user.id:
        raise ValidationError("You can only request swaps for your own duties.")
    if not reason.strip():
        raise ValidationError("Reason is required.")
    request = DutySwapRequest(
        requesting_user_id=acting_user.id,
        replacement_user_id=replacement_user_id,
        original_roster_entry_id=original_roster_entry_id,
        requested_roster_entry_id=requested_roster_entry_id,
        reason=reason.strip(),
        status=SWAP_PENDING,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(request)
    db.session.commit()
    audit_engine.log(
        action="workforce_identity.swap_requested",
        user=acting_user,
        target_type="DutySwapRequest",
        target_id=request.id,
        details={"original_entry_id": original_roster_entry_id},
    )
    return request


def approve_swap(acting_user, request_id: int, *, notes: str | None = None) -> DutySwapRequest:
    _require(acting_user, "workforce_identity:duty_coordinate")
    request = DutySwapRequest.query.get(request_id)
    if request is None or request.is_archived:
        raise NotFoundError("Swap request not found.")
    if request.status != SWAP_PENDING:
        raise ValidationError("Only pending swap requests can be approved.")
    original = request.original_roster_entry
    if original is None:
        raise NotFoundError("Original roster entry missing.")
    request.schedule_snapshot_before = roster_entry_snapshot(original)
    swap_result = apply_swap_to_roster(original, request.replacement_user_id)
    request.schedule_snapshot_after = swap_result["after"]
    request.status = SWAP_APPROVED
    request.reviewed_by_id = acting_user.id
    request.reviewed_at = datetime.now(timezone.utc)
    request.review_notes = notes
    db.session.commit()
    audit_engine.log(
        action="workforce_identity.swap_approved",
        user=acting_user,
        target_type="DutySwapRequest",
        target_id=request.id,
        details={"before": request.schedule_snapshot_before, "after": request.schedule_snapshot_after},
    )
    return request


def reject_swap(acting_user, request_id: int, *, notes: str | None = None) -> DutySwapRequest:
    _require(acting_user, "workforce_identity:duty_coordinate")
    request = DutySwapRequest.query.get(request_id)
    if request is None or request.is_archived:
        raise NotFoundError("Swap request not found.")
    if request.status != SWAP_PENDING:
        raise ValidationError("Only pending swap requests can be rejected.")
    request.status = SWAP_REJECTED
    request.reviewed_by_id = acting_user.id
    request.reviewed_at = datetime.now(timezone.utc)
    request.review_notes = notes
    db.session.commit()
    audit_engine.log(
        action="workforce_identity.swap_rejected",
        user=acting_user,
        target_type="DutySwapRequest",
        target_id=request.id,
    )
    return request


def cancel_swap(acting_user, request_id: int) -> DutySwapRequest:
    request = DutySwapRequest.query.get(request_id)
    if request is None or request.is_archived:
        raise NotFoundError("Swap request not found.")
    if request.requesting_user_id != acting_user.id:
        _require(acting_user, "workforce_identity:duty_coordinate")
    if request.status != SWAP_PENDING:
        raise ValidationError("Only pending swap requests can be cancelled.")
    request.status = SWAP_CANCELLED
    db.session.commit()
    audit_engine.log(
        action="workforce_identity.swap_cancelled",
        user=acting_user,
        target_type="DutySwapRequest",
        target_id=request.id,
    )
    return request


def list_pending_swaps(acting_user) -> list[DutySwapRequest]:
    _require(acting_user, "workforce_identity:duty_coordinate")
    return (
        DutySwapRequest.query.filter_by(status=SWAP_PENDING, is_archived=False)
        .order_by(DutySwapRequest.created_at.asc())
        .all()
    )


def list_user_swaps(user) -> list[DutySwapRequest]:
    return (
        DutySwapRequest.query.filter(
            DutySwapRequest.is_archived.is_(False),
            or_(
                DutySwapRequest.requesting_user_id == user.id,
                DutySwapRequest.replacement_user_id == user.id,
            ),
        )
        .order_by(DutySwapRequest.created_at.desc())
        .all()
    )
