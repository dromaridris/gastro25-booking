"""AI provider factory."""

from __future__ import annotations

from gi_platform.clinical_ai.config import ClinicalAIConfig
from gi_platform.clinical_ai.constants import (
    PROVIDER_CLAUDE, PROVIDER_GEMINI, PROVIDER_LOCAL, PROVIDER_NULL,
    PROVIDER_OPENAI, PROVIDER_STUB,
)
from gi_platform.clinical_ai.providers import (
    AIProvider,
    ClaudeProvider,
    GeminiProvider,
    LocalLLMProvider,
    NullAIProvider,
    OpenAIProvider,
    StubAIProvider,
)

_PROVIDER_REGISTRY: dict[str, type[AIProvider]] = {
    PROVIDER_NULL: NullAIProvider,
    PROVIDER_STUB: StubAIProvider,
    PROVIDER_OPENAI: OpenAIProvider,
    PROVIDER_CLAUDE: ClaudeProvider,
    PROVIDER_GEMINI: GeminiProvider,
    PROVIDER_LOCAL: LocalLLMProvider,
}

_active_provider: AIProvider | None = None
_active_config: ClinicalAIConfig | None = None


def create_ai_provider(provider_key: str) -> AIProvider:
    cls = _PROVIDER_REGISTRY.get(provider_key)
    if cls is None:
        raise ValueError(f"Unknown provider '{provider_key}'. Registered: {sorted(_PROVIDER_REGISTRY)}")
    return cls()


def resolve_provider(config: ClinicalAIConfig | None = None) -> AIProvider:
    cfg = config or ClinicalAIConfig.from_env()
    for key in cfg.provider_chain():
        if key in _PROVIDER_REGISTRY:
            return create_ai_provider(key)
    return StubAIProvider()


def init_ai_provider(config: ClinicalAIConfig | None = None) -> AIProvider:
    global _active_provider, _active_config
    cfg = config or ClinicalAIConfig.from_env()
    _active_config = cfg
    _active_provider = resolve_provider(cfg)
    return _active_provider


def get_ai_provider() -> AIProvider:
    if _active_provider is None:
        return resolve_provider(ClinicalAIConfig.from_env())
    return _active_provider


def set_ai_provider(provider: AIProvider) -> None:
    global _active_provider
    _active_provider = provider
