from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.clinical_history import services
from app.modules.clinical_history.forms import (
    ChiefComplaintForm,
    ConfirmDiagnosisForm,
    FollowUpForm,
    NarrativeSectionForm,
)
from app.modules.clinical_history.models import (
    ALL_NARRATIVE_SECTIONS,
    DiagnosisDefinition,
    HistoryNarrativeSection,
    InvestigationSuggestionRecord,
)
from app.modules.encounters import services as encounter_services

bp = Blueprint("clinical_history", __name__, url_prefix="/clinical-history")


def _wants_json() -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.accept_mimetypes.best == "application/json"
    )


@bp.route("/encounters/<int:encounter_id>")
@login_required
@handle_service_errors
def encounter_hub(encounter_id):
    encounter = encounter_services.get_encounter(current_user, encounter_id)
    session = services.get_or_create_initial_session(current_user, encounter)
    sessions = services.list_sessions_for_encounter(current_user, encounter_id)
    return render_template(
        "clinical_history/encounter_hub.html",
        encounter=encounter,
        session=session,
        sessions=sessions,
    )


@bp.route("/sessions/<int:session_id>")
@login_required
@handle_service_errors
def view_session(session_id):
    session = services.get_session(current_user, session_id)
    encounter = encounter_services.get_encounter(current_user, session.encounter_id)
    narratives = {
        n.section_key: n
        for n in HistoryNarrativeSection.query.filter_by(session_id=session.id, is_archived=False).all()
    }
    differential = services.get_differential_display(current_user, session)
    management = services.get_management_for_session(current_user, session)
    suggestions = InvestigationSuggestionRecord.query.filter_by(session_id=session.id, is_archived=False).all()
    from app.modules.clinical_history.narrative_engine import SECTION_LABELS

    return render_template(
        "clinical_history/session_detail.html",
        session=session,
        encounter=encounter,
        narratives=narratives,
        differential=differential,
        management=management,
        suggestions=suggestions,
        section_labels=SECTION_LABELS,
    )


@bp.route("/sessions/<int:session_id>/complaint", methods=["GET", "POST"])
@login_required
@handle_service_errors
def select_complaint(session_id):
    session = services.get_session(current_user, session_id)
    encounter = encounter_services.get_encounter(current_user, session.encounter_id)
    form = ChiefComplaintForm()
    form.complaint_code.choices = [(c.code, c.name) for c in services.list_complaints(current_user)]

    if form.validate_on_submit():
        services.set_chief_complaint(current_user, session, form.complaint_code.data)
        flash("Chief complaint recorded. Continue with the adaptive interview.", "success")
        return redirect(url_for("clinical_history.interview", session_id=session.id))

    return render_template("clinical_history/complaint.html", form=form, session=session, encounter=encounter)


@bp.route("/sessions/<int:session_id>/interview", methods=["GET", "POST"])
@login_required
@handle_service_errors
def interview(session_id):
    session = services.get_session(current_user, session_id)
    encounter = encounter_services.get_encounter(current_user, session.encounter_id)

    if not session.chief_complaint_code:
        return redirect(url_for("clinical_history.select_complaint", session_id=session.id))

    if request.method == "POST":
        answers = {}
        for key, val in request.form.items():
            if key.startswith("q_"):
                answers[key[2:]] = val
        if answers:
            services.save_answers(current_user, session, answers)
            flash("Answers saved.", "success")

        if "generate_narrative" in request.form:
            _batch, complete, _meta = services.get_interview_batch(current_user, session)
            if not complete:
                flash("Complete all relevant questions before generating narrative.", "warning")
            else:
                services.regenerate_narratives(current_user, session)
                flash("History narrative generated — review and edit before completing.", "success")
                return redirect(url_for("clinical_history.narrative_review", session_id=session.id))

        _batch, complete, _meta = services.get_interview_batch(current_user, session)
        if complete and "continue" in request.form:
            services.regenerate_narratives(current_user, session)
            return redirect(url_for("clinical_history.narrative_review", session_id=session.id))

    batch, complete, meta = services.get_interview_batch(current_user, session)
    return render_template(
        "clinical_history/interview.html",
        session=session,
        encounter=encounter,
        questions=batch,
        interview_complete=complete,
        purpose_hint=meta.get("purpose_hint") if meta else None,
        differential=meta.get("differential") if meta else [],
    )


@bp.route("/sessions/<int:session_id>/narrative", methods=["GET", "POST"])
@login_required
@handle_service_errors
def narrative_review(session_id):
    session = services.get_session(current_user, session_id)
    encounter = encounter_services.get_encounter(current_user, session.encounter_id)

    if request.method == "POST" and "complete" in request.form:
        try:
            services.complete_history(current_user, session)
        except ValidationError as e:
            flash(str(e), "danger")
        else:
            flash("Clinical history completed.", "success")
            return redirect(url_for("clinical_history.view_session", session_id=session.id))

    narratives = {
        n.section_key: n
        for n in HistoryNarrativeSection.query.filter_by(session_id=session.id, is_archived=False).all()
    }
    forms = {}
    for key in ALL_NARRATIVE_SECTIONS:
        f = NarrativeSectionForm(prefix=key)
        row = narratives.get(key)
        if row:
            f.text.data = row.display_text
        forms[key] = f

    if request.method == "POST":
        for key in ALL_NARRATIVE_SECTIONS:
            prefix = f"{key}-"
            text_val = request.form.get(f"{prefix}text")
            if text_val is not None and text_val.strip():
                services.update_narrative_section(current_user, session, key, text_val)

    differential = services.get_differential_display(current_user, session)
    suggestions = InvestigationSuggestionRecord.query.filter_by(session_id=session.id, is_archived=False).all()

    from app.modules.clinical_history.narrative_engine import SECTION_LABELS

    return render_template(
        "clinical_history/narrative_review.html",
        session=session,
        encounter=encounter,
        narratives=narratives,
        section_labels=SECTION_LABELS,
        differential=differential,
        suggestions=suggestions,
    )


