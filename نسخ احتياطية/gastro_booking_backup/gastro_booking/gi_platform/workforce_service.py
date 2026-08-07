"""Ward workforce task queue — PG trainee, house officer, registrar, etc."""

from __future__ import annotations

from gi_platform.constants import can_approve_ward_task

TASK_TYPES = {
    'labs': {'title': 'Enter laboratory results', 'default_role': 'house_officer'},
    'investigations': {'title': 'Review investigations', 'default_role': 'house_officer'},
    'registry': {'title': 'Research registry follow-up', 'default_role': 'registrar'},
    'ward_round': {'title': 'Ward round documentation', 'default_role': 'registrar'},
    'endoscopy_booking': {'title': 'Book major procedure', 'default_role': 'consultant'},
    'consultant_review': {'title': 'Consultant review', 'default_role': 'consultant'},
    'nursing_obs': {'title': 'Nursing observations', 'default_role': 'staff_nurse'},
}


def list_tasks_for_patient(db, ward_patient_id: int) -> list:
    return db.execute(
        """
        SELECT t.*, u.full_name AS assignee_name
        FROM gi_workforce_task t
        LEFT JOIN user u ON u.id = t.assigned_user_id
        WHERE t.ward_patient_id = ?
        ORDER BY
            CASE t.status WHEN 'pending' THEN 0 WHEN 'in_progress' THEN 1 ELSE 2 END,
            t.created_at DESC
        """,
        (ward_patient_id,),
    ).fetchall()


def get_task(db, task_id: int):
    return db.execute('SELECT * FROM gi_workforce_task WHERE id = ?', (task_id,)).fetchone()


def create_task(db, *, ward_patient_id: int, task_type: str, title: str = '',
                assigned_role: str = '', assigned_user_id: int | None = None,
                notes: str = '', created_by: int | None = None) -> int:
    meta = TASK_TYPES.get(task_type, {})
    if not title:
        title = meta.get('title', task_type.replace('_', ' ').title())
    if not assigned_role:
        assigned_role = meta.get('default_role', 'registrar')
    if assigned_user_id is None and created_by is not None:
        assigned_user_id = created_by
    cur = db.execute(
        """
        INSERT INTO gi_workforce_task
        (ward_patient_id, task_type, assigned_role, assigned_user_id, title, notes, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (ward_patient_id, task_type, assigned_role, assigned_user_id, title, notes, created_by),
    )
    task_id = cur.lastrowid
    db.commit()
    combined = ' '.join(p for p in (title, notes) if p)
    if '@' in combined:
        from gi_platform import user_mention_service
        user_mention_service.process_mentions(
            db,
            combined,
            context_title=title,
            link_url=f'/ward/patient/{ward_patient_id}/tasks',
            source_module='ward_task',
            source_id=task_id,
            actor_id=created_by,
        )
    return task_id


def seed_default_tasks(db, ward_patient_id: int, created_by: int | None = None) -> int:
    count = 0
    for task_type in ('history', 'labs', 'investigations', 'registry', 'ward_round', 'nursing_obs'):
        exists = db.execute(
            """
            SELECT 1 FROM gi_workforce_task
            WHERE ward_patient_id = ? AND task_type = ? LIMIT 1
            """,
            (ward_patient_id, task_type),
        ).fetchone()
        if exists:
            continue
        create_task(
            db, ward_patient_id=ward_patient_id, task_type=task_type,
            created_by=created_by, assigned_user_id=created_by,
        )
        count += 1
    return count


def can_complete_task(task, *, user_id: int | None, role: str | None) -> bool:
    if not task:
        return False
    if can_approve_ward_task(role):
        return True
    if user_id and task['assigned_user_id'] == user_id:
        return True
    if user_id and task['created_by'] == user_id:
        return True
    return False


def update_task_status(db, task_id: int, status: str) -> None:
    db.execute(
        """
        UPDATE gi_workforce_task
        SET status = ?, completed_at = CASE WHEN ? = 'done' THEN datetime('now') ELSE completed_at END
        WHERE id = ?
        """,
        (status, status, task_id),
    )
    db.commit()


def delete_task(db, task_id: int) -> bool:
    row = db.execute('SELECT id FROM gi_workforce_task WHERE id = ?', (task_id,)).fetchone()
    if not row:
        return False
    db.execute('DELETE FROM gi_workforce_task WHERE id = ?', (task_id,))
    db.commit()
    return True
