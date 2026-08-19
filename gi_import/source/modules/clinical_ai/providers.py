"""AI provider abstraction — provider-independent adapters."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from .config import ClinicalAIConfig
from .constants import PROVIDER_CLAUDE, PROVIDER_GEMINI, PROVIDER_LOCAL, PROVIDER_NULL, PROVIDER_OPENAI
from .models import AIProviderRequest, AIProviderResponse


class AIProvider(ABC):
    """Base adapter contract. Application code depends on this only."""

    provider_key: str

    @abstractmethod
    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        raise NotImplementedError

    def health_check(self) -> bool:
        return True


class NullAIProvider(AIProvider):
    provider_key = PROVIDER_NULL

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        return AIProviderResponse(
            provider_key=self.provider_key,
            model="null",
            content="",
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            raw={"stub": True},
            finish_reason="null_provider",
        )


class OpenAIProvider(AIProvider):
    provider_key = PROVIDER_OPENAI

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        model = request.model or "gpt-4o"
        return AIProviderResponse(
            provider_key=self.provider_key,
            model=model,
            content="",
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            raw={"adapter": "openai", "note": "Sprint 9A — adapter stub; wire HTTP client in future sprint"},
            finish_reason="adapter_stub",
        )


class ClaudeProvider(AIProvider):
    provider_key = PROVIDER_CLAUDE

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        model = request.model or "claude-3-5-sonnet"
        return AIProviderResponse(
            provider_key=self.provider_key,
            model=model,
            content="",
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            raw={"adapter": "claude", "note": "Sprint 9A — adapter stub"},
            finish_reason="adapter_stub",
        )


class GeminiProvider(AIProvider):
    provider_key = PROVIDER_GEMINI

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        model = request.model or "gemini-pro"
        return AIProviderResponse(
            provider_key=self.provider_key,
            model=model,
            content="",
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            raw={"adapter": "gemini", "note": "Sprint 9A — adapter stub"},
            finish_reason="adapter_stub",
        )


class LocalLLMProvider(AIProvider):
    provider_key = PROVIDER_LOCAL

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        model = request.model or "local"
        time.sleep(0)
        return AIProviderResponse(
            provider_key=self.provider_key,
            model=model,
            content="",
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            raw={"adapter": "local", "endpoint": "configurable"},
            finish_reason="adapter_stub",
        )


class RecordingAIProvider(AIProvider):
    """Test wrapper that records calls without external network."""

    def __init__(self, inner: AIProvider) -> None:
        self.inner = inner
        self.calls: list[AIProviderRequest] = []

    @property
    def provider_key(self) -> str:
        return self.inner.provider_key

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        self.calls.append(request)
        return self.inner.complete(request, config=config)
