"""Documentation routes (Phase 4)."""

from __future__ import annotations

from flask import flash, redirect, render_template, request, session, url_for

from clinical_knowledge_platform.documentation import service as doc_svc
from clinical_knowledge_platform.schema import init_ckp_schema


def register_documentation_routes(app, *, get_db, login_required, roles_required=None):
    roles_required = roles_required or (lambda *roles: login_required)

    @app.route("/clinical-encounter/<int:session_id>/documents")
    @login_required
    def ckp_documents_list(session_id: int):
        db = get_db()
        init_ckp_schema(db)
        docs = doc_svc.list_documents(db, session_id)
        return render_template(
            "ckp/documents.html",
            session_id=session_id,
            docs=docs,
            doc_types=doc_svc.DOCUMENT_TYPES,
        )

    @app.route("/clinical-encounter/<int:session_id>/documents/generate", methods=["POST"])
    @login_required
    def ckp_documents_generate(session_id: int):
        db = get_db()
        init_ckp_schema(db)
        doc_type = request.form.get("doc_type") or "soap"
        force = request.form.get("force_regen") == "1"
        try:
            doc = doc_svc.create_or_regen_document(
                db,
                session_id=session_id,
                doc_type=doc_type,
                actor_id=session.get("user_id"),
                force_regen=force,
            )
            flash(f"Document {doc_type} draft v{doc['version']} ready", "success")
            return redirect(url_for("ckp_document_view", document_id=doc["id"]))
        except Exception as e:
            flash(str(e), "error")
            return redirect(url_for("ckp_documents_list", session_id=session_id))

    @app.route("/clinical-encounter/<int:session_id>/documents/generate-all", methods=["POST"])
    @login_required
    def ckp_documents_generate_all(session_id: int):
        db = get_db()
        init_ckp_schema(db)
        n = 0
        for dt in doc_svc.DOCUMENT_TYPES:
            try:
                doc_svc.create_or_regen_document(
                    db, session_id=session_id, doc_type=dt, actor_id=session.get("user_id")
                )
                n += 1
            except Exception:
                pass
        flash(f"Generated/updated {n} document drafts from EBS", "success")
        return redirect(url_for("ckp_documents_list", session_id=session_id))

    @app.route("/ckp/documents/<int:document_id>")
    @login_required
    def ckp_document_view(document_id: int):
        db = get_db()
        init_ckp_schema(db)
        doc = db.execute("SELECT * FROM ckp_document WHERE id=?", (document_id,)).fetchone()
        if not doc:
            flash("Document not found", "error")
            return redirect(url_for("ckp_encounter_home"))
        return render_template(
            "ckp/document_view.html",
            doc=dict(doc),
            versions=doc_svc.version_history(db, document_id),
            audit=doc_svc.audit_trail(db, document_id),
        )

    @app.route("/ckp/documents/<int:document_id>/edit", methods=["POST"])
    @login_required
    def ckp_document_edit(document_id: int):
        db = get_db()
        try:
            doc_svc.edit_document(
                db,
                document_id,
                body_text=request.form.get("body_text") or "",
                actor_id=session.get("user_id"),
            )
            flash("Document saved (new version)", "success")
        except Exception as e:
            flash(str(e), "error")
        return redirect(url_for("ckp_document_view", document_id=document_id))

    @app.route("/ckp/documents/<int:document_id>/finalize", methods=["POST"])
    @login_required
    def ckp_document_finalize(document_id: int):
        db = get_db()
        try:
            doc_svc.finalize_document(db, document_id, actor_id=session.get("user_id"))
            flash("Document finalized — physician is final author", "success")
        except Exception as e:
            flash(str(e), "error")
        return redirect(url_for("ckp_document_view", document_id=document_id))
