from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.core.exceptions import ValidationError
from app.engines import audit_engine
from app.modules.auth import services
from app.modules.auth.forms import LoginForm

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("core.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = services.authenticate(form.email.data, form.password.data)
        except ValidationError as e:
            audit_engine.log(
                action="auth.login_failed",
                details={"email": form.email.data.lower().strip()},
                ip_address=request.remote_addr,
            )
            flash(str(e), "danger")
            return render_template("auth/login.html", form=form)

        # Session management: "remember me" controls whether the session
        # survives browser close (Flask-Login's remember cookie, capped
        # at REMEMBER_COOKIE_DURATION) versus a browser-session-only
        # cookie that still respects PERMANENT_SESSION_LIFETIME.
        session.permanent = True
        login_user(user, remember=form.remember_me.data)

        audit_engine.log(
            action="auth.login_success",
            user=user,
            ip_address=request.remote_addr,
        )
        return redirect(url_for("core.dashboard"))

    return render_template("auth/login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    audit_engine.log(
        action="auth.logout",
        user=current_user,
        ip_address=request.remote_addr,
    )
    logout_user()
    return redirect(url_for("auth.login"))
