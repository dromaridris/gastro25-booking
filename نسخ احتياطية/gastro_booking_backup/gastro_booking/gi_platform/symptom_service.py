"""Multi-symptom history support — per-symptom questions, onset, and combined differential."""

from __future__ import annotations

import json
import re
from typing import Any

from gi_platform.catalogue_runtime import compute_differential_for_session, list_complaints

# Shared question categories asked once per session (not per symptom).
SHARED_QUESTION_PREFIXES = (
    'gh.q.current_medications', 'gh.q.alcohol', 'gh.q.allerg',
    'gh.q.pmh', 'gh.q.family', 'gh.q.social', 'gh.q.surgical',
    'q.common.alcohol', 'q.common.smoking', 'q.common.allergy',
    'q.common.drugs', 'q.common.pmh', 'q.common.family', 'q.common.surgical',
    'q.common.social',
)
SHARED_QUESTION_SECTIONS = frozenset({'pmh', 'surgical', 'drugs', 'allergy', 'family', 'social'})
SHARED_QUESTION_TOKENS = ('alcohol', 'smok', 'allerg')

DURATION_ACUTE = 'acute'
DURATION_SUBACUTE = 'subacute'
DURATION_CHRONIC = 'chronic'


def classify_duration(onset_text: str) -> str:
    """Classify acute / subacute / chronic from free-text or standard onset answers."""
    text = (onset_text or '').strip().lower()
    if not text:
        return ''
    if text in ('hours', 'hour', 'today', 'since today'):
        return DURATION_ACUTE
    if text in ('days', 'day', '1-2 days', '2-3 days', 'few days'):
        return DURATION_ACUTE
    if text in ('weeks', 'week', '1-2 weeks', 'few weeks'):
        return DURATION_SUBACUTE
    if text in ('months', 'month', 'years', 'year', 'longstanding', 'chronic'):
        return DURATION_CHRONIC
    if re.search(r'\b(hour|today|yesterday|acute)\b', text):
        return DURATION_ACUTE
    if re.search(r'\b(day|days)\b', text):
        return DURATION_ACUTE
    if re.search(r'\b(week|weeks)\b', text):
        return DURATION_SUBACUTE
    if re.search(r'\b(month|months|year|years|chronic|long.?standing)\b', text):
        return DURATION_CHRONIC
    return DURATION_SUBACUTE


def duration_label(category: str) -> str:
    return {
        DURATION_ACUTE: 'acute',
        DURATION_SUBACUTE: 'subacute',
        DURATION_CHRONIC: 'chronic',
    }.get(category, category or '')


def is_shared_question(question_key: str, *, section: str = '') -> bool:
    key = (question_key or '').lower()
    if any(key.startswith(p) for p in SHARED_QUESTION_PREFIXES):
        return True
    if any(tok in key for tok in SHARED_QUESTION_TOKENS):
        return True
    return (section or '').lower() in SHARED_QUESTION_SECTIONS


def list_session_symptoms(db, session_id: int) -> list[dict]:
    rows = db.execute(
        """
        SELECT * FROM gi_history_session_symptom
        WHERE session_id = ?
        ORDER BY is_primary DESC, sort_order, id
        """,
        (session_id,),
    ).fetchall()
    return [symptom_to_dict(r) for r in rows]


def get_symptom(db, symptom_id: int) -> dict | None:
    row = db.execute(
        'SELECT * FROM gi_history_session_symptom WHERE id = ?', (symptom_id,),
    ).fetchone()
    return symptom_to_dict(row) if row else None


def set_session_symptoms(
    db,
    session_id: int,
    *,
    symptoms: list[dict[str, Any]],
) -> list[dict]:
    """
    Replace session symptoms. Each item: complaint_code, onset_text (optional), is_primary (optional).
    """
    db.execute('DELETE FROM gi_history_session_symptom WHERE session_id = ?', (session_id,))
    complaints_map = {c['code']: c['name'] for c in list_complaints(db)}
    saved: list[dict] = []
    chief_parts: list[str] = []

    for idx, item in enumerate(symptoms):
        code = (item.get('complaint_code') or '').strip()
        if not code:
            continue
        name = (item.get('symptom_name') or '').strip() or complaints_map.get(code, code)
        onset = (item.get('onset_text') or '').strip()
        duration_cat = classify_duration(onset) if onset else (item.get('duration_category') or '')
        is_primary = bool(item.get('is_primary')) or idx == 0
        cur = db.execute(
            """
            INSERT INTO gi_history_session_symptom (
                session_id, complaint_code, symptom_name, onset_text,
                duration_category, is_primary, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, code, name, onset, duration_cat, 1 if is_primary else 0, idx),
        )
        saved.append(get_symptom(db, cur.lastrowid))
        label = name
        if onset:
            label = f"{name} ({onset})"
        chief_parts.append(label)

    if saved:
        primary = next((s for s in saved if s['is_primary']), saved[0])
        chief = ' + '.join(chief_parts)
        db.execute(
            """
            UPDATE gi_history_session
            SET complaint_code = ?, chief_complaint = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (primary['complaint_code'], chief, session_id),
        )
    db.commit()
    return saved


