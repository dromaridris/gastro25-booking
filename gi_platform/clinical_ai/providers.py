"""AI provider adapters — ported from GastroIntelligence."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

import requests

from gi_platform.clinical_ai.config import ClinicalAIConfig
from gi_platform.clinical_ai.constants import (
    PROVIDER_CLAUDE, PROVIDER_GEMINI, PROVIDER_LOCAL, PROVIDER_NULL,
    PROVIDER_OPENAI, PROVIDER_STUB,
)
from gi_platform.clinical_ai.models import AIProviderRequest, AIProviderResponse


class AIProvider(ABC):
    provider_key: str

    @abstractmethod
    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        raise NotImplementedError


class NullAIProvider(AIProvider):
    provider_key = PROVIDER_NULL

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        return AIProviderResponse(
            provider_key=self.provider_key,
            model='null',
            content='',
            token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            raw={'stub': True},
            finish_reason='null_provider',
        )


class StubAIProvider(AIProvider):
    """Gastro25 default — records prompt and returns structured placeholder."""

    provider_key = PROVIDER_STUB

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        preview = (request.prompt or '')[:500]
        content = (
            'NARRATIVE:\n'
            'Clinical AI provider is in stub mode. Your request was assembled with the full '
            'GastroIntelligence prompt engine and logged for audit.\n\n'
            'BULLETS:\n'
            '- Configure CLINICAL_AI_DEFAULT_PROVIDER=openai|claude|gemini|local for live LLM output\n'
            '- Context from patient history, labs, and knowledge library is included in the prompt\n'
            '- CDS differential remains available when LLM returns no content\n\n'
            f'RECOMMENDATIONS:\n'
            f'- Review assembled prompt preview ({len(request.prompt or "")} chars)\n'
        )
        return AIProviderResponse(
            provider_key=self.provider_key,
            model='stub',
            content=content,
            token_usage={'prompt_tokens': len(preview.split()), 'completion_tokens': 0, 'total_tokens': len(preview.split())},
            raw={'adapter': 'stub', 'prompt_preview': preview},
            finish_reason='stub',
        )


class OpenAIProvider(AIProvider):
    provider_key = PROVIDER_OPENAI

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        api_key = (os.environ.get('OPENAI_API_KEY') or '').strip()
        model = request.model or 'gpt-4o-mini'
        if not api_key:
            return AIProviderResponse(
                provider_key=self.provider_key, model=model, content='',
                token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                raw={'adapter': 'openai', 'error': 'OPENAI_API_KEY not set'},
                finish_reason='missing_key',
            )
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': request.prompt or ''}],
            'max_tokens': min(request.max_tokens or config.max_tokens, config.max_tokens),
            'temperature': request.temperature if request.temperature is not None else config.temperature,
        }
        try:
            resp = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json=payload,
                timeout=config.request_timeout_seconds,
            )
            data = resp.json()
            if resp.status_code >= 400:
                err = data.get('error', {}).get('message', resp.text[:300])
                raise RuntimeError(err)
            choice = (data.get('choices') or [{}])[0]
            content = (choice.get('message') or {}).get('content') or ''
            usage = data.get('usage') or {}
            return AIProviderResponse(
                provider_key=self.provider_key,
                model=model,
                content=content,
                token_usage={
                    'prompt_tokens': usage.get('prompt_tokens', 0),
                    'completion_tokens': usage.get('completion_tokens', 0),
                    'total_tokens': usage.get('total_tokens', 0),
                },
                raw={'adapter': 'openai', 'id': data.get('id')},
                finish_reason=choice.get('finish_reason') or 'stop',
            )
        except Exception as exc:
            return AIProviderResponse(
                provider_key=self.provider_key, model=model, content='',
                token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                raw={'adapter': 'openai', 'error': str(exc)},
                finish_reason='error',
            )


class ClaudeProvider(AIProvider):
    provider_key = PROVIDER_CLAUDE

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        api_key = (os.environ.get('ANTHROPIC_API_KEY') or '').strip()
        model = request.model or 'claude-3-5-sonnet-latest'
        if not api_key:
            return AIProviderResponse(
                provider_key=self.provider_key, model=model, content='',
                token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                raw={'adapter': 'claude', 'error': 'ANTHROPIC_API_KEY not set'},
                finish_reason='missing_key',
            )
        payload = {
            'model': model,
            'max_tokens': min(request.max_tokens or config.max_tokens, config.max_tokens),
            'messages': [{'role': 'user', 'content': request.prompt or ''}],
        }
        try:
            resp = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'anthropic-version': '2023-06-01',
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=config.request_timeout_seconds,
            )
            data = resp.json()
            if resp.status_code >= 400:
                err = data.get('error', {}).get('message', resp.text[:300])
                raise RuntimeError(err)
            parts = data.get('content') or []
            content = ''.join(p.get('text', '') for p in parts if p.get('type') == 'text')
            usage = data.get('usage') or {}
            return AIProviderResponse(
                provider_key=self.provider_key,
                model=model,
                content=content,
                token_usage={
                    'prompt_tokens': usage.get('input_tokens', 0),
                    'completion_tokens': usage.get('output_tokens', 0),
                    'total_tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0),
                },
                raw={'adapter': 'claude', 'id': data.get('id')},
                finish_reason=(data.get('stop_reason') or 'stop'),
            )
        except Exception as exc:
            return AIProviderResponse(
                provider_key=self.provider_key, model=model, content='',
                token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                raw={'adapter': 'claude', 'error': str(exc)},
                finish_reason='error',
            )


class GeminiProvider(AIProvider):
    provider_key = PROVIDER_GEMINI

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        api_key = (os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY') or '').strip()
        model = request.model or 'gemini-1.5-flash'
        if not api_key:
            return AIProviderResponse(
                provider_key=self.provider_key, model=model, content='',
                token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                raw={'adapter': 'gemini', 'error': 'GOOGLE_API_KEY not set'},
                finish_reason='missing_key',
            )
        url = (
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
            f'?key={api_key}'
        )
        payload = {'contents': [{'parts': [{'text': request.prompt or ''}]}]}
        try:
            resp = requests.post(url, json=payload, timeout=config.request_timeout_seconds)
            data = resp.json()
            if resp.status_code >= 400:
                err = data.get('error', {}).get('message', resp.text[:300])
                raise RuntimeError(err)
            candidates = data.get('candidates') or []
            parts = ((candidates[0].get('content') or {}).get('parts') or []) if candidates else []
            content = ''.join(p.get('text', '') for p in parts)
            return AIProviderResponse(
                provider_key=self.provider_key,
                model=model,
                content=content,
                token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                raw={'adapter': 'gemini'},
                finish_reason='stop',
            )
        except Exception as exc:
            return AIProviderResponse(
                provider_key=self.provider_key, model=model, content='',
                token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                raw={'adapter': 'gemini', 'error': str(exc)},
                finish_reason='error',
            )


class LocalLLMProvider(AIProvider):
    provider_key = PROVIDER_LOCAL

    def complete(self, request: AIProviderRequest, *, config: ClinicalAIConfig) -> AIProviderResponse:
        endpoint = (
            os.environ.get('LOCAL_LLM_URL')
            or os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')
        ).rstrip('/')
        model = request.model or os.environ.get('LOCAL_LLM_MODEL', 'llama3')
        if not endpoint:
            return AIProviderResponse(
                provider_key=self.provider_key, model=model, content='',
                token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                raw={'adapter': 'local', 'error': 'LOCAL_LLM_URL not set'},
                finish_reason='missing_key',
            )
        payload = {
            'model': model,
            'prompt': request.prompt or '',
            'stream': False,
        }
        try:
            resp = requests.post(
                f'{endpoint}/api/generate',
                json=payload,
                timeout=config.request_timeout_seconds,
            )
            data = resp.json()
            if resp.status_code >= 400:
                raise RuntimeError(data.get('error', resp.text[:300]))
            content = data.get('response') or ''
            return AIProviderResponse(
                provider_key=self.provider_key,
                model=model,
                content=content,
                token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                raw={'adapter': 'local', 'endpoint': endpoint},
                finish_reason='stop',
            )
        except Exception as exc:
            return AIProviderResponse(
                provider_key=self.provider_key, model=model, content='',
                token_usage={'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
                raw={'adapter': 'local', 'error': str(exc)},
                finish_reason='error',
            )
