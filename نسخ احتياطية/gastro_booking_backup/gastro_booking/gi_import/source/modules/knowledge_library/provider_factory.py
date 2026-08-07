"""Knowledge provider factory — configuration-driven selection."""

from __future__ import annotations

from flask import Flask

from app.modules.knowledge_library.interfaces import KnowledgeProvider
from app.modules.knowledge_library.providers import NullKnowledgeProvider, PostgresKnowledgeProvider

_PROVIDER_REGISTRY: dict[str, type] = {
    "postgres": PostgresKnowledgeProvider,
    "null": NullKnowledgeProvider,
}

_active_provider: KnowledgeProvider | None = None


def register_provider_class(provider_key: str, provider_cls: type) -> None:
    """Allow future providers (markdown, json, api, cloud) without engine changes."""
    _PROVIDER_REGISTRY[provider_key] = provider_cls


def create_knowledge_provider(provider_key: str) -> KnowledgeProvider:
    cls = _PROVIDER_REGISTRY.get(provider_key)
    if cls is None:
        raise ValueError(
            f"Unknown KNOWLEDGE_PROVIDER '{provider_key}'. "
            f"Registered: {sorted(_PROVIDER_REGISTRY)}"
        )
    return cls()


def init_knowledge_provider(app: Flask) -> KnowledgeProvider:
    global _active_provider
    provider_key = app.config.get("KNOWLEDGE_PROVIDER", "postgres")
    _active_provider = create_knowledge_provider(provider_key)
    return _active_provider


def get_knowledge_provider() -> KnowledgeProvider:
    if _active_provider is None:
        return create_knowledge_provider("null")
    return _active_provider


def set_knowledge_provider(provider: KnowledgeProvider) -> None:
    """Test hook / runtime swap without redeploying clinical engines."""
    global _active_provider
    _active_provider = provider
