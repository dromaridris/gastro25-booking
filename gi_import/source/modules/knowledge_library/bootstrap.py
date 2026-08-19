"""Application bootstrap for Knowledge Library."""

from flask import Flask

from app.modules.knowledge_library.provider_factory import init_knowledge_provider


def init_knowledge_library(app: Flask) -> None:
    """Wire provider from configuration only — no content seeding at startup."""
    init_knowledge_provider(app)
