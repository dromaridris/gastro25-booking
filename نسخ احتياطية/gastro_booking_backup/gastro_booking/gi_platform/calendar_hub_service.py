"""Unified calendar hub — appointments, roster duties, education, custom events."""

from __future__ import annotations


def list_events(db, *, from_date: str, to_date: str, user_id: int | None = None) -> list[dict]:
    events: list[dict] = []

    appts = db.execute(
        """
        SELECT id, patient_name, procedure_type, appointment_date AS event_date,
               'appointment' AS source, mrn
        FROM appointment
        WHERE appointment_date >= ? AND appointment_date <= ?
        ORDER BY appointment_date, patient_name
        """,
        (from_date, to_date),
    ).fetchall()
    for a in appts:
        events.append({
            'event_date': a['event_date'],
            'title': f"{a['patient_name']} — {a['procedure_type']}",
            'event_type': 'appointment',
            'source': 'booking',
            'source_id': a['id'],
            'meta': a['mrn'] or '',
        })

    duties = db.execute(
        """
        SELECT s.roster_date AS event_date, s.shift_type, p.title AS period_title,
               p.roster_type, u.full_name
        FROM gi_duty_roster_assignment a
        JOIN gi_duty_roster_shift s ON s.id = a.shift_id
        JOIN gi_duty_roster_period p ON p.id = s.period_id
        JOIN user u ON u.id = a.user_id
        WHERE p.status = 'published'
          AND s.roster_date >= ? AND s.roster_date <= ?
        ORDER BY s.roster_date
        """,
        (from_date, to_date),
    ).fetchall()
    for d in duties:
        events.append({
            'event_date': d['event_date'],
            'title': f"{d['full_name']} — {d['shift_type']}",
            'event_type': 'roster',
            'source': 'roster',
            'source_id': None,
            'meta': d['period_title'] or d['roster_type'],
        })

    edu = db.execute(
        """
        SELECT e.id, e.title, e.activity_date AS event_date, e.activity_type,
               u.full_name
        FROM gi_education_activity e
        JOIN user u ON u.id = e.user_id
        WHERE e.is_archived = 0
          AND e.activity_date >= ? AND e.activity_date <= ?
        ORDER BY e.activity_date
        """,
        (from_date, to_date),
    ).fetchall()
    for e in edu:
        events.append({
            'event_date': e['event_date'],
            'title': e['title'],
            'event_type': 'education',
            'source': 'education',
            'source_id': e['id'],
            'meta': e['full_name'],
        })

    custom = db.execute(
        """
        SELECT * FROM gi_calendar_event
        WHERE event_date >= ? AND event_date <= ?
        ORDER BY event_date
        """,
        (from_date, to_date),
    ).fetchall()
    for c in custom:
        events.append({
            'event_date': c['event_date'],
            'title': c['title'],
            'event_type': c['event_type'],
            'source': 'calendar',
            'source_id': c['id'],
            'meta': c['description'] or '',
            'link_url': c['link_url'],
        })

    if user_id:
        my_duties = [
            e for e in events
            if e['event_type'] != 'roster' or str(user_id) in (e.get('meta') or '')
        ]
        # keep all non-roster; roster already filtered by date only
        events = events

    events.sort(key=lambda e: (e['event_date'], e['title']))
    return events


def create_event(
    db,
    *,
    title: str,
    event_date: str,
    event_type: str = 'general',
    description: str = '',
    link_url: str = '',
    created_by: int | None = None,
) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_calendar_event
        (title, event_date, event_type, description, link_url, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            title.strip(),
            event_date,
            (event_type or 'general').strip(),
            (description or '').strip() or None,
            (link_url or '').strip() or None,
            created_by,
        ),
    )
    db.commit()
    return cur.lastrowid
