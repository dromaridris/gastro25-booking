"""Context builder — Gastro25 SQLite integration hooks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from gi_platform.clinical_ai.constants import (
    ALL_CONTEXT_SOURCES,
    CONTEXT_CLINICAL_HISTORY,
    CONTEXT_CLINICAL_REGISTRY,
    CONTEXT_IMAGING,
    CONTEXT_KNOWLEDGE_OBJECTS,
    CONTEXT_LABORATORY,
    CONTEXT_PROCEDURES,
    CONTEXT_REPORTS,
    CONTEXT_RESEARCH,
)

ContextFetcher = Callable[..., Any]


@dataclass
class ContextRequest:
    ward_patient_id: int | None = None
    history_session_id: int | None = None
    sources: list[str] = field(default_factory=list)
    topic_keys: list[str] = field(default_factory=list)
    object_types: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class ContextBuilder:
    def __init__(self) -> None:
        self._fetchers: dict[str, ContextFetcher] = {}

    def register_fetcher(self, source_key: str, fetcher: ContextFetcher) -> None:
        if source_key not in ALL_CONTEXT_SOURCES:
            raise ValueError(f'Unknown context source: {source_key}')
        self._fetchers[source_key] = fetcher

    def available_sources(self) -> list[str]:
        return sorted(self._fetchers.keys())

    def build(self, request: ContextRequest) -> dict[str, Any]:
        sources = request.sources or list(self._fetchers.keys())
        payload: dict[str, Any] = {}
        for source in sources:
            fetcher = self._fetchers.get(source)
            if fetcher is None:
                continue
            payload[source] = fetcher(
                ward_patient_id=request.ward_patient_id,
                history_session_id=request.history_session_id,
                topic_keys=request.topic_keys,
                object_types=request.object_types,
                extra=request.extra,
            )
        return payload


def default_context_builder(db) -> ContextBuilder:
    builder = ContextBuilder()

    def _history(**kwargs: Any) -> dict[str, Any]:
        wid = kwargs.get('ward_patient_id')
        if not wid:
            return {}
        sess = db.execute(
            """
            SELECT * FROM gi_history_session
            WHERE ward_patient_id = ? ORDER BY updated_at DESC LIMIT 1
            """,
            (wid,),
        ).fetchone()
        if not sess:
            return {}
        answers = db.execute(
            'SELECT question_key, answer_text FROM gi_history_answer WHERE session_id = ?',
            (sess['id'],),
        ).fetchall()
        return {
            'session_id': sess['id'],
            'complaint_code': sess['complaint_code'] if 'complaint_code' in sess.keys() else None,
            'chief_complaint': sess['chief_complaint'],
            'final_diagnosis': sess['final_diagnosis'] if 'final_diagnosis' in sess.keys() else '',
            'answers': [dict(a) for a in answers],
        }

    def _knowledge(**kwargs: Any) -> list[dict[str, Any]]:
        object_types = kwargs.get('object_types') or ['guideline', 'condition', 'score']
        rows = db.execute(
            """
            SELECT slug, title, object_type, status, summary
            FROM gi_knowledge_object
            WHERE status = 'published' AND object_type IN ({})
            ORDER BY title LIMIT 30
            """.format(','.join('?' * len(object_types))),
            object_types,
        ).fetchall()
        return [dict(r) for r in rows]

    def _laboratory(**kwargs: Any) -> list[dict[str, Any]]:
        wid = kwargs.get('ward_patient_id')
        if not wid:
            return []
        rows = db.execute(
            """
            SELECT test_code, test_name, result_value, result_unit, reference_range, result_date
            FROM gi_lab_result WHERE ward_patient_id = ?
            ORDER BY result_date DESC LIMIT 40
            """,
            (wid,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _procedures(**kwargs: Any) -> list[dict[str, Any]]:
        wid = kwargs.get('ward_patient_id')
        if not wid:
            return []
        patient = db.execute('SELECT mrn FROM ward_patient WHERE id = ?', (wid,)).fetchone()
        if not patient or not patient['mrn']:
            return []
        rows = db.execute(
            """
            SELECT appointment_date, procedure_type, patient_name, clinical_notes
            FROM appointment WHERE mrn = ? ORDER BY appointment_date DESC LIMIT 15
            """,
            (patient['mrn'],),
        ).fetchall()
        return [dict(r) for r in rows]

    def _research(**kwargs: Any) -> list[dict[str, Any]]:
        wid = kwargs.get('ward_patient_id')
        if not wid:
            return []
        patient = db.execute('SELECT mrn FROM ward_patient WHERE id = ?', (wid,)).fetchone()
        if not patient or not patient['mrn']:
            return []
        rows = db.execute(
            """
            SELECT r.title, e.enrolled_at
            FROM gi_research_enrollment e
            JOIN gi_research_registry r ON r.id = e.registry_id
            WHERE e.mrn = ? OR e.ward_patient_id = ?
            ORDER BY e.enrolled_at DESC LIMIT 10
            """,
            (patient['mrn'], wid),
        ).fetchall()
        return [dict(r) for r in rows]

    def _scores(**kwargs: Any) -> list[dict[str, Any]]:
        wid = kwargs.get('ward_patient_id')
        if not wid:
            return []
        rows = db.execute(
            """
            SELECT score_code, score_name, score_value, created_at
            FROM gi_clinical_score_result WHERE ward_patient_id = ?
            ORDER BY created_at DESC LIMIT 15
            """,
            (wid,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _empty(**kwargs: Any) -> list[Any]:
        return []

    builder.register_fetcher(CONTEXT_CLINICAL_HISTORY, _history)
    builder.register_fetcher(CONTEXT_KNOWLEDGE_OBJECTS, _knowledge)
    builder.register_fetcher(CONTEXT_LABORATORY, _laboratory)
    builder.register_fetcher(CONTEXT_PROCEDURES, _procedures)
    builder.register_fetcher(CONTEXT_RESEARCH, _research)
    builder.register_fetcher(CONTEXT_CLINICAL_REGISTRY, _scores)
    for source in (CONTEXT_IMAGING, CONTEXT_REPORTS):
        builder.register_fetcher(source, _empty)
    return builder
