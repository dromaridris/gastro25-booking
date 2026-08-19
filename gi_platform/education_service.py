"""Education activity log — lightweight portfolio record."""

from __future__ import annotations


ACTIVITY_TYPES = (
    'journal_club', 'morning_report', 'bedside_teaching', 'conference',
    'workshop', 'self_study', 'other',
)


def list_activities(db, *, user_id: int | None = None) -> list:
    sql = """
        SELECT e.*, u.full_name AS user_name, c.full_name AS created_by_name
        FROM gi_education_activity e
        JOIN user u ON u.id = e.user_id
        LEFT JOIN user c ON c.id = e.created_by
        WHERE e.is_archived = 0
    """
    params: list = []
    if user_id:
        sql += ' AND e.user_id = ?'
        params.append(user_id)
    sql += ' ORDER BY e.activity_date DESC, e.id DESC'
    return db.execute(sql, params).fetchall()


def get_activity(db, activity_id: int):
    return db.execute(
        """
        SELECT e.*, u.full_name AS user_name
        FROM gi_education_activity e
        JOIN user u ON u.id = e.user_id
        WHERE e.id = ? AND e.is_archived = 0
        """,
        (activity_id,),
    ).fetchone()


def create(
    db,
    *,
    user_id: int,
    title: str,
    activity_type: str,
    activity_date: str,
    description: str = '',
    duration_minutes: int | None = None,
    location: str = '',
    created_by: int | None = None,
) -> int:
    if not title.strip():
        raise ValueError('Title is required.')
    atype = activity_type.strip() if activity_type in ACTIVITY_TYPES else 'other'
    cur = db.execute(
        """
        INSERT INTO gi_education_activity
        (user_id, title, activity_type, activity_date, description,
         duration_minutes, location, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            title.strip(),
            atype,
            activity_date,
            (description or '').strip() or None,
            duration_minutes,
            (location or '').strip() or None,
            created_by,
        ),
    )
    db.commit()
    return cur.lastrowid


def archive(db, activity_id: int) -> None:
    db.execute(
        'UPDATE gi_education_activity SET is_archived = 1 WHERE id = ?', (activity_id,)
    )
    db.commit()
