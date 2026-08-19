"""Platform identity constants — NOT editable by hospitals (Sprint 8A)."""

import os

# Non-editable platform identity
PLATFORM_NAME = "GastroIntelligence"
PLATFORM_SUPPORT_EMAIL = "oaa.aao120@gmail.com"
PLATFORM_VERSION = "1.0.0"

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_SYSTEM = "system"
THEME_MODES = (THEME_LIGHT, THEME_DARK, THEME_SYSTEM)

LOGO_HOSPITAL = "hospital"
LOGO_DEPARTMENT = "department"
LOGO_TYPES = (LOGO_HOSPITAL, LOGO_DEPARTMENT)

# Project-root folder for the developer / platform logo (per product spec).
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PLATFORM_LOGO_DIR = os.path.join(_PROJECT_ROOT, "brand logo")
PLATFORM_LOGO_FILENAME = "gastrointelligence.svg"

# Fallback when project folder logo is missing (bundled static asset).
PLATFORM_LOGO_STATIC = "platform/gastrointelligence.svg"

ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
MAX_LOGO_BYTES = 5 * 1024 * 1024

DEFAULT_PRIMARY = "#1a5276"
DEFAULT_SECONDARY = "#2874a6"
DEFAULT_ACCENT = "#3498db"
