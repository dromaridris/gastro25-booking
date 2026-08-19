"""
Audit Engine — the single reusable entry point for writing audit trail
entries. Every module that performs a state-changing or security-relevant
action (auth, user management, and later reports/research/knowledge
library) calls `audit_engine.log(...)` — no module writes to AuditLog
directly, so the log format and behavior stay consistent as the system
grows.

Design decisions worth knowing about:

1. `log()` commits immediately, in its own right. It does not participate
   in the caller's transaction. This is deliberate: if a request fails
   partway through and rolls back, you still want a record that the
   attempt happened. The tradeoff is that a successful audit log write
   for an action whose OWN commit later fails would leave a log entry
   for something that didn't actually happen — acceptable for Sprint 1A;
   flagged below as a improvement to revisit (e.g. an outbox pattern) if
   audit precision becomes critical enough to justify the complexity.

2. Never raises up into the caller on its own logging failure being the
   ONLY thing that fails — a broken audit write should not be able to
   block a legitimate login. It logs a warning via Python's logging
   module instead. This is a deliberate availability-over-strictness
   tradeoff for this sprint; revisit if audit completeness must be
   guaranteed (e.g. compliance requirement) rather than best-effort.
"""

import logging

from app.extensions import db
from app.modules.audit.models import AuditLog

logger = logging.getLogger(__name__)


def log(
    action: str,
    user=None,
    target_type: str = None,
    target_id: int = None,
    details: dict = None,
    ip_address: str = None,
    department_id: int = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        user_id=getattr(user, "id", None),
        department_id=department_id or getattr(user, "department_id", None),
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
    )
    entry.details = details or {}

    try:
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to write audit log entry for action=%s", action)
        return None

    return entry


def list_recent(limit: int = 100, action_prefix: str = None, user_id: int = None):
    """Read path for the Audit Log viewer UI. Filters are optional so the
    same function serves both 'show me everything' and a narrowed view."""
    query = AuditLog.query.order_by(AuditLog.created_at.desc())
    if action_prefix:
        query = query.filter(AuditLog.action.like(f"{action_prefix}%"))
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    return query.limit(limit).all()
