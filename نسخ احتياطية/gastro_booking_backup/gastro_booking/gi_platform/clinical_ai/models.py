"""Clinical AI datamodels — provider-neutral (no SQLAlchemy)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from gi_platform.clinical_ai.constants import SESSION_PENDING


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
    raw_text: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {
            'narrative': self.narrative,
            'sections': [s.to_dict() for s in self.sections],
            'bullet_lists': self.bullet_lists,
            'tables': self.tables,
            'recommendations': self.recommendations,
            'references': self.references,
            'raw_text': self.raw_text,
        }


@dataclass
class AISessionRecord:
    id: int
    session_uuid: str
    ward_patient_id: int | None = None
    history_session_id: int | None = None
    created_by: int | None = None
    session_type: str = 'clinical_ai'
    prompt_type: str | None = None
    provider_key: str = 'stub'
    model_name: str | None = None
    status: str = SESSION_PENDING
    execution_duration_ms: int | None = None
    token_usage_json: str | None = None
    response_metadata_json: str | None = None
    prompt_text: str | None = None
    response_text: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

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


@dataclass
class AIRequestAuditRecord:
    session_uuid: str
    user_id: int
    ward_patient_id: int | None
    provider_key: str
    model_name: str | None
    prompt_type: str
    execution_duration_ms: int | None
    status: str
    token_usage_json: str | None = None

    @property
    def token_usage(self) -> dict[str, Any]:
        if not self.token_usage_json:
            return {}
        return json.loads(self.token_usage_json)

    @token_usage.setter
    def token_usage(self, value: dict[str, Any]) -> None:
        self.token_usage_json = json.dumps(value or {})
