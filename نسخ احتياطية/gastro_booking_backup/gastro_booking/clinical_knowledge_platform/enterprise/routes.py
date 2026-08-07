"""Enterprise routes (Phase 8)."""

from __future__ import annotations

from flask import flash, redirect, render_template, request, session, url_for

from clinical_knowledge_platform.enterprise import service as ent_svc
from clinical_knowledge_platform.schema import init_ckp_schema


def register_enterprise_routes(app, *, get_db, login_required, roles_required=None):
    roles_required = roles_required or (lambda *roles: login_required)

    @app.route("/ckp/enterprise/")
    @login_required
    @roles_required("admin", "hod")
    def ckp_enterprise_home():
        db = get_db()
        init_ckp_schema(db)
        tenant = ent_svc.ensure_default_tenant(db)
        return render_template(
            "ckp/enterprise_home.html",
            tenant=tenant,
            departments=ent_svc.list_departments(db, tenant["id"]),
            integrations=ent_svc.list_integrations(db, tenant["id"]),
            obs=ent_svc.observability_snapshot(db),
            perms_admin=ent_svc.role_permissions(db, "admin"),
        )

    @app.route("/ckp/enterprise/integration/<int:endpoint_id>/health", methods=["POST"])
    @login_required
    @roles_required("admin", "hod")
    def ckp_integration_health(endpoint_id: int):
        db = get_db()
        init_ckp_schema(db)
        health = ent_svc.check_integration_health(db, endpoint_id)
        ent_svc.audit(
            db,
            action="integration_health_check",
            actor_id=session.get("user_id"),
            object_kind="integration",
            object_id=str(endpoint_id),
            detail=health,
        )
        flash(f"Health: {health}", "success" if health.get("ok") else "error")
        return redirect(url_for("ckp_enterprise_home"))

    @app.route("/ckp/enterprise/jobs/enqueue", methods=["POST"])
    @login_required
    @roles_required("admin", "hod")
    def ckp_job_enqueue():
        db = get_db()
        init_ckp_schema(db)
        jid = ent_svc.enqueue_job(db, request.form.get("job_type") or "demo_job", {"note": request.form.get("note")})
        flash(f"Job #{jid} queued", "success")
        return redirect(url_for("ckp_enterprise_home"))

    @app.route("/ckp/enterprise/jobs/process", methods=["POST"])
    @login_required
    @roles_required("admin", "hod")
    def ckp_job_process():
        db = get_db()
        init_ckp_schema(db)
        result = ent_svc.process_next_job(db)
        flash(f"Processed: {result}" if result else "No queued jobs", "success")
        return redirect(url_for("ckp_enterprise_home"))

    @app.route("/ckp/enterprise/notify", methods=["POST"])
    @login_required
    @roles_required("admin", "hod")
    def ckp_notify():
        db = get_db()
        init_ckp_schema(db)
        nid = ent_svc.notify(
            db,
            title=request.form.get("title") or "Test notification",
            body=request.form.get("body") or "",
            recipient=request.form.get("recipient"),
        )
        flash(f"Notification #{nid} sent (in-app stub)", "success")
        return redirect(url_for("ckp_enterprise_home"))

    @app.route("/ckp/enterprise/search")
    @login_required
    def ckp_enterprise_search():
        db = get_db()
        init_ckp_schema(db)
        q = request.args.get("q") or ""
        results = ent_svc.search(db, q) if q else []
        return render_template("ckp/enterprise_search.html", q=q, results=results)

    @app.route("/ckp/api/v1/health")
    def ckp_api_health():
        from flask import jsonify
        db = get_db()
        init_ckp_schema(db)
        return jsonify({"ok": True, "service": "ckp", "observability": ent_svc.observability_snapshot(db)})

    @app.route("/ckp/api/v1/i18n/<locale>/<path:key>")
    def ckp_api_i18n(locale: str, key: str):
        from flask import jsonify
        db = get_db()
        init_ckp_schema(db)
        return jsonify({"key": key, "locale": locale, "value": ent_svc.t(db, key, locale)})
