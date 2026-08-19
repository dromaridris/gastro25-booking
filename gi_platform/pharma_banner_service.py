"""Pharma / education ticker banner — separate from login promotions."""

from __future__ import annotations

from gi_platform.security_utils import sanitize_link_url

BANNER_PAGES = frozenset({
    'dashboard', 'ward_dashboard', 'ward_patient_view', 'gi_calendar_hub',
})


def list_active(db) -> list:
    return db.execute(
        """
        SELECT * FROM gi_pharma_banner
        WHERE is_active = 1
        ORDER BY sort_order, id
        """
    ).fetchall()


def list_all(db) -> list:
    return db.execute(
        'SELECT * FROM gi_pharma_banner ORDER BY sort_order, id'
    ).fetchall()


def create(db, *, label: str, message: str, link_url: str = '', sort_order: int = 0) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_pharma_banner (label, message, link_url, sort_order)
        VALUES (?, ?, ?, ?)
        """,
        (label.strip(), message.strip(), sanitize_link_url(link_url) or None, sort_order),
    )
    db.commit()
    return cur.lastrowid


def update(db, banner_id: int, **fields) -> None:
    row = db.execute('SELECT id FROM gi_pharma_banner WHERE id = ?', (banner_id,)).fetchone()
    if not row:
        raise ValueError('Banner not found.')
    sets = []
    params = []
    for key in ('label', 'message', 'link_url', 'sort_order', 'is_active'):
        if key in fields:
            val = fields[key]
            if key == 'link_url':
                val = sanitize_link_url(val) or None
            sets.append(f'{key} = ?')
            params.append(val)
    if not sets:
        return
    params.append(banner_id)
    db.execute(f'UPDATE gi_pharma_banner SET {", ".join(sets)} WHERE id = ?', params)
    db.commit()


def delete(db, banner_id: int) -> None:
    db.execute('DELETE FROM gi_pharma_banner WHERE id = ?', (banner_id,))
    db.commit()


def should_show(endpoint: str | None) -> bool:
    return bool(endpoint and endpoint in BANNER_PAGES)
