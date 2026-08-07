"""Department logbook — all clinical staff, CanMEDS evaluation by HOD."""

from __future__ import annotations

import json

from gi_platform.constants import CANMEDS_DOMAINS, CANMEDS_SCORE_LABELS, CLINICAL_STAFF_ROLES
from gi_platform import activity_service


def log_activity(db, **kwargs) -> int | None:
    """Backward-compatible wrapper — logs for all staff via activity_service."""
    return activity_service.record_activity(db, **kwargs)


def list_entries_grouped_by_patient(db, user_id: int, *, limit: int = 500) -> list[dict]:
    """Group logbook entries under patient MRN/name, then by activity type."""
    rows = list_entries_for_user(db, user_id, limit=limit)
    groups: dict[str, dict] = {}
    for e in rows:
        key = (e['mrn'] or '').strip() or f"wp-{e['ward_patient_id'] or 'none'}"
        label = (e['patient_name'] or e['wp_name'] or '').strip() or 'No patient linked'
        if key not in groups:
            groups[key] = {'mrn': e['mrn'] or '', 'patient_name': label, 'by_type': {}}
        atype = e['activity_type'] or 'other'
        groups[key]['by_type'].setdefault(atype, []).append(e)
    out = sorted(groups.values(), key=lambda g: g['patient_name'].lower())
    for g in out:
        g['types'] = sorted(g['by_type'].items(), key=lambda x: x[0])
    return out


def list_entries_for_user(db, user_id: int, *, limit: int = 200) -> list:
    return db.execute(
        """
        SELECT e.*, wp.patient_name AS wp_name
        FROM gi_portfolio_entry e
        LEFT JOIN ward_patient wp ON wp.id = e.ward_patient_id
        WHERE e.user_id = ?
        ORDER BY e.created_at DESC LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()


def list_department_entries(db, *, role: str | None = None, limit: int = 500) -> list:
    sql = """
        SELECT e.*, u.full_name AS staff_name, u.role AS staff_role,
               wp.patient_name AS wp_name
        FROM gi_portfolio_entry e
        JOIN user u ON u.id = e.user_id
        LEFT JOIN ward_patient wp ON wp.id = e.ward_patient_id
        WHERE u.role IN ({})
    """.format(','.join('?' * len(CLINICAL_STAFF_ROLES)))
    params: list = list(CLINICAL_STAFF_ROLES)
    if role:
        sql += ' AND u.role = ?'
        params.append(role)
    sql += ' ORDER BY e.created_at DESC LIMIT ?'
    params.append(limit)
    return db.execute(sql, params).fetchall()


def list_trainee_entries(db, *, limit: int = 200) -> list:
    return list_department_entries(db, limit=limit)


def get_entry(db, entry_id: int):
    return db.execute(
        """
        SELECT e.*, u.full_name AS staff_name, u.role AS staff_role
        FROM gi_portfolio_entry e
        JOIN user u ON u.id = e.user_id
        WHERE e.id = ?
        """,
        (entry_id,),
    ).fetchone()


def list_evaluations(db, entry_id: int) -> list:
    return db.execute(
        """
        SELECT ev.*, u.full_name AS evaluator_name
        FROM gi_logbook_evaluation ev
        JOIN user u ON u.id = ev.evaluator_id
        WHERE ev.portfolio_entry_id = ?
        ORDER BY ev.created_at DESC
        """,
        (entry_id,),
    ).fetchall()


def add_evaluation(
    db, *, entry_id: int, evaluator_id: int, competency_domain: str,
    score: int, note: str = '',
) -> int:
    score = max(1, min(5, int(score)))
    cur = db.execute(
        """
        INSERT INTO gi_logbook_evaluation
        (portfolio_entry_id, evaluator_id, competency_domain, score, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (entry_id, evaluator_id, competency_domain, score, note.strip()),
    )
    db.execute(
        'UPDATE gi_portfolio_entry SET verified = 1 WHERE id = ?', (entry_id,)
    )
    db.commit()
    return cur.lastrowid


def staff_summary(db, user_id: int, *, days: int = 30) -> dict:
    entries = db.execute(
        """
        SELECT COUNT(*) AS total,
               COUNT(DISTINCT date(created_at)) AS active_days
        FROM gi_portfolio_entry
        WHERE user_id = ? AND created_at >= datetime('now', ?)
        """,
        (user_id, f'-{days} days'),
    ).fetchone()
    evals = db.execute(
        """
        SELECT AVG(score) AS avg_score, COUNT(*) AS eval_count
        FROM gi_logbook_evaluation ev
        JOIN gi_portfolio_entry e ON e.id = ev.portfolio_entry_id
        WHERE e.user_id = ?
        """,
        (user_id,),
    ).fetchone()
    return {
        'total_activities': entries['total'] if entries else 0,
        'active_days': entries['active_days'] if entries else 0,
        'avg_evaluation_score': round(evals['avg_score'], 2) if evals and evals['avg_score'] else None,
        'evaluation_count': evals['eval_count'] if evals else 0,
    }


def staff_activity_rollups(db, *, days: int = 30, limit: int = 50) -> list:
    """Grouped logbook summary by staff — for HOD dashboard."""
    return db.execute(
        """
        SELECT u.id AS user_id, u.full_name, u.role,
               COUNT(e.id) AS activity_count,
               COUNT(DISTINCT date(e.created_at)) AS active_days,
               MAX(e.created_at) AS last_activity
        FROM gi_portfolio_entry e
        JOIN user u ON u.id = e.user_id
        WHERE e.created_at >= datetime('now', ?)
          AND u.role IN ({})
        GROUP BY u.id
        ORDER BY activity_count DESC
        LIMIT ?
        """.format(','.join('?' * len(CLINICAL_STAFF_ROLES))),
        (f'-{days} days', *CLINICAL_STAFF_ROLES, limit),
    ).fetchall()


def export_logbook_rows(db, *, days: int = 365) -> list:
    """Full logbook data for Excel export (CanMEDS / portfolio standard fields)."""
    return db.execute(
        """
        SELECT e.created_at, u.full_name AS staff_name, u.role AS staff_role,
               e.activity_type, e.title, e.mrn, e.patient_name,
               wp.patient_name AS ward_patient_name,
               e.source_module, e.source_type,
               ev.competency_domain, ev.score AS canmeds_score, ev.note AS evaluator_note,
               ev.created_at AS evaluated_at, evu.full_name AS evaluator_name
        FROM gi_portfolio_entry e
        JOIN user u ON u.id = e.user_id
        LEFT JOIN ward_patient wp ON wp.id = e.ward_patient_id
        LEFT JOIN gi_logbook_evaluation ev ON ev.portfolio_entry_id = e.id
        LEFT JOIN user evu ON evu.id = ev.evaluator_id
        WHERE e.created_at >= datetime('now', ?)
        ORDER BY e.created_at DESC
        """,
        (f'-{days} days',),
    ).fetchall()


def domain_label(code: str) -> str:
    return dict(CANMEDS_DOMAINS).get(code, code.replace('_', ' ').title())


def score_label(score: int) -> str:
    return CANMEDS_SCORE_LABELS.get(score, str(score))
