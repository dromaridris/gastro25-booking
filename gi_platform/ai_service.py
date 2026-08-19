"""Clinical AI session service — delegates to gi_platform.clinical_ai stack."""

from __future__ import annotations

from gi_platform.clinical_ai.constants import PROMPT_CLINICAL_REASONING
from gi_platform.clinical_ai.service import ClinicalAIService
from gi_platform.clinical_ai.session_manager import AISessionManager

_session_mgr = AISessionManager()


def create_session(db, *, ward_patient_id: int | None = None,
                   session_type: str = 'clinical_ai', created_by: int | None = None) -> int:
    session = _session_mgr.create_open_session(
        db, ward_patient_id=ward_patient_id, created_by=created_by, session_type=session_type,
    )
    return session.id


def get_session(db, session_id: int):
    return db.execute(
        "SELECT * FROM gi_ai_session WHERE id = ?", (session_id,),
    ).fetchone()


def list_sessions(db, ward_patient_id: int | None = None) -> list:
    if ward_patient_id:
        return db.execute(
            "SELECT * FROM gi_ai_session WHERE ward_patient_id = ? ORDER BY created_at DESC",
            (ward_patient_id,),
        ).fetchall()
    return db.execute(
        "SELECT * FROM gi_ai_session ORDER BY created_at DESC LIMIT 50"
    ).fetchall()


def ask(db, session_id: int, prompt: str, *, role: str | None = None,
        user_id: int | None = None, prompt_type: str = PROMPT_CLINICAL_REASONING) -> str:
    svc = ClinicalAIService(db)
    result = svc.ask_session(
        role=role, user_id=user_id, session_id=session_id,
        prompt=prompt, prompt_type=prompt_type,
    )
    parsed = result.get('parsed_response') or {}
    return parsed.get('narrative') or parsed.get('raw_text') or ''


def list_logs(db, session_id: int) -> list:
    return _session_mgr.list_logs(db, session_id)


def get_clinical_ai_service(db, app_config: dict | None = None) -> ClinicalAIService:
    return ClinicalAIService(db, app_config=app_config or {})
