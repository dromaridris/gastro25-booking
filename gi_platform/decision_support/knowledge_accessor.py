"""Load CDS artifacts from gi_knowledge_object — Gastro25 SQLite backend."""

from __future__ import annotations

import json
from typing import Any

from gi_platform.decision_support.constants import (
    OBJECT_TYPE_CDS_RULE,
    OBJECT_TYPE_DISEASE,
    OBJECT_TYPE_GUIDELINE,
    OBJECT_TYPE_HISTORY_QUESTION,
    OBJECT_TYPE_INVESTIGATION,
    OBJECT_TYPE_MANAGEMENT,
    OBJECT_TYPE_SCORE,
    PROVIDER_KEY,
    RULE_KIND_ALIASES,
    RULE_KIND_BRANCH_ACTIVATION,
    RULE_KIND_INVESTIGATION_ADVANCED,
    RULE_KIND_INVESTIGATION_BASELINE,
    RULE_KIND_PRIOR,
    RULE_KIND_QUESTION,
    RULE_KIND_RED_FLAG,
    RULE_KIND_WEIGHT,
    STATUS_PUBLISHED,
)
from gi_platform.decision_support.knowledge_object import KnowledgeObject


def _normalize_rule_kind(kind: str | None) -> str | None:
    if not kind:
        return None
    return RULE_KIND_ALIASES.get(kind, kind)


def _row_to_object(row) -> KnowledgeObject:
    attrs = json.loads(row['body_json'] or '{}')
    if not isinstance(attrs, dict):
        attrs = {}
    stable = row['stable_id'] if 'stable_id' in row.keys() and row['stable_id'] else row['slug']
    return KnowledgeObject(
        stable_id=stable,
        title=row['title'],
        object_type=row['object_type'],
        summary=row['summary'] or '',
        body=str(attrs.get('body', '') or ''),
        topic_key=row['slug'],
        attributes=attrs,
        object_id=row['id'],
    )


