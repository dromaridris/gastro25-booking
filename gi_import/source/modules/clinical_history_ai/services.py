"""Clinical History AI orchestration services."""

from __future__ import annotations

from typing import Any

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine
from app.extensions import db
from app.modules.clinical_history_ai.ai_generator import HistoryAIGenerator
from app.modules.clinical_history_ai.catalogue_seed import seed_guided_history_questions_if_empty
from app.modules.clinical_history_ai.constants import (
    AUDIT_PREFIX,
    DRAFT_STATUS_APPROVED,
    DRAFT_STATUS_DRAFT,
    DRAFT_STATUS_MODIFIED,
    DRAFT_STATUS_REJECTED,
    DRAFT_STATUS_REVIEWED,
    SESSION_STATUS_APPROVED,
    SESSION_STATUS_COMPOSING,
    SESSION_STATUS_DISCARDED,
    SESSION_STATUS_DRAFT_READY,
    SESSION_STATUS_QUESTIONING,
)
from app.modules.clinical_history_ai.history_composer import HistoryComposer
from app.modules.clinical_history_ai.models import (
    GuidedHistoryAnswer,
    GuidedHistoryDraft,
    GuidedHistorySession,
)
from app.modules.clinical_history_ai.permissions import require_history_document, require_history_view
from app.modules.clinical_history_ai.question_engine import HistoryQuestionEngine
from app.modules.clinical_intake.services import get_intake_for_encounter
from app.modules.encounters.models import ClinicalEncounter


def ensure_questions_seeded() -> int:
    return seed_guided_history_questions_if_empty()


def on_complaint_selected(*, intake, acting_user=None, encounter=None, **context) -> dict[str, Any]:
    """Intake hook handler — starts guided history when complaint is selected."""
    _ = context
    if encounter is None:
        encounter = ClinicalEncounter.query.get(intake.encounter_id)
    if encounter is None or acting_user is None:
        return {"started": False, "reason": "missing_context"}
    session = start_guided_session(acting_user, encounter=encounter, intake_record=intake)
    return {"started": True, "guided_session_id": session.id}


def start_guided_session(acting_user, *, encounter: ClinicalEncounter, intake_record) -> GuidedHistorySession:
    require_history_document(acting_user)
    ensure_questions_seeded()

    existing = GuidedHistorySession.query.filter_by(
        encounter_id=encounter.id, is_archived=False
    ).first()
    if existing and existing.status not in (SESSION_STATUS_DISCARDED, SESSION_STATUS_APPROVED):
        return existing

    session = GuidedHistorySession(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        intake_record_id=intake_record.id,
        chief_complaint=intake_record.chief_complaint,
        normalized_complaint=intake_record.normalized_complaint,
        complaint_entry_code=_complaint_code_from_intake(intake_record),
        status=SESSION_STATUS_QUESTIONING,
        department_id=encounter.department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(session)
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.session_started",
        user=acting_user,
        target_type="GuidedHistorySession",
        target_id=session.id,
        details={"encounter_id": encounter.id, "intake_record_id": intake_record.id},
    )
    return session


def _complaint_code_from_intake(intake_record) -> str | None:
    if intake_record.complaint_entry_id:
        from app.modules.clinical_intake.models import ChiefComplaintEntry

        entry = ChiefComplaintEntry.query.get(intake_record.complaint_entry_id)
        if entry:
            return entry.code
    return None


def get_session(acting_user, session_id: int) -> GuidedHistorySession:
    require_history_view(acting_user, session_id=session_id)
    session = GuidedHistorySession.query.get(session_id)
    if session is None or session.is_archived:
        raise NotFoundError(f"No guided history session with id {session_id}")
    return session


def get_session_for_encounter(acting_user, encounter_id: int) -> GuidedHistorySession | None:
    require_history_view(acting_user)
    return GuidedHistorySession.query.filter_by(
        encounter_id=encounter_id, is_archived=False
    ).first()


def get_next_questions(
    acting_user,
    session_id: int,
    *,
    limit: int = 5,
    specialty_code: str | None = None,
) -> list[dict[str, Any]]:
    session = get_session(acting_user, session_id)
    engine = HistoryQuestionEngine()
    questions = engine.next_questions(session, limit=limit, specialty_code=specialty_code)
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.questions_presented",
        user=acting_user,
        target_type="GuidedHistorySession",
        target_id=session.id,
        details={"question_ids": [q["question_id"] for q in questions]},
    )
    return questions


