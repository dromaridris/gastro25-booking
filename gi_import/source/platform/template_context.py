"""Merged template context — single pass for branding, UI, and release metadata."""

from app.modules.branding import branding_service
from app.modules.branding.branding_config import PlatformIdentity
from app.modules.branding.theme_engine import render_theme_css
from app.modules.branding_integration.cache import get_cached_template_context
from app.platform.release import PLATFORM_RELEASE
from app.ui.context import get_ui_context


def get_merged_template_context() -> dict:
    ctx = dict(get_cached_template_context())
    ctx.update(get_ui_context())
    ctx.setdefault("gi_quick_actions", [])
    ctx.setdefault("gi_nav_groups", [])
    ctx.setdefault("gi_footer_show_platform", True)

    # Always read live branding colours — cached CSS can lag after Branding Settings save
    view = branding_service.get_branding_view()
    ctx["branding"] = view
    ctx["theme_css"] = render_theme_css(
        view.primary_color,
        view.secondary_color,
        view.accent_color,
        theme_mode=view.theme_mode,
    )

    platform = ctx.get("platform")
    if platform is not None:
        ctx["platform"] = PlatformIdentity(
            name=platform.name,
            support_email=platform.support_email,
            version=PLATFORM_RELEASE,
        )
    return ctx
