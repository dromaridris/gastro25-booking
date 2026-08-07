"""Smart scoring engine — auto-calculate from labs, history, and Knowledge Library."""

from __future__ import annotations

import json
import re
from typing import Any

from gi_platform import history_service
from gi_platform.score_registry import SCORE_BY_CODE, SCORE_REGISTRY, ScoreResult, _num


def _lab_key_from_code(code: str) -> str:
    return code.replace('lab.', '') if code.startswith('lab.') else code


def build_patient_context(
    db,
    *,
    ward_patient_id: int | None = None,
    session_id: int | None = None,
    complaint_code: str = '',
    diagnosis: str = '',
) -> dict[str, Any]:
    ctx: dict[str, Any] = {'labs': {}, 'answers': {}}
    if session_id:
        sess = history_service.get_session(db, session_id)
        if sess:
            ctx['complaint_code'] = sess['complaint_code'] or complaint_code
            ctx['diagnosis'] = (sess['final_diagnosis'] if 'final_diagnosis' in sess.keys() else '') or diagnosis
            ctx['answers'] = history_service.get_answers_map(db, session_id)
        else:
            ctx['complaint_code'] = complaint_code
            ctx['diagnosis'] = diagnosis
    else:
        ctx['complaint_code'] = complaint_code
        ctx['diagnosis'] = diagnosis

    if ward_patient_id:
        wp = db.execute('SELECT * FROM ward_patient WHERE id = ?', (ward_patient_id,)).fetchone()
        if wp:
            ctx['mrn'] = wp['mrn']
            ctx['gender'] = wp['gender'] or ''
            age_val = _num(wp['age'])
            if age_val is not None:
                ctx['age'] = int(age_val)
        rows = db.execute(
            """
            SELECT test_code, test_name, result_value, result_unit, status
            FROM gi_lab_result
            WHERE ward_patient_id = ? AND status = 'completed'
            ORDER BY result_date DESC, recorded_at DESC
            """,
            (ward_patient_id,),
        ).fetchall()
        for r in rows:
            key = _lab_key_from_code(r['test_code'] or '')
            if not key:
                key = re.sub(r'[^a-z0-9_]', '_', (r['test_name'] or '').lower())
            if key and key not in ctx['labs']:
                ctx['labs'][key] = r['result_value']
    return ctx


def _matches_triggers(entry: dict, ctx: dict) -> bool:
    complaint = (ctx.get('complaint_code') or '').lower()
    diagnosis = (ctx.get('diagnosis') or '').lower()
    answers_text = ' '.join(str(v) for v in (ctx.get('answers') or {}).values()).lower()
    combined = f'{complaint} {diagnosis} {answers_text}'

    for c in entry.get('complaints') or ():
        if c.lower() in combined or c.lower() == complaint:
            return True
    for d in entry.get('diagnoses') or ():
        if d.lower() in combined or d.lower() in diagnosis:
            return True
    labs = ctx.get('labs') or {}
    needed = entry.get('labs') or set()
    if needed and needed.issubset(set(labs.keys()) | {_lab_key_from_code(k) for k in labs}):
        return True
    return not (entry.get('complaints') or entry.get('diagnoses'))


def discover_scores_from_knowledge(db, ctx: dict) -> list[str]:
    """Suggest scores from Knowledge Library guideline/score objects."""
    suggested: set[str] = set()
    complaint = ctx.get('complaint_code') or ''
    diagnosis = (ctx.get('diagnosis') or '').lower()

    rows = db.execute(
        """
        SELECT slug, title, body_json, object_type FROM gi_knowledge_object
        WHERE status = 'published' AND object_type IN ('score', 'guideline', 'management', 'disease')
        """
    ).fetchall()
    score_names = {s['code']: s['calc'].__name__ for s in SCORE_REGISTRY}
    keywords = {
        'meld': ('meld',), 'meld_na': ('meld-na', 'meld na'),
        'child_pugh': ('child-pugh', 'child pugh'),
        'gbs': ('glasgow-blatchford', 'glasgow blatchford', 'gbs'),
        'bisap': ('bisap',), 'fib4': ('fib-4', 'fib4'), 'apri': ('apri',),
        'albi': ('albi',), 'maddrey': ('maddrey',), 'aims65': ('aims65',),
        'rockall_pre': ('rockall',), 'qsofa': ('qsofa',),
    }
    for row in rows:
        blob = f"{row['title']} {row['body_json'] or ''}".lower()
        if complaint and complaint.lower() in blob:
            pass
        if diagnosis and diagnosis and any(w in blob for w in diagnosis.split()):
            pass
        for code, terms in keywords.items():
            if any(t in blob for t in terms):
                if not complaint and not diagnosis:
                    continue
                if complaint.lower() in blob or (diagnosis and any(p in blob for p in diagnosis.split()[:3])):
                    suggested.add(code)
                elif row['object_type'] == 'score':
                    suggested.add(code)
    for entry in SCORE_REGISTRY:
        if _matches_triggers(entry, ctx):
            suggested.add(entry['code'])
    return sorted(suggested)


