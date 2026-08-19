"""Optional per-user daily MCQ solve target.

Stores enabled + target count, and a rolling "solved today" counter keyed by
local calendar date (YYYY-MM-DD). When the stored date is not today, progress
reads as 0 (and is reset on the next solve). Not a gamification system — just
a counter of questions answered today.
"""
from __future__ import annotations

from datetime import date


DEFAULT_TARGET = 50
MIN_TARGET = 1
MAX_TARGET = 500


def _today() -> str:
    return date.today().isoformat()


def _ensure_row(db, user_id: int) -> None:
    db.execute(
        """INSERT OR IGNORE INTO mcqbank_user_settings (user_id)
           VALUES (?)""",
        (user_id,),
    )


def get_status(db, user_id: int) -> dict:
    """Return daily-target status for UI / API.

    Keys: enabled, target, solved, date, met.
    When disabled, solved/target still reflect stored values so settings UI
    can show them, but templates should hide the counter.
    """
    if not user_id:
        return {
            "enabled": False,
            "target": DEFAULT_TARGET,
            "solved": 0,
            "date": _today(),
            "met": False,
        }

    _ensure_row(db, user_id)
    row = db.execute(
        "SELECT * FROM mcqbank_user_settings WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    today = _today()
    stored_date = row["daily_solved_date"]
    solved = int(row["daily_solved_count"] or 0) if stored_date == today else 0
    # Lazy reset so a stale counter does not linger across days without a solve.
    if stored_date and stored_date != today and int(row["daily_solved_count"] or 0) != 0:
        db.execute(
            """UPDATE mcqbank_user_settings
               SET daily_solved_count = 0, daily_solved_date = ?, updated_at = datetime('now')
               WHERE user_id = ?""",
            (today, user_id),
        )
        db.commit()
        stored_date = today

    target = max(MIN_TARGET, int(row["daily_target_count"] or DEFAULT_TARGET))
    enabled = bool(row["daily_target_enabled"])
    return {
        "enabled": enabled,
        "target": target,
        "solved": solved,
        "date": stored_date or today,
        "met": enabled and solved >= target,
    }


def set_settings(db, user_id: int, *, enabled: bool, target_count: int | None = None) -> dict:
    _ensure_row(db, user_id)
    target = DEFAULT_TARGET if target_count is None else int(target_count)
    target = max(MIN_TARGET, min(MAX_TARGET, target))
    db.execute(
        """UPDATE mcqbank_user_settings
           SET daily_target_enabled = ?, daily_target_count = ?, updated_at = datetime('now')
           WHERE user_id = ?""",
        (1 if enabled else 0, target, user_id),
    )
    db.commit()
    return get_status(db, user_id)


def record_solves(db, user_id: int, n: int = 1) -> dict:
    """Increment today's solved count by n (clamped). Always tracks even if
    the feature is currently disabled, so enabling mid-day still shows progress
    from answers already recorded today."""
    if not user_id or n <= 0:
        return get_status(db, user_id)
    _ensure_row(db, user_id)
    today = _today()
    row = db.execute(
        "SELECT daily_solved_count, daily_solved_date FROM mcqbank_user_settings WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if row["daily_solved_date"] == today:
        new_count = int(row["daily_solved_count"] or 0) + n
    else:
        new_count = n
    db.execute(
        """UPDATE mcqbank_user_settings
           SET daily_solved_count = ?, daily_solved_date = ?, updated_at = datetime('now')
           WHERE user_id = ?""",
        (new_count, today, user_id),
    )
    db.commit()
    return get_status(db, user_id)
