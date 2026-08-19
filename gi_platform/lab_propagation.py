"""Propagate ward lab results to patient-scoped clinical surfaces.

Single source of truth remains ``gi_lab_result`` (written by lab_service /
patient_journey_service). This module refreshes linked consumers without a
second divergent write path for clinicians.

Surfaces:
- Linked CI encounters (idempotent ``ci_ix_result`` rows under ``ward:`` prefix;
  never overwrites clinician categorical IX codes)
- Score recalculation hook (delegates to score_service)
- Helpers for workflow / consult / discharge read-through
"""

from __future__ import annotations

from typing import Any

WARD_IX_PREFIX = 'ward:'
WARD_NOTE_MARKER = '[ward_lab auto]'


def _table_exists(db, name: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return bool(row)


def list_labs_for_patient(
    db,
    *,
    ward_patient_id: int | None = None,
    mrn: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Read-through from gi_lab_result (canonical ward labs)."""
    if not _table_exists(db, 'gi_lab_result'):
        return []
    rows = []
    if ward_patient_id:
        rows = db.execute(
            """
            SELECT * FROM gi_lab_result
            WHERE ward_patient_id = ?
            ORDER BY COALESCE(result_date, recorded_at) DESC, id DESC
            LIMIT ?
            """,
            (ward_patient_id, limit),
        ).fetchall()
    elif mrn:
        rows = db.execute(
            """
            SELECT * FROM gi_lab_result
            WHERE mrn = ?
            ORDER BY COALESCE(result_date, recorded_at) DESC, id DESC
            LIMIT ?
            """,
            (mrn, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def format_lab_value(row: dict[str, Any] | Any) -> str:
    if hasattr(row, 'keys') and not isinstance(row, dict):
        row = dict(row)
    value = (row.get('result_value') or '').strip()
    unit = (row.get('result_unit') or '').strip()
    if value and unit:
        return f'{value} {unit}'
    return value or '—'


def format_labs_block(labs: list[dict[str, Any]], *, max_items: int = 20) -> str:
    """Plain-text block suitable for discharge / note prefill."""
    if not labs:
        return ''
    lines = []
    for lab in labs[:max_items]:
        name = (lab.get('test_name') or lab.get('test_code') or 'Lab').strip()
        date = (lab.get('result_date') or '')[:10]
        ref = (lab.get('reference_range') or '').strip()
        bit = f"{name}: {format_lab_value(lab)}"
        if ref:
            bit += f' (ref {ref})'
        if date:
            bit += f' [{date}]'
        lines.append(bit)
    return 'Laboratory results:\n' + '\n'.join(f'- {x}' for x in lines)


def labs_for_encounter(db, encounter: dict[str, Any] | Any) -> list[dict[str, Any]]:
    if hasattr(encounter, 'keys') and not isinstance(encounter, dict):
        encounter = dict(encounter)
    wid = encounter.get('ward_patient_id')
    if not wid:
        return []
    return list_labs_for_patient(db, ward_patient_id=int(wid))


def _ward_ix_code(test_code: str | None, test_name: str | None, result_id: int | None) -> str:
    code = (test_code or '').strip()
    if code:
        return f'{WARD_IX_PREFIX}{code}'
    slug = (test_name or 'lab').strip().lower().replace(' ', '_')[:48] or 'lab'
    rid = result_id or 0
    return f'{WARD_IX_PREFIX}{slug}:{rid}'


def sync_labs_to_ci_encounters(
    db,
    *,
    ward_patient_id: int,
    limit_per_encounter: int = 40,
) -> int:
    """Idempotently mirror latest ward labs into linked CI encounters.

    Only touches investigation_code values starting with ``ward:``.
    Clinician-entered categorical ``ci_ix_result`` rows are never deleted
    or overwritten.
    """
    if not ward_patient_id:
        return 0
    if not _table_exists(db, 'ci_encounter') or not _table_exists(db, 'ci_ix_result'):
        return 0

    encounters = db.execute(
        """
        SELECT id FROM ci_encounter
        WHERE ward_patient_id = ? AND COALESCE(status, 'open') != 'deleted'
        ORDER BY id DESC
        """,
        (ward_patient_id,),
    ).fetchall()
    if not encounters:
        return 0

    labs = list_labs_for_patient(db, ward_patient_id=ward_patient_id, limit=limit_per_encounter)
    if not labs:
        return 0

    # Deduplicate by test_code (keep newest)
    seen: set[str] = set()
    latest: list[dict[str, Any]] = []
    for lab in labs:
        key = (lab.get('test_code') or '').strip() or f"name:{(lab.get('test_name') or '').strip()}"
        if key in seen:
            continue
        seen.add(key)
        latest.append(lab)

    updated = 0
    for enc in encounters:
        eid = enc['id']
        for lab in latest:
            ix_code = _ward_ix_code(lab.get('test_code'), lab.get('test_name'), lab.get('id'))
            label = format_lab_value(lab)
            note = f"{WARD_NOTE_MARKER} {lab.get('test_name') or ''}".strip()
            existing = db.execute(
                """
                SELECT id, note FROM ci_ix_result
                WHERE encounter_id = ? AND investigation_code = ?
                """,
                (eid, ix_code),
            ).fetchone()
            if existing:
                # Only refresh auto-synced rows
                if existing['note'] and WARD_NOTE_MARKER not in (existing['note'] or ''):
                    continue
                db.execute(
                    """
                    UPDATE ci_ix_result
                    SET result_label = ?, note = ?, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (label, note, existing['id']),
                )
            else:
                db.execute(
                    """
                    INSERT INTO ci_ix_result
                        (encounter_id, investigation_code, result_label, note, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    """,
                    (eid, ix_code, label, note),
                )
            updated += 1
    if updated:
        db.commit()
    return updated


def ensure_lab_mrn(db, *, ward_patient_id: int | None, result_id: int | None = None) -> None:
    """Backfill mrn on gi_lab_result from ward_patient when missing."""
    if not ward_patient_id or not _table_exists(db, 'gi_lab_result'):
        return
    wp = db.execute('SELECT mrn FROM ward_patient WHERE id = ?', (ward_patient_id,)).fetchone()
    mrn = (wp['mrn'] if wp else None) or ''
    if not mrn:
        return
    if result_id:
        db.execute(
            "UPDATE gi_lab_result SET mrn = ? WHERE id = ? AND (mrn IS NULL OR mrn = '')",
            (mrn, result_id),
        )
    else:
        db.execute(
            """
            UPDATE gi_lab_result SET mrn = ?
            WHERE ward_patient_id = ? AND (mrn IS NULL OR mrn = '')
            """,
            (mrn, ward_patient_id),
        )


def after_lab_result_saved(
    db,
    *,
    ward_patient_id: int | None = None,
    session_id: int | None = None,
    result_id: int | None = None,
    recalculate_scores: bool = True,
) -> dict[str, Any]:
    """Call from lab save paths after gi_lab_result is committed.

    Preserves approvals / existing save flows; only refreshes derived views.
    """
    summary: dict[str, Any] = {'ci_synced': 0, 'scores': False}

    if ward_patient_id:
        ensure_lab_mrn(db, ward_patient_id=ward_patient_id, result_id=result_id)
        try:
            db.commit()
        except Exception:
            pass
        try:
            summary['ci_synced'] = sync_labs_to_ci_encounters(db, ward_patient_id=ward_patient_id)
        except Exception:
            summary['ci_synced'] = 0

    if recalculate_scores and (ward_patient_id or session_id):
        try:
            from gi_platform import score_service
            score_service.auto_calculate_and_store(
                db, ward_patient_id=ward_patient_id, session_id=session_id,
            )
            summary['scores'] = True
        except Exception:
            summary['scores'] = False

    return summary
