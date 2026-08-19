"""Clinical registry dashboard — aggregate hospital statistics from SQLite."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from gi_platform.clinical_registry_catalog import (
    BUILTIN_DISEASE_GROUPS,
    CATEGORY_LABELS,
    CLINICAL_MODULE_CARDS,
    CORE_CARDS,
    PROCEDURE_CARDS,
)


def _today() -> date:
    return date.today()


def _period_bounds(period: str) -> tuple[str | None, str | None]:
    today = _today()
    if period == 'today':
        iso = today.isoformat()
        return iso, iso
    if period == 'week':
        start = today - timedelta(days=today.weekday())
        return start.isoformat(), today.isoformat()
    if period == 'month':
        start = today.replace(day=1)
        return start.isoformat(), today.isoformat()
    if period == 'year':
        start = today.replace(month=1, day=1)
        return start.isoformat(), today.isoformat()
    return None, None


def _count_appts(db, *, start: str | None = None, end: str | None = None,
                 procedure_types: list[str] | None = None) -> int:
    q = 'SELECT COUNT(*) AS c FROM appointment WHERE 1=1'
    params: list = []
    if start and end:
        q += ' AND appointment_date BETWEEN ? AND ?'
        params.extend([start, end])
    elif start:
        q += ' AND appointment_date = ?'
        params.append(start)
    if procedure_types:
        placeholders = ','.join('?' * len(procedure_types))
        q += f' AND procedure_type IN ({placeholders})'
        params.extend(procedure_types)
    return db.execute(q, params).fetchone()['c']


def _report_stats(db, table: str, *, procedure_types: list[str] | None = None) -> dict:
    if not _table_exists(db, table):
        return {'total': 0, 'draft': 0, 'finalized': 0, 'pending': 0, 'completed': 0}
    base = f"""
        SELECT r.status, COUNT(*) AS c
        FROM {table} r
        JOIN appointment a ON a.id = r.appointment_id
    """
    params: list = []
    where = []
    if procedure_types:
        placeholders = ','.join('?' * len(procedure_types))
        where.append(f'a.procedure_type IN ({placeholders})')
        params.extend(procedure_types)
    if where:
        base += ' WHERE ' + ' AND '.join(where)
    base += ' GROUP BY r.status'
    rows = db.execute(base, params).fetchall()
    totals = {'draft': 0, 'finalized': 0}
    for row in rows:
        st = (row['status'] or '').lower()
        if st == 'finalized':
            totals['finalized'] = row['c']
        else:
            totals['draft'] += row['c']
    total = totals['draft'] + totals['finalized']
    return {
        'total': total,
        'draft': totals['draft'],
        'finalized': totals['finalized'],
        'pending': totals['draft'],
        'completed': totals['finalized'],
    }


def _table_exists(db, name: str) -> bool:
    row = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,),
    ).fetchone()
    return row is not None


def _distinct_patients(db) -> int:
    appt = db.execute(
        "SELECT COUNT(DISTINCT mrn) AS c FROM appointment WHERE mrn IS NOT NULL AND mrn != ''"
    ).fetchone()['c']
    ward = 0
    if _table_exists(db, 'ward_patient'):
        ward = db.execute('SELECT COUNT(*) AS c FROM ward_patient').fetchone()['c']
    return max(appt, ward)


def _active_admissions(db) -> int:
    if not _table_exists(db, 'ward_admission'):
        return 0
    return db.execute(
        "SELECT COUNT(*) AS c FROM ward_admission WHERE is_active = 1"
    ).fetchone()['c']


def _match_diagnosis_count(db, terms: list[str]) -> int:
    if not terms or not _table_exists(db, 'gi_history_session'):
        return 0
    clauses = []
    params: list = []
    for term in terms:
        like = f'%{term.lower()}%'
        clauses.append(
            "(LOWER(COALESCE(final_diagnosis,'')) LIKE ? OR LOWER(COALESCE(chief_complaint,'')) LIKE ? "
            "OR LOWER(COALESCE(complaint_code,'')) LIKE ?)"
        )
        params.extend([like, like, like])
    sql = f"""
        SELECT COUNT(DISTINCT COALESCE(ward_patient_id, id)) AS c
        FROM gi_history_session WHERE {' OR '.join(clauses)}
    """
    try:
        return db.execute(sql, params).fetchone()['c']
    except Exception:
        return 0


def _load_custom_diagnoses(db) -> list[dict]:
    if not _table_exists(db, 'gi_registry_diagnosis'):
        return []
    rows = db.execute(
        "SELECT * FROM gi_registry_diagnosis WHERE is_active = 1 ORDER BY disease_name"
    ).fetchall()
    out = []
    for r in rows:
        terms = [r['disease_name'], r['disease_code']]
        if r['match_terms_json']:
            import json
            try:
                terms.extend(json.loads(r['match_terms_json']))
            except json.JSONDecodeError:
                pass
        out.append({
            'code': r['disease_code'],
            'name': r['disease_name'],
            'category': 'custom',
            'icon': r['icon'] or '🩺',
            'match_terms': [t.lower() for t in terms if t],
            'subtypes': [],
            'source': 'registry',
        })
    return out


def _load_template_diagnoses(db) -> list[dict]:
    if not _table_exists(db, 'gi_history_template'):
        return []
    rows = db.execute('SELECT disease_code, disease_name FROM gi_history_template ORDER BY disease_name').fetchall()
    builtin_codes = {g['code'] for g in BUILTIN_DISEASE_GROUPS}
    for g in BUILTIN_DISEASE_GROUPS:
        for st in g.get('subtypes', []):
            builtin_codes.add(st['code'])
    out = []
    for r in rows:
        if r['disease_code'] in builtin_codes:
            continue
        out.append({
            'code': r['disease_code'],
            'name': r['disease_name'],
            'category': 'custom',
            'icon': '📋',
            'match_terms': [r['disease_name'].lower(), r['disease_code'].lower()],
            'subtypes': [],
            'source': 'history_template',
        })
    return out


def _procedure_card_stats(db, card: dict) -> dict:
    keys = card['procedure_keys']
    today = _today().isoformat()
    week_start = (_today() - timedelta(days=_today().weekday())).isoformat()
    month_start = _today().replace(day=1).isoformat()
    year_start = _today().replace(month=1, day=1).isoformat()
    end = today
    reports = _report_stats(db, card['report_table'], procedure_types=keys) if card.get('report_table') else {}
    return {
        'total': _count_appts(db, procedure_types=keys),
        'today': _count_appts(db, start=today, end=today, procedure_types=keys),
        'week': _count_appts(db, start=week_start, end=end, procedure_types=keys),
        'month': _count_appts(db, start=month_start, end=end, procedure_types=keys),
        'year': _count_appts(db, start=year_start, end=end, procedure_types=keys),
        'pending_reports': reports.get('pending', 0),
        'completed_reports': reports.get('completed', 0),
        'draft_reports': reports.get('draft', 0),
        'finalized_reports': reports.get('finalized', 0),
    }


def _ercp_extended_stats(db) -> dict:
    base = _procedure_card_stats(db, {
        'procedure_keys': ['ercp'], 'report_table': 'ercp_report',
    })
    followups = 0
    repeat_scheduled = 0
    if _table_exists(db, 'ercp_followup'):
        followups = db.execute('SELECT COUNT(DISTINCT report_id) AS c FROM ercp_followup').fetchone()['c']
    if _table_exists(db, 'appointment'):
        repeat_scheduled = db.execute(
            """
            SELECT COUNT(*) AS c FROM appointment
            WHERE procedure_type = 'ercp' AND appointment_date >= date('now')
            """
        ).fetchone()['c']
    base['patients_under_followup'] = followups
    base['repeat_scheduled'] = repeat_scheduled
    return base


def _module_stats(db, card_id: str) -> dict:
    if card_id == 'research':
        registries = enrollments = exports = 0
        if _table_exists(db, 'gi_research_registry'):
            registries = db.execute(
                "SELECT COUNT(*) AS c FROM gi_research_registry WHERE status IN ('active','approved','published')"
            ).fetchone()['c']
        if _table_exists(db, 'gi_research_enrollment'):
            enrollments = db.execute('SELECT COUNT(*) AS c FROM gi_research_enrollment').fetchone()['c']
        if _table_exists(db, 'gi_research_registry'):
            exports = db.execute('SELECT COUNT(*) AS c FROM gi_research_registry').fetchone()['c']
        return {
            'active_registries': registries,
            'total_cases': enrollments,
            'export_datasets': exports,
        }
    if card_id == 'knowledge':
        published = total = 0
        if _table_exists(db, 'gi_knowledge_object'):
            total = db.execute('SELECT COUNT(*) AS c FROM gi_knowledge_object').fetchone()['c']
            published = db.execute(
                "SELECT COUNT(*) AS c FROM gi_knowledge_object WHERE status = 'published'"
            ).fetchone()['c']
        return {'total': total, 'published': published}
    if card_id == 'encounters':
        n = 0
        if _table_exists(db, 'gi_history_session'):
            n = db.execute('SELECT COUNT(*) AS c FROM gi_history_session').fetchone()['c']
        return {'total_encounters': n}
    if card_id == 'laboratory':
        orders = results = 0
        if _table_exists(db, 'gi_investigation_order'):
            orders = db.execute('SELECT COUNT(*) AS c FROM gi_investigation_order').fetchone()['c']
        if _table_exists(db, 'gi_lab_result'):
            results = db.execute('SELECT COUNT(*) AS c FROM gi_lab_result').fetchone()['c']
        return {'orders': orders, 'results': results}
    if card_id == 'medications':
        n = 0
        if _table_exists(db, 'gi_medication_entry'):
            n = db.execute('SELECT COUNT(*) AS c FROM gi_medication_entry').fetchone()['c']
        return {'total_entries': n}
    if card_id == 'followup':
        ercp_fu = dil_fu = 0
        if _table_exists(db, 'ercp_followup'):
            ercp_fu = db.execute('SELECT COUNT(*) AS c FROM ercp_followup').fetchone()['c']
        if _table_exists(db, 'dilatation_followup'):
            dil_fu = db.execute('SELECT COUNT(*) AS c FROM dilatation_followup').fetchone()['c']
        return {'ercp_followups': ercp_fu, 'dilatation_followups': dil_fu, 'total': ercp_fu + dil_fu}
    if card_id == 'documents':
        n = 0
        if _table_exists(db, 'gi_gov_document'):
            n = db.execute('SELECT COUNT(*) AS c FROM gi_gov_document').fetchone()['c']
        return {'total_documents': n}
    if card_id == 'ai_assistant':
        n = 0
        if _table_exists(db, 'gi_ai_session'):
            n = db.execute('SELECT COUNT(*) AS c FROM gi_ai_session').fetchone()['c']
        return {'ai_sessions': n}
    return {}


def _disease_card_stats(db, group: dict) -> dict:
    total = _match_diagnosis_count(db, group.get('match_terms', []))
    subtypes = []
    for st in group.get('subtypes', []):
        cnt = _match_diagnosis_count(db, st.get('match_terms', []))
        subtypes.append({'label': st['name'], 'value': cnt})
    return {'total_patients': total, 'subtypes': subtypes}


def recent_activity(db, limit: int = 12) -> list[dict]:
    items: list[dict] = []
    rows = db.execute(
        """
        SELECT appointment_date AS when_at, patient_name AS label,
               procedure_type AS detail, 'appointment' AS kind
        FROM appointment ORDER BY appointment_date DESC, id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    for r in rows:
        items.append(dict(r))
    if _table_exists(db, 'ercp_report'):
        for r in db.execute(
            """
            SELECT r.finalized_at AS when_at, a.patient_name AS label,
                   'ERCP report finalized' AS detail, 'report' AS kind
            FROM ercp_report r JOIN appointment a ON a.id = r.appointment_id
            WHERE r.status = 'finalized' AND r.finalized_at != ''
            ORDER BY r.finalized_at DESC LIMIT 6
            """
        ).fetchall():
            items.append(dict(r))
    items.sort(key=lambda x: x.get('when_at') or '', reverse=True)
    return items[:limit]