def calculate_scores(
    db,
    *,
    ward_patient_id: int | None = None,
    session_id: int | None = None,
    complaint_code: str = '',
    diagnosis: str = '',
    only_codes: list[str] | None = None,
) -> list[ScoreResult]:
    ctx = build_patient_context(
        db, ward_patient_id=ward_patient_id, session_id=session_id,
        complaint_code=complaint_code, diagnosis=diagnosis,
    )
    if only_codes is None:
        discovered = set(discover_scores_from_knowledge(db, ctx))
        for entry in SCORE_REGISTRY:
            if _matches_triggers(entry, ctx):
                discovered.add(entry['code'])
        only_codes = sorted(discovered) if discovered else [s['code'] for s in SCORE_REGISTRY]

    results: list[ScoreResult] = []
    for code in only_codes:
        entry = SCORE_BY_CODE.get(code)
        if not entry:
            continue
        result = entry['calc'](ctx)
        results.append(result)
    return results


def persist_score_results(
    db,
    results: list[ScoreResult],
    *,
    session_id: int | None = None,
    ward_patient_id: int | None = None,
) -> int:
    count = 0
    for r in results:
        if not r.available or r.value is None:
            continue
        existing = db.execute(
            """
            SELECT id FROM gi_clinical_score_result
            WHERE score_code = ? AND (
                (session_id IS NOT NULL AND session_id = ?)
                OR (ward_patient_id IS NOT NULL AND ward_patient_id = ?)
            )
            ORDER BY id DESC LIMIT 1
            """,
            (r.code, session_id, ward_patient_id),
        ).fetchone()
        if existing:
            db.execute(
                """
                UPDATE gi_clinical_score_result
                SET score_name = ?, score_value = ?, interpretation = ?,
                    inputs_json = ?, auto_calculated = 1, updated_at = datetime('now')
                WHERE id = ?
                """,
                (r.name, float(r.value) if isinstance(r.value, (int, float)) else None,
                 r.interpretation, json.dumps(r.inputs), existing['id']),
            )
        else:
            db.execute(
                """
                INSERT INTO gi_clinical_score_result
                (session_id, ward_patient_id, score_code, score_name, score_value,
                 interpretation, inputs_json, auto_calculated)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (session_id, ward_patient_id, r.code, r.name,
                 float(r.value) if isinstance(r.value, (int, float)) else None,
                 r.interpretation, json.dumps(r.inputs)),
            )
        count += 1
    db.commit()
    return count


def auto_calculate_and_store(
    db,
    *,
    ward_patient_id: int | None = None,
    session_id: int | None = None,
) -> list[ScoreResult]:
    results = calculate_scores(db, ward_patient_id=ward_patient_id, session_id=session_id)
    persist_score_results(db, results, session_id=session_id, ward_patient_id=ward_patient_id)
    return results


def scores_for_patient(db, *, ward_patient_id: int | None = None, session_id: int | None = None) -> list:
    if session_id:
        return db.execute(
            'SELECT * FROM gi_clinical_score_result WHERE session_id = ? ORDER BY created_at DESC',
            (session_id,),
        ).fetchall()
    if ward_patient_id:
        return db.execute(
            'SELECT * FROM gi_clinical_score_result WHERE ward_patient_id = ? ORDER BY created_at DESC',
            (ward_patient_id,),
        ).fetchall()
    return []