def sync_legacy_complaint(db, session_id: int) -> None:
    """If no multi-symptom rows exist, create one from legacy complaint_code."""
    existing = db.execute(
        'SELECT COUNT(*) AS c FROM gi_history_session_symptom WHERE session_id = ?',
        (session_id,),
    ).fetchone()['c']
    if existing:
        return
    sess = db.execute('SELECT * FROM gi_history_session WHERE id = ?', (session_id,)).fetchone()
    if not sess or not sess['complaint_code']:
        return
    db.execute(
        """
        INSERT INTO gi_history_session_symptom (
            session_id, complaint_code, symptom_name, is_primary, sort_order
        ) VALUES (?, ?, ?, 1, 0)
        """,
        (session_id, sess['complaint_code'], sess['chief_complaint'] or sess['complaint_code']),
    )
    db.commit()


def compute_combined_differential(db, session_id: int) -> dict[str, Any]:
    """Merge differentials from all session symptoms."""
    from gi_platform.cds_service import AssessmentResult

    sync_legacy_complaint(db, session_id)
    symptoms = list_session_symptoms(db, session_id)
    if not symptoms:
        return {'diagnoses': [], 'symptoms': [], 'red_flags': [], 'investigations': []}

    merged_dx: dict[str, dict] = {}
    red_flags: list[str] = []
    investigations: list[dict] = []
    seen_inv: set[str] = set()

    for sym in symptoms:
        result = compute_differential_for_session(db, sym['complaint_code'], session_id)
        if not isinstance(result, AssessmentResult):
            continue
        for dx in (getattr(result, 'differentials', None) or getattr(result, 'diagnoses', None) or []):
            name = dx.get('name') or dx.get('diagnosis_name') or dx.get('title') or ''
            if not name:
                continue
            key = name.lower()
            score = float(dx.get('score') or dx.get('probability') or 0)
            if score <= 0:
                # CDS legacy rows often have no numeric score — keep a floor so they still surface.
                level = (dx.get('consideration_level') or '').lower()
                score = 0.8 if 'strong' in level else 0.5 if level else 0.4
            if key not in merged_dx or score > merged_dx[key]['score']:
                merged_dx[key] = {
                    'name': name,
                    'score': score,
                    'category': dx.get('category', ''),
                    'from_symptoms': [sym['symptom_name']],
                }
            elif sym['symptom_name'] not in merged_dx[key]['from_symptoms']:
                merged_dx[key]['from_symptoms'].append(sym['symptom_name'])
                merged_dx[key]['score'] += score * 0.25
        for rf in result.red_flags or []:
            label = rf if isinstance(rf, str) else rf.get('label') or rf.get('name') or ''
            if label and label not in red_flags:
                red_flags.append(label)
        for inv in result.investigations or []:
            inv_name = inv.get('name') or ''
            if inv_name and inv_name not in seen_inv:
                seen_inv.add(inv_name)
                investigations.append(inv)

    diagnoses = sorted(merged_dx.values(), key=lambda d: -d['score'])
    return {
        'diagnoses': diagnoses,
        'symptoms': symptoms,
        'red_flags': red_flags,
        'investigations': investigations,
    }


def symptom_to_dict(row) -> dict:
    data = dict(row)
    return {
        'id': data['id'],
        'session_id': data['session_id'],
        'complaint_code': data['complaint_code'],
        'symptom_name': data['symptom_name'],
        'onset_text': data.get('onset_text') or '',
        'duration_category': data.get('duration_category') or '',
        'duration_label': duration_label(data.get('duration_category') or ''),
        'is_primary': bool(data.get('is_primary')),
        'sort_order': data.get('sort_order', 0),
    }
