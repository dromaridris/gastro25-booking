"""Clinical history / encounter SQLite service."""

from __future__ import annotations

import json


def create_session(db, *, ward_patient_id: int | None = None,
                   appointment_id: int | None = None, mrn: str = '',
                   chief_complaint: str = '', complaint_code: str = '',
                   created_by: int | None = None) -> int:
    cur = db.execute(
        """
        INSERT INTO gi_history_session
        (ward_patient_id, appointment_id, mrn, chief_complaint, complaint_code, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (ward_patient_id, appointment_id, mrn, chief_complaint, complaint_code, created_by),
    )
    db.commit()
    return cur.lastrowid


def get_session(db, session_id: int):
    return db.execute(
        "SELECT * FROM gi_history_session WHERE id = ?", (session_id,)
    ).fetchone()


def list_sessions_for_patient(db, ward_patient_id: int) -> list[dict]:
    return db.execute(
        """
        SELECT * FROM gi_history_session
        WHERE ward_patient_id = ?
        ORDER BY created_at DESC
        """,
        (ward_patient_id,),
    ).fetchall()


def set_complaint(db, session_id: int, complaint_code: str, chief_complaint: str = '') -> None:
    db.execute(
        """
        UPDATE gi_history_session
        SET complaint_code = ?, chief_complaint = COALESCE(NULLIF(?, ''), chief_complaint),
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (complaint_code, chief_complaint, session_id),
    )
    db.commit()


def save_answer(db, session_id: int, question_key: str,
                answer_text: str = '', answer_json: dict | None = None,
                symptom_id: int | None = None) -> None:
    sid = symptom_id
    existing = db.execute(
        """
        SELECT id FROM gi_history_answer
        WHERE session_id = ? AND question_key = ?
          AND COALESCE(symptom_id, 0) = COALESCE(?, 0)
        """,
        (session_id, question_key, sid),
    ).fetchone()
    if existing:
        db.execute(
            """
            UPDATE gi_history_answer
            SET answer_text = ?, answer_json = ?
            WHERE id = ?
            """,
            (answer_text, json.dumps(answer_json or {}), existing['id']),
        )
    else:
        db.execute(
            """
            INSERT INTO gi_history_answer (session_id, symptom_id, question_key, answer_text, answer_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, sid, question_key, answer_text, json.dumps(answer_json or {})),
        )
    db.execute(
        "UPDATE gi_history_session SET updated_at = datetime('now') WHERE id = ?",
        (session_id,),
    )
    db.commit()


def list_answers(db, session_id: int, *, symptom_id: int | None = None) -> list[dict]:
    if symptom_id is not None:
        return db.execute(
            """
            SELECT * FROM gi_history_answer
            WHERE session_id = ? AND (symptom_id = ? OR symptom_id IS NULL)
            ORDER BY id
            """,
            (session_id, symptom_id),
        ).fetchall()
    return db.execute(
        "SELECT * FROM gi_history_answer WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()


def get_answers_map(db, session_id: int, *, symptom_id: int | None = None) -> dict[str, str]:
    rows = list_answers(db, session_id, symptom_id=symptom_id)
    return {r['question_key']: r['answer_text'] or '' for r in rows}


def save_narrative(db, session_id: int, narrative_text: str, sections: dict | None = None) -> None:
    db.execute(
        """
        INSERT INTO gi_history_narrative (session_id, narrative_text, sections_json)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            narrative_text = excluded.narrative_text,
            sections_json = excluded.sections_json,
            generated_at = datetime('now')
        """,
        (session_id, narrative_text, json.dumps(sections or {})),
    )
    db.commit()


def save_examination(db, session_id: int, examination_text: str) -> None:
    db.execute(
        "UPDATE gi_history_session SET examination_text = ?, updated_at = datetime('now') WHERE id = ?",
        (examination_text, session_id),
    )
    db.commit()


def get_narrative(db, session_id: int):
    return db.execute(
        "SELECT * FROM gi_history_narrative WHERE session_id = ?", (session_id,)
    ).fetchone()


def get_latest_narrative_for_patient(db, ward_patient_id: int):
    """Most recently generated history narrative linked to this ward patient."""
    return db.execute(
        """
        SELECT n.*, s.id AS session_id, s.chief_complaint, s.complaint_code
        FROM gi_history_narrative n
        JOIN gi_history_session s ON s.id = n.session_id
        WHERE s.ward_patient_id = ?
        ORDER BY n.generated_at DESC, n.id DESC
        LIMIT 1
        """,
        (ward_patient_id,),
    ).fetchone()


def add_medication(db, *, drug_name: str, session_id: int | None = None,
                   ward_patient_id: int | None = None, dose: str = '',
                   frequency: str = '', route: str = '', notes: str = '') -> int:
    cur = db.execute(
        """
        INSERT INTO gi_medication_entry
        (session_id, ward_patient_id, drug_name, dose, frequency, route, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, ward_patient_id, drug_name, dose, frequency, route, notes),
    )
    db.commit()
    return cur.lastrowid


def list_medications(db, *, session_id: int | None = None,
                     ward_patient_id: int | None = None) -> list[dict]:
    if session_id:
        return db.execute(
            "SELECT * FROM gi_medication_entry WHERE session_id = ? ORDER BY id DESC",
            (session_id,),
        ).fetchall()
    if ward_patient_id:
        return db.execute(
            "SELECT * FROM gi_medication_entry WHERE ward_patient_id = ? ORDER BY id DESC",
            (ward_patient_id,),
        ).fetchall()
    return []
