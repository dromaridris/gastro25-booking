"""User permission grants — roster manager assignments."""

from __future__ import annotations

from gi_platform.constants import (
    PERM_ROSTER_HOUSE_OFFICER, PERM_ROSTER_TRAINEE,
    ROSTER_PERMISSION_LABELS, ROSTER_PERMISSIONS, has_full_access,
)


def has_permission(db, user_id: int | None, permission_code: str) -> bool:
    if not user_id:
        return False
    user = db.execute('SELECT role FROM user WHERE id = ?', (user_id,)).fetchone()
    if user and has_full_access(user['role']):
        return True
    row = db.execute(
        'SELECT 1 FROM gi_user_permission WHERE user_id = ? AND permission_code = ?',
        (user_id, permission_code),
    ).fetchone()
    return bool(row)


def grant_permission(db, user_id: int, permission_code: str, granted_by: int | None) -> None:
    db.execute(
        """
        INSERT OR IGNORE INTO gi_user_permission (user_id, permission_code, granted_by)
        VALUES (?, ?, ?)
        """,
        (user_id, permission_code, granted_by),
    )
    db.commit()


def revoke_permission(db, user_id: int, permission_code: str) -> None:
    db.execute(
        'DELETE FROM gi_user_permission WHERE user_id = ? AND permission_code = ?',
        (user_id, permission_code),
    )
    db.commit()


def list_user_permissions(db, user_id: int) -> list[str]:
    rows = db.execute(
        'SELECT permission_code FROM gi_user_permission WHERE user_id = ?', (user_id,)
    ).fetchall()
    return [r['permission_code'] for r in rows]


def list_all_grants(db) -> list:
    return db.execute(
        """
        SELECT p.*, u.full_name, u.username, u.role,
               g.full_name AS granted_by_name
        FROM gi_user_permission p
        JOIN user u ON u.id = p.user_id
        LEFT JOIN user g ON g.id = p.granted_by
        WHERE p.permission_code IN ({})
        ORDER BY p.permission_code, u.full_name
        """.format(','.join('?' * len(ROSTER_PERMISSIONS))),
        ROSTER_PERMISSIONS,
    ).fetchall()


def permission_label(code: str) -> str:
    return ROSTER_PERMISSION_LABELS.get(code, code)


def can_manage_roster(db, user_id: int | None, roster_type: str) -> bool:
    from gi_platform.constants import ROSTER_TYPE_HOUSE_OFFICER, ROSTER_TYPE_TRAINEE
    perm = PERM_ROSTER_TRAINEE if roster_type == ROSTER_TYPE_TRAINEE else PERM_ROSTER_HOUSE_OFFICER
    return has_permission(db, user_id, perm)