def build_dashboard(db, *, period: str = 'all') -> dict:
    today = _today()
    p_start, p_end = _period_bounds(period)

    cards: list[dict] = []

    for c in CORE_CARDS:
        stats: dict = {}
        if c['id'] == 'patients':
            stats = {'total_patients': _distinct_patients(db)}
        elif c['id'] == 'appointments':
            stats = {
                'today': _count_appts(db, start=today.isoformat(), end=today.isoformat()),
                'this_week': _count_appts(db, start=(today - timedelta(days=today.weekday())).isoformat(), end=today.isoformat()),
                'this_month': _count_appts(db, start=today.replace(day=1).isoformat(), end=today.isoformat()),
                'total': _count_appts(db),
            }
        elif c['id'] == 'admissions':
            stats = {
                'active_admissions': _active_admissions(db),
                'ward_patients': db.execute('SELECT COUNT(*) AS c FROM ward_patient').fetchone()['c'] if _table_exists(db, 'ward_patient') else 0,
            }
        cards.append({**c, 'stats': stats, 'card_type': 'core'})

    for c in PROCEDURE_CARDS:
        stats = _ercp_extended_stats(db) if c['id'] == 'ercp' else _procedure_card_stats(db, c)
        cards.append({**c, 'stats': stats, 'card_type': 'procedure'})

    for group in BUILTIN_DISEASE_GROUPS:
        cards.append({
            'id': group['code'],
            'title': group['name'],
            'icon': group['icon'],
            'category': 'disease',
            'card_type': 'disease',
            'stats': _disease_card_stats(db, group),
        })

    for group in _load_template_diagnoses(db) + _load_custom_diagnoses(db):
        cards.append({
            'id': group['code'],
            'title': group['name'],
            'icon': group.get('icon', '🩺'),
            'category': group.get('category', 'custom'),
            'card_type': 'disease',
            'stats': _disease_card_stats(db, group),
            'source': group.get('source'),
        })

    for c in CLINICAL_MODULE_CARDS:
        cards.append({**c, 'stats': _module_stats(db, c['id']), 'card_type': 'module'})

    summary = {
        'total_patients': _distinct_patients(db),
        'appointments_today': _count_appts(db, start=today.isoformat(), end=today.isoformat()),
        'active_admissions': _active_admissions(db),
        'ercp_total': _count_appts(db, procedure_types=['ercp']),
    }

    return {
        'cards': cards,
        'categories': CATEGORY_LABELS,
        'summary': summary,
        'recent': recent_activity(db),
        'period': period,
        'period_start': p_start,
        'period_end': p_end,
    }


