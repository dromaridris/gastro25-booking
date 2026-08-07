"""Clinical History services — Sprint 4C-HIST."""

import json

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.clinical_history.intelligence.question_selector import question_purpose_hint
from app.modules.clinical_history.intelligence.teaching_engine import (
    generate_teaching_explanation,
    persist_teaching_explanation,
)
from app.modules.clinical_history import (
    interview_engine,
    investigation_advisor,
    management_advisor,
    narrative_engine,
    reasoning_engine,
)
from app.modules.clinical_history.catalogue_seed import seed_clinical_history_catalogue_if_empty
from app.modules.clinical_history.models import (
    ALL_NARRATIVE_SECTIONS,
    ChiefComplaintDefinition,
    FollowUpEntry,
    HistoryAnswer,
    HistoryNarrativeSection,
    HistorySession,
    SESSION_KIND_FOLLOW_UP,
    SESSION_KIND_INITIAL,
    SESSION_STATUS_COMPLETED,
    SESSION_STATUS_DRAFT,
    SESSION_STATUS_IN_PROGRESS,
)
from app.modules.encounters.models import ClinicalEncounter


def ensure_catalogue_seeded() -> None:
    seed_clinical_history_catalogue_if_empty()


def _require(acting_user, code: str, target_id=None):
    permission_engine.require(
        acting_user, code, audit_context={"target_type": "HistorySession", "target_id": target_id}
    )


def get_session(acting_user, session_id: int) -> HistorySession:
    _require(acting_user, "history:view", session_id)
    session = HistorySession.query.get(session_id)
    if session is None or session.is_archived:
        raise NotFoundError(f"No history session with id {session_id}")
    return session


def list_sessions_for_encounter(acting_user, encounter_id: int):
    _require(acting_user, "history:view")
    return (
        HistorySession.query.filter_by(encounter_id=encounter_id, is_archived=False)
        .order_by(HistorySession.created_at.desc())
        .all()
    )


