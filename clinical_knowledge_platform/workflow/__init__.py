"""Phase 3 clinical encounter workspace routes."""

from __future__ import annotations

from flask import flash, redirect, render_template, request, url_for

from clinical_knowledge_platform import repository as repo
from clinical_knowledge_platform.schema import init_ckp_schema
from clinical_knowledge_platform.seed_demo import seed_demo_gastroenterology
from clinical_knowledge_platform.validation import validate_knowledge
from clinical_knowledge_platform.workflow.controller import EncounterController


def register_ckp_routes(app, *, get_db, login_required, roles_required=None):
    roles_required = roles_required or (lambda *roles: login_required)

    def _ensure(db):
        init_ckp_schema(db)
        if not repo.latest_published_release(db):
            seed_demo_gastroenterology(db, force=True)
            db.commit()

    @app.route("/clinical-encounter/")
    @login_required
    def ckp_encounter_home():
        db = get_db()
        _ensure(db)
        releases = repo.list_releases(db)
        pub = repo.latest_published_release(db)
        rows = db.execute(
            "SELECT id, patient_label, release_id, status, updated_at FROM cre_session ORDER BY id DESC LIMIT 30"
        ).fetchall()
        return render_template(
            "ckp/encounter_home.html",
            releases=releases,
            published=pub,
            sessions=rows,
            validation=validate_knowledge(db),
        )

    @app.route("/clinical-encounter/start", methods=["POST"])
    @login_required
    def ckp_encounter_start():
        db = get_db()
        _ensure(db)
        label = (request.form.get("patient_label") or "").strip() or "Unnamed patient"
        try:
            ctl = EncounterController.start(db, patient_label=label)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("ckp_encounter_home"))
        return redirect(url_for("ckp_encounter_workspace", session_id=ctl.session_id, channel="history"))

    @app.route("/clinical-encounter/<int:session_id>")
    @login_required
    def ckp_encounter_workspace(session_id: int):
        db = get_db()
        _ensure(db)
        channel = (request.args.get("channel") or "history").strip()
        try:
            ctl = EncounterController(db, session_id)
        except ValueError:
            flash("Encounter not found", "error")
            return redirect(url_for("ckp_encounter_home"))
        if channel != ctl.ebs.get("channel"):
            ctl.set_channel(channel if channel in ("history", "examination", "investigations", "summary", "plan") else "history")
        snap = ctl.snapshot()
        symptoms = [
            e for e in repo.list_entities(db, entity_type="symptom", lifecycle="active")
        ]
        # Findings that can be entered as Ix results (investigation_finding entities)
        findings = repo.list_entities(db, entity_type="investigation_finding", lifecycle="active")
        return render_template(
            "ckp/encounter_workspace.html",
            snap=snap,
            ebs=snap["ebs"],
            channel=snap["ebs"].get("channel") or "history",
            symptoms=symptoms,
            findings=findings,
            explain=snap["explainability"],
        )

    @app.route("/clinical-encounter/<int:session_id>/intake", methods=["POST"])
    @login_required
    def ckp_encounter_intake(session_id: int):
        db = get_db()
        ctl = EncounterController(db, session_id)
        codes = request.form.getlist("symptom_codes")
        free = (request.form.get("free_text") or "").strip()
        complaints = list(codes)
        if free:
            complaints.append(free)
        ctl.intake(complaints)
        return redirect(url_for("ckp_encounter_workspace", session_id=session_id, channel="history"))

    @app.route("/clinical-encounter/<int:session_id>/answer", methods=["POST"])
    @login_required
    def ckp_encounter_answer(session_id: int):
        db = get_db()
        ctl = EncounterController(db, session_id)
        q = request.form.get("question_code") or ""
        polarity = request.form.get("polarity") or "present"
        value = (request.form.get("value") or "").strip() or None
        ctl.answer_question(q, polarity, value)
        return redirect(url_for("ckp_encounter_workspace", session_id=session_id, channel="history"))

    @app.route("/clinical-encounter/<int:session_id>/exam", methods=["POST"])
    @login_required
    def ckp_encounter_exam(session_id: int):
        db = get_db()
        ctl = EncounterController(db, session_id)
        ctl.record_exam(
            request.form.get("sign_code") or "",
            request.form.get("polarity") or "present",
            (request.form.get("value") or "").strip() or None,
        )
        return redirect(url_for("ckp_encounter_workspace", session_id=session_id, channel="examination"))

    @app.route("/clinical-encounter/<int:session_id>/order-ix", methods=["POST"])
    @login_required
    def ckp_encounter_order_ix(session_id: int):
        db = get_db()
        ctl = EncounterController(db, session_id)
        ctl.order_investigation(request.form.get("ix_code") or "")
        return redirect(url_for("ckp_encounter_workspace", session_id=session_id, channel="investigations"))

    @app.route("/clinical-encounter/<int:session_id>/result", methods=["POST"])
    @login_required
    def ckp_encounter_result(session_id: int):
        db = get_db()
        ctl = EncounterController(db, session_id)
        ctl.record_result(
            request.form.get("finding_code") or "",
            request.form.get("polarity") or "present",
            (request.form.get("value") or "").strip() or None,
        )
        return redirect(url_for("ckp_encounter_workspace", session_id=session_id, channel="investigations"))

    @app.route("/clinical-encounter/<int:session_id>/summary", methods=["POST"])
    @login_required
    def ckp_encounter_summary(session_id: int):
        db = get_db()
        ctl = EncounterController(db, session_id)
        ctl.save_summary_edits(
            {
                "narrative_draft": request.form.get("narrative_draft"),
                "assessment_note": request.form.get("assessment_note"),
            }
        )
        return redirect(url_for("ckp_encounter_workspace", session_id=session_id, channel="summary"))

    @app.route("/clinical-encounter/<int:session_id>/plan", methods=["POST"])
    @login_required
    def ckp_encounter_plan(session_id: int):
        db = get_db()
        ctl = EncounterController(db, session_id)
        ctl.save_plan_edits(
            {
                "plan_text": request.form.get("plan_text"),
                "follow_up_text": request.form.get("follow_up_text"),
            }
        )
        return redirect(url_for("ckp_encounter_workspace", session_id=session_id, channel="plan"))

    @app.route("/clinical-encounter/<int:session_id>/regen-narrative", methods=["POST"])
    @login_required
    def ckp_encounter_regen(session_id: int):
        db = get_db()
        ctl = EncounterController(db, session_id)
        ctl.regen_narrative()
        return redirect(url_for("ckp_encounter_workspace", session_id=session_id, channel="summary"))

    # --- Knowledge authoring (Phase 1) ---
    @app.route("/ckp/knowledge/")
    @login_required
    @roles_required("admin", "hod", "specialist", "consultant")
    def ckp_knowledge_home():
        db = get_db()
        _ensure(db)
        return render_template(
            "ckp/knowledge_home.html",
            domains=repo.list_domains(db),
            releases=repo.list_releases(db),
            validation=validate_knowledge(db),
            entity_counts=validate_knowledge(db)["counts"],
        )

    @app.route("/ckp/knowledge/seed-demo", methods=["POST"])
    @login_required
    @roles_required("admin", "hod")
    def ckp_seed_demo():
        db = get_db()
        init_ckp_schema(db)
        result = seed_demo_gastroenterology(db, force=True)
        db.commit()
        flash(f"Demo knowledge seeded: {result}", "success")
        return redirect(url_for("ckp_knowledge_home"))

    @app.route("/clinical-encounter/<int:session_id>/autosave", methods=["POST"])
    @login_required
    def ckp_encounter_autosave(session_id: int):
        """Continuous channel sync — no Run AI button; persists EBS edits."""
        from flask import jsonify
        db = get_db()
        try:
            ctl = EncounterController(db, session_id)
        except ValueError:
            return jsonify({"ok": False, "error": "not_found"}), 404
        channel = (request.form.get("channel") or request.json.get("channel") if request.is_json else None) or ctl.ebs.get("channel")
        if request.is_json:
            data = request.get_json(silent=True) or {}
            if data.get("summary_edits"):
                ctl.save_summary_edits(data["summary_edits"])
            if data.get("plan_edits"):
                ctl.save_plan_edits(data["plan_edits"])
            if data.get("channel"):
                ctl.set_channel(data["channel"])
        else:
            if channel in ("history", "examination", "investigations", "summary", "plan"):
                ctl.set_channel(channel)
            if request.form.get("narrative_draft") is not None:
                ctl.save_summary_edits({"narrative_draft": request.form.get("narrative_draft")})
            if request.form.get("plan_text") is not None:
                ctl.save_plan_edits({"plan_text": request.form.get("plan_text")})
        snap = ctl.snapshot()
        return jsonify({"ok": True, "updated_at": snap["ebs"].get("updated_at"), "channel": snap["ebs"].get("channel")})