@bp.route("/sessions/<int:session_id>/confirm-diagnosis", methods=["GET", "POST"])
@login_required
@handle_service_errors
def confirm_diagnosis(session_id):
    session = services.get_session(current_user, session_id)
    encounter = encounter_services.get_encounter(current_user, session.encounter_id)
    form = ConfirmDiagnosisForm()
    form.diagnosis_code.choices = [
        (d.code, d.name)
        for d in DiagnosisDefinition.query.filter_by(is_archived=False).order_by(DiagnosisDefinition.name).all()
    ]

    if form.validate_on_submit():
        try:
            services.confirm_diagnosis(current_user, session, form.diagnosis_code.data)
        except ValidationError as e:
            flash(str(e), "danger")
        else:
            flash("Diagnosis confirmed. Management guidance is now available.", "success")
            return redirect(url_for("clinical_history.view_session", session_id=session.id))

    management = services.get_management_for_session(current_user, session)
    differential = services.get_differential_display(current_user, session)

    return render_template(
        "clinical_history/confirm_diagnosis.html",
        form=form,
        session=session,
        encounter=encounter,
        differential=differential,
        management=management,
    )


@bp.route("/sessions/<int:session_id>/suggestions/<investigation_code>/accept", methods=["POST"])
@login_required
@handle_service_errors
def accept_suggestion(session_id, investigation_code):
    session = services.get_session(current_user, session_id)
    rec, order_placed = services.accept_suggestion(current_user, session, investigation_code)
    if _wants_json():
        return jsonify(
            {
                "ok": bool(rec and rec.is_accepted),
                "accepted": bool(rec and rec.is_accepted),
                "order_placed": order_placed,
                "code": investigation_code,
            }
        )
    if rec and rec.is_accepted:
        flash("Suggestion marked accepted.", "success")
        if order_placed:
            flash("Investigation order placed for this encounter.", "success")
    else:
        flash("Suggestion could not be updated.", "warning")
    return redirect(request.referrer or url_for("clinical_history.view_session", session_id=session.id))


@bp.route("/sessions/<int:session_id>/suggestions/<investigation_code>/dismiss", methods=["POST"])
@login_required
@handle_service_errors
def dismiss_suggestion(session_id, investigation_code):
    session = services.get_session(current_user, session_id)
    services.dismiss_suggestion(current_user, session, investigation_code)
    if _wants_json():
        return jsonify({"ok": True, "dismissed": True, "code": investigation_code})
    flash("Suggestion dismissed.", "info")
    return redirect(request.referrer or url_for("clinical_history.view_session", session_id=session.id))


@bp.route("/sessions/<int:session_id>/suggestions/accept-all", methods=["POST"])
@login_required
@handle_service_errors
def accept_all_suggestions(session_id):
    session = services.get_session(current_user, session_id)
    pending = InvestigationSuggestionRecord.query.filter_by(
        session_id=session.id, is_archived=False, is_accepted=False, is_dismissed=False
    ).all()
    results = []
    for suggestion in pending:
        rec, order_placed = services.accept_suggestion(
            current_user, session, suggestion.investigation_code
        )
        results.append(
            {
                "code": suggestion.investigation_code,
                "accepted": bool(rec and rec.is_accepted),
                "order_placed": order_placed,
            }
        )
    if _wants_json():
        return jsonify({"ok": True, "results": results})
    flash(f"Accepted {sum(1 for r in results if r['accepted'])} investigation suggestions.", "success")
    return redirect(url_for("clinical_history.view_session", session_id=session.id))


@bp.route("/sessions/<int:session_id>/teaching")
@login_required
@handle_service_errors
def teaching_mode(session_id):
    session = services.get_session(current_user, session_id)
    encounter = encounter_services.get_encounter(current_user, session.encounter_id)
    teaching = services.get_teaching_explanation(current_user, session)
    return render_template(
        "clinical_history/teaching.html",
        session=session,
        encounter=encounter,
        teaching=teaching,
    )


@bp.route("/patients/<int:patient_id>/follow-up", methods=["GET", "POST"])
@login_required
@handle_service_errors
def new_follow_up(patient_id):
    from app.modules.patients import services as patient_services

    patient = patient_services.get_patient(current_user, patient_id)
    form = FollowUpForm()

    if form.validate_on_submit():
        services.create_follow_up(
            current_user,
            patient_id=patient.id,
            narrative_text=form.narrative_text.data,
        )
        flash("Follow-up entry recorded.", "success")
        return redirect(url_for("patients.view_patient", patient_id=patient.id))

    follow_ups = services.list_follow_ups_for_patient(current_user, patient_id)
    return render_template(
        "clinical_history/follow_up.html",
        form=form,
        patient=patient,
        follow_ups=follow_ups,
    )
