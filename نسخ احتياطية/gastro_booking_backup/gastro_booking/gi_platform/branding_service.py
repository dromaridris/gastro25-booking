"""White-label branding settings — site name, colors, dual logos."""

from __future__ import annotations

import os
import uuid

from werkzeug.utils import secure_filename

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'branding')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_LOGO_EXT = frozenset({'.png', '.jpg', '.jpeg', '.webp', '.ico', '.svg'})

DEFAULTS = {
    'site_name': 'Gastroenterology • Advanced Endoscopy',
    'slogan': 'The Source of Truth and Care',
    'dept_subtitle': 'Research Center · Ward 25 · JPMC',
    'primary_color': '#A6192E',
    'secondary_color': '#1a1a2e',
    'hospital_logo_filename': '',
    'logo_filename': '',  # department logo
    'favicon_filename': '',
    'show_hospital_logo': True,
    'show_department_logo': True,
}


def _row(db):
    return db.execute('SELECT * FROM gi_branding_settings WHERE id = 1').fetchone()


def get_settings(db) -> dict:
    row = _row(db)
    if not row:
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    keys = set(row.keys()) if hasattr(row, 'keys') else set()
    for key in DEFAULTS:
        if key in keys and row[key] is not None:
            val = row[key]
            if key in ('show_hospital_logo', 'show_department_logo'):
                out[key] = bool(val)
            else:
                out[key] = val
    return out


def save_settings(db, *, fields: dict, updated_by: int | None = None) -> None:
    current = get_settings(db)
    for key, val in fields.items():
        if key not in DEFAULTS or val is None:
            continue
        if key in ('show_hospital_logo', 'show_department_logo'):
            current[key] = bool(val)
        else:
            current[key] = val
    if current.get('dept_subtitle') is None:
        current['dept_subtitle'] = DEFAULTS['dept_subtitle']
    params = (
        current['site_name'],
        current['slogan'],
        current['dept_subtitle'],
        current['primary_color'],
        current['secondary_color'],
        current['hospital_logo_filename'],
        current['logo_filename'],
        current['favicon_filename'],
        1 if current['show_hospital_logo'] else 0,
        1 if current['show_department_logo'] else 0,
        updated_by,
    )
    if _row(db):
        db.execute(
            """
            UPDATE gi_branding_settings SET
                site_name = ?, slogan = ?, dept_subtitle = ?,
                primary_color = ?, secondary_color = ?,
                hospital_logo_filename = ?, logo_filename = ?, favicon_filename = ?,
                show_hospital_logo = ?, show_department_logo = ?,
                updated_at = datetime('now'), updated_by = ?
            WHERE id = 1
            """,
            params,
        )
    else:
        db.execute(
            """
            INSERT INTO gi_branding_settings
            (id, site_name, slogan, dept_subtitle, primary_color, secondary_color,
             hospital_logo_filename, logo_filename, favicon_filename,
             show_hospital_logo, show_department_logo, updated_at, updated_by)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """,
            params,
        )
    db.commit()


def save_upload(file_obj, *, kind: str) -> str:
    if kind not in ('hospital', 'department', 'favicon'):
        raise ValueError('Invalid upload kind.')
    filename = secure_filename(file_obj.filename or '')
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_LOGO_EXT:
        raise ValueError('Unsupported image format.')
    stored = f'{kind}_{uuid.uuid4().hex}{ext}'
    file_obj.save(os.path.join(UPLOAD_DIR, stored))
    return stored


def asset_path(filename: str | None) -> str | None:
    if not filename:
        return None
    path = os.path.join(UPLOAD_DIR, filename)
    return path if os.path.isfile(path) else None


def logo_filename_for_kind(settings: dict, kind: str) -> str | None:
    if kind in ('hospital',):
        return settings.get('hospital_logo_filename') or None
    if kind in ('department', 'logo'):
        return settings.get('logo_filename') or None
    if kind == 'favicon':
        return settings.get('favicon_filename') or None
    return None
