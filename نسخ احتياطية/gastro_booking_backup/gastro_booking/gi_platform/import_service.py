"""Import manager — job queue with background-style processing."""

from __future__ import annotations

import json
import os
import re
import uuid

IMPORT_UPLOAD_DIR = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'import_uploads'
)
os.makedirs(IMPORT_UPLOAD_DIR, exist_ok=True)

JOB_STATUS_LABELS = {
    'queued': 'Queued',
    'processing': 'Processing',
    'done': 'Done',
    'failed': 'Failed',
}

def _delete_upload(path: str | None) -> bool:
    """Remove a large source upload after text extraction (keep extracted text only)."""
    if not path:
        return False
    try:
        if os.path.isfile(path):
            os.remove(path)
            return True
    except OSError:
        pass
    return False


def create_job(
    db,
    job_type: str,
    filename: str = '',
    created_by: int | None = None,
    stored_path: str = '',
) -> tuple[int, dict]:
    cur = db.execute(
        """
        INSERT INTO gi_import_job (job_type, filename, created_by, status)
        VALUES (?, ?, ?, 'queued')
        """,
        (job_type, filename, created_by),
    )
    db.commit()
    job_id = cur.lastrowid
    if stored_path:
        db.execute(
            'UPDATE gi_import_job SET summary_json = ? WHERE id = ?',
            (json.dumps({'stored_path': stored_path}), job_id),
        )
        db.commit()
    summary = process_job(db, job_id) or {}
    return job_id, summary


def save_upload(file_storage) -> tuple[str, str]:
    """Save uploaded file; return (stored_path, original_filename)."""
    orig = file_storage.filename or 'upload.bin'
    safe = re.sub(r'[^\w.\-]', '_', orig)
    stored = f"{uuid.uuid4().hex}_{safe}"
    path = os.path.join(IMPORT_UPLOAD_DIR, stored)
    file_storage.save(path)
    return path, orig


