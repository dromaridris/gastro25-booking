"""Provider credential and connectivity checks for Clinical AI admin."""

from __future__ import annotations

import os

from gi_platform.clinical_ai.constants import (
    PROVIDER_CLAUDE, PROVIDER_GEMINI, PROVIDER_LOCAL, PROVIDER_OPENAI, PROVIDER_STUB,
)


def _has_key(*names: str) -> bool:
    for name in names:
        if (os.environ.get(name) or '').strip():
            return True
    return False


def provider_env_status() -> dict[str, dict]:
    return {
        PROVIDER_STUB: {'configured': True, 'env_var': None},
        PROVIDER_OPENAI: {
            'configured': _has_key('OPENAI_API_KEY'),
            'env_var': 'OPENAI_API_KEY',
        },
        PROVIDER_CLAUDE: {
            'configured': _has_key('ANTHROPIC_API_KEY'),
            'env_var': 'ANTHROPIC_API_KEY',
        },
        PROVIDER_GEMINI: {
            'configured': _has_key('GOOGLE_API_KEY', 'GEMINI_API_KEY'),
            'env_var': 'GOOGLE_API_KEY or GEMINI_API_KEY',
        },
        PROVIDER_LOCAL: {
            'configured': _has_key('LOCAL_LLM_URL', 'OLLAMA_HOST'),
            'env_var': 'LOCAL_LLM_URL or OLLAMA_HOST',
        },
    }


def test_provider(provider_key: str) -> dict:
    """Lightweight connectivity probe — returns ok/error without persisting."""
    from gi_platform.clinical_ai.config import ClinicalAIConfig
    from gi_platform.clinical_ai.constants import PROVIDER_STUB
    from gi_platform.clinical_ai.models import AIProviderRequest
    from gi_platform.clinical_ai.provider_factory import create_ai_provider

    status = provider_env_status().get(provider_key, {'configured': False})
    if provider_key not in (PROVIDER_STUB,) and not status.get('configured'):
        return {
            'ok': False,
            'provider': provider_key,
            'message': f"Missing env: {status.get('env_var')}",
        }
    provider = create_ai_provider(provider_key)
    cfg = ClinicalAIConfig.from_env()
    req = AIProviderRequest(
        prompt='Reply with exactly: OK',
        model=None,
        max_tokens=16,
        temperature=0.0,
    )
    try:
        resp = provider.complete(req, config=cfg)
        content = (resp.content or '').strip()
        ok = bool(content) and resp.finish_reason not in ('adapter_stub', 'null_provider')
        if provider_key == PROVIDER_STUB:
            ok = True
            content = content or 'Stub provider ready.'
        return {
            'ok': ok,
            'provider': provider_key,
            'model': resp.model,
            'finish_reason': resp.finish_reason,
            'preview': content[:200],
            'message': 'Connected' if ok else 'Provider returned empty or stub response.',
        }
    except Exception as exc:
        return {'ok': False, 'provider': provider_key, 'message': str(exc)}
