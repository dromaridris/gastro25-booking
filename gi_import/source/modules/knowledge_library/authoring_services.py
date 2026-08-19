"""Knowledge Library authoring — write operations (Sprint 5C)."""

from __future__ import annotations

import json
import re

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError, ValidationError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.knowledge_library.constants import (
    ALL_OBJECT_TYPES,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    STATUS_SUPERSEDED,
)
from app.modules.knowledge_library.models import KnowledgeObjectLinkRecord, KnowledgeObjectRecord

_STABLE_ID_RE = re.compile(r"^kl\.[a-z0-9_.]+$")


def _department_id_for(acting_user, department_id: int | None = None) -> int:
    return department_id or getattr(acting_user, "department_id", None) or 1


def _require_view(acting_user) -> None:
    permission_engine.require(acting_user, "knowledge_library:view")


def _require_edit(acting_user, *, audit_context: dict | None = None) -> None:
    permission_engine.require(
        acting_user,
        "knowledge_library:edit",
        audit_context=audit_context or {"target_type": "KnowledgeObjectRecord"},
    )


def _require_suggest(acting_user) -> None:
    permission_engine.require(acting_user, "knowledge_library:suggest")


def _can_edit_record(acting_user, record: KnowledgeObjectRecord) -> bool:
    if permission_engine.check(acting_user, "knowledge_library:edit"):
        return True
    if not permission_engine.check(acting_user, "knowledge_library:suggest"):
        return False
    return record.status == STATUS_DRAFT and record.created_by_id == getattr(acting_user, "id", None)


def _validate_object_type(object_type: str) -> None:
    if object_type not in ALL_OBJECT_TYPES:
        raise ValidationError(f"Invalid object type: {object_type}")


def _validate_stable_id(stable_id: str) -> str:
    sid = (stable_id or "").strip().lower()
    if not sid:
        raise ValidationError("Stable ID is required (e.g. kl.disease.celiac).")
    if not _STABLE_ID_RE.match(sid):
        raise ValidationError("Stable ID must match pattern kl.{type}.{slug} (lowercase, dots, underscores).")
    return sid


def _parse_attributes(raw: str | dict | None) -> dict:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Attributes must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValidationError("Attributes JSON must be an object.")
    return parsed


def _latest_versions_query(include_archived: bool = False):
    """Return subquery of max version_sequence per stable_id."""
    q = db.session.query(
        KnowledgeObjectRecord.stable_id,
        db.func.max(KnowledgeObjectRecord.version_sequence).label("max_seq"),
    )
    if not include_archived:
        q = q.filter(KnowledgeObjectRecord.is_archived.is_(False))
    return q.group_by(KnowledgeObjectRecord.stable_id).subquery()


def list_knowledge_objects(
    acting_user,
    *,
    object_type: str | None = None,
    include_archived: bool = False,
    status: str | None = None,
    topic_key: str | None = None,
):
    _require_view(acting_user)
    latest = _latest_versions_query(include_archived=include_archived)
    query = (
        KnowledgeObjectRecord.query.join(
            latest,
            db.and_(
                KnowledgeObjectRecord.stable_id == latest.c.stable_id,
                KnowledgeObjectRecord.version_sequence == latest.c.max_seq,
            ),
        )
    )
    if not include_archived:
        query = query.filter(KnowledgeObjectRecord.is_archived.is_(False))
    if object_type:
        query = query.filter(KnowledgeObjectRecord.object_type == object_type)
    if status:
        query = query.filter(KnowledgeObjectRecord.status == status)
    if topic_key:
        query = query.filter(KnowledgeObjectRecord.topic_key == topic_key)
    return query.order_by(
        KnowledgeObjectRecord.object_type.asc(),
        KnowledgeObjectRecord.title.asc(),
    ).all()


def get_knowledge_record(acting_user, record_id: int) -> KnowledgeObjectRecord:
    _require_view(acting_user)
    record = KnowledgeObjectRecord.query.get(record_id)
    if record is None:
        raise NotFoundError(f"No knowledge object with id {record_id}")
    return record


