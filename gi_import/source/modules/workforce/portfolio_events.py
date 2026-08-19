"""Event-driven portfolio synchronisation — Sprint 7A integration hooks."""

from __future__ import annotations

from app.extensions import db
from app.modules.workforce.competency_engine import competency_progress_for_user


def _user_ids(*ids) -> list[int]:
    return [uid for uid in ids if uid is not None]


def _refresh_users(user_ids: list[int]) -> None:
    for uid in set(user_ids):
        competency_progress_for_user(uid, official_only=False)


def on_encounter_closed(encounter, acting_user) -> None:
    from app.modules.workforce.portfolio_engine import sync_encounter_by_id

    sync_encounter_by_id(encounter.id)
    _refresh_users(_user_ids(encounter.created_by_id, getattr(acting_user, "id", None)))
    db.session.commit()


def on_history_completed(session, acting_user) -> None:
    from app.modules.workforce.portfolio_engine import sync_history_session_by_id

    sync_history_session_by_id(session.id)
    _refresh_users(_user_ids(session.created_by_id, getattr(acting_user, "id", None)))
    db.session.commit()


def on_follow_up_created(entry, acting_user) -> None:
    from app.modules.workforce.portfolio_engine import sync_follow_up_by_id

    sync_follow_up_by_id(entry.id)
    _refresh_users(_user_ids(entry.documented_by_id, getattr(acting_user, "id", None)))
    db.session.commit()


def on_procedure_completed(session, acting_user) -> None:
    from app.modules.workforce.portfolio_engine import sync_procedure_session_by_id

    sync_procedure_session_by_id(session.id)
    team = [
        session.endoscopist_id,
        session.assistant_id,
        session.nurse_id,
        session.technician_id,
        session.anaesthetist_id,
        getattr(acting_user, "id", None),
    ]
    _refresh_users(_user_ids(*team))
    db.session.commit()


def on_report_finalized(report, acting_user) -> None:
    from app.modules.workforce.portfolio_engine import sync_report_by_id

    sync_report_by_id(report.id)
    user_ids = _user_ids(report.author_id, report.supervising_consultant_id, getattr(acting_user, "id", None))
    if report.procedure_session:
        ps = report.procedure_session
        user_ids.extend(_user_ids(ps.endoscopist_id, ps.assistant_id))
    _refresh_users(user_ids)
    db.session.commit()


def on_lab_reviewed(result_set, acting_user) -> None:
    from app.modules.workforce.portfolio_engine import sync_lab_result_set_by_id

    sync_lab_result_set_by_id(result_set.id)
    _refresh_users(_user_ids(result_set.reviewed_by_id, getattr(acting_user, "id", None)))
    db.session.commit()


def on_imaging_reviewed(study, acting_user) -> None:
    from app.modules.workforce.portfolio_engine import sync_imaging_study_by_id

    sync_imaging_study_by_id(study.id)
    _refresh_users(_user_ids(study.reviewed_by_id, getattr(acting_user, "id", None)))
    db.session.commit()


def on_research_enrolled(case, acting_user) -> None:
    from app.modules.workforce.portfolio_engine import sync_research_case_by_id

    sync_research_case_by_id(case.id)
    _refresh_users(_user_ids(case.enrolled_by_id, case.reviewer_id, getattr(acting_user, "id", None)))
    db.session.commit()
