"""Consult request workflow — ward patient scoped."""

from __future__ import annotations

from gi_platform import notification_service

STATUS_PENDING = 'pending'
STATUS_ACCEPTED = 'accepted'
STATUS_COMPLETED = 'completed'
STATUS_REJECTED = 'rejected'
STATUS_CANCELLED = 'cancelled'

URGENCY_CHOICES = ('routine', 'urgent', 'emergency')


def list_requests(db, *, status: str | None = None, ward_patient_id: int | None = None) -> list:
    sql = """
        SELECT c.*,
               wp.patient_name, wp.mrn,
               ru.full_name AS requesting_name,
               au.full_name AS assigned_name
        FROM gi_consult_request c
        JOIN ward_patient wp ON wp.id = c.ward_patient_id
        LEFT JOIN user ru ON ru.id = c.requesting_user_id
        LEFT JOIN user au ON au.id = c.assigned_user_id
        WHERE 1=1
    """
    params: list = []
    if status:
        sql += ' AND c.status = ?'
        params.append(status)
    if ward_patient_id:
        sql += ' AND c.ward_patient_id = ?'
        params.append(ward_patient_id)
    sql += ' ORDER BY c.created_at DESC'
    return db.execute(sql, params).fetchall()


def get_request(db, request_id: int):
    return db.execute(
        """
        SELECT c.*, wp.patient_name, wp.mrn,
               ru.full_name AS requesting_name, au.full_name AS assigned_name
        FROM gi_consult_request c
        JOIN ward_patient wp ON wp.id = c.ward_patient_id
        LEFT JOIN user ru ON ru.id = c.requesting_user_id
        LEFT JOIN user au ON au.id = c.assigned_user_id
        WHERE c.id = ?
        """,
        (request_id,),
    ).fetchone()


def create(
    db,
    *,
    ward_patient_id: int,
    specialty: str,
    clinical_question: str,
    urgency: str = 'routine',
    requesting_user_id: int | None = None,
) -> int:
    if not specialty.strip():
        raise ValueError('Specialty is required.')
    if not clinical_question.strip():
        raise ValueError('Clinical question is required.')
    if urgency not in URGENCY_CHOICES:
        urgency = 'routine'
    cur = db.execute(
        """
        INSERT INTO gi_consult_request
        (ward_patient_id, specialty, clinical_question, urgency, requesting_user_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            ward_patient_id,
            specialty.strip(),
            clinical_question.strip(),
            urgency,
            requesting_user_id,
            STATUS_PENDING,
        ),
    )
    db.commit()
    return cur.lastrowid


def accept(db, request_id: int, *, user_id: int) -> None:
    req = get_request(db, request_id)
    if not req or req['status'] != STATUS_PENDING:
        raise ValueError('Only pending requests can be accepted.')
    db.execute(
        """
        UPDATE gi_consult_request
        SET status = ?, assigned_user_id = ?
        WHERE id = ?
        """,
        (STATUS_ACCEPTED, user_id, request_id),
    )
    db.commit()
    if req['requesting_user_id']:
        notification_service.notify_user(
            db,
            user_id=req['requesting_user_id'],
            title=f'Consult accepted: {req["specialty"]}',
            body='Your consult request has been accepted.',
            link_url=f'/consult-requests/{request_id}',
        )


def complete(db, request_id: int, *, user_id: int, response_notes: str) -> None:
    req = get_request(db, request_id)
    if not req or req['status'] not in (STATUS_PENDING, STATUS_ACCEPTED):
        raise ValueError('Request cannot be completed in current status.')
    db.execute(
        """
        UPDATE gi_consult_request
        SET status = ?, response_notes = ?, responded_at = datetime('now'),
            assigned_user_id = COALESCE(assigned_user_id, ?)
        WHERE id = ?
        """,
        (STATUS_COMPLETED, response_notes.strip(), user_id, request_id),
    )
    db.commit()
    if req['requesting_user_id']:
        notification_service.notify_user(
            db,
            user_id=req['requesting_user_id'],
            title=f'Consult completed: {req["specialty"]}',
            body=response_notes[:200],
            link_url=f'/consult-requests/{request_id}',
        )


def reject(db, request_id: int, *, reason: str) -> None:
    req = get_request(db, request_id)
    if not req or req['status'] != STATUS_PENDING:
        raise ValueError('Only pending requests can be rejected.')
    db.execute(
        """
        UPDATE gi_consult_request
        SET status = ?, response_notes = ?, responded_at = datetime('now')
        WHERE id = ?
        """,
        (STATUS_REJECTED, reason.strip(), request_id),
    )
    db.commit()


def cancel(db, request_id: int, *, user_id: int) -> None:
    req = get_request(db, request_id)
    if not req or req['status'] in (STATUS_COMPLETED, STATUS_CANCELLED):
        raise ValueError('Request cannot be cancelled.')
    if req['requesting_user_id'] != user_id:
        raise ValueError('Only the requester can cancel this consult.')
    db.execute(
        'UPDATE gi_consult_request SET status = ? WHERE id = ?',
        (STATUS_CANCELLED, request_id),
    )
    db.commit()
