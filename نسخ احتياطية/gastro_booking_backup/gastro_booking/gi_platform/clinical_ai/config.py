"""Clinical AI configuration — env + optional Flask app.config."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from gi_platform.clinical_ai.constants import PROVIDER_NULL, PROVIDER_STUB


@dataclass
class ClinicalAIConfig:
    default_provider: str = PROVIDER_NULL
    provider_priority: list[str] = field(default_factory=list)
    request_timeout_seconds: float = 60.0
    max_tokens: int = 4096
    temperature: float = 0.2
    log_prompts: bool = True
    log_responses: bool = True
    trainee_ai_enabled: bool = False
    feature_flags: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_env(cls, app_config: dict | None = None) -> ClinicalAIConfig:
        cfg = app_config or {}
        legacy = (os.environ.get('GI_AI_PROVIDER') or cfg.get('GI_AI_PROVIDER') or '').strip().lower()
        default = (
            cfg.get('CLINICAL_AI_DEFAULT_PROVIDER')
            or os.environ.get('CLINICAL_AI_DEFAULT_PROVIDER')
            or legacy
            or PROVIDER_STUB
        )
        if default == 'stub':
            default = PROVIDER_STUB
        priority_raw = cfg.get('CLINICAL_AI_PROVIDER_PRIORITY') or os.environ.get('CLINICAL_AI_PROVIDER_PRIORITY', '')
        priority = [p.strip() for p in priority_raw.split(',') if p.strip()] if priority_raw else []
        flags_raw = cfg.get('CLINICAL_AI_FEATURE_FLAGS') or os.environ.get('CLINICAL_AI_FEATURE_FLAGS', '')
        if isinstance(flags_raw, str) and flags_raw:
            flags = {k.strip(): True for k in flags_raw.split(',') if k.strip()}
        elif isinstance(flags_raw, dict):
            flags = dict(flags_raw)
        else:
            flags = {}
        return cls(
            default_provider=default,
            provider_priority=priority,
            request_timeout_seconds=float(cfg.get('CLINICAL_AI_REQUEST_TIMEOUT') or os.environ.get('CLINICAL_AI_REQUEST_TIMEOUT') or 60),
            max_tokens=int(cfg.get('CLINICAL_AI_MAX_TOKENS') or os.environ.get('CLINICAL_AI_MAX_TOKENS') or 4096),
            temperature=float(cfg.get('CLINICAL_AI_TEMPERATURE') or os.environ.get('CLINICAL_AI_TEMPERATURE') or 0.2),
            log_prompts=str(cfg.get('CLINICAL_AI_LOG_PROMPTS', os.environ.get('CLINICAL_AI_LOG_PROMPTS', 'true'))).lower() in ('1', 'true', 'yes'),
            log_responses=str(cfg.get('CLINICAL_AI_LOG_RESPONSES', os.environ.get('CLINICAL_AI_LOG_RESPONSES', 'true'))).lower() in ('1', 'true', 'yes'),
            trainee_ai_enabled=str(cfg.get('CLINICAL_AI_TRAINEE_ENABLED', os.environ.get('CLINICAL_AI_TRAINEE_ENABLED', 'false'))).lower() in ('1', 'true', 'yes'),
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
            'default_provider': self.default_provider,
            'provider_priority': self.provider_priority,
            'request_timeout_seconds': self.request_timeout_seconds,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'log_prompts': self.log_prompts,
            'log_responses': self.log_responses,
            'trainee_ai_enabled': self.trainee_ai_enabled,
            'feature_flags': self.feature_flags,
            'provider_chain': self.provider_chain(),
        }
