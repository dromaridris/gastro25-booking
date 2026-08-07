"""Clinical Intake RBAC — reuses encounter permissions (no new permission codes)."""

from __future__ import annotations

from app.engines import permission_engine


def require_intake_use(user, *, encounter_id: int | None = None) -> None:
    """Users who can create encounters can use Clinical Intake."""
    permission_engine.require(
        user,
        "encounter:create",
        audit_context={"target_type": "ClinicalIntakeRecord", "target_id": encounter_id},
    )


def require_intake_view(user, *, encounter_id: int | None = None) -> None:
    permission_engine.require(
        user,
        "encounter:view",
        audit_context={"target_type": "ClinicalIntakeRecord", "target_id": encounter_id},
    )


def can_use_intake(user) -> bool:
    return permission_engine.check(user, "encounter:create")


def can_view_intake(user) -> bool:
    return permission_engine.check(user, "encounter:view")
