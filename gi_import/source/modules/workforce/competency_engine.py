"""Competency tracking engine — Sprint 7A."""

from __future__ import annotations

from app.extensions import db
from app.modules.workforce.competency_standards_seed import COMPETENCY_STANDARDS_SEED, competency_status
from app.modules.workforce.constants import ACTIVITY_PROCEDURE_SKILL, OFFICIAL_VERIFY_STATUSES
from app.modules.workforce.models import CompetencyStandard, PortfolioEntry


def seed_competency_standards() -> int:
    inserted = 0
    for code, name, specialty, required, sort_order in COMPETENCY_STANDARDS_SEED:
        if CompetencyStandard.query.filter_by(code=code).first():
            continue
        db.session.add(
            CompetencyStandard(
                code=code,
                name=name,
                specialty=specialty,
                required_count=required,
                sort_order=sort_order,
                is_active=True,
                department_id=1,
            )
        )
        inserted += 1
    if inserted:
        db.session.commit()
    return inserted


def _completed_count(user_id: int, skill_code: str, *, official_only: bool = True) -> int:
    query = PortfolioEntry.query.filter_by(
        user_id=user_id,
        activity_type=ACTIVITY_PROCEDURE_SKILL,
        skill_code=skill_code,
        is_archived=False,
    )
    if official_only:
        query = query.filter(PortfolioEntry.verification_status.in_(OFFICIAL_VERIFY_STATUSES))
    return query.count()


def competency_progress_for_user(user_id: int, *, official_only: bool = False) -> list[dict]:
    seed_competency_standards()
    standards = (
        CompetencyStandard.query.filter_by(is_archived=False, is_active=True)
        .order_by(CompetencyStandard.sort_order.asc())
        .all()
    )
    rows: list[dict] = []
    for std in standards:
        completed = _completed_count(user_id, std.code, official_only=official_only)
        required = std.required_count
        remaining = max(required - completed, 0)
        pct = round(min(completed, required) * 100 / required, 1) if required else 100.0
        rows.append(
            {
                "skill_code": std.code,
                "name": std.name,
                "specialty": std.specialty,
                "required_count": required,
                "completed_count": completed,
                "remaining_count": remaining,
                "completion_pct": pct,
                "status": competency_status(completed, required),
            }
        )
    return rows


def competency_summary_by_specialty(user_id: int, *, official_only: bool = False) -> dict[str, dict]:
    progress = competency_progress_for_user(user_id, official_only=official_only)
    summary: dict[str, dict] = {}
    for row in progress:
        bucket = summary.setdefault(
            row["specialty"],
            {"total_skills": 0, "competent_skills": 0, "in_progress_skills": 0, "not_started_skills": 0},
        )
        bucket["total_skills"] += 1
        if row["status"] == "competent":
            bucket["competent_skills"] += 1
        elif row["status"] == "in_progress":
            bucket["in_progress_skills"] += 1
        else:
            bucket["not_started_skills"] += 1
    return summary
