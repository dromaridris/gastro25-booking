"""Extend Gastro25 /search with ward + knowledge hits via context processor."""

from flask import request

from gi_platform import knowledge_service


def register_search_extension(app, *, get_db):
    @app.context_processor
    def _gi_search_hits():
        if request.endpoint != 'search_patients':
            return {}
        q = request.args.get('q', '').strip()
        if not q:
            return {}
        db = get_db()
        knowledge_hits = knowledge_service.search_knowledge(db, q, limit=10)
        ward_hits = db.execute(
            """
            SELECT id, patient_name, mrn
            FROM ward_patient
            WHERE patient_name LIKE ? COLLATE NOCASE OR mrn LIKE ? COLLATE NOCASE
            ORDER BY patient_name LIMIT 10
            """,
            (f'%{q}%', f'%{q}%'),
        ).fetchall()
        return {
            'gi_knowledge_hits': knowledge_hits,
            'gi_ward_hits': ward_hits,
            'GI_SEARCH_EXTENDED': True,
        }
