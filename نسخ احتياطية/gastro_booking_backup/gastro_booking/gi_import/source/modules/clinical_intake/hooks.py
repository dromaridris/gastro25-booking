"""Extension hooks for future clinical intake workflows."""

from __future__ import annotations

from typing import Any, Callable

IntakeHookHandler = Callable[..., dict[str, Any]]

_HOOK_REGISTRY: dict[str, list[IntakeHookHandler]] = {}


def register_intake_extension(hook_name: str, handler: IntakeHookHandler) -> None:
    """Register a handler for a named intake lifecycle hook."""
    _HOOK_REGISTRY.setdefault(hook_name, []).append(handler)


def registered_hooks() -> list[str]:
    return sorted(_HOOK_REGISTRY.keys())


def run_intake_extensions(hook_name: str, intake, **context: Any) -> dict[str, Any]:
    """
    Execute registered extension handlers.

    Sprint 9B: hooks only — history, differential, investigations, and management
    attach in later sprints.
    """
    results: dict[str, Any] = {}
    for index, handler in enumerate(_HOOK_REGISTRY.get(hook_name, [])):
        key = getattr(handler, "__name__", f"handler_{index}")
        results[key] = handler(intake=intake, **context)
    return results
