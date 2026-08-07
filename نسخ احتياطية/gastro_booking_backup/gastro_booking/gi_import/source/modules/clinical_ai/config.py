"""Clinical AI configuration — loaded from Flask app config / environment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from flask import Flask, current_app

from .constants import PROVIDER_NULL


@dataclass
class ClinicalAIConfig:
    default_provider: str = PROVIDER_NULL
    provider_priority: list[str] = field(default_factory=list)
    request_timeout_seconds: float = 60.0
    max_tokens: int = 4096
    temperature: float = 0.2
    log_prompts: bool = False
    log_responses: bool = False
    trainee_ai_enabled: bool = False
    feature_flags: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_app(cls, app: Flask | None = None) -> "ClinicalAIConfig":
        cfg = app.config if app is not None else current_app.config
        priority_raw = cfg.get("CLINICAL_AI_PROVIDER_PRIORITY", "")
        priority = [p.strip() for p in priority_raw.split(",") if p.strip()] if priority_raw else []
        flags_raw = cfg.get("CLINICAL_AI_FEATURE_FLAGS", {})
        if isinstance(flags_raw, str):
            flags = {k.strip(): True for k in flags_raw.split(",") if k.strip()}
        else:
            flags = dict(flags_raw or {})
        return cls(
            default_provider=cfg.get("CLINICAL_AI_DEFAULT_PROVIDER", PROVIDER_NULL),
            provider_priority=priority,
            request_timeout_seconds=float(cfg.get("CLINICAL_AI_REQUEST_TIMEOUT", 60)),
            max_tokens=int(cfg.get("CLINICAL_AI_MAX_TOKENS", 4096)),
            temperature=float(cfg.get("CLINICAL_AI_TEMPERATURE", 0.2)),
            log_prompts=bool(cfg.get("CLINICAL_AI_LOG_PROMPTS", False)),
            log_responses=bool(cfg.get("CLINICAL_AI_LOG_RESPONSES", False)),
            trainee_ai_enabled=bool(cfg.get("CLINICAL_AI_TRAINEE_ENABLED", False)),
            feature_flags=flags,
        )

    def provider_chain(self) -> list[str]:
        chain: list[str] = []
        for key in self.provider_priority:
            if key not in chain:
                chain.append(key)
        if self.default_provider and self.default_provider not in chain:
            chain.insert(0, self.default_provider)
        return chain or [self.default_provider or PROVIDER_NULL]

    def feature_enabled(self, flag: str) -> bool:
        return self.feature_flags.get(flag, False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_provider": self.default_provider,
            "provider_priority": self.provider_priority,
            "request_timeout_seconds": self.request_timeout_seconds,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "log_prompts": self.log_prompts,
            "log_responses": self.log_responses,
            "trainee_ai_enabled": self.trainee_ai_enabled,
            "feature_flags": self.feature_flags,
        }
