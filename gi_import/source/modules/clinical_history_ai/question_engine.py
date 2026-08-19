"""Configurable History Question Engine with adaptive selection."""

from __future__ import annotations

import json
from typing import Any

from app.modules.clinical_history_ai.models import (
    GuidedHistoryAnswer,
    GuidedHistoryQuestion,
    GuidedHistoryQuestionRule,
    GuidedHistorySession,
)
from app.modules.knowledge_library.services import get_knowledge_service


class HistoryQuestionEngine:
    """Loads and adapts history questions from structured configuration."""

    def load_questions_for_complaint(
        self,
        complaint_code: str | None,
        *,
        specialty_code: str | None = None,
    ) -> list[GuidedHistoryQuestion]:
        if not complaint_code:
            return []
        rules = (
            GuidedHistoryQuestionRule.query.filter_by(
                complaint_code=complaint_code, is_archived=False
            )
            .order_by(GuidedHistoryQuestionRule.sort_order)
            .all()
        )
        if specialty_code:
            rules = [
                r
                for r in rules
                if r.specialty_code in (None, specialty_code)
            ]
        question_ids = [rule.question_id for rule in rules]
        if not question_ids:
            return []

        questions = (
            GuidedHistoryQuestion.query.filter(
                GuidedHistoryQuestion.question_id.in_(question_ids),
                GuidedHistoryQuestion.status == "active",
                GuidedHistoryQuestion.is_archived.is_(False),
            )
            .all()
        )
        order = {qid: idx for idx, qid in enumerate(question_ids)}
        return sorted(questions, key=lambda q: (order.get(q.question_id, 999), q.priority))

    def next_questions(
        self,
        session: GuidedHistorySession,
        *,
        limit: int = 5,
        specialty_code: str | None = None,
    ) -> list[dict[str, Any]]:
        all_questions = self.load_questions_for_complaint(
            session.complaint_entry_code, specialty_code=specialty_code
        )
        answers = {
            row.question_id: row.response_value
            for row in GuidedHistoryAnswer.query.filter_by(
                session_id=session.id, is_archived=False
            ).all()
        }
        presented = set(session.presented_question_ids)
        selected: list[dict[str, Any]] = []

        for question in all_questions:
            if question.question_id in answers:
                continue
            if not self._should_show(question, answers, session):
                continue
            knowledge_refs = self._knowledge_references(question)
            selected.append(
                {
                    "question_id": question.question_id,
                    "question_text": question.question_text,
                    "category": question.category,
                    "clinical_purpose": question.clinical_purpose,
                    "question_type": question.question_type,
                    "answer_options": question.answer_options,
                    "is_required": question.is_required,
                    "priority": question.priority,
                    "knowledge_references": knowledge_refs,
                    "version": question.version,
                }
            )
            if len(selected) >= limit:
                break

        if selected:
            new_presented = list(presented | {item["question_id"] for item in selected})
            session.presented_question_ids = new_presented

        return selected

    def interview_complete(self, session: GuidedHistorySession) -> bool:
        questions = self.load_questions_for_complaint(session.complaint_entry_code)
        answers = {
            row.question_id: row.response_value
            for row in GuidedHistoryAnswer.query.filter_by(
                session_id=session.id, is_archived=False
            ).all()
        }
        for question in questions:
            if not self._should_show(question, answers, session):
                continue
            if question.is_required and question.question_id not in answers:
                return False
        return True

    def _should_show(
        self,
        question: GuidedHistoryQuestion,
        answers: dict[str, str],
        session: GuidedHistorySession,
    ) -> bool:
        rules = question.conditional_rules or {}
        show_when = rules.get("show_when") or []
        hide_when = rules.get("hide_when") or []

        for rule in show_when:
            if not self._rule_matches(rule, answers):
                return False
        for rule in hide_when:
            if self._rule_matches(rule, answers):
                return False

        rule_row = GuidedHistoryQuestionRule.query.filter_by(
            complaint_code=session.complaint_entry_code or "",
            question_id=question.question_id,
            is_archived=False,
        ).first()
        if rule_row and rule_row.activation_rules:
            activation = rule_row.activation_rules
            for rule in activation.get("show_when") or []:
                if not self._rule_matches(rule, answers):
                    return False
            for rule in activation.get("hide_when") or []:
                if self._rule_matches(rule, answers):
                    return False
        return True

    @staticmethod
    def _rule_matches(rule: dict[str, Any], answers: dict[str, str]) -> bool:
        question_id = rule.get("question_id")
        if not question_id:
            return True
        answer = (answers.get(question_id) or "").strip().lower()
        if "answer_equals" in rule:
            return answer == str(rule["answer_equals"]).strip().lower()
        if "answer_in" in rule:
            allowed = {str(v).strip().lower() for v in rule["answer_in"]}
            return answer in allowed
        if "answer_not_in" in rule:
            blocked = {str(v).strip().lower() for v in rule["answer_not_in"]}
            return answer not in blocked
        return bool(answer)

    @staticmethod
    def _knowledge_references(question: GuidedHistoryQuestion) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        service = get_knowledge_service()
        if question.knowledge_stable_id:
            obj = service.get_published(question.knowledge_stable_id)
            if obj:
                refs.append(
                    {
                        "stable_id": obj.stable_id,
                        "title": obj.title,
                        "topic_key": obj.topic_key,
                        "status": obj.version.status,
                    }
                )
        if question.knowledge_topic_key:
            for obj in service.find_by_topic_key(question.knowledge_topic_key):
                refs.append(
                    {
                        "stable_id": obj.stable_id,
                        "title": obj.title,
                        "topic_key": obj.topic_key,
                        "status": obj.version.status,
                    }
                )
        return refs
