"""Research platform routes (Phase 7)."""

from __future__ import annotations

from flask import flash, redirect, render_template, request, session, url_for

from clinical_knowledge_platform.research import service as res_svc
from clinical_knowledge_platform.schema import init_ckp_schema


def register_research_platform_routes(app, *, get_db, login_required, roles_required=None):
    roles_required = roles_required or (lambda *roles: login_required)

    @app.route("/ckp/research/")
    @login_required
    def ckp_research_home():
        db = get_db()
        init_ckp_schema(db)
        return render_template(
            "ckp/research_home.html",
            stats=res_svc.dashboard_stats(db),
            registries=res_svc.list_registries(db),
            studies=[dict(r) for r in db.execute("SELECT * FROM ckp_research_study ORDER BY id DESC LIMIT 20").fetchall()],
        )

    @app.route("/ckp/research/registry/create", methods=["POST"])
    @login_required
    @roles_required("admin", "hod", "consultant", "specialist")
    def ckp_research_registry_create():
        db = get_db()
        init_ckp_schema(db)
        variables = [
            {"key": "diseases", "source": "timelines.disease"},
            {"key": "encounters", "source": "summary.encounter_count"},
            {"key": "risk", "source": "risk"},
        ]
        reg = res_svc.create_registry(
            db,
            code=(request.form.get("code") or "").strip(),
            label=(request.form.get("label") or "").strip(),
            description=(request.form.get("description") or "").strip(),
            variables=variables,
            inclusion={"note": request.form.get("inclusion") or ""},
            exclusion={"note": request.form.get("exclusion") or ""},
            actor_id=session.get("user_id"),
        )
        flash(f"Registry {reg['code']} created", "success")
        return redirect(url_for("ckp_research_registry", registry_id=reg["id"]))

    @app.route("/ckp/research/registry/<int:registry_id>")
    @login_required
    def ckp_research_registry(registry_id: int):
        db = get_db()
        init_ckp_schema(db)
        reg = res_svc.get_registry(db, registry_id)
        if not reg:
            flash("Registry not found", "error")
            return redirect(url_for("ckp_research_home"))
        cohorts = [dict(r) for r in db.execute(
            "SELECT * FROM ckp_research_cohort WHERE registry_id=? ORDER BY id DESC", (registry_id,)
        ).fetchall()]
        return render_template("ckp/research_registry.html", registry=reg, cohorts=cohorts)

    @app.route("/ckp/research/registry/<int:registry_id>/cohort", methods=["POST"])
    @login_required
    def ckp_research_cohort_create(registry_id: int):
        db = get_db()
        init_ckp_schema(db)
        c = res_svc.create_cohort(
            db,
            registry_id=registry_id,
            code=(request.form.get("code") or "").strip(),
            label=(request.form.get("label") or "").strip(),
            criteria={"inclusion": request.form.get("criteria") or ""},
        )
        flash("Cohort created", "success")
        return redirect(url_for("ckp_research_cohort", cohort_id=c["id"]))

    @app.route("/ckp/research/cohort/<int:cohort_id>")
    @login_required
    def ckp_research_cohort(cohort_id: int):
        db = get_db()
        init_ckp_schema(db)
        cohort = dict(db.execute("SELECT * FROM ckp_research_cohort WHERE id=?", (cohort_id,)).fetchone() or {})
        members = [dict(r) for r in db.execute("SELECT * FROM ckp_research_member WHERE cohort_id=?", (cohort_id,)).fetchall()]
        quality = res_svc.data_quality_report(db, cohort_id)
        survival = res_svc.survival_support_table(db, cohort_id)
        return render_template(
            "ckp/research_cohort.html",
            cohort=cohort,
            members=members,
            quality=quality,
            survival=survival,
        )

    @app.route("/ckp/research/cohort/<int:cohort_id>/enroll", methods=["POST"])
    @login_required
    def ckp_research_enroll(cohort_id: int):
        db = get_db()
        init_ckp_schema(db)
        patient_key = (request.form.get("patient_key") or "").strip()
        cohort = db.execute("SELECT * FROM ckp_research_cohort WHERE id=?", (cohort_id,)).fetchone()
        reg = res_svc.get_registry(db, cohort["registry_id"]) if cohort else None
        try:
            res_svc.enroll_from_longitudinal(
                db,
                cohort_id=cohort_id,
                patient_key=patient_key,
                registry_variables=(reg or {}).get("variables") or [],
            )
            flash("Patient enrolled (de-id token stored)", "success")
        except Exception as e:
            flash(str(e), "error")
        return redirect(url_for("ckp_research_cohort", cohort_id=cohort_id))

    @app.route("/ckp/research/cohort/<int:cohort_id>/export", methods=["POST"])
    @login_required
    @roles_required("admin", "hod", "consultant")
    def ckp_research_export(cohort_id: int):
        db = get_db()
        init_ckp_schema(db)
        result = res_svc.export_dataset(
            db, cohort_id=cohort_id, deidentified=True, actor_id=session.get("user_id")
        )
        flash(f"Export #{result['export_id']} created ({result['n']} rows, de-identified)", "success")
        return redirect(url_for("ckp_research_cohort", cohort_id=cohort_id))

    @app.route("/ckp/research/study/create", methods=["POST"])
    @login_required
    def ckp_research_study_create():
        db = get_db()
        init_ckp_schema(db)
        study = res_svc.create_study(
            db,
            code=(request.form.get("code") or "").strip(),
            title=(request.form.get("title") or "").strip(),
            registry_id=int(request.form["registry_id"]) if request.form.get("registry_id") else None,
            design={
                "inclusion": request.form.get("inclusion") or "",
                "exclusion": request.form.get("exclusion") or "",
                "outcomes": request.form.get("outcomes") or "",
            },
        )
        flash("Study created", "success")
        return redirect(url_for("ckp_research_home"))
