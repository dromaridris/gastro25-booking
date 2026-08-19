"""Login page promotional images — HOD-managed, daily rotation."""

from __future__ import annotations

import os
import random
import re
import uuid
from datetime import date

from gi_platform.security_utils import sanitize_link_url

PROMO_UPLOAD_DIR = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'login_promos'
)
os.makedirs(PROMO_UPLOAD_DIR, exist_ok=True)

MAX_VISIBLE_SLOTS = 4
ALLOWED_EXTENSIONS = frozenset({'.png', '.jpg', '.jpeg', '.webp', '.gif'})


def list_all(db) -> list:
    return db.execute(
        """
        SELECT p.*, u.full_name AS uploaded_by_name
        FROM gi_login_promo_image p
        LEFT JOIN user u ON u.id = p.uploaded_by
        ORDER BY p.created_at DESC
        """
    ).fetchall()


def list_active(db) -> list:
    return db.execute(
        """
        SELECT * FROM gi_login_promo_image
        WHERE is_active = 1
        ORDER BY id
        """
    ).fetchall()


def get_image(db, image_id: int):
    return db.execute(
        'SELECT * FROM gi_login_promo_image WHERE id = ?', (image_id,)
    ).fetchone()


def daily_display_images(db, *, max_slots: int = MAX_VISIBLE_SLOTS) -> list:
    """Pick up to max_slots active images; shuffle seed = today's date."""
    rows = list_active(db)
    if not rows:
        return []
    if len(rows) <= max_slots:
        return list(rows)
    ids = [r['id'] for r in rows]
    rng = random.Random(date.today().isoformat())
    rng.shuffle(ids)
    by_id = {r['id']: r for r in rows}
    return [by_id[i] for i in ids[:max_slots]]


def save_upload(db, file_storage, *, uploaded_by: int | None, label: str = '',
                link_url: str = '') -> int:
    orig = file_storage.filename or 'promo.bin'
    ext = os.path.splitext(orig)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f'Unsupported image type. Allowed: {", ".join(sorted(ALLOWED_EXTENSIONS))}')
    safe = re.sub(r'[^\w.\-]', '_', os.path.splitext(orig)[0])[:40] or 'promo'
    stored = f'{uuid.uuid4().hex}_{safe}{ext}'
    path = os.path.join(PROMO_UPLOAD_DIR, stored)
    file_storage.save(path)
    cur = db.execute(
        """
        INSERT INTO gi_login_promo_image
        (stored_filename, original_filename, label, link_url, uploaded_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (stored, orig, label.strip(), sanitize_link_url(link_url), uploaded_by),
    )
    db.commit()
    return cur.lastrowid


def delete_image(db, image_id: int) -> bool:
    row = get_image(db, image_id)
    if not row:
        return False
    path = os.path.join(PROMO_UPLOAD_DIR, row['stored_filename'])
    if os.path.isfile(path):
        os.remove(path)
    db.execute('DELETE FROM gi_login_promo_image WHERE id = ?', (image_id,))
    db.commit()
    return True


def toggle_active(db, image_id: int, active: bool) -> None:
    db.execute(
        'UPDATE gi_login_promo_image SET is_active = ? WHERE id = ?',
        (1 if active else 0, image_id),
    )
    db.commit()


def file_path(row) -> str | None:
    if not row:
        return None
    path = os.path.join(PROMO_UPLOAD_DIR, row['stored_filename'])
    return path if os.path.isfile(path) else None