def save_answers(
    acting_user,
    session_id: int,
    answers: dict[str, str],
) -> GuidedHistorySession:
    session = get_session(acting_user, session_id)
    require_history_document(acting_user, session_id=session.id)

    for question_id, response in answers.items():
        if response is None or str(response).strip() == "":
            continue
        existing = GuidedHistoryAnswer.query.filter_by(
            session_id=session.id, question_id=question_id, is_archived=False
        ).first()
        if existing:
            existing.response_value = str(response)
            existing.response_display = str(response)
            existing.version += 1
            existing.answered_at = utcnow()
            existing.answered_by_id = acting_user.id
        else:
            db.session.add(
                GuidedHistoryAnswer(
                    session_id=session.id,
                    encounter_id=session.encounter_id,
                    patient_id=session.patient_id,
                    question_id=question_id,
                    response_value=str(response),
                    response_display=str(response),
                    answered_by_id=acting_user.id,
                    department_id=session.department_id,
                    created_by_id=acting_user.id,
                )
            )

    db.session.commit()
    audit_engine.log(
        action=f"{AUDIT_PREFIX}.questions_answered",
        user=acting_user,
        target_type="GuidedHistorySession",
        target_id=session.id,
        details={"question_ids": list(answers.keys())},
    )
    return session


def generate_history_draft(acting_user, session_id: int) -> GuidedHistoryDraft:
    session = get_session(acting_user, session_id)
    require_history_document(acting_user, session_id=session.id)

    answer_rows = GuidedHistoryAnswer.query.filter_by(
        session_id=session.id, is_archived=False
    ).all()
    if not answer_rows:
        raise ValidationError("At least one answer is required before generating history.")

    composer = HistoryComposer()
    composed = composer.compose(session, answer_rows, chief_complaint=session.chief_complaint)

    generator = HistoryAIGenerator()
    ai_result = generator.generate(
        acting_user,
        encounter_id=session.encounter_id,
        patient_id=session.patient_id,
        composed_payload=composed,
    )
    session.status = SESSION_STATUS_COMPOSING
    session.ai_session_uuid = ai_result["ai_session_uuid"]

    sections = composed["sections"]
    ai_narrative = ai_result["parsed_response"].get("narrative")
    if ai_narrative:
        sections = _merge_ai_narrative(sections, ai_narrative, composed["structured_findings"])

    draft = GuidedHistoryDraft(
        session_id=session.id,
        status=DRAFT_STATUS_DRAFT,
        sections=sections,
        source_answer_ids=composed["source_answer_ids"],
        ai_session_uuid=ai_result["ai_session_uuid"],
        missing_information=composed["missing_information"],
        structured_findings=composed["structured_findings"],
        learning_notes=composed["learning_notes"],
        department_id=session.department_id,
        created_by_id=acting_user.id,
    )
    db.session.add(draft)
    session.status = SESSION_STATUS_DRAFT_READY
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.generation_requested",
        user=acting_user,
        target_type="GuidedHistoryDraft",
        target_id=draft.id,
        details={
            "session_id": session.id,
            "ai_session_uuid": ai_result["ai_session_uuid"],
            "source_answer_ids": composed["source_answer_ids"],
        },
    )
    return draft


def review_draft(acting_user, draft_id: int) -> GuidedHistoryDraft:
    draft = _get_draft(acting_user, draft_id)
    draft.status = DRAFT_STATUS_REVIEWED
    db.session.commit()
    return draft


def edit_draft(acting_user, draft_id: int, *, sections: dict[str, str | None]) -> GuidedHistoryDraft:
    draft = _get_draft(acting_user, draft_id)
    require_history_document(acting_user, session_id=draft.session_id)
    merged = dict(draft.sections)
    merged.update({k: v for k, v in sections.items() if v is not None})
    draft.sections = merged
    draft.physician_edited_text = _sections_to_text(merged)
    draft.status = DRAFT_STATUS_MODIFIED
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.draft_modified",
        user=acting_user,
        target_type="GuidedHistoryDraft",
        target_id=draft.id,
        details={"session_id": draft.session_id},
    )
    return draft


