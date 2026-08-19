"""Knowledge Library persistence — provider-internal registry (PostgreSQL provider)."""

import json

from app.core.base_model import BaseModel, utcnow
from app.extensions import db
from app.modules.knowledge_library.constants import STATUS_DRAFT


class KnowledgeObjectRecord(BaseModel):
    """
    Versioned knowledge object registry.

    Consumers never query this table directly — only PostgreSQLKnowledgeProvider does.
    """

    __tablename__ = "knowledge_object_records"
    __table_args__ = (
        db.UniqueConstraint("stable_id", "version_sequence", name="uq_knowledge_object_version"),
        db.Index("ix_knowledge_object_type_status", "object_type", "status"),
    )

    stable_id = db.Column(db.String(100), nullable=False, index=True)
    object_type = db.Column(db.String(40), nullable=False, index=True)
    specialty_code = db.Column(db.String(50), nullable=True, index=True)
    title = db.Column(db.String(255), nullable=False)
    version_label = db.Column(db.String(40), nullable=False, default="1.0.0")
    version_sequence = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default=STATUS_DRAFT, index=True)
    topic_key = db.Column(db.String(100), nullable=True, index=True)
    summary = db.Column(db.Text, nullable=True)
    body = db.Column(db.Text, nullable=True)
    attributes_json = db.Column(db.Text, nullable=True)
    supersedes_stable_id = db.Column(db.String(100), nullable=True)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    @property
    def attributes(self) -> dict:
        if not self.attributes_json:
            return {}
        try:
            return json.loads(self.attributes_json)
        except json.JSONDecodeError:
            return {}

    @attributes.setter
    def attributes(self, value: dict) -> None:
        self.attributes_json = json.dumps(value or {}, ensure_ascii=False)


class KnowledgeObjectLinkRecord(BaseModel):
    __tablename__ = "knowledge_object_links"
    __table_args__ = (
        db.Index("ix_knowledge_link_from", "from_stable_id", "link_type"),
        db.Index("ix_knowledge_link_to", "to_stable_id", "link_type"),
    )

    from_stable_id = db.Column(db.String(100), nullable=False)
    to_stable_id = db.Column(db.String(100), nullable=False)
    link_type = db.Column(db.String(40), nullable=False)
    version_sequence = db.Column(db.Integer, nullable=True)


class KnowledgeProviderRegistration(BaseModel):
    """Runtime provider selection metadata — no storage paths."""

    __tablename__ = "knowledge_provider_registrations"

    provider_key = db.Column(db.String(50), nullable=False, unique=True, index=True)
    display_name = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    config_json = db.Column(db.Text, nullable=True)
    activated_at = db.Column(db.DateTime(timezone=True), nullable=True)


def seed_default_provider_registration_if_empty() -> int:
    if KnowledgeProviderRegistration.query.first() is not None:
        return 0
    db.session.add(
        KnowledgeProviderRegistration(
            provider_key="postgres",
            display_name="PostgreSQL Knowledge Registry",
            is_active=True,
            config_json="{}",
            activated_at=utcnow(),
            department_id=1,
        )
    )
    db.session.add(
        KnowledgeProviderRegistration(
            provider_key="null",
            display_name="Null Provider (empty)",
            is_active=False,
            config_json="{}",
            department_id=1,
        )
    )
    db.session.commit()
    return 2
