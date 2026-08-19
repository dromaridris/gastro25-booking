"""Configurable History Question Engine — SQLite."""

from __future__ import annotations

import json
from typing import Any

from gi_platform.clinical_history_ai.constants import DEFAULT_COMPLAINT, QUESTION_STATUS_ACTIVE


def _parse_json(text: str | None, default):
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


class HistoryQuestionEngine:
    def load_questions_for_complaint(
        self,
        db,
        complaint_code: str | None,
        *,
        specialty_code: str | None = None,
    ) -> list[dict]:
        if not complaint_code:
            return []
        rules = db.execute(
            """
            SELECT * FROM gi_guided_history_question_rule
            WHERE complaint_code = ? ORDER BY sort_order
            """,
            (complaint_code,),
        ).fetchall()
        if not rules and complaint_code != DEFAULT_COMPLAINT:
            rules = db.execute(
                """
                SELECT * FROM gi_guided_history_question_rule
                WHERE complaint_code = ? ORDER BY sort_order
                """,
                (DEFAULT_COMPLAINT,),
            ).fetchall()

        if specialty_code:
            rules = [r for r in rules if not r['specialty_code'] or r['specialty_code'] == specialty_code]

        question_ids = [r['question_id'] for r in rules]
        if not question_ids:
            return self._fallback_kl_questions(db, complaint_code)

        placeholders = ','.join('?' * len(question_ids))
        rows = db.execute(
            f"""
            SELECT * FROM gi_guided_history_question
            WHERE question_id IN ({placeholders}) AND status = ?
            """,
            (*question_ids, QUESTION_STATUS_ACTIVE),
        ).fetchall()
        order = {qid: idx for idx, qid in enumerate(question_ids)}
        return sorted(
            [self._row_to_question(r) for r in rows],
            key=lambda q: (order.get(q['question_id'], 999), q['priority']),
        )

    def _fallback_kl_questions(self, db, complaint_code: str) -> list[dict]:
        from gi_platform.catalogue_runtime import get_next_questions
        session_row = db.execute(
            """
            SELECT id FROM gi_history_session
            WHERE complaint_code = ? ORDER BY updated_at DESC LIMIT 1
            """,
            (complaint_code,),
        ).fetchone()
        if not session_row:
            return []
        views = get_next_questions(db, complaint_code, session_row['id'], batch_size=20)
        out = []
        for v in views:
            out.append({
                'question_id': v.code,
                'question_text': v.prompt,
                'category': v.section or 'history_of_present_illness',
                'clinical_purpose': v.help_text,
                'question_type': v.answer_type,
                'answer_options': v.choices or [],
                'is_required': bool(v.is_exclusion),
                'priority': 100,
                'conditional_rules': {},
            })
        return out

    def next_questions(
        self,
        db,
        session_row,
        *,
        limit: int = 5,
        specialty_code: str | None = None,
    ) -> list[dict[str, Any]]:
        complaint = session_row['complaint_code']
        all_questions = self.load_questions_for_complaint(db, complaint, specialty_code=specialty_code)
        answers = {
            r['question_id']: r['response_value']
            for r in db.execute(
                'SELECT question_id, response_value FROM gi_guided_history_answer WHERE session_id = ?',
                (session_row['id'],),
            ).fetchall()
        }
        presented = set(_parse_json(session_row['presented_question_ids_json'], []))
        selected: list[dict[str, Any]] = []

        for question in all_questions:
            qid = question['question_id']
            if qid in answers:
                continue
            if not self._should_show(db, question, answers, session_row):
                continue
            selected.append({
                **question,
                'knowledge_references': self._knowledge_references(db, question),
            })
            if len(selected) >= limit:
                break

        if selected:
            new_presented = list(presented | {item['question_id'] for item in selected})
            db.execute(
                """
                UPDATE gi_guided_history_session
                SET presented_question_ids_json = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (json.dumps(new_presented), session_row['id']),
            )
            db.commit()
        return selected

    def interview_complete(self, db, session_row) -> bool:
        questions = self.load_questions_for_complaint(db, session_row['complaint_code'])
        answers = {
            r['question_id']: r['response_value']
            for r in db.execute(
                'SELECT question_id, response_value FROM gi_guided_history_answer WHERE session_id = ?',
                (session_row['id'],),
            ).fetchall()
        }
        for question in questions:
            if not self._should_show(db, question, answers, session_row):
                continue
            if question.get('is_required') and question['question_id'] not in answers:
                return False
        return True

    def _should_show(self, db, question: dict, answers: dict[str, str], session_row) -> bool:
        rules = question.get('conditional_rules') or {}
        for rule in rules.get('show_when') or []:
            if not self._rule_matches(rule, answers):
                return False
        for rule in rules.get('hide_when') or []:
            if self._rule_matches(rule, answers):
                return False

        rule_row = db.execute(
            """
            SELECT activation_rules_json FROM gi_guided_history_question_rule
            WHERE complaint_code = ? AND question_id = ?
            """,
            (session_row['complaint_code'] or '', question['question_id']),
        ).fetchone()
        if rule_row and rule_row['activation_rules_json']:
            activation = _parse_json(rule_row['activation_rules_json'], {})
            for rule in activation.get('show_when') or []:
                if not self._rule_matches(rule, answers):
                    return False
            for rule in activation.get('hide_when') or []:
                if self._rule_matches(rule, answers):
                    return False
        return True

    @staticmethod
    def _rule_matches(rule: dict[str, Any], answers: dict[str, str]) -> bool:
        question_id = rule.get('question_id')
        if not question_id:
            return True
        answer = (answers.get(question_id) or '').strip().lower()
        if 'answer_equals' in rule:
            return answer == str(rule['answer_equals']).strip().lower()
        if 'answer_in' in rule:
            allowed = {str(v).strip().lower() for v in rule['answer_in']}
            return answer in allowed
        if 'answer_not_in' in rule:
            blocked = {str(v).strip().lower() for v in rule['answer_not_in']}
            return answer not in blocked
        return bool(answer)

    @staticmethod
    def _knowledge_references(db, question: dict) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        stable_id = question.get('knowledge_stable_id')
        topic_key = question.get('knowledge_topic_key')
        if stable_id:
            row = db.execute(
                'SELECT slug, title, status FROM gi_knowledge_object WHERE slug = ? AND status = ?',
                (stable_id, 'published'),
            ).fetchone()
            if row:
                refs.append({'stable_id': row['slug'], 'title': row['title'], 'status': row['status']})
        if topic_key:
            rows = db.execute(
                """
                SELECT slug, title, status FROM gi_knowledge_object
                WHERE slug LIKE ? AND status = 'published' LIMIT 5
                """,
                (f'{topic_key}%',),
            ).fetchall()
            for row in rows:
                refs.append({'stable_id': row['slug'], 'title': row['title'], 'status': row['status']})
        return refs

    @staticmethod
    def _row_to_question(row) -> dict:
        return {
            'question_id': row['question_id'],
            'question_text': row['question_text'],
            'category': row['category'],
            'clinical_purpose': row['clinical_purpose'],
            'question_type': row['question_type'],
            'answer_options': _parse_json(row['answer_options_json'], []),
            'is_required': bool(row['is_required']),
            'priority': row['priority'],
            'conditional_rules': _parse_json(row['conditional_rules_json'], {}),
            'knowledge_topic_key': row['knowledge_topic_key'] if 'knowledge_topic_key' in row.keys() else None,
            'knowledge_stable_id': row['knowledge_stable_id'] if 'knowledge_stable_id' in row.keys() else None,
            'version': row['version'] if 'version' in row.keys() else 1,
        }
