"""Longitudinal routes (Phase 6)."""

from __future__ import annotations

from flask import flash, redirect, render_template, url_for

from clinical_knowledge_platform.longitudinal import service as long_svc
from clinical_knowledge_platform.schema import init_ckp_schema


def register_longitudinal_routes(app, *, get_db, login_required, roles_required=None):
    @app.route("/ckp/longitudinal/")
    @login_required
    def ckp_longitudinal_home():
        db = get_db()
        init_ckp_schema(db)
        rows = db.execute(
            "SELECT patient_key, updated_at FROM ckp_longitudinal_memory ORDER BY updated_at DESC LIMIT 50"
        ).fetchall()
        return render_template("ckp/longitudinal_home.html", memories=rows)

    @app.route("/ckp/longitudinal/<path:patient_key>")
    @login_required
    def ckp_longitudinal_patient(patient_key: str):
        db = get_db()
        init_ckp_schema(db)
        mem = long_svc.get_memory(db, patient_key)
        if not mem:
            flash("No longitudinal memory for this patient key", "error")
            return redirect(url_for("ckp_longitudinal_home"))
        return render_template(
            "ckp/longitudinal_patient.html",
            memory=mem,
            events=long_svc.list_events(db, patient_key),
            compare=long_svc.latest_compare(db, patient_key),
        )

    @app.route("/clinical-encounter/<int:session_id>/longitudinal/ingest", methods=["POST"])
    @login_required
    def ckp_longitudinal_ingest(session_id: int):
        db = get_db()
        init_ckp_schema(db)
        try:
            mem = long_svc.ingest_session_into_memory(db, session_id)
            flash("Encounter ingested into longitudinal memory", "success")
            return redirect(url_for("ckp_longitudinal_patient", patient_key=mem["patient_key"]))
        except Exception as e:
            flash(str(e), "error")
            return redirect(url_for("ckp_encounter_workspace", session_id=session_id, channel="summary"))