def procedure_hub(db, procedure_key: str) -> dict | None:
    card = None
    for c in PROCEDURE_CARDS:
        if c['id'] == procedure_key or procedure_key in c.get('procedure_keys', []):
            card = c
            break
    if not card:
        return None
    stats = _ercp_extended_stats(db) if card['id'] == 'ercp' else _procedure_card_stats(db, card)
    recent = db.execute(
        """
        SELECT a.id, a.appointment_date, a.patient_name, a.mrn, a.procedure_type,
               COALESCE(r.status, 'no report') AS report_status
        FROM appointment a
        LEFT JOIN {report_table} r ON r.appointment_id = a.id
        WHERE a.procedure_type IN ({placeholders})
        ORDER BY a.appointment_date DESC LIMIT 50
        """.format(
            report_table=card['report_table'] or 'appointment',
            placeholders=','.join('?' * len(card['procedure_keys'])),
        ),
        card['procedure_keys'],
    ).fetchall() if card.get('report_table') and _table_exists(db, card['report_table']) else db.execute(
        f"""
        SELECT id, appointment_date, patient_name, mrn, procedure_type,
               'scheduled' AS report_status
        FROM appointment WHERE procedure_type IN ({','.join('?' * len(card['procedure_keys']))})
        ORDER BY appointment_date DESC LIMIT 50
        """,
        card['procedure_keys'],
    ).fetchall()
    return {'card': card, 'stats': stats, 'recent': [dict(r) for r in recent]}