def approve_draft(acting_user, draft_id: int) -> GuidedHistoryDraft:
    draft = _get_draft(acting_user, draft_id)
    require_history_document(acting_user, session_id=draft.session_id)
    draft.status = DRAFT_STATUS_APPROVED
    session = draft.session
    session.status = SESSION_STATUS_APPROVED
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.draft_approved",
        user=acting_user,
        target_type="GuidedHistoryDraft",
        target_id=draft.id,
        details={"session_id": draft.session_id, "ai_session_uuid": draft.ai_session_uuid},
    )
    return draft


def reject_draft(acting_user, draft_id: int, *, reason: str | None = None) -> GuidedHistoryDraft:
    draft = _get_draft(acting_user, draft_id)
    draft.status = DRAFT_STATUS_REJECTED
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.draft_rejected",
        user=acting_user,
        target_type="GuidedHistoryDraft",
        target_id=draft.id,
        details={"session_id": draft.session_id, "reason": reason},
    )
    return draft


def regenerate_draft(acting_user, session_id: int) -> GuidedHistoryDraft:
    session = get_session(acting_user, session_id)
    require_history_document(acting_user, session_id=session.id)
    prior = GuidedHistoryDraft.query.filter_by(session_id=session.id, is_archived=False).all()
    for row in prior:
        row.archive(acting_user.id, reason="regenerated")
    return generate_history_draft(acting_user, session_id)


def discard_session(acting_user, session_id: int) -> GuidedHistorySession:
    session = get_session(acting_user, session_id)
    require_history_document(acting_user, session_id=session.id)
    session.status = SESSION_STATUS_DISCARDED
    db.session.commit()

    audit_engine.log(
        action=f"{AUDIT_PREFIX}.session_discarded",
        user=acting_user,
        target_type="GuidedHistorySession",
        target_id=session.id,
        details={},
    )
    return session


def start_from_encounter(acting_user, encounter_id: int) -> GuidedHistorySession:
    """Start guided history from existing intake on an encounter."""
    require_history_document(acting_user)
    encounter = ClinicalEncounter.query.get(encounter_id)
    if encounter is None or encounter.is_archived:
        raise NotFoundError(f"No encounter with id {encounter_id}")

    intake = get_intake_for_encounter(acting_user, encounter_id)
    if intake is None:
        raise ValidationError("Clinical intake must be completed before guided history.")
    return start_guided_session(acting_user, encounter=encounter, intake_record=intake)


def _get_draft(acting_user, draft_id: int) -> GuidedHistoryDraft:
    require_history_view(acting_user)
    draft = GuidedHistoryDraft.query.get(draft_id)
    if draft is None or draft.is_archived:
        raise NotFoundError(f"No guided history draft with id {draft_id}")
    return draft


def _merge_ai_narrative(
    sections: dict[str, str | None],
    narrative: str,
    structured_findings: list[dict],
) -> dict[str, str | None]:
    """Use AI narrative only to enhance sections that have underlying answers."""
    merged = dict(sections)
    if structured_findings and sections.get("history_of_present_illness"):
        merged["history_of_present_illness"] = narrative
    return merged


def _sections_to_text(sections: dict[str, str | None]) -> str:
    parts = []
    for key, value in sections.items():
        if value:
            parts.append(f"{key.replace('_', ' ').title()}:\n{value}")
    return "\n\n".join(parts)


def session_to_dict(session: GuidedHistorySession) -> dict[str, Any]:
    latest_draft = (
        GuidedHistoryDraft.query.filter_by(session_id=session.id, is_archived=False)
        .order_by(GuidedHistoryDraft.created_at.desc())
        .first()
    )
    return {
        "id": session.id,
        "encounter_id": session.encounter_id,
        "patient_id": session.patient_id,
        "chief_complaint": session.chief_complaint,
        "normalized_complaint": session.normalized_complaint,
        "complaint_entry_code": session.complaint_entry_code,
        "status": session.status,
        "ai_session_uuid": session.ai_session_uuid,
        "latest_draft": draft_to_dict(latest_draft) if latest_draft else None,
    }


def draft_to_dict(draft: GuidedHistoryDraft) -> dict[str, Any]:
    return {
        "id": draft.id,
        "session_id": draft.session_id,
        "status": draft.status,
        "sections": draft.sections,
        "source_answer_ids": draft.source_answer_ids,
        "ai_session_uuid": draft.ai_session_uuid,
        "missing_information": draft.missing_information,
        "structured_findings": draft.structured_findings,
        "learning_notes": draft.learning_notes,
        "physician_edited_text": draft.physician_edited_text,
    }
