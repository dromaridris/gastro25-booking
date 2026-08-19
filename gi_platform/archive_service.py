"""Clinical archive records — lightweight storage index."""

from __future__ import annotations

import os
import uuid

from werkzeug.utils import secure_filename

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'archive')
os.makedirs(UPLOAD_DIR, exist_ok=True)

RECORD_TYPES = ('document', 'report', 'image', 'export', 'other')


def list_records(db, *, record_type: str | None = None) -> list:
    sql = """
        SELECT a.*, u.full_name AS archived_by_name
        FROM gi_archive_record a
        LEFT JOIN user u ON u.id = a.archived_by
        WHERE 1=1
    """
    params: list = []
    if record_type:
        sql += ' AND a.record_type = ?'
        params.append(record_type)
    sql += ' ORDER BY a.archived_at DESC'
    return db.execute(sql, params).fetchall()


def get_record(db, record_id: int):
    return db.execute(
        'SELECT * FROM gi_archive_record WHERE id = ?', (record_id,)
    ).fetchone()


def file_path(record) -> str | None:
    if not record or not record['stored_path']:
        return None
    path = os.path.join(UPLOAD_DIR, record['stored_path'])
    return path if os.path.isfile(path) else None


def create(
    db,
    *,
    record_type: str,
    source_module: str,
    title: str,
    summary: str = '',
    source_id: int | None = None,
    file_obj=None,
    filename: str = '',
    archived_by: int | None = None,
) -> int:
    rtype = record_type if record_type in RECORD_TYPES else 'other'
    stored = None
    if file_obj and filename:
        safe = secure_filename(filename)
        ext = os.path.splitext(safe)[1]
        stored = f'{uuid.uuid4().hex}{ext}'
        file_obj.save(os.path.join(UPLOAD_DIR, stored))
    cur = db.execute(
        """
        INSERT INTO gi_archive_record
        (record_type, source_module, source_id, title, summary, stored_path, archived_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rtype,
            source_module.strip(),
            source_id,
            title.strip(),
            (summary or '').strip() or None,
            stored,
            archived_by,
        ),
    )
    db.commit()
    return cur.lastrowid