def get_latest_by_stable_id(acting_user, stable_id: str) -> KnowledgeObjectRecord | None:
    _require_view(acting_user)
    return (
        KnowledgeObjectRecord.query.filter_by(stable_id=stable_id, is_archived=False)
        .order_by(KnowledgeObjectRecord.version_sequence.desc())
        .first()
    )


def list_versions(acting_user, stable_id: str) -> list[KnowledgeObjectRecord]:
    _require_view(acting_user)
    return (
        KnowledgeObjectRecord.query.filter_by(stable_id=stable_id)
        .order_by(KnowledgeObjectRecord.version_sequence.desc())
        .all()
    )


def list_links(acting_user, stable_id: str) -> list[KnowledgeObjectLinkRecord]:
    _require_view(acting_user)
    return (
        KnowledgeObjectLinkRecord.query.filter_by(from_stable_id=stable_id, is_archived=False)
        .order_by(KnowledgeObjectLinkRecord.link_type.asc())
        .all()
    )


def create_knowledge_object(
    acting_user,
    *,
    object_type: str,
    title: str,
    stable_id: str,
    specialty_code: str | None = None,
    topic_key: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    attributes: str | dict | None = None,
    version_label: str = "1.0.0",
    department_id: int | None = None,
    as_suggestion: bool = False,
) -> KnowledgeObjectRecord:
    if as_suggestion:
        _require_suggest(acting_user)
    else:
        _require_edit(acting_user)

    _validate_object_type(object_type)
    sid = _validate_stable_id(stable_id)
    title_clean = (title or "").strip()
    if not title_clean:
        raise ValidationError("Title is required.")

    if KnowledgeObjectRecord.query.filter_by(stable_id=sid, version_sequence=1).first():
        raise ValidationError(f"Knowledge object '{sid}' already exists.")

    attrs = _parse_attributes(attributes)
    record = KnowledgeObjectRecord(
        stable_id=sid,
        object_type=object_type,
        title=title_clean,
        version_label=(version_label or "1.0.0").strip(),
        version_sequence=1,
        status=STATUS_DRAFT,
        specialty_code=(specialty_code or "").strip() or None,
        topic_key=(topic_key or "").strip() or None,
        summary=(summary or "").strip() or None,
        body=(body or "").strip() or None,
        department_id=_department_id_for(acting_user, department_id),
        created_by_id=getattr(acting_user, "id", None),
        updated_by_id=getattr(acting_user, "id", None),
    )
    record.attributes = attrs
    db.session.add(record)
    db.session.commit()

    audit_engine.log(
        action="knowledge_object.created",
        user=acting_user,
        target_type="KnowledgeObjectRecord",
        target_id=record.id,
        details={"stable_id": sid, "object_type": object_type, "as_suggestion": as_suggestion},
    )
    return record


def update_knowledge_object(
    acting_user,
    record: KnowledgeObjectRecord,
    *,
    title: str | None = None,
    specialty_code: str | None = None,
    topic_key: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    attributes: str | dict | None = None,
    version_label: str | None = None,
) -> KnowledgeObjectRecord:
    if not _can_edit_record(acting_user, record):
        permission_engine.require(acting_user, "knowledge_library:edit")

    if record.status == STATUS_PUBLISHED:
        raise ValidationError("Published knowledge cannot be edited in place. Create a new version.")
    if record.status == STATUS_SUPERSEDED:
        raise ValidationError("Superseded versions are read-only.")
    if record.is_archived:
        raise ValidationError("Archived knowledge cannot be edited. Restore it first.")

    if title is not None:
        title_clean = title.strip()
        if not title_clean:
            raise ValidationError("Title is required.")
        record.title = title_clean
    if specialty_code is not None:
        record.specialty_code = specialty_code.strip() or None
    if topic_key is not None:
        record.topic_key = topic_key.strip() or None
    if summary is not None:
        record.summary = summary.strip() or None
    if body is not None:
        record.body = body.strip() or None
    if attributes is not None:
        record.attributes = _parse_attributes(attributes)
    if version_label is not None:
        record.version_label = version_label.strip() or record.version_label

    record.updated_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="knowledge_object.updated",
        user=acting_user,
        target_type="KnowledgeObjectRecord",
        target_id=record.id,
        details={"stable_id": record.stable_id},
    )
    return record


