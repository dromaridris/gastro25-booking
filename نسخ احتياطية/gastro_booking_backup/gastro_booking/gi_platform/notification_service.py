"""In-app notifications for roster publish and governance alerts."""

from __future__ import annotations


def notify_user(db, *, user_id: int, title: str, body: str = '', link_url: str = '') -> int:
    cur = db.execute(
        """
        INSERT INTO gi_user_notification (user_id, title, body, link_url)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, title, body, link_url or None),
    )
    return cur.lastrowid


def list_unread(db, user_id: int, *, limit: int = 20) -> list:
    return db.execute(
        """
        SELECT * FROM gi_user_notification
        WHERE user_id = ? AND is_read = 0
        ORDER BY created_at DESC LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()


def list_all(db, user_id: int, *, limit: int = 50) -> list:
    return db.execute(
        """
        SELECT * FROM gi_user_notification
        WHERE user_id = ?
        ORDER BY created_at DESC LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()


def mark_read(db, notification_id: int, user_id: int) -> None:
    db.execute(
        'UPDATE gi_user_notification SET is_read = 1 WHERE id = ? AND user_id = ?',
        (notification_id, user_id),
    )
    db.commit()


def unread_count(db, user_id: int) -> int:
    row = db.execute(
        'SELECT COUNT(*) AS c FROM gi_user_notification WHERE user_id = ? AND is_read = 0',
        (user_id,),
    ).fetchone()
    return row['c'] if row else 0


_MY_TASKS_FILTER = """
    is_read = 0 AND (
        title LIKE '%@mentioned%'
        OR title LIKE 'Presenter:%'
        OR link_url LIKE '/ward/%'
        OR link_url LIKE '/governance/%'
        OR link_url LIKE '/research/%'
        OR link_url LIKE '/mcq-bank/%'
    )
"""


def has_my_tasks_alert(db, user_id: int) -> bool:
    row = db.execute(
        f'SELECT 1 FROM gi_user_notification WHERE user_id = ? AND {_MY_TASKS_FILTER} LIMIT 1',
        (user_id,),
    ).fetchone()
    return bool(row)


def mark_my_tasks_seen(db, user_id: int) -> None:
    db.execute(
        f'UPDATE gi_user_notification SET is_read = 1 WHERE user_id = ? AND {_MY_TASKS_FILTER}',
        (user_id,),
    )
    db.commit()
