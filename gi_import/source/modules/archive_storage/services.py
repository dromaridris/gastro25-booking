"""Archive storage list, search, restore."""

import json

from app.core.base_model import utcnow
from app.core.exceptions import NotFoundError
from app.engines import audit_engine, permission_engine
from app.extensions import db
from app.modules.archive_storage.models import ArchivedAsset, ArchivePolicy


def _require(user, code: str, target_id=None):
    permission_engine.require(user, code, audit_context={"target_type": "ArchivedAsset", "target_id": target_id})


def list_policies(acting_user) -> list[ArchivePolicy]:
    _require(acting_user, "archive_storage:view")
    return ArchivePolicy.query.filter_by(is_archived=False).order_by(ArchivePolicy.name).all()


def list_assets(acting_user, *, resource_type: str | None = None, limit: int = 100) -> list[ArchivedAsset]:
    _require(acting_user, "archive_storage:view")
    q = ArchivedAsset.query.filter_by(is_archived=False, restored_at=None)
    if resource_type:
        q = q.filter_by(resource_type=resource_type)
    return q.order_by(ArchivedAsset.archived_at.desc()).limit(limit).all()


def search_assets(acting_user, query: str) -> list[ArchivedAsset]:
    _require(acting_user, "archive_storage:view")
    pattern = f"%{query.strip()}%"
    return (
        ArchivedAsset.query.filter_by(is_archived=False, restored_at=None)
        .filter(ArchivedAsset.title.ilike(pattern))
        .order_by(ArchivedAsset.archived_at.desc())
        .limit(50)
        .all()
    )


def get_asset(acting_user, asset_id: int) -> ArchivedAsset:
    _require(acting_user, "archive_storage:view", asset_id)
    asset = ArchivedAsset.query.get(asset_id)
    if asset is None or asset.is_archived:
        raise NotFoundError(f"No archived asset with id {asset_id}")
    return asset


def register_asset(acting_user, *, resource_type: str, resource_id: int, title: str,
                   policy_id: int | None = None, storage_key: str | None = None,
                   metadata: dict | None = None) -> ArchivedAsset:
    _require(acting_user, "archive_storage:manage")
    asset = ArchivedAsset(
        policy_id=policy_id,
        resource_type=resource_type,
        resource_id=resource_id,
        title=title,
        archived_by_id=acting_user.id,
        storage_key=storage_key,
        metadata_json=json.dumps(metadata) if metadata else None,
        created_by_id=acting_user.id,
    )
    db.session.add(asset)
    db.session.commit()
    audit_engine.log("archive.register", user=acting_user, target_type="archived_asset", target_id=asset.id)
    return asset


def restore_asset(acting_user, asset_id: int) -> ArchivedAsset:
    _require(acting_user, "archive_storage:manage", asset_id)
    asset = get_asset(acting_user, asset_id)
    asset.restored_at = utcnow()
    db.session.commit()
    audit_engine.log("archive.restore", user=acting_user, target_type="archived_asset", target_id=asset.id)
    return asset
