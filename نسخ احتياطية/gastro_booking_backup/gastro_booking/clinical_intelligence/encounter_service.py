"""Persistence helpers for Clinical Intelligence encounters."""

from __future__ import annotations

import json
import sqlite3
from typing import Any


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def create_encounter(
    db: sqlite3.Connection,
    *,
    complaint_code: str,
    created_by: int | None,
    patient_label: str | None = None,
    ward_patient_id: int | None = None,
) -> dict:
    cur = db.execute(
        """
        INSERT INTO ci_encounter (complaint_code, patient_label, ward_patient_id, created_by, status, phase)
        VALUES (?, ?, ?, ?, 'draft', 'history')
        """,
        (complaint_code, patient_label, ward_patient_id, created_by),
    )
    db.commit()
    return get_encounter(db, cur.lastrowid)


def list_encounters(db: sqlite3.Connection, *, limit: int = 40) -> list[dict]:
    rows = db.execute(
        """
        SELECT id, complaint_code, patient_label, ward_patient_id, status, phase, urgency_flag, created_at, updated_at
        FROM ci_encounter
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_encounter(db: sqlite3.Connection, encounter_id: int) -> dict | None:
    return _row_to_dict(
        db.execute("SELECT * FROM ci_encounter WHERE id = ?", (encounter_id,)).fetchone()
    )


def touch_encounter(db: sqlite3.Connection, encounter_id: int, **fields: Any) -> None:
    if not fields:
        db.execute(
            "UPDATE ci_encounter SET updated_at = datetime('now') WHERE id = ?",
            (encounter_id,),
        )
        db.commit()
        return
    cols = []
    vals = []
    for k, v in fields.items():
        cols.append(f"{k} = ?")
        vals.append(v)
    cols.append("updated_at = datetime('now')")
    vals.append(encounter_id)
    db.execute(f"UPDATE ci_encounter SET {', '.join(cols)} WHERE id = ?", vals)
    db.commit()


def list_answers(db: sqlite3.Connection, encounter_id: int) -> list[dict]:
    rows = db.execute(
        """
        SELECT * FROM ci_history_answer
        WHERE encounter_id = ?
        ORDER BY id ASC
        """,
        (encounter_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_answer(
    db: sqlite3.Connection,
    encounter_id: int,
    *,
    question_id: str,
    answer_text: str,
    dedupe_key: str | None = None,
    section_key: str | None = None,
) -> None:
    db.execute(
        """
        INSERT INTO ci_history_answer
            (encounter_id, question_id, dedupe_key, answer_text, section_key, skipped, updated_at)
        VALUES (?, ?, ?, ?, ?, 0, datetime('now'))
        ON CONFLICT(encounter_id, question_id) DO UPDATE SET
            answer_text = excluded.answer_text,
            dedupe_key = excluded.dedupe_key,
            section_key = excluded.section_key,
            skipped = 0,
            updated_at = datetime('now')
        """,
        (encounter_id, question_id, dedupe_key, answer_text, section_key),
    )
    touch_encounter(db, encounter_id, phase="history")


def list_findings(db: sqlite3.Connection, encounter_id: int) -> list[dict]:
    rows = db.execute(
        """
        SELECT * FROM ci_exam_finding
        WHERE encounter_id = ?
        ORDER BY id ASC
        """,
        (encounter_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_finding(
    db: sqlite3.Connection,
    encounter_id: int,
    *,
    sign_code: str,
    status: str,
    system_key: str | None = None,
    note: str | None = None,
) -> None:
    if status not in {"present", "absent", "not_examined"}:
        status = "not_examined"
    db.execute(
        """
        INSERT INTO ci_exam_finding
            (encounter_id, system_key, sign_code, status, note, updated_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(encounter_id, sign_code) DO UPDATE SET
            system_key = excluded.system_key,
            status = excluded.status,
            note = excluded.note,
            updated_at = datetime('now')
        """,
        (encounter_id, system_key, sign_code, status, note),
    )
    touch_encounter(db, encounter_id, phase="exam")


def save_summary(db: sqlite3.Connection, encounter_id: int, summary: dict) -> None:
    touch_encounter(
        db,
        encounter_id,
        summary_json=json.dumps(summary, ensure_ascii=False),
        phase="summary",
        status="active",
    )


def save_draft(db: sqlite3.Connection, encounter_id: int, draft: dict) -> None:
    db.execute(
        """
        INSERT INTO ci_encounter_draft (encounter_id, draft_json, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(encounter_id) DO UPDATE SET
            draft_json = excluded.draft_json,
            updated_at = datetime('now')
        """,
        (encounter_id, json.dumps(draft, ensure_ascii=False)),
    )
    db.commit()


def list_ix_results(db: sqlite3.Connection, encounter_id: int) -> list[dict]:
    rows = db.execute(
        """
        SELECT * FROM ci_ix_result
        WHERE encounter_id = ?
        ORDER BY id ASC
        """,
        (encounter_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def save_ix_result(
    db: sqlite3.Connection,
    encounter_id: int,
    *,
    investigation_code: str,
    result_label: str,
    note: str | None = None,
) -> None:
    db.execute(
        """
        INSERT INTO ci_ix_result
            (encounter_id, investigation_code, result_label, note, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(encounter_id, investigation_code) DO UPDATE SET
            result_label = excluded.result_label,
            note = excluded.note,
            updated_at = datetime('now')
        """,
        (encounter_id, investigation_code, result_label, note),
    )
    touch_encounter(db, encounter_id, phase="investigations")
