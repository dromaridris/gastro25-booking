"""Full clinical governance — incidents, M&M, audits, documents, checklists."""

from __future__ import annotations

import json

from gi_platform import notification_service, user_mention_service


def _link_for_source(source_module: str) -> str:
    if source_module == 'mm':
        return '/governance/mm'
    if source_module == 'journal_club':
        return '/governance/journal-club'
    return '/ward/tasks'


def _create_training_assignments(
    db, *, source_module: str, source_id: int, title: str, details: str = '',
    session_date: str = '', training_route: str = '', assigned_by_id: int | None,
    presenter_usernames: str = '', attendee_usernames: str = '',
) -> int:
    """Resolve @usernames and create per-user training tasks + notifications."""
    presenter_ids = user_mention_service.resolve_mention_usernames(db, presenter_usernames)
    link = _link_for_source(source_module)
    created = 0

    def _insert(user_id: int, assignment_type: str, role_label: str) -> None:
        nonlocal created
        body_parts = [role_label, title]
        if session_date:
            body_parts.append(f'Date: {session_date}')
        if training_route:
            body_parts.append(f'Route: {training_route}')
        if details:
            body_parts.append(details)
        body = ' · '.join(body_parts)
        db.execute(
            """
            INSERT INTO gi_training_assignment
            (user_id, assignment_type, source_module, source_id, title, details,
             session_date, training_route, assigned_by_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, assignment_type, source_module, source_id, title, details or None,
                session_date or None, training_route or None, assigned_by_id,
            ),
        )
        notification_service.notify_user(
            db, user_id=user_id, title=f'{role_label}: {title}', body=body, link_url=link,
        )
        created += 1

    seen: set[int] = set()
    for uid in presenter_ids:
        if uid in seen:
            continue
        seen.add(uid)
        _insert(uid, f'{source_module}_presenter', 'Presenter')
    if created:
        db.commit()
    return created


def _notify_attendee_mentions(
    db, *, source_module: str, source_id: int, title: str, attendee_usernames: str,
    session_date: str = '', training_route: str = '', assigned_by_id: int | None = None,
) -> None:
    """@mentions in assigned/attendee fields (presenters handled separately)."""
    if not attendee_usernames or '@' not in attendee_usernames:
        return
    link = _link_for_source(source_module)
    user_mention_service.process_mentions(
        db,
        attendee_usernames,
        context_title=title,
        link_url=link,
        source_module=source_module,
        source_id=source_id,
        actor_id=assigned_by_id,
    )


def list_upcoming_presentations(db, *, days_ahead: int = 7) -> list:
    """Read-only M&M / journal club schedule — who presents today and this week."""
    from datetime import date, timedelta

    today = date.today().isoformat()
    end = (date.today() + timedelta(days=days_ahead)).isoformat()
    mm_rows = db.execute(
        """
        SELECT 'mm' AS source_module, m.id AS source_id, m.case_summary AS title,
               m.presentation_date AS session_date, m.presenter_usernames,
               m.training_route, m.assigned_usernames
        FROM gi_gov_mm_case m
        WHERE m.presentation_date IS NOT NULL
          AND m.presentation_date >= ? AND m.presentation_date <= ?
        ORDER BY m.presentation_date, m.id
        """,
        (today, end),
    ).fetchall()
    jc_rows = db.execute(
        """
        SELECT 'journal_club' AS source_module, j.id AS source_id, j.title,
               j.session_date AS session_date, j.presenter_usernames,
               j.training_route, j.assigned_usernames
        FROM gi_gov_journal_club j
        WHERE j.session_date IS NOT NULL
          AND j.session_date >= ? AND j.session_date <= ?
        ORDER BY j.session_date, j.id
        """,
        (today, end),
    ).fetchall()
    return list(mm_rows) + list(jc_rows)


def list_training_assignments_for_user(db, user_id: int, *, status: str = 'pending', limit: int = 50) -> list:
    """Personal @mention tasks — presenters only (not attendees)."""
    return db.execute(
        """
        SELECT a.*, u.full_name AS assigned_by_name
        FROM gi_training_assignment a
        LEFT JOIN user u ON u.id = a.assigned_by_id
        WHERE a.user_id = ? AND a.status = ?
          AND a.assignment_type LIKE '%_presenter'
        ORDER BY a.session_date IS NULL, a.session_date, a.created_at DESC
        LIMIT ?
        """,
        (user_id, status, limit),
    ).fetchall()


def training_assignment_count(db, source_module: str, source_id: int) -> int:
    row = db.execute(
        """
        SELECT COUNT(*) AS c FROM gi_training_assignment
        WHERE source_module = ? AND source_id = ?
        """,
        (source_module, source_id),
    ).fetchone()
    return row['c'] if row else 0


def complete_training_assignment(db, assignment_id: int, user_id: int) -> bool:
    row = db.execute(
        """
        SELECT id FROM gi_training_assignment
        WHERE id = ? AND user_id = ?
          AND (assignment_type LIKE '%_presenter' OR assignment_type = 'mention')
        """,
        (assignment_id, user_id),
    ).fetchone()
    if not row:
        return False
    db.execute(
        """
        UPDATE gi_training_assignment
        SET status = 'done', completed_at = datetime('now')
        WHERE id = ? AND user_id = ?
        """,
        (assignment_id, user_id),
    )
    db.commit()
    return True


def delete_training_assignment(db, assignment_id: int) -> bool:
    row = db.execute('SELECT id FROM gi_training_assignment WHERE id = ?', (assignment_id,)).fetchone()
    if not row:
        return False
    db.execute('DELETE FROM gi_training_assignment WHERE id = ?', (assignment_id,))
    db.commit()
    return True


# --- Incidents ---

def list_incidents(db, *, status: str | None = None, limit: int = 100) -> list:
    sql = """
        SELECT i.*, r.full_name AS reporter_name, v.full_name AS reviewer_name
        FROM gi_gov_incident i
        LEFT JOIN user r ON r.id = i.reported_by_id
        LEFT JOIN user v ON v.id = i.reviewer_id
        WHERE 1=1
    """
    params: list = []
    if status:
        sql += ' AND i.status = ?'
        params.append(status)
    sql += ' ORDER BY i.incident_date DESC LIMIT ?'
    params.append(limit)
    return db.execute(sql, params).fetchall()


def create_incident(db, *, incident_date: str, category: str, severity: str,
                    description: str, reported_by_id: int | None,
                    mrn: str = '', patient_name: str = '') -> int:
    cur = db.execute(
        """
        INSERT INTO gi_gov_incident
        (incident_date, category, severity, description, reported_by_id, mrn, patient_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (incident_date, category, severity, description, reported_by_id, mrn or None, patient_name or None),
    )
    db.commit()
    return cur.lastrowid


def review_incident(db, incident_id: int, *, reviewer_id: int, root_cause: str = '',
                    corrective_action: str = '', preventive_action: str = '',
                    status: str = 'closed') -> None:
    db.execute(
        """
        UPDATE gi_gov_incident
        SET reviewer_id = ?, root_cause = ?, corrective_action = ?,
            preventive_action = ?, status = ?
        WHERE id = ?
        """,
        (reviewer_id, root_cause, corrective_action, preventive_action, status, incident_id),
    )
    db.commit()


# --- M&M ---

def list_mm_cases(db, limit: int = 100) -> list:
    return db.execute(
        """
        SELECT m.*, p.full_name AS presenter_name, c.full_name AS chair_name
        FROM gi_gov_mm_case m
        LEFT JOIN user p ON p.id = m.presenter_id
        LEFT JOIN user c ON c.id = m.chair_id
        ORDER BY m.presentation_date DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()


def create_mm_case(db, *, case_summary: str, presentation_date: str = '',
                   mrn: str = '', patient_name: str = '', presenter_id: int | None = None,
                   is_important: bool = False, training_route: str = '',
                   assigned_usernames: str = '', presenter_usernames: str = '',
                   assigned_by_id: int | None = None) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_gov_mm_case
        (case_summary, presentation_date, mrn, patient_name, presenter_id,
         is_important, training_route, assigned_usernames, presenter_usernames)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (case_summary, presentation_date or None, mrn or None, patient_name or None, presenter_id,
         1 if is_important else 0, training_route or None, assigned_usernames or None,
         presenter_usernames or None),
    )
    case_id = cur.lastrowid
    db.commit()
    summary_preview = case_summary[:120] + ('…' if len(case_summary) > 120 else '')
    _create_training_assignments(
        db,
        source_module='mm',
        source_id=case_id,
        title=f'M&M: {summary_preview}',
        details=case_summary,
        session_date=presentation_date,
        training_route=training_route,
        assigned_by_id=assigned_by_id,
        presenter_usernames=presenter_usernames,
        attendee_usernames=assigned_usernames,
    )
    _notify_attendee_mentions(
        db, source_module='mm', source_id=case_id,
        title=f'M&M: {summary_preview}',
        attendee_usernames=assigned_usernames,
        session_date=presentation_date, training_route=training_route,
        assigned_by_id=assigned_by_id,
    )
    return case_id


def update_mm_case(db, case_id: int, **fields) -> None:
    allowed = ('discussion_notes', 'lessons_learned', 'recommendations',
               'follow_up_actions', 'status', 'chair_id', 'is_important',
               'training_route', 'assigned_usernames', 'presenter_usernames')
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f'{k} = ?')
            vals.append(v)
    if sets:
        vals.append(case_id)
        db.execute(f"UPDATE gi_gov_mm_case SET {', '.join(sets)} WHERE id = ?", vals)
        db.commit()


# --- Journal club ---

def list_journal_clubs(db, limit: int = 100) -> list:
    return db.execute(
        """
        SELECT j.*, u.full_name AS created_by_name
        FROM gi_gov_journal_club j
        LEFT JOIN user u ON u.id = j.created_by_id
        ORDER BY j.session_date DESC, j.created_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()


def create_journal_club(db, *, title: str, session_date: str = '', article_reference: str = '',
                        assigned_usernames: str = '', presenter_usernames: str = '',
                        training_route: str = '', is_important: bool = False,
                        notes: str = '', created_by_id: int | None = None) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_gov_journal_club
        (title, session_date, article_reference, assigned_usernames, presenter_usernames,
         training_route, is_important, notes, created_by_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (title, session_date or None, article_reference or None, assigned_usernames or None,
         presenter_usernames or None, training_route or None, 1 if is_important else 0,
         notes or None, created_by_id),
    )
    session_id = cur.lastrowid
    db.commit()
    details = article_reference or notes or ''
    _create_training_assignments(
        db,
        source_module='journal_club',
        source_id=session_id,
        title=f'Journal club: {title}',
        details=details,
        session_date=session_date,
        training_route=training_route,
        assigned_by_id=created_by_id,
        presenter_usernames=presenter_usernames,
        attendee_usernames=assigned_usernames,
    )
    _notify_attendee_mentions(
        db, source_module='journal_club', source_id=session_id,
        title=f'Journal club: {title}',
        attendee_usernames=assigned_usernames,
        session_date=session_date, training_route=training_route,
        assigned_by_id=created_by_id,
    )
    return session_id


# --- Audits ---

def list_audits(db, limit: int = 100) -> list:
    return db.execute(
        """
        SELECT a.*, u.full_name AS investigator_name
        FROM gi_gov_audit a
        LEFT JOIN user u ON u.id = a.investigator_id
        ORDER BY a.created_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()


def create_audit(db, *, title: str, objective: str, investigator_id: int | None = None,
                 methodology: str = '', status: str = 'planned') -> int:
    cur = db.execute(
        """
        INSERT INTO gi_gov_audit (title, objective, methodology, investigator_id, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title, objective, methodology, investigator_id, status),
    )
    db.commit()
    return cur.lastrowid


def update_audit(db, audit_id: int, **fields) -> None:
    allowed = ('status', 'findings_summary', 'timeline_start', 'timeline_end', 'methodology')
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f'{k} = ?')
            vals.append(v)
    if sets:
        vals.append(audit_id)
        db.execute(f"UPDATE gi_gov_audit SET {', '.join(sets)} WHERE id = ?", vals)
        db.commit()


# --- Documents ---

def list_documents(db, limit: int = 100) -> list:
    return db.execute(
        """
        SELECT d.*, u.full_name AS approved_by_name
        FROM gi_gov_document d
        LEFT JOIN user u ON u.id = d.approved_by_id
        ORDER BY d.title LIMIT ?
        """,
        (limit,),
    ).fetchall()


def create_document(db, *, title: str, document_type: str, content_summary: str = '',
                    version: str = '1.0') -> int:
    cur = db.execute(
        """
        INSERT INTO gi_gov_document (title, document_type, content_summary, version)
        VALUES (?, ?, ?, ?)
        """,
        (title, document_type, content_summary, version),
    )
    db.commit()
    return cur.lastrowid


def acknowledge_document(db, document_id: int, user_id: int) -> None:
    db.execute(
        """
        INSERT OR IGNORE INTO gi_gov_document_ack (document_id, user_id)
        VALUES (?, ?)
        """,
        (document_id, user_id),
    )
    db.commit()


# --- Checklists ---

def list_checklists(db, limit: int = 100) -> list:
    return db.execute(
        """
        SELECT c.*, u.full_name AS completed_by_name
        FROM gi_gov_checklist c
        LEFT JOIN user u ON u.id = c.completed_by_id
        ORDER BY c.created_at DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()


def create_checklist(db, *, checklist_type: str, items: list, completed_by_id: int | None) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_gov_checklist
        (checklist_type, items_json, is_complete, completed_by_id, completed_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        (checklist_type, json.dumps(items), 1, completed_by_id),
    )
    db.commit()
    return cur.lastrowid


# --- KPI summary ---

def quality_kpis(db) -> dict:
    open_incidents = db.execute(
        "SELECT COUNT(*) AS c FROM gi_gov_incident WHERE status IN ('open','under_review')"
    ).fetchone()['c']
    pending_audits = db.execute(
        "SELECT COUNT(*) AS c FROM gi_gov_audit WHERE status IN ('planned','in_progress')"
    ).fetchone()['c']
    pending_orders = db.execute(
        "SELECT COUNT(*) AS c FROM gi_investigation_order WHERE approval_status = 'pending_registrar'"
    ).fetchone()['c']
    active_docs = db.execute(
        "SELECT COUNT(*) AS c FROM gi_gov_document WHERE status = 'active'"
    ).fetchone()['c']
    return {
        'open_incidents': open_incidents,
        'pending_audits': pending_audits,
        'pending_registrar_orders': pending_orders,
        'active_documents': active_docs,
    }
