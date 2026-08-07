"""Workforce identity dashboards — Phase 7E."""

from __future__ import annotations

from datetime import date

from app.engines import permission_engine
from app.extensions import db
from app.modules.auth.models import User
from app.modules.rbac.models import Role
from app.modules.workforce import analytics_engine, competency_engine
from app.modules.workforce_identity.constants import TRAINING_ROLE_CODES
from app.modules.workforce_identity import duty_services, invitation_services, lifecycle_services, swap_services
from app.modules.workforce_identity.constants import INVITATION_PENDING, STATUS_EXPIRED
from app.modules.workforce_identity.models import TrainingInvitation, UserAccountLifecycle


def get_hod_workforce_dashboard(acting_user) -> dict:
    permission_engine.require(acting_user, "workforce_identity:dashboard_view")
    dept_id = getattr(acting_user, "department_id", 1) or 1
    active_trainees = lifecycle_services.list_active_trainees(department_id=dept_id)
    expiring = lifecycle_services.list_expiring_within(days=7)
    expired = UserAccountLifecycle.query.filter_by(status=STATUS_EXPIRED, is_archived=False).count()
    pending_invitations = TrainingInvitation.query.filter_by(
        status=INVITATION_PENDING, is_archived=False, department_id=dept_id
    ).count()
    today_team = duty_services.get_today_on_call_team(acting_user)
    pending_swaps = swap_services.list_pending_swaps(acting_user)
    dept_summary = analytics_engine.department_summary(dept_id)
    lifecycled_ids = {
        row[0]
        for row in db.session.query(UserAccountLifecycle.user_id)
        .filter(UserAccountLifecycle.is_archived.is_(False))
        .all()
    }
    unconfigured_query = (
        User.query.join(Role, User.role_id == Role.id)
        .filter(
            User.is_archived.is_(False),
            User.department_id == dept_id,
            Role.code.in_(TRAINING_ROLE_CODES),
        )
        .order_by(User.full_name.asc())
    )
    if lifecycled_ids:
        unconfigured_query = unconfigured_query.filter(~User.id.in_(lifecycled_ids))
    unconfigured_training_users = unconfigured_query.all()
    return {
        "active_trainees": active_trainees,
        "expiring_this_week": expiring,
        "expired_accounts": expired,
        "pending_invitations": pending_invitations,
        "today_team": today_team,
        "pending_swaps": pending_swaps,
        "attendance_summary": dept_summary.get("attendance", {}),
        "department_totals": dept_summary.get("department_totals", {}),
        "competency_overview": dept_summary.get("trainee_breakdown", []),
        "unconfigured_training_users": unconfigured_training_users,
    }


def get_coordinator_dashboard(acting_user) -> dict:
    permission_engine.require(acting_user, "workforce_identity:invite_manage")
    invitations = invitation_services.list_invitations(acting_user, status=INVITATION_PENDING)
    expiring = lifecycle_services.list_expiring_within(days=7)
    return {
        "pending_invitations": invitations,
        "expiring_accounts": expiring,
    }
