"""Flask routes for Clinical Intelligence Platform."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from clinical_intelligence import (
    consultation_engine,
    education_engine,
    encounter_service,
    evidence_service,
    exam_engine,
    history_engine,
    interpretation_engine,
    knowledge_importer,
    research_engine,
)
from clinical_intelligence import knowledge_loader as kl
from clinical_intelligence.ai_assist import ai_config
from clinical_intelligence.modules.history_bridge import resolve_ci_complaint


def register_clinical_intelligence_routes(app, *, get_db, login_required, roles_required=None):
    """Register /clinical-intel/* routes. Auth via existing login_required."""

    _roles = roles_required

    def _uid():
        return session.get("user_id")

    def _can_manage_knowledge():
        role = session.get("role") or ""
        return role in {"admin", "hod", "specialist"}

    def _nav(enc):
        return {
            "history": url_for("ci_history", encounter_id=enc["id"]),
            "exam": url_for("ci_exam", encounter_id=enc["id"]),
            "ix": url_for("ci_investigations", encounter_id=enc["id"]),
            "consult": url_for("ci_consult", encounter_id=enc["id"]),
            "teach": url_for("ci_teach", encounter_id=enc["id"]),
            "research": url_for("ci_research", encounter_id=enc["id"]),
        }

    def _ward_context(db, ward_patient_id: int | None):
        """Optional ward patient link for CI encounters (no answer sync)."""
        if not ward_patient_id:
            return None, None, None
        wp = db.execute(
            "SELECT * FROM ward_patient WHERE id = ?", (ward_patient_id,)
        ).fetchone()
        if not wp:
            return None, None, None
        label = (wp["patient_name"] or "").strip() or None
        if wp["mrn"]:
            label = f"{label} · MRN {wp['mrn']}" if label else f"MRN {wp['mrn']}"
        return ward_patient_id, label, wp

    @app.route("/clinical-intel/")
    @login_required
    def ci_home():
        db = get_db()
        encounters = encounter_service.list_encounters(db)
        complaints = kl.load_complaint_index()
        version = evidence_service.knowledge_version_info()
        return render_template(
            "clinical_intelligence/home.html",
            encounters=encounters,
            complaints=complaints,
            version=version,
            ai=ai_config(),
            can_manage_knowledge=_can_manage_knowledge(),
        )

    @app.route("/clinical-intel/new", methods=["GET", "POST"])
    @login_required
    def ci_new_encounter():
        complaints = kl.load_complaint_index()
        db = get_db()
        ward_raw = request.values.get("ward_patient_id")
        try:
            ward_id = int(ward_raw) if ward_raw else None
        except (TypeError, ValueError):
            ward_id = None
        ward_id, ward_label, wp = _ward_context(db, ward_id)
        suggested = resolve_ci_complaint(
            request.values.get("suggest_complaint"),
            has_template=kl.load_history_template,
        )

        if request.method == "POST":
            code = (request.form.get("complaint_code") or "").strip()
            label = (request.form.get("patient_label") or "").strip() or ward_label
            post_ward = ward_id
            if not code or not kl.load_history_template(code):
                flash("Select a complaint that has a history template.", "error")
                return render_template(
                    "clinical_intelligence/new.html",
                    complaints=complaints,
                    ward_patient_id=post_ward,
                    ward_patient=wp,
                    patient_label=label,
                    suggested_complaint=suggested or code,
                )
            enc = encounter_service.create_encounter(
                db,
                complaint_code=code,
                created_by=_uid(),
                patient_label=label,
                ward_patient_id=post_ward,
            )
            flash(
                "Encounter draft created"
                + (" (linked to ward patient)." if post_ward else "."),
                "success",
            )
            return redirect(url_for("ci_history", encounter_id=enc["id"]))

        return render_template(
            "clinical_intelligence/new.html",
            complaints=complaints,
            ward_patient_id=ward_id,
            ward_patient=wp,
            patient_label=ward_label,
            suggested_complaint=suggested,
        )

    def _save_history_answer(db, enc, *, qid: str, answer: str, section_key: str | None):
        library = kl.load_question_library()
        q = library.get(qid) or {}
        encounter_service.save_answer(
            db,
            enc["id"],
            question_id=qid,
            answer_text=answer,
            dedupe_key=q.get("dedupe_key"),
            section_key=section_key or q.get("section_key"),
        )
        answers = encounter_service.list_answers(db, enc["id"])
        encounter_service.save_draft(
            db,
            enc["id"],
            {"answers": {a["question_id"]: a.get("answer_text") for a in answers}},
        )
        amap = {a["question_id"]: a.get("answer_text") for a in answers}
        stop = history_engine.evaluate_stop_rules(enc["complaint_code"], amap)
        if stop:
            encounter_service.touch_encounter(db, enc["id"], urgency_flag="emergency")
        return answers, stop

    def _history_payload(enc, answers, *, focus_qid: str | None = None):
        board = history_engine.board_state(
            enc["complaint_code"], answers, focus_qid=focus_qid
        )
        coach = education_engine.coach_panel(
            enc["complaint_code"],
            focus_qid=board.get("focus_qid"),
            answers=answers,
        )
        return {"board": board, "coach": coach, "exam_url": url_for("ci_exam", encounter_id=enc["id"])}

    @app.route("/clinical-intel/<int:encounter_id>/history", methods=["GET", "POST"])
    @login_required
    def ci_history(encounter_id):
        db = get_db()
        enc = encounter_service.get_encounter(db, encounter_id)
        if not enc:
            flash("Encounter not found.", "error")
            return redirect(url_for("ci_home"))

        if request.method == "POST":
            qid = (request.form.get("question_id") or "").strip()
            answer = (request.form.get("answer_text") or "").strip()
            section_key = (request.form.get("section_key") or "").strip() or None
            if qid and answer:
                _answers, stop = _save_history_answer(
                    db, enc, qid=qid, answer=answer, section_key=section_key
                )
                for s in stop:
                    if s.get("message"):
                        flash(s["message"], "error")
            return redirect(url_for("ci_history", encounter_id=encounter_id))

        answers = encounter_service.list_answers(db, encounter_id)
        payload = _history_payload(enc, answers)
        return render_template(
            "clinical_intelligence/history.html",
            enc=enc,
            board=payload["board"],
            coach=payload["coach"],
            state=history_engine.next_questions(enc["complaint_code"], answers, limit=1),
            ci_tabs=_nav(enc),
            history_api={
                "state": url_for("ci_history_state", encounter_id=encounter_id),
                "answer": url_for("ci_history_answer", encounter_id=encounter_id),
            },
        )

    @app.route("/clinical-intel/<int:encounter_id>/history/state.json")
    @login_required
    def ci_history_state(encounter_id):
        db = get_db()
        enc = encounter_service.get_encounter(db, encounter_id)
        if not enc:
            return jsonify({"error": "not_found"}), 404
        focus = (request.args.get("focus") or "").strip() or None
        answers = encounter_service.list_answers(db, encounter_id)
        return jsonify(_history_payload(enc, answers, focus_qid=focus))

    @app.route("/clinical-intel/<int:encounter_id>/history/answer.json", methods=["POST"])
    @login_required
    def ci_history_answer(encounter_id):
        db = get_db()
        enc = encounter_service.get_encounter(db, encounter_id)
        if not enc:
            return jsonify({"error": "not_found"}), 404
        data = request.get_json(silent=True) or {}
        qid = (data.get("question_id") or request.form.get("question_id") or "").strip()
        answer = (data.get("answer_text") or request.form.get("answer_text") or "").strip()
        section_key = (data.get("section_key") or request.form.get("section_key") or "").strip() or None
        advance = data.get("advance", True)
        if not qid or not answer:
            return jsonify({"error": "question_id and answer_text required"}), 400
        answers, stop = _save_history_answer(
            db, enc, qid=qid, answer=answer, section_key=section_key
        )
        # Advance focus to next pending unless client pins focus
        focus = None
        if not advance:
            focus = qid
        payload = _history_payload(enc, answers, focus_qid=focus)
        payload["stop_rules"] = [
            {"id": s.get("id"), "action": s.get("action"), "message": s.get("message")}
            for s in stop
        ]
        return jsonify(payload)

    @app.route("/clinical-intel/<int:encounter_id>/exam", methods=["GET", "POST"])
    @login_required
    def ci_exam(encounter_id):
        db = get_db()
        enc = encounter_service.get_encounter(db, encounter_id)
        if not enc:
            flash("Encounter not found.", "error")
            return redirect(url_for("ci_home"))

        plan = exam_engine.exam_plan(enc["complaint_code"])

        if request.method == "POST":
            if not plan.get("available"):
                flash("No exam template for this complaint.", "error")
                return redirect(url_for("ci_exam", encounter_id=encounter_id))
            for sys in plan.get("systems") or []:
                for finding in sys.get("findings") or []:
                    code = finding["code"]
                    status = (request.form.get(f"status_{code}") or "not_examined").strip()
                    note = (request.form.get(f"note_{code}") or "").strip() or None
                    if status != "not_examined" or note:
                        encounter_service.save_finding(
                            db,
                            encounter_id,
                            sign_code=code,
                            status=status,
                            system_key=sys.get("key"),
                            note=note,
                        )
            flash("Examination findings saved.", "success")
            return redirect(url_for("ci_exam", encounter_id=encounter_id))

        findings = encounter_service.list_findings(db, encounter_id)
        by_code = {f["sign_code"]: f for f in findings}
        summary = exam_engine.exam_status_summary(plan, findings)
        return render_template(
            "clinical_intelligence/exam.html",
            enc=enc,
            plan=plan,
            by_code=by_code,
            summary=summary,
            ci_tabs=_nav(enc),
        )

    @app.route("/clinical-intel/<int:encounter_id>/investigations", methods=["GET", "POST"])
    @login_required
    def ci_investigations(encounter_id):
        db = get_db()
        enc = encounter_service.get_encounter(db, encounter_id)
        if not enc:
            flash("Encounter not found.", "error")
            return redirect(url_for("ci_home"))

        vocab = interpretation_engine.result_vocab(enc["complaint_code"])
        if request.method == "POST":
            code = (request.form.get("investigation_code") or "").strip()
            result = (request.form.get("result_label") or "").strip()
            note = (request.form.get("note") or "").strip() or None
            if code and result:
                encounter_service.save_ix_result(
                    db,
                    encounter_id,
                    investigation_code=code,
                    result_label=result,
                    note=note,
                )
                flash("Investigation result saved (categorical).", "success")
            return redirect(url_for("ci_investigations", encounter_id=encounter_id))

        answers = encounter_service.list_answers(db, encounter_id)
        findings = encounter_service.list_findings(db, encounter_id)
        # Refresh linked ward labs into ward:-prefixed CI IX rows (never wipe clinician data)
        from gi_platform import lab_propagation
        if enc.get("ward_patient_id"):
            try:
                lab_propagation.sync_labs_to_ci_encounters(
                    db, ward_patient_id=int(enc["ward_patient_id"]),
                )
            except Exception:
                pass
        all_ix = encounter_service.list_ix_results(db, encounter_id)
        ix_for_engine = [
            r for r in all_ix
            if not str(r.get("investigation_code") or "").startswith("ward:")
        ]
        result = consultation_engine.run_consultation(
            enc["complaint_code"],
            answers=answers,
            findings=findings,
            ix_results=ix_for_engine,
            urgency_flag=enc.get("urgency_flag"),
            include_ai=False,
            patient_label=enc.get("patient_label"),
        )
        ward_labs = lab_propagation.labs_for_encounter(db, enc)
        clinician_saved = [
            r for r in all_ix
            if not str(r.get("investigation_code") or "").startswith("ward:")
        ]
        return render_template(
            "clinical_intelligence/investigations.html",
            enc=enc,
            vocab=vocab,
            saved=clinician_saved,
            ward_labs=ward_labs,
            result=result,
            ci_tabs=_nav(enc),
        )

    @app.route("/clinical-intel/<int:encounter_id>/consult")
    @login_required
    def ci_consult(encounter_id):
        db = get_db()
        enc = encounter_service.get_encounter(db, encounter_id)
        if not enc:
            flash("Encounter not found.", "error")
            return redirect(url_for("ci_home"))

        answers = encounter_service.list_answers(db, encounter_id)
        findings = encounter_service.list_findings(db, encounter_id)
        from gi_platform import lab_propagation
        if enc.get("ward_patient_id"):
            try:
                lab_propagation.sync_labs_to_ci_encounters(
                    db, ward_patient_id=int(enc["ward_patient_id"]),
                )
            except Exception:
                pass
        ix_results = encounter_service.list_ix_results(db, encounter_id)
        # Interpretation uses clinician categorical rows only (ward: numeric mirrors are display/context)
        ix_for_engine = [
            r for r in ix_results
            if not str(r.get("investigation_code") or "").startswith("ward:")
        ]
        result = consultation_engine.run_consultation(
            enc["complaint_code"],
            answers=answers,
            findings=findings,
            ix_results=ix_for_engine,
            patient_label=enc.get("patient_label"),
            urgency_flag=enc.get("urgency_flag"),
            include_ai=True,
        )
        ward_labs = lab_propagation.labs_for_encounter(db, enc)
        if ward_labs:
            labs_block = lab_propagation.format_labs_block(ward_labs)
            doc = (result.get("documentation_text") or "").rstrip()
            if labs_block and labs_block not in doc:
                result["documentation_text"] = (doc + "\n\n" + labs_block).strip()
        encounter_service.save_summary(
            db,
            encounter_id,
            {
                "diagnoses": (result.get("reasoning") or {}).get("diagnoses"),
                "matched_patterns": (result.get("reasoning") or {}).get("matched_pattern_ids"),
                "scoring": result.get("scoring"),
                "urgency": enc.get("urgency_flag"),
                "knowledge_version": (result.get("knowledge_version") or {}).get("knowledge_version"),
                "ward_lab_count": len(ward_labs),
            },
        )
        # Log only real AI calls — offline fallback on every GET would spam ci_ai_assist_log.
        ai = result.get("ai_assist") or {}
        if ai and ai.get("mode") not in (None, "offline_rules", "disabled"):
            db.execute(
                """
                INSERT INTO ci_ai_assist_log (encounter_id, mode, payload_json, created_by, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (
                    encounter_id,
                    ai.get("mode"),
                    json.dumps(
                        {
                            "disclaimer": ai.get("disclaimer"),
                            "diagnostic_authority": False,
                        },
                        ensure_ascii=False,
                    ),
                    _uid(),
                ),
            )
            db.commit()
        return render_template(
            "clinical_intelligence/consult.html",
            enc=enc,
            result=result,
            ward_labs=ward_labs,
            ci_tabs=_nav(enc),
        )

    @app.route("/clinical-intel/<int:encounter_id>/export-to-ward", methods=["POST"])
    @login_required
    def ci_export_to_ward(encounter_id):
        """Explicit one-way export: CI consultation text → ward HPI / clinical note."""
        from clinical_intelligence.modules.history_bridge import export_ci_summary_to_ward

        db = get_db()
        enc = encounter_service.get_encounter(db, encounter_id)
        if not enc:
            flash("Encounter not found.", "error")
            return redirect(url_for("ci_home"))
        if not enc.get("ward_patient_id"):
            flash(
                "Link a ward patient first (start CI from ward Clinical workflow). "
                "CI remains canonical Bates; ward is the operational chart — export is opt-in only.",
                "error",
            )
            return redirect(url_for("ci_consult", encounter_id=encounter_id))

        answers = encounter_service.list_answers(db, encounter_id)
        findings = encounter_service.list_findings(db, encounter_id)
        ix_results = encounter_service.list_ix_results(db, encounter_id)
        result = consultation_engine.run_consultation(
            enc["complaint_code"],
            answers=answers,
            findings=findings,
            ix_results=ix_results,
            patient_label=enc.get("patient_label"),
            urgency_flag=enc.get("urgency_flag"),
            include_ai=False,
        )
        target = (request.form.get("target") or "both").strip()
        try:
            info = export_ci_summary_to_ward(
                db,
                encounter=dict(enc),
                documentation_text=result.get("documentation_text") or "",
                target=target,
                user_id=_uid(),
            )
            flash(
                f"Exported CI summary to ward chart ({info['target']}, {info['chars']} chars). "
                "Answers were not dual-written — ward narrative/note only.",
                "success",
            )
            return redirect(
                url_for("ward_patient_view", ward_patient_id=info["ward_patient_id"])
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("ci_consult", encounter_id=encounter_id))

    @app.route("/clinical-intel/<int:encounter_id>/teach")
    @login_required
    def ci_teach(encounter_id):
        db = get_db()
        enc = encounter_service.get_encounter(db, encounter_id)
        if not enc:
            flash("Encounter not found.", "error")
            return redirect(url_for("ci_home"))
        answers = encounter_service.list_answers(db, encounter_id)
        findings = encounter_service.list_findings(db, encounter_id)
        result = consultation_engine.run_consultation(
            enc["complaint_code"],
            answers=answers,
            findings=findings,
            include_ai=False,
            urgency_flag=enc.get("urgency_flag"),
        )
        return render_template(
            "clinical_intelligence/teach.html",
            enc=enc,
            education=result.get("education") or {},
            scoring=result.get("scoring") or {},
            ci_tabs=_nav(enc),
        )

    @app.route("/clinical-intel/<int:encounter_id>/research", methods=["GET", "POST"])
    @login_required
    def ci_research(encounter_id):
        db = get_db()
        enc = encounter_service.get_encounter(db, encounter_id)
        if not enc:
            flash("Encounter not found.", "error")
            return redirect(url_for("ci_home"))

        if request.method == "POST":
            title = (request.form.get("title") or "").strip()
            hypothesis = (request.form.get("hypothesis") or "").strip()
            if title and hypothesis:
                research_engine.save_research_item(
                    db,
                    encounter_id=encounter_id,
                    title=title,
                    hypothesis=hypothesis,
                    kind="hypothesis",
                    created_by=_uid(),
                )
                flash("Research item saved.", "success")
            return redirect(url_for("ci_research", encounter_id=encounter_id))

        answers = encounter_service.list_answers(db, encounter_id)
        findings = encounter_service.list_findings(db, encounter_id)
        result = consultation_engine.run_consultation(
            enc["complaint_code"],
            answers=answers,
            findings=findings,
            include_ai=False,
            urgency_flag=enc.get("urgency_flag"),
        )
        saved = research_engine.list_research_items(db, encounter_id=encounter_id)
        return render_template(
            "clinical_intelligence/research.html",
            enc=enc,
            research=result.get("research") or {},
            saved=saved,
            ci_tabs=_nav(enc),
        )

    @app.route("/clinical-intel/knowledge", methods=["GET", "POST"])
    @login_required
    def ci_knowledge_admin():
        if not _can_manage_knowledge():
            flash("Knowledge admin requires admin/hod/specialist.", "error")
            return redirect(url_for("ci_home"))
        db = get_db()
        version = evidence_service.knowledge_version_info()
        tree = knowledge_importer.validate_tree()
        events = evidence_service.list_knowledge_events(db)

        if request.method == "POST":
            action = (request.form.get("action") or "").strip()
            if action == "reload":
                evidence_service.reload_knowledge(db=db, reason="admin_ui")
                flash("Knowledge cache reloaded.", "success")
                return redirect(url_for("ci_knowledge_admin"))
            if action == "validate":
                flash(
                    f"Validation {'OK' if tree['ok'] else 'FAILED'} — {tree['count']} packs checked.",
                    "success" if tree["ok"] else "error",
                )
                return redirect(url_for("ci_knowledge_admin"))
            if action == "import":
                f = request.files.get("pack_file")
                dest_rel = (request.form.get("dest_relative") or "").strip()
                dry = bool(request.form.get("dry_run"))
                if not f or not dest_rel:
                    flash("File and destination path required.", "error")
                    return redirect(url_for("ci_knowledge_admin"))
                suffix = Path(f.filename or "pack.json").suffix or ".json"
                fd, tmp = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                try:
                    f.save(tmp)
                    result = knowledge_importer.install_pack(
                        Path(tmp), dest_relative=dest_rel, dry_run=dry
                    )
                    evidence_service.record_import_event(db, result=result, user_id=_uid())
                    if result.get("ok") and (result.get("installed") or dry):
                        flash(
                            f"Import {'dry-run OK' if dry else 'installed'} → {result.get('dest')}",
                            "success",
                        )
                    else:
                        flash(
                            "Import failed: " + "; ".join(result.get("errors") or ["unknown"]),
                            "error",
                        )
                finally:
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                return redirect(url_for("ci_knowledge_admin"))

        return render_template(
            "clinical_intelligence/knowledge_admin.html",
            version=version,
            tree=tree,
            events=events,
            ai=ai_config(),
        )

    @app.route("/clinical-intel/<int:encounter_id>")
    @login_required
    def ci_encounter(encounter_id):
        return redirect(url_for("ci_history", encounter_id=encounter_id))
