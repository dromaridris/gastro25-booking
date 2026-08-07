"""Education activity CRUD with portfolio sync hook."""

from datetime import date

from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.education.models import EducationActivity


def _require(user, code: str, target_id=None):
    permission_engine.require(user, code, audit_context={"target_type": "EducationActivity", "target_id": target_id})


def list_activities(acting_user, *, user_id: int | None = None) -> list[EducationActivity]:
    _require(acting_user, "education:view")
    q = EducationActivity.query.filter_by(is_archived=False)
    if user_id:
        q = q.filter_by(user_id=user_id)
    return q.order_by(EducationActivity.activity_date.desc()).all()


def get_activity(acting_user, activity_id: int) -> EducationActivity:
    _require(acting_user, "education:view", activity_id)
    act = EducationActivity.query.get(activity_id)
    if act is None or act.is_archived:
        raise NotFoundError(f"No education activity with id {activity_id}")
    return act


def create(acting_user, *, title: str, activity_type: str, activity_date: date,
           description: str | None = None, duration_minutes: int | None = None,
           location: str | None = None, user_id: int | None = None) -> EducationActivity:
    _require(acting_user, "education:record")
    target_user = user_id or acting_user.id
    act = EducationActivity(
        user_id=target_user,
        title=title.strip(),
        activity_type=activity_type.strip(),
        activity_date=activity_date,
        description=description,
        duration_minutes=duration_minutes,
        location=location,
        created_by_id=acting_user.id,
    )
    db.session.add(act)
    db.session.commit()
    _sync_portfolio(act)
    audit_engine.log("education.create", user=acting_user, target_type="education_activity", target_id=act.id)
    return act


def update(acting_user, activity_id: int, **fields) -> EducationActivity:
    _require(acting_user, "education:manage", activity_id)
    act = get_activity(acting_user, activity_id)
    for key in ("title", "activity_type", "description", "duration_minutes", "location"):
        if key in fields and fields[key] is not None:
            setattr(act, key, fields[key])
    if "activity_date" in fields and fields["activity_date"]:
        act.activity_date = fields["activity_date"]
    db.session.commit()
    _sync_portfolio(act)
    audit_engine.log("education.update", user=acting_user, target_type="education_activity", target_id=act.id)
    return act


def archive_activity(acting_user, activity_id: int) -> None:
    _require(acting_user, "education:manage", activity_id)
    act = get_activity(acting_user, activity_id)
    act.archive(acting_user.id)
    db.session.commit()
    audit_engine.log("education.archive", user=acting_user, target_type="education_activity", target_id=act.id)


def _sync_portfolio(activity: EducationActivity) -> None:
    try:
        from app.modules.workforce.portfolio_engine import sync_portfolio
        sync_portfolio(activity.user_id)
    except Exception:
        pass
