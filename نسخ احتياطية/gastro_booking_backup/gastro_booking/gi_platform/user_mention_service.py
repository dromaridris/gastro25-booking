"""@username mention helpers for assignment fields."""

from __future__ import annotations

import re

MENTION_RE = re.compile(r'@([a-zA-Z0-9_.-]+)')


def list_mentionable_users(db, *, q: str = '', limit: int = 20) -> list[dict]:
    q = (q or '').strip().lstrip('@')
    sql = """
        SELECT id, username, full_name, role FROM user
        WHERE is_approved = 1
    """
    params: list = []
    if q:
        sql += " AND (username LIKE ? OR full_name LIKE ?)"
        like = f'%{q}%'
        params.extend([like, like])
    sql += " ORDER BY full_name LIMIT ?"
    params.append(limit)
    rows = db.execute(sql, params).fetchall()
    return [{'id': r['id'], 'username': r['username'], 'full_name': r['full_name'], 'role': r['role']} for r in rows]


def parse_mentions(text: str) -> list[str]:
    return list(dict.fromkeys(MENTION_RE.findall(text or '')))


def resolve_mention_usernames(db, text: str) -> list[int]:
    names = [n.strip().lower() for n in parse_mentions(text)]
    if not names:
        # Allow plain comma-separated usernames without @ prefix.
        names = [
            p.strip().lower().lstrip('@')
            for p in (text or '').replace(';', ',').split(',')
            if p.strip()
        ]
    if not names:
        return []
    placeholders = ','.join('?' * len(names))
    rows = db.execute(
        f"SELECT id FROM user WHERE LOWER(username) IN ({placeholders}) AND is_approved = 1",
        names,
    ).fetchall()
    return [r['id'] for r in rows]


def format_mention(username: str) -> str:
    return f'@{username}'


def _mention_snippet(text: str, limit: int = 200) -> str:
    t = (text or '').strip()
    if len(t) <= limit:
        return t
    return t[: limit - 1] + '…'


def _already_notified(db, *, user_id: int, source_module: str, source_id: int) -> bool:
    row = db.execute(
        """
        SELECT 1 FROM gi_training_assignment
        WHERE user_id = ? AND source_module = ? AND source_id = ?
        LIMIT 1
        """,
        (user_id, source_module, source_id),
    ).fetchone()
    return bool(row)


def process_mentions(
    db,
    text: str,
    *,
    context_title: str,
    link_url: str = '',
    source_module: str = 'general',
    source_id: int | None = None,
    actor_id: int | None = None,
    only_user_ids: list[int] | None = None,
) -> int:
    """Notify @mentioned users and add a My Tasks entry. Returns count notified."""
    from gi_platform import notification_service

    if only_user_ids is not None:
        user_ids = only_user_ids
    else:
        user_ids = resolve_mention_usernames(db, text)
    if not user_ids:
        return 0

    exclude: set[int] = set()
    if actor_id:
        exclude.add(actor_id)

    notified = 0
    seen: set[int] = set()
    sid = source_id or 0
    body = _mention_snippet(text)

    for uid in user_ids:
        if uid in exclude or uid in seen:
            continue
        if sid and _already_notified(db, user_id=uid, source_module=source_module, source_id=sid):
            continue
        seen.add(uid)
        notification_service.notify_user(
            db,
            user_id=uid,
            title=f'You were @mentioned in: {context_title}',
            body=body,
            link_url=link_url or None,
        )
        db.execute(
            """
            INSERT INTO gi_training_assignment
            (user_id, assignment_type, source_module, source_id, title, details, assigned_by_id)
            VALUES (?, 'mention', ?, ?, ?, ?, ?)
            """,
            (uid, source_module, sid, context_title, body or None, actor_id),
        )
        notified += 1

    if notified:
        db.commit()
    return notified


def process_mentions_diff(
    db,
    old_text: str,
    new_text: str,
    **kwargs,
) -> int:
    """Notify only newly added @mentions (for edits)."""
    old_ids = set(resolve_mention_usernames(db, old_text or ''))
    new_ids = resolve_mention_usernames(db, new_text or '')
    only_new = [uid for uid in new_ids if uid not in old_ids]
    if not only_new:
        return 0
    return process_mentions(db, new_text, only_user_ids=only_new, **kwargs)


def list_mention_assignments_for_user(db, user_id: int, *, status: str = 'pending', limit: int = 50) -> list:
    return db.execute(
        """
        SELECT a.*, u.full_name AS assigned_by_name
        FROM gi_training_assignment a
        LEFT JOIN user u ON u.id = a.assigned_by_id
        WHERE a.user_id = ? AND a.status = ? AND a.assignment_type = 'mention'
        ORDER BY a.created_at DESC
        LIMIT ?
        """,
        (user_id, status, limit),
    ).fetchall()
