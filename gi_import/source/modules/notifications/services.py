"""User notification services."""

from app.core.base_model import utcnow
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.notifications.models import UserNotification


def _require(user, code: str):
    permission_engine.require(user, code)


def list_for_user(acting_user, *, unread_only: bool = False, limit: int = 50) -> list[UserNotification]:
    _require(acting_user, "notification:view")
    q = UserNotification.query.filter_by(user_id=acting_user.id, is_archived=False)
    if unread_only:
        q = q.filter_by(is_read=False)
    return q.order_by(UserNotification.created_at.desc()).limit(limit).all()


def unread_count(acting_user) -> int:
    if not permission_engine.check(acting_user, "notification:view"):
        return 0
    return UserNotification.query.filter_by(
        user_id=acting_user.id, is_read=False, is_archived=False
    ).count()


def mark_read(acting_user, notification_id: int) -> UserNotification:
    _require(acting_user, "notification:view")
    note = UserNotification.query.filter_by(id=notification_id, user_id=acting_user.id).first()
    if note is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Notification not found.")
    note.is_read = True
    note.read_at = utcnow()
    db.session.commit()
    return note


def mark_all_read(acting_user) -> int:
    _require(acting_user, "notification:view")
    notes = UserNotification.query.filter_by(user_id=acting_user.id, is_read=False, is_archived=False).all()
    now = utcnow()
    for n in notes:
        n.is_read = True
        n.read_at = now
    db.session.commit()
    return len(notes)


def create_for_user(
    user_id: int,
    *,
    title: str,
    body: str | None = None,
    category: str = "general",
    link_url: str | None = None,
    source_module: str | None = None,
    source_id: int | None = None,
) -> UserNotification:
    note = UserNotification(
        user_id=user_id,
        title=title,
        body=body,
        category=category,
        link_url=link_url,
        source_module=source_module,
        source_id=source_id,
    )
    db.session.add(note)
    db.session.commit()
    audit_engine.log("notification.create", target_type="user_notification", target_id=note.id, details={"user_id": user_id})
    return note
