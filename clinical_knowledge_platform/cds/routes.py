"""CDS routes (Phase 5)."""

from __future__ import annotations

from flask import flash, redirect, render_template, url_for

from clinical_knowledge_platform.cds import service as cds_svc
from clinical_knowledge_platform.schema import init_ckp_schema


def register_cds_routes(app, *, get_db, login_required, roles_required=None):
    @app.route("/clinical-encounter/<int:session_id>/cds")
    @login_required
    def ckp_cds_panel(session_id: int):
        db = get_db()
        init_ckp_schema(db)
        alerts = cds_svc.list_active_alerts(db, session_id)
        return render_template("ckp/cds.html", session_id=session_id, alerts=alerts)

    @app.route("/clinical-encounter/<int:session_id>/cds/refresh", methods=["POST"])
    @login_required
    def ckp_cds_refresh(session_id: int):
        db = get_db()
        init_ckp_schema(db)
        try:
            alerts = cds_svc.refresh_cds_for_session(db, session_id)
            flash(f"CDS refreshed — {len(alerts)} advisories (advisory only)", "success")
        except Exception as e:
            flash(str(e), "error")
        return redirect(url_for("ckp_cds_panel", session_id=session_id))
