"""AI provider factory — configuration-driven selection."""

from __future__ import annotations

from flask import Flask

from .config import ClinicalAIConfig
from .constants import PROVIDER_CLAUDE, PROVIDER_GEMINI, PROVIDER_LOCAL, PROVIDER_NULL, PROVIDER_OPENAI
from .providers import (
    AIProvider,
    ClaudeProvider,
    GeminiProvider,
    LocalLLMProvider,
    NullAIProvider,
    OpenAIProvider,
)

_PROVIDER_REGISTRY: dict[str, type[AIProvider]] = {
    PROVIDER_NULL: NullAIProvider,
    PROVIDER_OPENAI: OpenAIProvider,
    PROVIDER_CLAUDE: ClaudeProvider,
    PROVIDER_GEMINI: GeminiProvider,
    PROVIDER_LOCAL: LocalLLMProvider,
}

_active_provider: AIProvider | None = None


def register_provider_class(provider_key: str, provider_cls: type[AIProvider]) -> None:
    _PROVIDER_REGISTRY[provider_key] = provider_cls


def create_ai_provider(provider_key: str) -> AIProvider:
    cls = _PROVIDER_REGISTRY.get(provider_key)
    if cls is None:
        raise ValueError(
            f"Unknown CLINICAL_AI provider '{provider_key}'. Registered: {sorted(_PROVIDER_REGISTRY)}"
        )
    return cls()


def resolve_provider(config: ClinicalAIConfig | None = None) -> AIProvider:
    cfg = config or ClinicalAIConfig.from_app()
    for key in cfg.provider_chain():
        if key in _PROVIDER_REGISTRY:
            return create_ai_provider(key)
    return NullAIProvider()


def init_ai_provider(app: Flask) -> AIProvider:
    global _active_provider
    cfg = ClinicalAIConfig.from_app(app)
    _active_provider = resolve_provider(cfg)
    return _active_provider


def get_ai_provider() -> AIProvider:
    if _active_provider is None:
        return NullAIProvider()
    return _active_provider


def set_ai_provider(provider: AIProvider) -> None:
    global _active_provider
    _active_provider = provider
