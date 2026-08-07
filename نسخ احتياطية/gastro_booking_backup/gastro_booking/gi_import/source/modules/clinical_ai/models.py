"""Clinical AI domain models."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.base_model import BaseModel
from app.extensions import db

from .constants import SESSION_PENDING


@dataclass
class AIProviderRequest:
    prompt: str
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIProviderResponse:
    provider_key: str
    model: str
    content: str
    token_usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None


@dataclass
class ParsedSection:
    section_type: str
    title: str | None
    content: str | list[str] | dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParsedAIResponse:
    narrative: str | None = None
    sections: list[ParsedSection] = field(default_factory=list)
    bullet_lists: list[list[str]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "narrative": self.narrative,
            "sections": [s.to_dict() for s in self.sections],
            "bullet_lists": self.bullet_lists,
            "tables": self.tables,
            "recommendations": self.recommendations,
            "references": self.references,
            "raw_text": self.raw_text,
        }


class AISessionRecord(BaseModel):
    __tablename__ = "clinical_ai_sessions"

    session_uuid = db.Column(
        db.String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4())
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True, index=True)
    encounter_id = db.Column(db.Integer, db.ForeignKey("clinical_encounters.id"), nullable=True, index=True)

    prompt_type = db.Column(db.String(64), nullable=False, index=True)
    provider_key = db.Column(db.String(32), nullable=False)
    model_name = db.Column(db.String(128), nullable=True)

    status = db.Column(db.String(32), nullable=False, default=SESSION_PENDING, index=True)
    execution_duration_ms = db.Column(db.Integer, nullable=True)

    token_usage_json = db.Column(db.Text, nullable=True)
    response_metadata_json = db.Column(db.Text, nullable=True)
    prompt_text = db.Column(db.Text, nullable=True)
    response_text = db.Column(db.Text, nullable=True)

    @property
    def token_usage(self) -> dict[str, Any]:
        if not self.token_usage_json:
            return {}
        return json.loads(self.token_usage_json)

    @token_usage.setter
    def token_usage(self, value: dict[str, Any]) -> None:
        self.token_usage_json = json.dumps(value or {})

    @property
    def response_metadata(self) -> dict[str, Any]:
        if not self.response_metadata_json:
            return {}
        return json.loads(self.response_metadata_json)

    @response_metadata.setter
    def response_metadata(self, value: dict[str, Any]) -> None:
        self.response_metadata_json = json.dumps(value or {})


class AIRequestAuditRecord(BaseModel):
    __tablename__ = "clinical_ai_request_audits"

    session_uuid = db.Column(db.String(36), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True)

    provider_key = db.Column(db.String(32), nullable=False)
    model_name = db.Column(db.String(128), nullable=True)
    prompt_type = db.Column(db.String(64), nullable=False)

    execution_duration_ms = db.Column(db.Integer, nullable=True)
    token_usage_json = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, index=True)

    @property
    def token_usage(self) -> dict[str, Any]:
        if not self.token_usage_json:
            return {}
        return json.loads(self.token_usage_json)

    @token_usage.setter
    def token_usage(self, value: dict[str, Any]) -> None:
        self.token_usage_json = json.dumps(value or {})
