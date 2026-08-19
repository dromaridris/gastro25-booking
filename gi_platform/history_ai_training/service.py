"""History AI training — admin-configurable questions and branching rules."""

from __future__ import annotations

import json
from typing import Any

TRAINING_ROLES = ('admin', 'hod', 'specialist')

QUESTION_TYPES = ('boolean', 'choice', 'text', 'number')
CATEGORIES = (
    'history_of_present_illness', 'associated_symptoms', 'red_flags',
    'negative_findings', 'past_medical_history', 'medication', 'social',
)


def _parse_json(text: str | None, default):
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def list_questions(db, *, q: str = '') -> list[dict]:
    sql = 'SELECT * FROM gi_guided_history_question WHERE 1=1'
    params: list[Any] = []
    if q:
        sql += ' AND (question_id LIKE ? OR question_text LIKE ?)'
        params.extend([f'%{q}%', f'%{q}%'])
    sql += ' ORDER BY priority, question_id'
    return [_question_row(r) for r in db.execute(sql, params).fetchall()]


def get_trained_question(db, question_id: str) -> dict | None:
    row = db.execute(
        'SELECT * FROM gi_guided_history_question WHERE question_id = ?', (question_id,),
    ).fetchone()
    return _question_row(row) if row else None


def get_question(db, question_id: str) -> dict | None:
    return get_trained_question(db, question_id)


def create_question(db, *, question_id: str, question_text: str, category: str,
                    question_type: str = 'boolean', answer_options: list | None = None,
                    is_required: bool = False, priority: int = 100,
                    conditional_rules: dict | None = None, clinical_purpose: str = '') -> dict:
    db.execute(
        """
        INSERT INTO gi_guided_history_question (
            question_id, question_text, category, clinical_purpose, question_type,
            answer_options_json, is_required, priority, conditional_rules_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """,
        (
            question_id, question_text, category, clinical_purpose, question_type,
            json.dumps(answer_options or []), 1 if is_required else 0, priority,
            json.dumps(conditional_rules or {}),
        ),
    )
    db.commit()
    return get_trained_question(db, question_id)


def update_question(db, question_id: str, **fields) -> dict | None:
    row = db.execute(
        'SELECT id FROM gi_guided_history_question WHERE question_id = ?', (question_id,),
    ).fetchone()
    if not row:
        return None
    mapping = {
        'question_text': 'question_text',
        'category': 'category',
        'clinical_purpose': 'clinical_purpose',
        'question_type': 'question_type',
        'is_required': 'is_required',
        'priority': 'priority',
    }
    sets = []
    params: list[Any] = []
    for key, col in mapping.items():
        if key in fields and fields[key] is not None:
            val = fields[key]
            if key == 'is_required':
                val = 1 if val else 0
            sets.append(f'{col} = ?')
            params.append(val)
    if 'answer_options' in fields:
        sets.append('answer_options_json = ?')
        params.append(json.dumps(fields['answer_options'] or []))
    if 'conditional_rules' in fields:
        sets.append('conditional_rules_json = ?')
        params.append(json.dumps(fields['conditional_rules'] or {}))
    if not sets:
        return get_trained_question(db, question_id)
    params.append(question_id)
    db.execute(
        f"UPDATE gi_guided_history_question SET {', '.join(sets)} WHERE question_id = ?",
        params,
    )
    db.commit()
    return get_trained_question(db, question_id)


def delete_question(db, question_id: str) -> bool:
    db.execute('DELETE FROM gi_guided_history_question_rule WHERE question_id = ?', (question_id,))
    cur = db.execute('DELETE FROM gi_guided_history_question WHERE question_id = ?', (question_id,))
    db.commit()
    return cur.rowcount > 0


def list_rules_for_complaint(db, complaint_code: str) -> list[dict]:
    rows = db.execute(
        """
        SELECT r.*, q.question_text
        FROM gi_guided_history_question_rule r
        JOIN gi_guided_history_question q ON q.question_id = r.question_id
        WHERE r.complaint_code = ?
        ORDER BY r.sort_order
        """,
        (complaint_code,),
    ).fetchall()
    return [_rule_row(r) for r in rows]


def add_complaint_rule(
    db, *, complaint_code: str, question_id: str, sort_order: int = 100,
    activation_rules: dict | None = None,
) -> dict:
    db.execute(
        """
        INSERT OR REPLACE INTO gi_guided_history_question_rule
        (complaint_code, question_id, sort_order, activation_rules_json)
        VALUES (?, ?, ?, ?)
        """,
        (complaint_code, question_id, sort_order, json.dumps(activation_rules or {})),
    )
    db.commit()
    row = db.execute(
        """
        SELECT r.*, q.question_text FROM gi_guided_history_question_rule r
        JOIN gi_guided_history_question q ON q.question_id = r.question_id
        WHERE r.complaint_code = ? AND r.question_id = ?
        """,
        (complaint_code, question_id),
    ).fetchone()
    return _rule_row(row)


def delete_rule(db, rule_id: int) -> bool:
    cur = db.execute('DELETE FROM gi_guided_history_question_rule WHERE id = ?', (rule_id,))
    db.commit()
    return cur.rowcount > 0


def _question_row(row) -> dict:
    data = dict(row)
    return {
        'id': data['id'],
        'question_id': data['question_id'],
        'question_text': data['question_text'],
        'category': data['category'],
        'clinical_purpose': data.get('clinical_purpose') or '',
        'question_type': data['question_type'],
        'answer_options': _parse_json(data.get('answer_options_json'), []),
        'is_required': bool(data.get('is_required')),
        'priority': data.get('priority', 100),
        'conditional_rules': _parse_json(data.get('conditional_rules_json'), {}),
        'status': data.get('status', 'active'),
    }


def _rule_row(row) -> dict:
    data = dict(row)
    return {
        'id': data['id'],
        'complaint_code': data['complaint_code'],
        'question_id': data['question_id'],
        'question_text': data.get('question_text') or '',
        'sort_order': data.get('sort_order', 100),
        'activation_rules': _parse_json(data.get('activation_rules_json'), {}),
    }
