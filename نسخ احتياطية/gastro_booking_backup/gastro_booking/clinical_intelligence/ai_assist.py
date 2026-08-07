"""AI assist layer — optional summarize / next-question suggestions. Never sole diagnostic authority."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from clinical_intelligence import history_engine


def ai_config() -> dict[str, Any]:
    enabled = str(os.environ.get("CI_AI_ENABLED", "false")).lower() in {"1", "true", "yes"}
    key = (os.environ.get("OPENAI_API_KEY") or os.environ.get("CI_OPENAI_API_KEY") or "").strip()
    model = os.environ.get("CI_AI_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    return {
        "enabled": enabled,
        "has_api_key": bool(key),
        "model": model,
        "provider": "openai" if key else None,
        "usable": enabled and bool(key),
    }


def _offline_summary(documentation_text: str, next_qs: list[dict]) -> dict[str, Any]:
    lines = [ln for ln in (documentation_text or "").splitlines() if ln.strip()]
    brief = "\n".join(lines[:12]) if lines else "No documentation draft yet."
    suggestions = [
        {"id": q.get("id"), "prompt": q.get("prompt"), "source": "knowledge_history_engine"}
        for q in (next_qs or [])[:5]
    ]
    return {
        "mode": "offline_rules",
        "summary": brief,
        "next_questions": suggestions,
        "disclaimer": (
            "AI assist unavailable or disabled — showing rule-based history next questions. "
            "This is NOT a diagnosis."
        ),
        "diagnostic_authority": False,
    }


def _openai_chat(prompt: str, *, model: str, api_key: str) -> str:
    body = json.dumps(
        {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You assist clinicians with note summarization and suggesting which "
                        "knowledge-base questions to ask next. You must NOT invent diagnoses, "
                        "lab values, or replace clinical judgment. Keep output concise."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def assist_consultation(
    *,
    complaint_code: str,
    documentation_text: str,
    answers: list[dict],
    allowed_next_questions: list[dict] | None = None,
) -> dict[str, Any]:
    cfg = ai_config()
    next_qs = allowed_next_questions
    if next_qs is None:
        next_qs = history_engine.next_questions(complaint_code, answers, limit=5).get("next") or []

    if not cfg["usable"]:
        out = _offline_summary(documentation_text, next_qs)
        out["config"] = {k: cfg[k] for k in ("enabled", "has_api_key", "model", "usable")}
        return out

    allowed = "\n".join(f"- {q.get('id')}: {q.get('prompt')}" for q in next_qs[:8])
    prompt = (
        f"Complaint: {complaint_code}\n\n"
        f"Documentation draft:\n{documentation_text[:4000]}\n\n"
        f"Allowed next questions from knowledge base (suggest subset only):\n{allowed}\n\n"
        "Return:\n1) Short clinical note summary (5-8 bullets)\n"
        "2) Up to 3 next question IDs from the allowed list with one-line rationale\n"
        "Do not state a definitive diagnosis."
    )
    try:
        text = _openai_chat(
            prompt,
            model=cfg["model"],
            api_key=(os.environ.get("OPENAI_API_KEY") or os.environ.get("CI_OPENAI_API_KEY") or "").strip(),
        )
        return {
            "mode": "openai",
            "summary": text,
            "next_questions": [
                {"id": q.get("id"), "prompt": q.get("prompt"), "source": "knowledge_constrained"}
                for q in next_qs[:3]
            ],
            "disclaimer": "Optional AI assist only — not diagnostic authority. Verify against findings.",
            "diagnostic_authority": False,
            "config": {k: cfg[k] for k in ("enabled", "has_api_key", "model", "usable")},
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
        out = _offline_summary(documentation_text, next_qs)
        out["error"] = str(exc)
        out["config"] = {k: cfg[k] for k in ("enabled", "has_api_key", "model", "usable")}
        return out
