"""Configurable history templates — disease-based question designer."""

from __future__ import annotations

import json


def list_templates(db, *, q: str = '') -> list:
    sql = 'SELECT * FROM gi_history_template WHERE 1=1'
    params: list = []
    if q:
        sql += ' AND (disease_name LIKE ? OR disease_code LIKE ?)'
        like = f'%{q}%'
        params.extend([like, like])
    sql += ' ORDER BY disease_name'
    return db.execute(sql, params).fetchall()


def get_template(db, template_id: int):
    return db.execute('SELECT * FROM gi_history_template WHERE id = ?', (template_id,)).fetchone()


def get_template_by_code(db, disease_code: str):
    return db.execute(
        'SELECT * FROM gi_history_template WHERE disease_code = ?', (disease_code,),
    ).fetchone()


def list_questions(db, template_id: int) -> list:
    return db.execute(
        """
        SELECT * FROM gi_history_template_question
        WHERE template_id = ?
        ORDER BY sort_order, id
        """,
        (template_id,),
    ).fetchall()


def create_template(
    db, *, disease_code: str, disease_name: str,
    symptoms: list | None = None, red_flags: list | None = None,
    risk_factors: list | None = None, positive_findings: list | None = None,
    negative_findings: list | None = None, exclusions: list | None = None,
    created_by: int | None = None,
) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_history_template
        (disease_code, disease_name, symptoms_json, red_flags_json, risk_factors_json,
         positive_findings_json, negative_findings_json, exclusions_json, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            disease_code.strip(), disease_name.strip(),
            json.dumps(symptoms or []), json.dumps(red_flags or []),
            json.dumps(risk_factors or []), json.dumps(positive_findings or []),
            json.dumps(negative_findings or []), json.dumps(exclusions or []),
            created_by,
        ),
    )
    db.commit()
    return cur.lastrowid


def update_template(db, template_id: int, **fields) -> None:
    allowed = {
        'disease_code', 'disease_name', 'symptoms_json', 'red_flags_json',
        'risk_factors_json', 'positive_findings_json', 'negative_findings_json',
        'exclusions_json',
    }
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f'{k} = ?')
            vals.append(v if k.endswith('_json') else v)
        elif k in ('symptoms', 'red_flags', 'risk_factors', 'positive_findings', 'negative_findings', 'exclusions'):
            sets.append(f'{k}_json = ?')
            vals.append(json.dumps(v))
    if sets:
        sets.append("updated_at = datetime('now')")
        vals.append(template_id)
        db.execute(f"UPDATE gi_history_template SET {', '.join(sets)} WHERE id = ?", vals)
        db.commit()


def delete_template(db, template_id: int) -> None:
    db.execute('DELETE FROM gi_history_template_question WHERE template_id = ?', (template_id,))
    db.execute('DELETE FROM gi_history_template WHERE id = ?', (template_id,))
    db.commit()


def add_question(
    db, *, template_id: int, question_key: str, prompt: str,
    answer_type: str = 'text', choices: list | None = None,
    sort_order: int = 0, is_red_flag: bool = False, is_exclusion: bool = False,
) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_history_template_question
        (template_id, question_key, prompt, answer_type, choices_json,
         sort_order, is_red_flag, is_exclusion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (template_id, question_key, prompt, answer_type, json.dumps(choices or []),
         sort_order, 1 if is_red_flag else 0, 1 if is_exclusion else 0),
    )
    db.commit()
    return cur.lastrowid


def delete_question(db, question_id: int) -> None:
    db.execute('DELETE FROM gi_history_template_question WHERE id = ?', (question_id,))
    db.commit()


def template_questions_for_complaint(db, complaint_code: str) -> list[dict]:
    """Return custom template questions merged for a complaint/disease code."""
    tpl = get_template_by_code(db, complaint_code)
    if not tpl:
        tpl = db.execute(
            "SELECT * FROM gi_history_template WHERE disease_code LIKE ? LIMIT 1",
            (f'%{complaint_code}%',),
        ).fetchone()
    if not tpl:
        return []
    rows = list_questions(db, tpl['id'])
    out = []
    for r in rows:
        out.append({
            'code': r['question_key'],
            'prompt': r['prompt'],
            'section': 'presenting',
            'answer_type': r['answer_type'],
            'choices': json.loads(r['choices_json'] or '[]') or None,
            'is_exclusion': bool(r['is_exclusion']),
            'is_red_flag': bool(r['is_red_flag']),
            'from_template': True,
        })
    return out