def list_jobs(db, limit: int = 50) -> list:
    return db.execute(
        "SELECT * FROM gi_import_job ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()


def get_job(db, job_id: int):
    return db.execute("SELECT * FROM gi_import_job WHERE id = ?", (job_id,)).fetchone()


def parse_summary(job) -> dict:
    raw = job['summary_json'] if job else None
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def mark_job(db, job_id: int, status: str, summary: dict | None = None,
             error_text: str = '') -> None:
    db.execute(
        """
        UPDATE gi_import_job
        SET status = ?, summary_json = ?, error_text = ?,
            finished_at = CASE WHEN ? IN ('done', 'failed') THEN datetime('now') ELSE finished_at END
        WHERE id = ?
        """,
        (status, json.dumps(summary or {}), error_text, status, job_id),
    )
    db.commit()


def process_job(db, job_id: int) -> dict | None:
    """Process queued import job synchronously (Blueprint §22 — fast UI, inline worker)."""
    job = get_job(db, job_id)
    if not job or job['status'] not in ('queued', 'processing'):
        return parse_summary(job)
    pending = parse_summary(job)
    stored_path = pending.get('stored_path', '')
    mark_job(db, job_id, 'processing', pending or None)
    try:
        if job['job_type'] == 'knowledge_import':
            summary = _process_knowledge_import(db, job, stored_path=stored_path)
        elif job['job_type'] == 'catalogue_refresh':
            from gi_platform.catalogue_migrate import migrate_knowledge_catalogue, migrate_research_catalogue
            migrate_knowledge_catalogue(db)
            migrate_research_catalogue(db)
            summary = {
                'message': 'Catalogue refreshed from bundled GI definitions.',
            }
        else:
            summary = {
                'message': f"Job type {job['job_type']} acknowledged.",
            }
        # Drop bulky source PDF after extraction — text lives in knowledge object body.
        if stored_path:
            deleted = _delete_upload(stored_path)
            if isinstance(summary, dict):
                summary.pop('stored_path', None)
                summary['source_file_deleted'] = deleted
                if deleted and summary.get('message'):
                    summary['message'] = (
                        str(summary['message']).rstrip()
                        + ' Source PDF removed from disk after extraction.'
                    )
        mark_job(db, job_id, 'done', summary)
        return summary
    except Exception as exc:
        if stored_path:
            _delete_upload(stored_path)
        mark_job(db, job_id, 'failed', error_text=str(exc), summary={
            **pending,
            'stored_path': '',
            'source_file_deleted': True,
        })
        return None


def _infer_object_type(filename: str, title: str) -> str:
    low = f'{filename} {title}'.lower()
    if any(k in low for k in ('guideline', 'jaid', 'bsg', 'nice', 'esge', 'asge')):
        return 'guideline'
    if 'complaint' in low:
        return 'complaint'
    if 'score' in low or 'calculator' in low:
        return 'score'
    if 'disease' in low:
        return 'disease'
    if 'management' in low or 'approach' in low:
        return 'guideline'
    if filename.lower().endswith('.pdf'):
        return 'guideline'
    return 'concept'


def _process_knowledge_import(db, job, *, stored_path: str = '') -> dict:
    from gi_platform import knowledge_service
    from gi_platform import pdf_extract_service

    filename = job['filename'] or ''
    title = os.path.splitext(os.path.basename(filename))[0].replace('_', ' ').replace('-', ' ').strip()
    title = re.sub(r'\s+', ' ', title).title() or 'Imported object'
    object_type = _infer_object_type(filename, title)
    slug_base = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or 'import'
    slug = slug_base
    n = 1
    while knowledge_service.get_object_by_slug(db, slug):
        slug = f"{slug_base}-{n}"
        n += 1

    extraction = {'method': 'none', 'pages': 0, 'char_count': 0, 'excerpt': ''}
    body: dict = {}
    if stored_path and os.path.isfile(stored_path):
        extraction = pdf_extract_service.extract_document_text(stored_path)
        if extraction.get('text'):
            body = {
                'imported_text': extraction['text'],
                'extraction_method': extraction.get('method', 'none'),
                'page_count': extraction.get('pages', 0),
            }

    type_label = object_type.replace('_', ' ')
    summary_text = (
        f'Imported from {filename or "manual entry"}. '
        f'Staged as {type_label} — pending clinical review before publishing.'
    )
    if extraction.get('excerpt'):
        summary_text += f' Extracted preview: {extraction["excerpt"][:280]}'
    elif stored_path and extraction.get('method') == 'none':
        summary_text += (
            ' No text could be extracted automatically'
            + (' (install pypdf for PDF text; pytesseract+pdf2image for scanned OCR).' if not extraction.get('ocr_available') else '.')
        )

    obj_id = knowledge_service.create_object(
        db, slug=slug, title=title, object_type=object_type,
        summary=summary_text,
        body=body,
        status='review',
        created_by=job['created_by'],
    )
    provenance_notes = 'Auto-staged for human review. Approve in Knowledge → Review queue.'
    if extraction.get('method') not in (None, 'none'):
        provenance_notes += f' Text extracted via {extraction["method"]} ({extraction.get("char_count", 0)} chars).'
    knowledge_service.add_provenance(
        db, obj_id, source_type='pdf_import', source_filename=filename,
        import_job_id=job['id'],
        notes=provenance_notes,
    )
    from gi_platform import audit_service
    audit_service.log_event(
        db, action='knowledge_import_staged', entity_type='gi_knowledge_object',
        entity_id=obj_id, user_id=job['created_by'],
        details={'filename': filename, 'job_id': job['id'], 'stored_path': stored_path},
    )
    return {
        'object_id': obj_id,
        'slug': slug,
        'title': title,
        'object_type': object_type,
        'status': 'review',
        'filename': filename,
        'extraction_method': extraction.get('method', 'none'),
        'char_count': extraction.get('char_count', 0),
        'page_count': extraction.get('pages', 0),
        'text_excerpt': extraction.get('excerpt', ''),
        'message': (
            f'File uploaded. "{title}" was added to the Knowledge Library '
            f'as {type_label} (status: review). '
            + (
                f'Extracted {extraction.get("char_count", 0)} characters via {extraction.get("method")}. '
                if extraction.get('method') not in (None, 'none') else
                'No text extracted — review manually or install pypdf/OCR tools. '
            )
            + 'Open Review queue to approve.'
        ),
    }


def cleanup_stale_import_uploads(*, older_than_hours: float | None = None) -> int:
    """Delete leftover PDFs/binaries under import_uploads (post-extraction orphans)."""
    removed = 0
    if not os.path.isdir(IMPORT_UPLOAD_DIR):
        return 0
    now = __import__('time').time()
    for name in os.listdir(IMPORT_UPLOAD_DIR):
        path = os.path.join(IMPORT_UPLOAD_DIR, name)
        if not os.path.isfile(path):
            continue
        if older_than_hours is not None:
            age_h = (now - os.path.getmtime(path)) / 3600.0
            if age_h < older_than_hours:
                continue
        if _delete_upload(path):
            removed += 1
    return removed


def job_has_download(job) -> bool:
    summary = parse_summary(job)
    path = summary.get('stored_path') or ''
    return bool(path and os.path.isfile(path))


def job_download_path(job) -> str | None:
    summary = parse_summary(job)
    path = summary.get('stored_path') or ''
    if path and os.path.isfile(path):
        return path
    return None


def file_path_for_object(db, object_id: int) -> str | None:
    row = db.execute(
        """
        SELECT j.summary_json
        FROM gi_knowledge_provenance p
        JOIN gi_import_job j ON j.id = p.import_job_id
        WHERE p.object_id = ? AND p.source_type = 'pdf_import'
        ORDER BY p.id DESC LIMIT 1
        """,
        (object_id,),
    ).fetchone()
    if not row:
        return None
    summary = parse_summary(row)
    path = summary.get('stored_path') or ''
    if path and os.path.isfile(path):
        return path
    return None
