"""Department announcements — Sprint 7C."""

from __future__ import annotations

from datetime import datetime

from app.core.base_model import utcnow
from app.core.exceptions import ValidationError
from app.extensions import db
from app.engines import permission_engine
from app.modules.dept_ops.constants import ALL_ANNOUNCEMENT_CATEGORIES
from app.modules.dept_ops.models import AnnouncementReadReceipt, DepartmentAnnouncement


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def list_announcements(acting_user, *, include_expired: bool = False) -> list[DepartmentAnnouncement]:
    _require(acting_user, "dept_ops:view")
    query = DepartmentAnnouncement.query.filter_by(is_archived=False).order_by(
        DepartmentAnnouncement.created_at.desc()
    )
    if not include_expired:
        now = utcnow()
        query = query.filter(
            db.or_(DepartmentAnnouncement.expires_at.is_(None), DepartmentAnnouncement.expires_at >= now)
        )
    return query.all()


def publish_announcement(
    acting_user,
    *,
    title: str,
    body: str,
    category: str,
    priority: str = "normal",
    expires_at: datetime | None = None,
) -> DepartmentAnnouncement:
    _require(acting_user, "dept_ops:announce")
    if category not in ALL_ANNOUNCEMENT_CATEGORIES:
        raise ValidationError(f"Invalid announcement category '{category}'.")
    ann = DepartmentAnnouncement(
        title=title.strip(),
        body=body.strip(),
        category=category,
        priority=priority,
        expires_at=expires_at,
        published_by_id=acting_user.id,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(ann)
    db.session.commit()
    return ann


def mark_announcement_read(acting_user, announcement_id: int) -> AnnouncementReadReceipt:
    _require(acting_user, "dept_ops:view")
    existing = AnnouncementReadReceipt.query.filter_by(
        announcement_id=announcement_id, user_id=acting_user.id
    ).first()
    if existing:
        return existing
    receipt = AnnouncementReadReceipt(
        announcement_id=announcement_id,
        user_id=acting_user.id,
        read_at=utcnow(),
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(receipt)
    db.session.commit()
    return receipt


def unread_announcements(acting_user) -> list[DepartmentAnnouncement]:
    all_active = list_announcements(acting_user)
    read_ids = {
        r.announcement_id
        for r in AnnouncementReadReceipt.query.filter_by(user_id=acting_user.id).all()
    }
    return [a for a in all_active if a.id not in read_ids]
