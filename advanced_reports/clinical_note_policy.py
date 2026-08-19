"""Clinical note & print layout policy — shared rules for structured endoscopy reports.

Print layout modes (all advanced reports except EUS / legacy ERCP):
- ≤4 uploaded images → sidebar_images: report + images on page 1 (two columns).
- ≥5 uploaded images → default (ERCP split): report only on page 1, ALL images on page 2.
"""

from __future__ import annotations

from advanced_reports.configs import PROCEDURE_REGISTRY

# EUS keeps legacy split layout; ERCP lives in app.py (untouched).
LEGACY_PRINT_LAYOUT_KEYS = frozenset({'eus'})
SIDEBAR_IMAGE_SLOTS = 4
SIDEBAR_IMAGE_MAX_COUNT = 4  # ≤ this count → sidebar; ≥5 → split pages


def is_structured_endoscopy(procedure_key: str, cfg: dict | None = None) -> bool:
    if procedure_key in LEGACY_PRINT_LAYOUT_KEYS:
        return False
    if cfg and cfg.get('print_layout') == 'sidebar_images':
        return True
    if procedure_key in PROCEDURE_REGISTRY:
        return True
    if cfg and cfg.get('image_table'):
        return True
    return False


def uses_sidebar_print_layout(procedure_key: str, cfg: dict | None = None) -> bool:
    """Whether procedure supports structured endoscopy print (either mode)."""
    return is_structured_endoscopy(procedure_key, cfg)


def resolve_print_layout(
    procedure_key: str,
    cfg: dict | None,
    uploaded_image_count: int,
) -> str:
    """Return 'sidebar_images' (≤4 images) or 'default' (≥5 images, ERCP split)."""
    if not is_structured_endoscopy(procedure_key, cfg):
        return (cfg or {}).get('print_layout') or 'default'
    if uploaded_image_count <= SIDEBAR_IMAGE_MAX_COUNT:
        return 'sidebar_images'
    return 'default'


def sidebar_slot_count(cfg: dict | None = None) -> int:
    if cfg and cfg.get('print_sidebar_slots'):
        return int(cfg['print_sidebar_slots'])
    return SIDEBAR_IMAGE_SLOTS
