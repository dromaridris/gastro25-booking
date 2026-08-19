"""Branding routes — setup wizard, settings, about."""

from flask import Blueprint, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors
from app.modules.branding import branding_service
from app.modules.branding.constants import PLATFORM_LOGO_DIR, PLATFORM_LOGO_FILENAME, THEME_MODES
from app.modules.branding.forms import BrandingSettingsForm, SetupWizardForm

bp = Blueprint("branding", __name__)


@bp.route("/setup", methods=["GET", "POST"])
def setup_wizard():
    if not branding_service.is_setup_required():
        return redirect(url_for("auth.login"))

    form = SetupWizardForm()
    suggested = None
    palette = None

    if request.method == "GET":
        hn = request.args.get("hospital_name", "")
        dn = request.args.get("department_name", "")
        if hn or dn:
            suggested = branding_service.suggest_slogan(hn, dn)

    if form.validate_on_submit():
        hospital_file = form.hospital_logo.data
        dept_file = form.department_logo.data
        try:
            if hospital_file:
                palette = branding_service.preview_palette_from_upload(hospital_file)
            branding_service.complete_initial_setup(
                hospital_name=form.hospital_name.data,
                department_name=form.department_name.data,
                hospital_logo_file=hospital_file.stream if hospital_file else None,
                hospital_logo_filename=hospital_file.filename if hospital_file else None,
                department_logo_file=dept_file.stream if dept_file else None,
                department_logo_filename=dept_file.filename if dept_file else None,
                primary_color=form.primary_color.data,
                secondary_color=form.secondary_color.data,
                accent_color=form.accent_color.data,
                slogan=form.slogan.data,
                accept_suggested_slogan=form.use_suggested_slogan.data,
                suggested_slogan=form.suggested_slogan.data or suggested,
            )
            flash("Initial setup complete. Welcome to your clinical platform.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash(str(e), "danger")

    if form.hospital_name.data and form.department_name.data and not suggested:
        suggested = branding_service.suggest_slogan(form.hospital_name.data, form.department_name.data)

    return render_template(
        "branding/setup_wizard.html",
        form=form,
        suggested_slogan=suggested,
        palette=palette,
        theme_modes=THEME_MODES,
    )


@bp.route("/branding/settings", methods=["GET", "POST"])
@login_required
@handle_service_errors
def settings():
    config = branding_service.get_config()
    form = BrandingSettingsForm(obj=config)

    if form.validate_on_submit():
        dept_file = form.department_logo.data
        hospital_file = form.hospital_logo.data
        branding_service.update_branding(
            current_user,
            hospital_name=form.hospital_name.data,
            department_name=form.department_name.data,
            hospital_logo_file=hospital_file.stream if hospital_file else None,
            hospital_logo_filename=hospital_file.filename if hospital_file else None,
            department_logo_file=dept_file.stream if dept_file else None,
            department_logo_filename=dept_file.filename if dept_file else None,
            remove_department_logo=form.remove_department_logo.data,
            primary_color=form.primary_color.data,
            secondary_color=form.secondary_color.data,
            accent_color=form.accent_color.data,
            slogan=form.slogan.data,
            theme_mode=form.theme_mode.data,
        )
        flash("Branding updated.", "success")
        return redirect(url_for("branding.settings"))

    view = branding_service.get_branding_view()
    return render_template("branding/settings.html", form=form, branding=view)


@bp.route("/about")
def about():
    view = branding_service.get_branding_view()
    platform = branding_service.get_template_context()["platform"]
    from app.modules.branding.logo_manager import platform_logo_url

    return render_template(
        "branding/about.html",
        branding=view,
        platform=platform,
        platform_logo_url=platform_logo_url(),
    )


@bp.route("/platform-logo")
def platform_logo():
    """Serve developer logo from project `brand logo` folder."""
    return send_from_directory(PLATFORM_LOGO_DIR, PLATFORM_LOGO_FILENAME)


@bp.route("/branding/pharma-banner", methods=["GET", "POST"])
@login_required
@handle_service_errors
def pharma_banner_manage():
    from app.modules.branding import pharma_banner_service

    config = branding_service.get_config()
    if request.method == "POST":
        if "toggle" in request.form:
            pharma_banner_service.toggle_banner(current_user, request.form.get("enabled") == "1")
            flash("Banner setting updated.", "success")
        elif "add_slide" in request.form:
            pharma_banner_service.create_slide(
                current_user,
                title=request.form.get("title", ""),
                body_html=request.form.get("body_html"),
                link_url=request.form.get("link_url"),
                sort_order=request.form.get("sort_order", 0, type=int),
            )
            flash("Slide added.", "success")
        elif "delete_slide" in request.form:
            pharma_banner_service.delete_slide(current_user, request.form.get("slide_id", type=int))
            flash("Slide removed.", "success")
        return redirect(url_for("branding.pharma_banner_manage"))
    slides = pharma_banner_service.list_all_slides(current_user)
    return render_template("branding/pharma_banner_manage.html", config=config, slides=slides)


def register_setup_guard(app):
    """Redirect to setup wizard on fresh installations."""

    @app.before_request
    def _require_setup_complete():
        from flask import request

        if not branding_service.is_setup_required():
            return None
        endpoint = request.endpoint or ""
        allowed = (
            endpoint.startswith("branding.setup_wizard"),
            endpoint.startswith("branding.platform_logo"),
            endpoint.startswith("static"),
        )
        if any(allowed):
            return None
        return redirect(url_for("branding.setup_wizard"))
