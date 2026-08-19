"""
Gastro25 Core Services — Image Service
----------------------------------------
Generic upload / compression / ordering / storage / deletion / retrieval
helpers for procedure-report images (used by ERCP today; any future
procedure report with a slot-based image gallery can reuse this as-is).

Compression behaviour and image quality are UNCHANGED from the original
`compress_ercp_image()` in app.py — this module only relocates that
logic, it does not alter resize thresholds, JPEG quality, or the
RGB/LANCZOS/optimize settings.

Every table used with this service is expected to have the same shape as
the existing `ercp_report_image` table:
    (id, <fk_column>, slot, filename, uploaded_by, uploaded_at)
with a UNIQUE(<fk_column>, slot) constraint (needed for the upsert-on-
re-upload behaviour).

Filenames are still built as `{prefix}_{entity_id}_slot_{slot}.jpg` —
identical to ERCP's previous `report_{report_id}_slot_{slot}.jpg` scheme
— so existing files already on disk keep resolving with no migration.
"""

import os
from datetime import datetime


def build_filename(prefix, entity_id, slot):
    """e.g. build_filename('report', 42, 3) -> 'report_42_slot_3.jpg'."""
    return f'{prefix}_{entity_id}_slot_{slot}.jpg'


def compress_and_save(file_storage, dest_path, max_dimension, jpeg_quality):
    """Resize/compress an uploaded image and save it as a JPEG at
    dest_path. Identical behaviour/quality to the original
    compress_ercp_image()."""
    from PIL import Image
    img = Image.open(file_storage)
    img = img.convert('RGB')
    img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
    img.save(dest_path, 'JPEG', quality=jpeg_quality, optimize=True)


def upsert_image_record(dbconn, table, fk_column, fk_value, slot, filename, username):
    """Insert a new image record, or replace the existing one for that
    slot (same ON CONFLICT upsert semantics as the original code). Does
    not commit — caller commits, same as before."""
    now = datetime.utcnow().isoformat()
    dbconn.execute(
        f'INSERT INTO {table} ({fk_column}, slot, filename, uploaded_by, uploaded_at) '
        f'VALUES (?,?,?,?,?) '
        f'ON CONFLICT({fk_column}, slot) DO UPDATE SET filename=excluded.filename, '
        f'uploaded_by=excluded.uploaded_by, uploaded_at=excluded.uploaded_at',
        (fk_value, slot, filename, username, now)
    )


def get_image_record(dbconn, table, fk_column, fk_value, slot):
    """Single image record for one slot, or None."""
    return dbconn.execute(
        f'SELECT * FROM {table} WHERE {fk_column} = ? AND slot = ?', (fk_value, slot)
    ).fetchone()


def list_images(dbconn, table, fk_column, fk_value):
    """All image records for a report, ordered by slot."""
    return dbconn.execute(
        f'SELECT * FROM {table} WHERE {fk_column} = ? ORDER BY slot', (fk_value,)
    ).fetchall()


def index_by_slot(images):
    """[Row, Row, ...] -> {slot: Row} for quick per-slot lookup (used by
    the report editor's image grid)."""
    return {img['slot']: img for img in images}


def ordered_slots(images, total_slots):
    """Full slot -> image_or_None sequence for printed layouts. For a
    6-slot gallery this always yields exactly 6 (slot, image_or_None)
    tuples in order, filling gaps for empty slots — same fixed layout the
    printed report has always shown."""
    by_slot = index_by_slot(images)
    return [(slot, by_slot.get(slot)) for slot in range(1, total_slots + 1)]


def delete_image(dbconn, table, directory, image_record):
    """Remove the file from disk (best-effort — a missing file on disk is
    not treated as an error, same as before) and delete its DB record.
    Does not commit."""
    try:
        os.remove(os.path.join(directory, image_record['filename']))
    except OSError:
        pass
    dbconn.execute(f'DELETE FROM {table} WHERE id = ?', (image_record['id'],))


def serve_image(directory, filename):
    """Stream an image file from disk as the HTTP response."""
    from flask import send_from_directory
    return send_from_directory(directory, filename)