def publish_knowledge_object(acting_user, record: KnowledgeObjectRecord) -> KnowledgeObjectRecord:
    _require_edit(acting_user, audit_context={"target_type": "KnowledgeObjectRecord", "target_id": record.id})

    if record.status != STATUS_DRAFT:
        raise ValidationError("Only draft knowledge can be published.")
    if record.is_archived:
        raise ValidationError("Cannot publish archived knowledge.")

    from app.modules.knowledge_library.validation import validate_for_publish_or_raise
    from app.modules.knowledge_library.kl_catalog_loader import reset_kl_catalog_index
    from app.modules.clinical_history.intelligence.catalog_provider import reset_catalog_provider

    validate_for_publish_or_raise(record)

    for prev in KnowledgeObjectRecord.query.filter_by(
        stable_id=record.stable_id,
        status=STATUS_PUBLISHED,
        is_archived=False,
    ).all():
        if prev.id != record.id:
            prev.status = STATUS_SUPERSEDED

    record.status = STATUS_PUBLISHED
    record.published_at = utcnow()
    record.updated_by_id = getattr(acting_user, "id", None)
    db.session.commit()
    reset_kl_catalog_index()
    reset_catalog_provider()

    audit_engine.log(
        action="knowledge_object.published",
        user=acting_user,
        target_type="KnowledgeObjectRecord",
        target_id=record.id,
        details={"stable_id": record.stable_id, "version_sequence": record.version_sequence},
    )
    return record


def create_new_version(
    acting_user,
    stable_id: str,
    *,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    attributes: str | dict | None = None,
    version_label: str | None = None,
) -> KnowledgeObjectRecord:
    _require_edit(acting_user)

    latest = (
        KnowledgeObjectRecord.query.filter_by(stable_id=stable_id)
        .order_by(KnowledgeObjectRecord.version_sequence.desc())
        .first()
    )
    if latest is None:
        raise NotFoundError(f"No knowledge object with stable_id {stable_id}")

    new_seq = latest.version_sequence + 1
    vl = (version_label or _bump_version_label(latest.version_label)).strip()
    attrs = _parse_attributes(attributes) if attributes is not None else dict(latest.attributes)

    record = KnowledgeObjectRecord(
        stable_id=stable_id,
        object_type=latest.object_type,
        title=(title or latest.title).strip(),
        version_label=vl,
        version_sequence=new_seq,
        status=STATUS_DRAFT,
        specialty_code=latest.specialty_code,
        topic_key=latest.topic_key,
        summary=(summary if summary is not None else latest.summary),
        body=(body if body is not None else latest.body),
        supersedes_stable_id=stable_id,
        department_id=latest.department_id,
        created_by_id=getattr(acting_user, "id", None),
        updated_by_id=getattr(acting_user, "id", None),
    )
    record.attributes = attrs
    db.session.add(record)
    db.session.commit()

    audit_engine.log(
        action="knowledge_object.version_created",
        user=acting_user,
        target_type="KnowledgeObjectRecord",
        target_id=record.id,
        details={"stable_id": stable_id, "version_sequence": new_seq},
    )
    return record


def _bump_version_label(current: str) -> str:
    parts = (current or "1.0.0").split(".")
    try:
        major = int(parts[0])
        return f"{major + 1}.0.0"
    except (ValueError, IndexError):
        return "2.0.0"


def archive_knowledge_object(
    acting_user,
    record: KnowledgeObjectRecord,
    reason: str | None = None,
) -> KnowledgeObjectRecord:
    _require_edit(acting_user, audit_context={"target_type": "KnowledgeObjectRecord", "target_id": record.id})

    if record.is_archived:
        raise ValidationError("Knowledge object is already archived.")

    record.archive(getattr(acting_user, "id", None), (reason or "").strip() or None)
    record.status = STATUS_ARCHIVED
    record.updated_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="knowledge_object.archived",
        user=acting_user,
        target_type="KnowledgeObjectRecord",
        target_id=record.id,
        details={"stable_id": record.stable_id, "reason": reason},
    )
    return record