def get_or_create_initial_session(acting_user, encounter: ClinicalEncounter) -> HistorySession:
    _require(acting_user, "history:document")
    ensure_catalogue_seeded()

    existing = (
        HistorySession.query.filter_by(
            encounter_id=encounter.id,
            session_kind=SESSION_KIND_INITIAL,
            is_archived=False,
        )
        .order_by(HistorySession.created_at.desc())
        .first()
    )
    if existing and existing.status != SESSION_STATUS_COMPLETED:
        return existing

    session = HistorySession(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        status=SESSION_STATUS_DRAFT,
        session_kind=SESSION_KIND_INITIAL,
        department_id=encounter.department_id,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(session)
    db.session.commit()

    audit_engine.log(
        action="history.session_created",
        user=acting_user,
        target_type="HistorySession",
        target_id=session.id,
        details={"encounter_id": encounter.id},
    )
    return session


def list_complaints(acting_user):
    _require(acting_user, "history:view")
    ensure_catalogue_seeded()
    return (
        ChiefComplaintDefinition.query.filter_by(is_archived=False)
        .order_by(ChiefComplaintDefinition.sort_order, ChiefComplaintDefinition.name)
        .all()
    )


def set_chief_complaint(acting_user, session: HistorySession, complaint_code: str) -> HistorySession:
    _require(acting_user, "history:document", session.id)
    complaint = ChiefComplaintDefinition.query.filter_by(code=complaint_code, is_archived=False).first()
    if complaint is None:
        raise ValidationError("Invalid chief complaint selected.")

    session.chief_complaint_code = complaint.code
    session.status = SESSION_STATUS_IN_PROGRESS
    db.session.commit()

    audit_engine.log(
        action="history.complaint_selected",
        user=acting_user,
        target_type="HistorySession",
        target_id=session.id,
        details={"complaint_code": complaint_code},
    )
    return session


def save_answers(acting_user, session: HistorySession, answers: dict[str, str]) -> HistorySession:
    _require(acting_user, "history:document", session.id)
    if not session.chief_complaint_code:
        raise ValidationError("Select a chief complaint before answering questions.")

    from app.modules.clinical_history.models import HistoryQuestionDefinition
    from app.modules.clinical_history import cds_adapter

    cds_active = cds_adapter.kl_drives_interview(session.chief_complaint_code)

    for qcode, value in answers.items():
        if value is None or str(value).strip() == "":
            continue
        q = HistoryQuestionDefinition.query.filter_by(code=qcode, is_archived=False).first()
        if q is None:
            continue
        val = str(value).strip()
        existing = HistoryAnswer.query.filter_by(session_id=session.id, question_code=qcode).first()
        if existing:
            existing.answer_value = val
            existing.answer_display = val
            existing.answered_at = utcnow()
            existing.answered_by_id = getattr(acting_user, "id", None)
        else:
            db.session.add(HistoryAnswer(
                session_id=session.id,
                question_code=qcode,
                answer_value=val,
                answer_display=val,
                section=q.section,
                answered_by_id=getattr(acting_user, "id", None),
                department_id=session.department_id,
                created_by_id=getattr(acting_user, "id", None),
            ))

    if cds_active:
        session.differential = {
            d["diagnosis_code"]: 0
            for d in cds_adapter.differential_for_display(session)
        }
    else:
        session.differential = reasoning_engine.compute_differential(session.chief_complaint_code, session.id)
    db.session.commit()

    audit_engine.log(
        action="history.answers_saved",
        user=acting_user,
        target_type="HistorySession",
        target_id=session.id,
        details={"question_count": len(answers)},
    )
    return session


def get_interview_batch(acting_user, session: HistorySession, batch_size: int = 1):
    _require(acting_user, "history:view", session.id)
    if not session.chief_complaint_code:
        return [], False, None

    from app.modules.clinical_history import cds_adapter

    if cds_adapter.kl_drives_interview(session.chief_complaint_code):
        batch, complete, meta = cds_adapter.resolve_question_batch(session, batch_size=batch_size)
        return batch, complete, meta

    batch = interview_engine.get_next_question_batch(
        session.chief_complaint_code, session.id, batch_size=batch_size
    )
    complete = interview_engine.interview_complete(session.chief_complaint_code, session.id)
    hint = None
    if batch:
        hint = question_purpose_hint(session.chief_complaint_code, batch[0].code, session.id)
    differential = reasoning_engine.differential_for_display(session.chief_complaint_code, session.id)
    return batch, complete, {"purpose_hint": hint, "differential": differential}


def regenerate_narratives(acting_user, session: HistorySession) -> HistorySession:
    _require(acting_user, "history:document", session.id)
    if not session.chief_complaint_code:
        raise ValidationError("Chief complaint required.")

    complaint = ChiefComplaintDefinition.query.filter_by(code=session.chief_complaint_code).first()
    sections = narrative_engine.generate_all_sections(session.id, complaint.name if complaint else session.chief_complaint_code)

    for key, text in sections.items():
        row = HistoryNarrativeSection.query.filter_by(session_id=session.id, section_key=key).first()
        if row and row.is_manually_edited:
            continue
        if row:
            row.generated_text = text
        else:
            db.session.add(HistoryNarrativeSection(
                session_id=session.id,
                section_key=key,
                generated_text=text,
                department_id=session.department_id,
                created_by_id=getattr(acting_user, "id", None),
            ))

    session.differential = reasoning_engine.compute_differential(session.chief_complaint_code, session.id)
    investigation_advisor.sync_suggestion_records(session)
    db.session.commit()

    audit_engine.log(
        action="history.narrative_generated",
        user=acting_user,
        target_type="HistorySession",
        target_id=session.id,
        details={},
    )
    return session


def update_narrative_section(acting_user, session: HistorySession, section_key: str, text: str) -> HistoryNarrativeSection:
    _require(acting_user, "history:document", session.id)
    if section_key not in ALL_NARRATIVE_SECTIONS:
        raise ValidationError("Invalid narrative section.")

    row = HistoryNarrativeSection.query.filter_by(session_id=session.id, section_key=section_key).first()
    if row is None:
        row = HistoryNarrativeSection(
            session_id=session.id,
            section_key=section_key,
            department_id=session.department_id,
            created_by_id=getattr(acting_user, "id", None),
        )
        db.session.add(row)

    row.edited_text = text.strip()
    row.is_manually_edited = True
    db.session.commit()
    return row


def complete_history(acting_user, session: HistorySession) -> HistorySession:
    _require(acting_user, "history:document", session.id)
    if not interview_engine.interview_complete(session.chief_complaint_code, session.id):
        raise ValidationError("Complete the adaptive interview before finalizing history.")
    regenerate_narratives(acting_user, session)
    session.status = SESSION_STATUS_COMPLETED
    session.completed_at = utcnow()
    db.session.commit()

    audit_engine.log(
        action="history.completed",
        user=acting_user,
        target_type="HistorySession",
        target_id=session.id,
        details={},
    )
    from app.modules.workforce.portfolio_events import on_history_completed

    on_history_completed(session, acting_user)
    return session


def get_differential_display(acting_user, session: HistorySession) -> list[dict]:
    _require(acting_user, "history:view", session.id)
    if not session.chief_complaint_code:
        return []
    from app.modules.clinical_history import cds_adapter

    if cds_adapter.kl_drives_interview(session.chief_complaint_code):
        return cds_adapter.differential_for_display(session)
    return reasoning_engine.differential_for_display(session.chief_complaint_code, session.id)


def confirm_diagnosis(acting_user, session: HistorySession, diagnosis_code: str) -> HistorySession:
    _require(acting_user, "history:confirm_diagnosis", session.id)
    session.confirmed_diagnosis_code = diagnosis_code
    session.diagnosis_confirmed_at = utcnow()
    session.diagnosis_confirmed_by_id = getattr(acting_user, "id", None)
    investigation_advisor.sync_suggestion_records(session)
    persist_teaching_explanation(session)
    db.session.commit()

    audit_engine.log(
        action="history.diagnosis_confirmed",
        user=acting_user,
        target_type="HistorySession",
        target_id=session.id,
        details={"diagnosis_code": diagnosis_code},
    )
    return session


def get_management_for_session(acting_user, session: HistorySession) -> dict | None:
    _require(acting_user, "history:view", session.id)
    if not session.confirmed_diagnosis_code:
        return None
    return management_advisor.get_management_support(session.confirmed_diagnosis_code)


def dismiss_suggestion(acting_user, session: HistorySession, investigation_code: str):
    _require(acting_user, "history:document", session.id)
    from app.modules.clinical_history.models import InvestigationSuggestionRecord

    rec = InvestigationSuggestionRecord.query.filter_by(
        session_id=session.id,
        investigation_code=investigation_code,
        is_archived=False,
    ).first()
    if rec:
        rec.is_dismissed = True
        db.session.commit()


def accept_suggestion(acting_user, session: HistorySession, investigation_code: str):
    _require(acting_user, "history:document", session.id)
    from app.modules.clinical_history.models import InvestigationSuggestionRecord

    rec = InvestigationSuggestionRecord.query.filter_by(
        session_id=session.id,
        investigation_code=investigation_code,
        is_archived=False,
    ).first()
    if rec:
        rec.is_accepted = True
        rec.is_dismissed = False
        db.session.commit()
        order_placed = _place_investigation_order_for_suggestion(
            acting_user, session, investigation_code, rec.reason_text
        )
        if order_placed:
            audit_engine.log(
                action="history.suggestion_order_placed",
                user=acting_user,
                target_type="HistorySession",
                target_id=session.id,
                details={"investigation_code": investigation_code},
            )
        return rec, order_placed
    return rec, False


def _place_investigation_order_for_suggestion(acting_user, session: HistorySession, investigation_code: str, reason: str | None) -> bool:
    """Bridge accepted history suggestions to Sprint 4A-LAB orders when mappable."""
    from app.engines import permission_engine
    from app.modules.encounters.models import ClinicalEncounter
    from app.modules.investigations import services as investigation_services
    from app.modules.investigations.models import InvestigationCatalogueItem, InvestigationOrder, InvestigationPanel

    if not permission_engine.check(acting_user, "investigation:request"):
        return False

    encounter = ClinicalEncounter.query.get(session.encounter_id)
    if encounter is None or encounter.is_archived or not encounter.is_open:
        return False

    panel_codes = {
        "lab.cbc": "panel.cbc",
        "lab.lft": "panel.baseline_lft",
        "lab.crp": None,
    }
    lab_item_codes = {
        "lab.crp": "lab.crp",
        "lab.calprotectin": "lab.calprotectin",
        "lab.amylase": "lab.amylase",
        "lab.urea": "lab.urea",
    }
    imaging_codes = {
        "img.motility": "img.esophageal_manometry",
        "proc.manometry": "img.esophageal_manometry",
    }

    try:
        panel_code = panel_codes.get(investigation_code)
        if panel_code:
            panel = InvestigationPanel.query.filter_by(code=panel_code, is_archived=False).first()
            if panel is None:
                return False
            exists = InvestigationOrder.query.filter_by(
                encounter_id=encounter.id, panel_id=panel.id, is_archived=False
            ).first()
            if exists:
                return False
            investigation_services.create_lab_order(
                acting_user,
                encounter,
                panel_id=panel.id,
                clinical_indication=reason or f"Accepted suggestion: {investigation_code}",
            )
            return True

        item_code = lab_item_codes.get(investigation_code)
        if item_code:
            item = InvestigationCatalogueItem.query.filter_by(code=item_code, is_archived=False).first()
            if item is None:
                return False
            investigation_services.create_lab_order(
                acting_user,
                encounter,
                catalogue_item_ids=[item.id],
                clinical_indication=reason or f"Accepted suggestion: {investigation_code}",
            )
            return True

        img_code = imaging_codes.get(investigation_code)
        if img_code:
            item = InvestigationCatalogueItem.query.filter_by(code=img_code, is_archived=False).first()
            if item is None:
                return False
            investigation_services.create_imaging_order(
                acting_user,
                encounter,
                catalogue_item_id=item.id,
                clinical_indication=reason or f"Accepted suggestion: {investigation_code}",
            )
            return True
    except ValidationError:
        return False
    return False


def create_follow_up(acting_user, patient_id: int, narrative_text: str, encounter_id: int = None, prior_session_id: int = None) -> FollowUpEntry:
    _require(acting_user, "history:follow_up")
    entry = FollowUpEntry(
        patient_id=patient_id,
        encounter_id=encounter_id,
        prior_session_id=prior_session_id,
        narrative_text=narrative_text.strip(),
        documented_by_id=getattr(acting_user, "id", None),
        department_id=1,
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(entry)
    db.session.commit()

    audit_engine.log(
        action="history.follow_up_created",
        user=acting_user,
        target_type="FollowUpEntry",
        target_id=entry.id,
        details={"patient_id": patient_id},
    )
    from app.modules.workforce.portfolio_events import on_follow_up_created

    on_follow_up_created(entry, acting_user)
    return entry


def list_follow_ups_for_patient(acting_user, patient_id: int):
    _require(acting_user, "history:view")
    return (
        FollowUpEntry.query.filter_by(patient_id=patient_id, is_archived=False)
        .order_by(FollowUpEntry.documented_at.desc())
        .all()
    )


def research_filter_answers(acting_user, question_code: str, answer_value: str = None) -> list[dict]:
    """Structured answer query for research — independent of narrative documentation."""
    _require(acting_user, "research:view")
    q = HistoryAnswer.query.filter_by(question_code=question_code, is_archived=False)
    if answer_value is not None:
        q = q.filter_by(answer_value=answer_value)
    rows = q.limit(500).all()
    return [
        {
            "session_id": r.session_id,
            "question_code": r.question_code,
            "answer_value": r.answer_value,
            "section": r.section,
            "answered_at": r.answered_at.isoformat() if r.answered_at else None,
        }
        for r in rows
    ]


def patient_history_timeline(acting_user, patient_id: int) -> list[dict]:
    _require(acting_user, "history:view")
    events = []
    for session in HistorySession.query.filter_by(patient_id=patient_id, is_archived=False).all():
        label = session.chief_complaint_code or "History session"
        events.append({
            "kind": "history_session",
            "timestamp": session.completed_at or session.created_at,
            "label": label.replace("hist.", "").replace("_", " ").title(),
            "status": session.status,
            "id": session.id,
            "url_key": "clinical_history.view_session",
        })
    for fu in FollowUpEntry.query.filter_by(patient_id=patient_id, is_archived=False).all():
        events.append({
            "kind": "follow_up",
            "timestamp": fu.documented_at,
            "label": "Follow-up note",
            "status": "recorded",
            "id": fu.id,
            "url_key": None,
        })
    events.sort(key=lambda e: e["timestamp"] or utcnow(), reverse=True)
    return events


def get_teaching_explanation(acting_user, session: HistorySession) -> dict:
    _require(acting_user, "history:view", session.id)
    if session.teaching_json:
        return session.teaching
    if session.confirmed_diagnosis_code:
        return generate_teaching_explanation(session)
    return {}