class CdsKnowledgeAccessor:
    """Specialty-independent knowledge reader over SQLite gi_knowledge_object."""

    def __init__(self, db):
        self._db = db

    @property
    def provider_key(self) -> str:
        return PROVIDER_KEY

    def _published_rules(self, rule_kind: str | None = None, complaint_code: str | None = None) -> list[KnowledgeObject]:
        rows = self._db.execute(
            """
            SELECT * FROM gi_knowledge_object
            WHERE object_type = ? AND status = ?
            ORDER BY title LIMIT 5000
            """,
            (OBJECT_TYPE_CDS_RULE, STATUS_PUBLISHED),
        ).fetchall()
        out: list[KnowledgeObject] = []
        for row in rows:
            obj = _row_to_object(row)
            kind = _normalize_rule_kind(obj.attributes.get('rule_kind'))
            if rule_kind and kind != rule_kind:
                continue
            if complaint_code and obj.attributes.get('complaint_code') != complaint_code:
                continue
            out.append(obj)
        return out

    def differential_priors(self, complaint_code: str) -> list[KnowledgeObject]:
        return self._published_rules(RULE_KIND_PRIOR, complaint_code)

    def weight_rules(self, complaint_code: str) -> list[KnowledgeObject]:
        return self._published_rules(RULE_KIND_WEIGHT, complaint_code)

    def question_rules(self, complaint_code: str) -> list[KnowledgeObject]:
        rules = self._published_rules(RULE_KIND_QUESTION, complaint_code)
        questions = self._db.execute(
            """
            SELECT * FROM gi_knowledge_object
            WHERE object_type = ? AND status = ?
            ORDER BY title LIMIT 5000
            """,
            (OBJECT_TYPE_HISTORY_QUESTION, STATUS_PUBLISHED),
        ).fetchall()
        for row in questions:
            q = _row_to_object(row)
            if q.attributes.get('complaint_code') not in (complaint_code, None, ''):
                continue
            q_code = q.attributes.get('question_code')
            if not any(r.attributes.get('question_code') == q_code for r in rules):
                rules.append(q)
        return rules

    def red_flag_rules(self, complaint_code: str) -> list[KnowledgeObject]:
        return self._published_rules(RULE_KIND_RED_FLAG, complaint_code)

    def branch_activation_rules(self, complaint_code: str) -> list[KnowledgeObject]:
        return self._published_rules(RULE_KIND_BRANCH_ACTIVATION, complaint_code)

    def baseline_investigations(self, complaint_code: str) -> list[KnowledgeObject]:
        baseline = self._published_rules(RULE_KIND_INVESTIGATION_BASELINE, complaint_code)
        if baseline:
            return baseline
        rows = self._db.execute(
            """
            SELECT * FROM gi_knowledge_object
            WHERE object_type = ? AND status = ?
              AND json_extract(body_json, '$.complaint_code') = ?
            ORDER BY title
            """,
            (OBJECT_TYPE_INVESTIGATION, STATUS_PUBLISHED, complaint_code),
        ).fetchall()
        return [_row_to_object(r) for r in rows]

    def advanced_investigations(self, complaint_code: str, diagnosis_code: str | None = None) -> list[KnowledgeObject]:
        rows = self._published_rules(RULE_KIND_INVESTIGATION_ADVANCED, complaint_code)
        if diagnosis_code:
            rows = [
                r for r in rows
                if not r.attributes.get('diagnosis_code') or r.attributes.get('diagnosis_code') == diagnosis_code
            ]
        return rows

    def score_definitions(self) -> list[KnowledgeObject]:
        rows = self._db.execute(
            """
            SELECT * FROM gi_knowledge_object
            WHERE object_type = ? AND status = ?
            ORDER BY title LIMIT 500
            """,
            (OBJECT_TYPE_SCORE, STATUS_PUBLISHED),
        ).fetchall()
        return [_row_to_object(r) for r in rows]

    def disease(self, diagnosis_code: str) -> KnowledgeObject | None:
        rows = self._db.execute(
            """
            SELECT * FROM gi_knowledge_object
            WHERE object_type = ? AND status = ?
            """,
            (OBJECT_TYPE_DISEASE, STATUS_PUBLISHED),
        ).fetchall()
        for row in rows:
            obj = _row_to_object(row)
            if obj.attributes.get('diagnosis_code') == diagnosis_code or obj.stable_id == diagnosis_code:
                return obj
        return None

    def investigation(self, investigation_code: str) -> KnowledgeObject | None:
        rows = self._db.execute(
            """
            SELECT * FROM gi_knowledge_object
            WHERE object_type = ? AND status = ?
            """,
            (OBJECT_TYPE_INVESTIGATION, STATUS_PUBLISHED),
        ).fetchall()
        for row in rows:
            obj = _row_to_object(row)
            if obj.attributes.get('investigation_code') == investigation_code or obj.stable_id == investigation_code:
                return obj
        slug_row = self._db.execute(
            'SELECT * FROM gi_knowledge_object WHERE slug = ? AND status = ?',
            (investigation_code, STATUS_PUBLISHED),
        ).fetchone()
        if slug_row:
            return _row_to_object(slug_row)
        return None

    def guidelines_for_diagnosis(self, diagnosis_code: str) -> list[KnowledgeObject]:
        linked: list[KnowledgeObject] = []
        dx = self.disease(diagnosis_code)
        if dx and dx.object_id:
            link_rows = self._db.execute(
                """
                SELECT ko.* FROM gi_knowledge_link l
                JOIN gi_knowledge_object ko ON ko.id = l.target_id
                WHERE l.source_id = ? AND l.link_type IN ('applies_to', 'managed_by', 'guideline_for')
                  AND ko.object_type = ? AND ko.status = ?
                """,
                (dx.object_id, OBJECT_TYPE_GUIDELINE, STATUS_PUBLISHED),
            ).fetchall()
            linked.extend(_row_to_object(r) for r in link_rows)

        patterns = (f'%{diagnosis_code}%', f'kl.{diagnosis_code}%')
        for pattern in patterns:
            rows = self._db.execute(
                """
                SELECT * FROM gi_knowledge_object
                WHERE object_type = ? AND status = ?
                  AND (slug LIKE ? OR body_json LIKE ?)
                LIMIT 20
                """,
                (OBJECT_TYPE_GUIDELINE, STATUS_PUBLISHED, pattern, pattern),
            ).fetchall()
            for row in rows:
                obj = _row_to_object(row)
                if obj.stable_id not in {g.stable_id for g in linked}:
                    linked.append(obj)
        return linked

    def management_for_diagnosis(self, diagnosis_code: str) -> KnowledgeObject | None:
        rows = self._db.execute(
            """
            SELECT * FROM gi_knowledge_object
            WHERE object_type = ? AND status = ?
            """,
            (OBJECT_TYPE_MANAGEMENT, STATUS_PUBLISHED),
        ).fetchall()
        for row in rows:
            obj = _row_to_object(row)
            if obj.attributes.get('diagnosis_code') == diagnosis_code:
                return obj
        return None

    def question_prompt(self, question_code: str) -> str:
        slug = f'kl.question.{question_code.replace(".", "_")}'
        row = self._db.execute(
            """
            SELECT title, body_json FROM gi_knowledge_object
            WHERE (slug = ? OR body_json LIKE ?) AND status = ?
            LIMIT 1
            """,
            (slug, f'%"question_code": "{question_code}"%', STATUS_PUBLISHED),
        ).fetchone()
        if row:
            body = json.loads(row['body_json'] or '{}')
            return body.get('prompt') or row['title']
        return question_code

    def references_for_object(self, stable_id: str) -> list[KnowledgeObject]:
        row = self._db.execute(
            'SELECT id FROM gi_knowledge_object WHERE slug = ? OR stable_id = ?',
            (stable_id, stable_id),
        ).fetchone()
        if not row:
            return []
        refs = self._db.execute(
            """
            SELECT ko.* FROM gi_knowledge_link l
            JOIN gi_knowledge_object ko ON ko.id = l.target_id
            WHERE l.source_id = ? AND l.link_type IN ('references', 'cites')
            """,
            (row['id'],),
        ).fetchall()
        return [_row_to_object(r) for r in refs]
