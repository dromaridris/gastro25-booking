"""Internal messaging — Sprint 7C."""

from __future__ import annotations

from app.core.base_model import utcnow
from app.core.exceptions import ValidationError
from app.extensions import db
from app.engines import permission_engine
from app.modules.dept_ops.constants import ALL_MESSAGE_SCOPES, MSG_DEPARTMENT, MSG_DIRECT, MSG_TEAM
from app.modules.dept_ops.models import InternalMessage


def _require(user, permission: str) -> None:
    permission_engine.require(user, permission)


def send_message(
    acting_user,
    *,
    subject: str,
    body: str,
    message_scope: str = MSG_DIRECT,
    recipient_id: int | None = None,
    parent_id: int | None = None,
) -> InternalMessage:
    _require(acting_user, "dept_ops:message")
    if message_scope not in ALL_MESSAGE_SCOPES:
        raise ValidationError(f"Invalid message scope '{message_scope}'.")
    if message_scope == MSG_DIRECT and recipient_id is None:
        raise ValidationError("Direct messages require a recipient.")
    msg = InternalMessage(
        sender_id=acting_user.id,
        recipient_id=recipient_id,
        message_scope=message_scope,
        subject=subject.strip(),
        body=body.strip(),
        parent_id=parent_id,
        department_id=getattr(acting_user, "department_id", 1) or 1,
        created_by_id=acting_user.id,
    )
    db.session.add(msg)
    db.session.commit()
    return msg


def inbox(acting_user) -> list[InternalMessage]:
    _require(acting_user, "dept_ops:view")
    uid = acting_user.id
    return (
        InternalMessage.query.filter_by(is_archived=False)
        .filter(
            db.or_(
                InternalMessage.recipient_id == uid,
                InternalMessage.message_scope == MSG_DEPARTMENT,
                InternalMessage.message_scope == MSG_TEAM,
            )
        )
        .order_by(InternalMessage.created_at.desc())
        .all()
    )


def mark_message_read(acting_user, message: InternalMessage) -> InternalMessage:
    _require(acting_user, "dept_ops:view")
    message.read_at = utcnow()
    db.session.commit()
    return message
