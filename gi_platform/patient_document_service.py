"""Patient document upload and listing — ward patient scoped."""

from __future__ import annotations

import os
import uuid

from werkzeug.utils import secure_filename

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'patient_documents')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = frozenset({'.pdf', '.jpg', '.jpeg', '.png', '.txt'})
ALLOWED_MIME = frozenset({
    'application/pdf', 'image/jpeg', 'image/png', 'text/plain', 'application/octet-stream',
})


def list_for_patient(db, ward_patient_id: int) -> list:
    return db.execute(
        """
        SELECT d.*, u.full_name AS uploaded_by_name
        FROM gi_patient_document d
        LEFT JOIN user u ON u.id = d.uploaded_by
        WHERE d.ward_patient_id = ? AND d.is_archived = 0
        ORDER BY d.created_at DESC
        """,
        (ward_patient_id,),
    ).fetchall()


def get_document(db, doc_id: int):
    return db.execute(
        'SELECT * FROM gi_patient_document WHERE id = ? AND is_archived = 0', (doc_id,)
    ).fetchone()


def file_path(doc) -> str | None:
    if not doc or not doc['stored_filename']:
        return None
    path = os.path.join(UPLOAD_DIR, doc['stored_filename'])
    return path if os.path.isfile(path) else None


def upload(
    db,
    *,
    ward_patient_id: int,
    title: str,
    file_obj,
    filename: str,
    content_type: str | None = None,
    category: str = 'general',
    notes: str | None = None,
    uploaded_by: int | None = None,
) -> int:
    if not filename:
        raise ValueError('File is required.')
    safe = secure_filename(filename)
    ext = os.path.splitext(safe)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Unsupported file type. Use PDF, JPEG, PNG, or plain text.')
    ct = (content_type or 'application/octet-stream').split(';')[0].strip().lower()
    if ct not in ALLOWED_MIME:
        raise ValueError('Unsupported content type.')

    stored = f'{ward_patient_id}_{uuid.uuid4().hex}{ext}'
    dest = os.path.join(UPLOAD_DIR, stored)
    file_obj.save(dest)
    size = os.path.getsize(dest)

    cur = db.execute(
        """
        INSERT INTO gi_patient_document
        (ward_patient_id, title, category, stored_filename, original_filename,
         content_type, file_size, notes, uploaded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ward_patient_id,
            (title or safe).strip() or safe,
            (category or 'general').strip(),
            stored,
            safe,
            ct,
            size,
            (notes or '').strip() or None,
            uploaded_by,
        ),
    )
    db.commit()
    return cur.lastrowid


def archive(db, doc_id: int) -> None:
    db.execute(
        'UPDATE gi_patient_document SET is_archived = 1 WHERE id = ?', (doc_id,)
    )
    db.commit()
