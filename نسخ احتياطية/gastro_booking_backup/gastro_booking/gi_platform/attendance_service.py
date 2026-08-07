"""Activity-based attendance — any site clinical/academic activity = present."""

from __future__ import annotations

import calendar
from datetime import date, datetime

from gi_platform.constants import ATTENDANCE_ADJUST_TYPES, CLINICAL_STAFF_ROLES


def _month_range(year: int, month: int) -> tuple[str, str]:
    start = date(year, month, 1).isoformat()
    last = calendar.monthrange(year, month)[1]
    end = date(year, month, last).isoformat()
    return start, end


def compute_monthly_attendance(db, *, year: int, month: int) -> list[dict]:
    """Recompute attendance for all clinical staff for a given month."""
    start, end = _month_range(year, month)
    staff = db.execute(
        f"SELECT id, full_name, role FROM user WHERE role IN ({','.join('?' * len(CLINICAL_STAFF_ROLES))}) AND is_approved = 1 ORDER BY full_name",
        tuple(CLINICAL_STAFF_ROLES),
    ).fetchall()

    results = []
    for s in staff:
        activity_days = db.execute(
            """
            SELECT DISTINCT date(created_at) AS d
            FROM gi_portfolio_entry
            WHERE user_id = ? AND date(created_at) BETWEEN ? AND ?
            """,
            (s['id'], start, end),
        ).fetchall()
        active_dates = {r['d'] for r in activity_days}

        adj_rows = db.execute(
            """
            SELECT adjustment_date, adjustment_type FROM gi_attendance_adjustment
            WHERE user_id = ? AND adjustment_date BETWEEN ? AND ?
            """,
            (s['id'], start, end),
        ).fetchall()
        adj_dates = {r['adjustment_date'] for r in adj_rows}

        last_day = calendar.monthrange(year, month)[1]
        present = absent = leave = 0
        for day in range(1, last_day + 1):
            d = date(year, month, day).isoformat()
            if d in adj_dates:
                adj = next(r for r in adj_rows if r['adjustment_date'] == d)
                status = 'leave' if adj['adjustment_type'] == 'leave' else 'adjusted'
                if status == 'leave':
                    leave += 1
            elif d in active_dates:
                status = 'present'
                present += 1
            else:
                if date(year, month, day).weekday() < 5:
                    status = 'absent'
                    absent += 1
                else:
                    continue
            db.execute(
                """
                INSERT INTO gi_attendance_record (user_id, attendance_date, status, activity_count, computed_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(user_id, attendance_date) DO UPDATE SET
                    status = excluded.status,
                    activity_count = excluded.activity_count,
                    computed_at = datetime('now')
                """,
                (s['id'], d, status, 1 if status == 'present' else 0),
            )
        db.commit()
        results.append({
            'user_id': s['id'],
            'full_name': s['full_name'],
            'role': s['role'],
            'present_days': present,
            'absent_days': absent,
            'leave_days': leave,
            'active_days': len(active_dates),
        })
    return results


def add_adjustment(
    db, *, user_id: int, adjustment_date: str, adjustment_type: str,
    hours: float = 8, notes: str = '', approved_by_id: int | None = None,
) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_attendance_adjustment
        (user_id, adjustment_date, adjustment_type, hours, notes, approved_by_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, adjustment_date, adjustment_type, hours, notes, approved_by_id),
    )
    status = 'leave' if adjustment_type == 'leave' else 'adjusted'
    db.execute(
        """
        INSERT INTO gi_attendance_record (user_id, attendance_date, status, activity_count)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(user_id, attendance_date) DO UPDATE SET status = excluded.status
        """,
        (user_id, adjustment_date, status),
    )
    db.commit()
    return cur.lastrowid


def my_attendance(db, user_id: int, *, year: int, month: int) -> list:
    start, end = _month_range(year, month)
    return db.execute(
        """
        SELECT * FROM gi_attendance_record
        WHERE user_id = ? AND attendance_date BETWEEN ? AND ?
        ORDER BY attendance_date
        """,
        (user_id, start, end),
    ).fetchall()
