"""Application bootstrap for Clinical AI infrastructure."""

from flask import Flask

from .provider_factory import init_ai_provider


def init_clinical_ai(app: Flask) -> None:
    """Wire AI provider from configuration only — no medical logic at startup."""
    init_ai_provider(app)