def restore_knowledge_object(acting_user, record: KnowledgeObjectRecord) -> KnowledgeObjectRecord:
    _require_edit(acting_user)

    if not record.is_archived:
        raise ValidationError("Knowledge object is not archived.")

    record.restore()
    if record.status == STATUS_ARCHIVED:
        record.status = STATUS_DRAFT
    record.updated_by_id = getattr(acting_user, "id", None)
    db.session.commit()

    audit_engine.log(
        action="knowledge_object.restored",
        user=acting_user,
        target_type="KnowledgeObjectRecord",
        target_id=record.id,
        details={"stable_id": record.stable_id},
    )
    return record


def upsert_link(
    acting_user,
    *,
    from_stable_id: str,
    to_stable_id: str,
    link_type: str,
    version_sequence: int | None = None,
) -> KnowledgeObjectLinkRecord:
    _require_edit(acting_user)

    existing = KnowledgeObjectLinkRecord.query.filter_by(
        from_stable_id=from_stable_id,
        to_stable_id=to_stable_id,
        link_type=link_type,
        is_archived=False,
    ).first()
    if existing:
        return existing

    link = KnowledgeObjectLinkRecord(
        from_stable_id=from_stable_id.strip(),
        to_stable_id=to_stable_id.strip(),
        link_type=link_type.strip(),
        version_sequence=version_sequence,
        department_id=_department_id_for(acting_user),
        created_by_id=getattr(acting_user, "id", None),
    )
    db.session.add(link)
    db.session.commit()

    audit_engine.log(
        action="knowledge_link.created",
        user=acting_user,
        target_type="KnowledgeObjectLinkRecord",
        target_id=link.id,
        details={"from": from_stable_id, "to": to_stable_id, "link_type": link_type},
    )
    return link


def archive_link(acting_user, link: KnowledgeObjectLinkRecord, reason: str | None = None) -> None:
    _require_edit(acting_user)
    link.archive(getattr(acting_user, "id", None), reason)
    db.session.commit()


def object_type_catalogue():
    """UI labels for object types — specialty-agnostic."""
    from app.modules.knowledge_library.constants import (
        OBJECT_TYPE_CDS_RULE,
        OBJECT_TYPE_COMPLAINT,
        OBJECT_TYPE_DISEASE,
        OBJECT_TYPE_GUIDELINE,
        OBJECT_TYPE_HISTORY_QUESTION,
        OBJECT_TYPE_INVESTIGATION,
        OBJECT_TYPE_MANAGEMENT,
        OBJECT_TYPE_SCORE,
    )

    return [
        (OBJECT_TYPE_DISEASE, "Diseases"),
        (OBJECT_TYPE_COMPLAINT, "Chief complaints"),
        (OBJECT_TYPE_HISTORY_QUESTION, "Interview questions"),
        (OBJECT_TYPE_CDS_RULE, "CDS rules (weights, branching, red flags)"),
        (OBJECT_TYPE_INVESTIGATION, "Investigations"),
        (OBJECT_TYPE_SCORE, "Clinical scores"),
        (OBJECT_TYPE_GUIDELINE, "Guidelines"),
        (OBJECT_TYPE_MANAGEMENT, "Management recommendations"),
    ]


def list_guideline_topics_for_admin() -> list[dict[str, str]]:
    """Human-readable guideline topic list for the admin screen (not internal type codes)."""
    import json
    import os

    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
    )
    index_path = os.path.join(project_root, "knowledge_library", "index.json")
    if not os.path.isfile(index_path):
        return []

    with open(index_path, encoding="utf-8") as handle:
        payload = json.load(handle)

    topics: list[dict[str, str]] = []
    for slug in payload.get("topics") or []:
        title_path = os.path.join(project_root, "knowledge_library", "topics", f"{slug}.json")
        title = slug.replace("_", " ").title()
        if os.path.isfile(title_path):
            try:
                with open(title_path, encoding="utf-8") as topic_file:
                    topic_data = json.load(topic_file)
                    raw_title = (topic_data.get("title") or "").strip()
                    if raw_title and not raw_title.startswith("ueg ") and len(raw_title) < 80:
                        title = raw_title.title()
            except (OSError, json.JSONDecodeError):
                pass
        topics.append({"slug": slug, "title": title})
    return topics