def diagnosis_hub(db, code: str) -> dict | None:
    group = next((g for g in BUILTIN_DISEASE_GROUPS if g['code'] == code), None)
    if not group:
        for g in _load_template_diagnoses(db) + _load_custom_diagnoses(db):
            if g['code'] == code:
                group = g
                break
    if not group:
        row = None
        if _table_exists(db, 'gi_history_template'):
            row = db.execute(
                'SELECT disease_code AS code, disease_name AS name FROM gi_history_template WHERE disease_code = ?',
                (code,),
            ).fetchone()
        if row:
            group = {'code': row['code'], 'name': row['name'], 'match_terms': [row['name'].lower()], 'subtypes': []}
    if not group:
        return None
    sessions = []
    if _table_exists(db, 'gi_history_session'):
        terms = group.get('match_terms', [group['name'].lower()])
        clauses, params = [], []
        for term in terms:
            like = f'%{term.lower()}%'
            clauses.append(
                "(LOWER(COALESCE(final_diagnosis,'')) LIKE ? OR LOWER(COALESCE(chief_complaint,'')) LIKE ?)"
            )
            params.extend([like, like])
        sessions = db.execute(
            f"""
            SELECT s.id, s.created_at, s.final_diagnosis, s.chief_complaint, s.ward_patient_id,
                   p.patient_name AS patient_name, p.mrn
            FROM gi_history_session s
            LEFT JOIN ward_patient p ON p.id = s.ward_patient_id
            WHERE {' OR '.join(clauses)}
            ORDER BY s.created_at DESC LIMIT 40
            """,
            params,
        ).fetchall()
    return {
        'group': group,
        'stats': _disease_card_stats(db, group),
        'sessions': [dict(s) for s in sessions],
    }


def add_registry_diagnosis(
    db, *, disease_code: str, disease_name: str, match_terms: list[str] | None = None,
    icon: str = '🩺', created_by: int | None = None,
) -> int:
    import json
    cur = db.execute(
        """
        INSERT INTO gi_registry_diagnosis
        (disease_code, disease_name, match_terms_json, icon, created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            disease_code.strip().lower().replace(' ', '_'),
            disease_name.strip(),
            json.dumps(match_terms or [disease_name.strip().lower()]),
            icon,
            created_by,
        ),
    )
    db.commit()
    return cur.lastrowid
