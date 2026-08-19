"""Deterministic CDS — delegates to gi_platform.decision_support orchestrator."""

from __future__ import annotations

import json
from typing import Any

from gi_platform.decision_support.adapters import (
    LegacyAssessmentContext as AssessmentContext,
    LegacyAssessmentResult as AssessmentResult,
    build_context_from_session,
    to_legacy_result,
)
from gi_platform.decision_support.service import get_decision_support_service

__all__ = ['AssessmentContext', 'AssessmentResult', 'assess', 'persist_assessment']


def _match_knowledge(db, terms: list[str], limit: int = 10) -> list:
    if not terms:
        return []
    clauses = []
    params: list[Any] = []
    for term in terms:
        like = f'%{term.strip()}%'
        clauses.append('(title LIKE ? OR summary LIKE ? OR slug LIKE ?)')
        params.extend([like, like, like])
    sql = f"""
        SELECT * FROM gi_knowledge_object
        WHERE status = 'published' AND ({' OR '.join(clauses)})
        ORDER BY title LIMIT ?
    """
    params.append(limit)
    return db.execute(sql, params).fetchall()


def assess(db, context: AssessmentContext, *, include_teaching: bool = True) -> AssessmentResult:
    if context.complaint_code and (context.session_id or context.ward_patient_id):
        ds_ctx = build_context_from_session(
            db,
            session_id=context.session_id,
            complaint_code=context.complaint_code,
            ward_patient_id=context.ward_patient_id,
            teaching_mode=include_teaching,
            legacy=context,
        )
        if ds_ctx.complaint_code:
            result = get_decision_support_service(db).assess(ds_ctx)
            legacy = to_legacy_result(result)
            if not include_teaching:
                legacy.teaching = []
            return legacy

    terms = [context.chief_complaint] + context.symptoms + context.findings
    terms = [t for t in terms if t and t.strip()]
    hits = _match_knowledge(db, terms)
    result = AssessmentResult()

    for row in hits:
        obj_type = row['object_type']
        item = {'id': row['id'], 'slug': row['slug'], 'title': row['title'], 'summary': row['summary']}
        if obj_type in ('condition', 'disease'):
            result.differentials.append(item)
        elif obj_type == 'guideline':
            result.guidelines.append(item)
        elif obj_type == 'score':
            result.scores.append(item)

    blob = ' '.join(terms).lower()
    if any(t in blob for t in ['bleed', 'melena', 'hematemesis']):
        result.investigations.extend([
            {'name': 'CBC + coagulation profile', 'priority': 'urgent',
             'rationale': 'Baseline hemoglobin and coagulation before endoscopy.'},
            {'name': 'Upper GI endoscopy', 'priority': 'urgent',
             'rationale': 'Diagnostic and therapeutic for upper GI bleeding.'},
        ])
    if include_teaching and result.differentials:
        result.teaching.append('Rank differentials by pre-test probability and hemodynamic status.')
    return result


def persist_assessment(db, context: AssessmentContext, result: AssessmentResult,
                       created_by: int | None = None) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_cds_assessment (session_id, ward_patient_id, context_json, result_json, created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            context.session_id,
            context.ward_patient_id,
            json.dumps(context.__dict__, default=list),
            json.dumps(result.__dict__, default=list),
            created_by,
        ),
    )
    for inv in result.investigations:
        if context.session_id:
            db.execute(
                """
                INSERT INTO gi_investigation_suggestion (session_id, name, rationale, priority)
                VALUES (?, ?, ?, ?)
                """,
                (
                    context.session_id,
                    inv.get('name', inv.get('investigation_code', 'Investigation')),
                    inv.get('rationale', inv.get('reason', '')),
                    inv.get('priority', inv.get('tier', 'routine')),
                ),
            )
    db.commit()
    return cur.lastrowid
