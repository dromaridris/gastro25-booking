"""G25-native analytics metrics registry."""

from __future__ import annotations

from typing import Any, Callable

METRICS: dict[str, dict[str, Any]] = {
    'g25.clinical.assessment_runs': {
        'name': 'Clinical assessment runs',
        'description': 'Total differential assessment generations.',
        'category': 'clinical_ai',
    },
    'g25.clinical.signed_documents': {
        'name': 'Signed clinical documents',
        'description': 'Documents signed via documentation AI.',
        'category': 'documentation',
    },
    'g25.clinical.ai_sessions': {
        'name': 'Clinical AI sessions',
        'description': 'Total AI session records.',
        'category': 'clinical_ai',
    },
    'g25.journey.events': {
        'name': 'Journey timeline events',
        'description': 'Events recorded in patient journey.',
        'category': 'journey',
    },
    'g25.research.enrollments': {
        'name': 'Research enrollments',
        'description': 'Active research enrollment count.',
        'category': 'research',
    },
}


def _count_table(db, table: str, where: str = '1=1') -> int:
    row = db.execute(f'SELECT COUNT(*) AS c FROM {table} WHERE {where}').fetchone()
    return int(row['c'])


RUNNERS: dict[str, Callable] = {
    'g25.clinical.assessment_runs': lambda db: _count_table(db, 'gi_clinical_assessment_run'),
    'g25.clinical.signed_documents': lambda db: _count_table(db, 'gi_signed_clinical_document'),
    'g25.clinical.ai_sessions': lambda db: _count_table(db, 'gi_ai_session'),
    'g25.journey.events': lambda db: _count_table(db, 'gi_journey_event'),
    'g25.research.enrollments': lambda db: _count_table(db, 'gi_research_enrollment', "status != 'withdrawn'"),
}


def list_metrics() -> list[dict[str, Any]]:
    return [
        {'metric_id': mid, **meta, 'status': 'active'}
        for mid, meta in METRICS.items()
    ]


def run_metric(db, metric_id: str) -> dict[str, Any]:
    if metric_id not in METRICS:
        raise ValueError(f'Unknown metric: {metric_id}')
    runner = RUNNERS[metric_id]
    value = runner(db)
    return {
        'metric_id': metric_id,
        'name': METRICS[metric_id]['name'],
        'value': value,
        'unit': 'count',
        'category': METRICS[metric_id]['category'],
    }
