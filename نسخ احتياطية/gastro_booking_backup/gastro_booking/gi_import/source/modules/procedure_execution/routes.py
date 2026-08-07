from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors
from app.modules.procedure_execution import services
from app.modules.procedure_execution.forms import (
    CancelSessionForm,
    ChecklistForm,
    OutcomeForm,
    SedationForm,
    TeamAssignmentForm,
    TimeTrackingForm,
)

bp = Blueprint("procedure_execution", __name__, url_prefix="/procedure-sessions")


@bp.route("/")
@login_required
@handle_service_errors
def list_sessions():
    sessions = services.list_sessions(current_user)
    return render_template("procedure_execution/list.html", sessions=sessions)


@bp.route("/for-procedure/<int:procedure_id>")
@login_required
@handle_service_errors
def open_for_procedure(procedure_id):
    session = services.get_or_create_session(current_user, procedure_id)
    return redirect(url_for("procedure_execution.view_session", session_id=session.id))


@bp.route("/<int:session_id>")
@login_required
@handle_service_errors
def view_session(session_id):
    session = services.get_session(current_user, session_id)
    occupancy = services.list_room_occupancy(current_user, session_id=session.id)
    return render_template(
        "procedure_execution/session.html",
        session=session,
        occupancy=occupancy,
        team_form=TeamAssignmentForm(),
        times_form=TimeTrackingForm(),
        sedation_form=SedationForm(),
        checklist_form=ChecklistForm(),
        outcome_form=OutcomeForm(),
    )


@bp.route("/<int:session_id>/team", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_team(session_id):
    session = services.get_session(current_user, session_id)
    form = TeamAssignmentForm(
        endoscopist_id=str(session.endoscopist_id) if session.endoscopist_id else "",
        assistant_id=str(session.assistant_id) if session.assistant_id else "",
        nurse_id=str(session.nurse_id) if session.nurse_id else "",
        technician_id=str(session.technician_id) if session.technician_id else "",
        anaesthetist_id=str(session.anaesthetist_id) if session.anaesthetist_id else "",
    )
    if form.validate_on_submit():
        try:
            services.update_team(
                current_user,
                session,
                endoscopist_id=int(form.endoscopist_id.data) if form.endoscopist_id.data else None,
                assistant_id=int(form.assistant_id.data) if form.assistant_id.data else None,
                nurse_id=int(form.nurse_id.data) if form.nurse_id.data else None,
                technician_id=int(form.technician_id.data) if form.technician_id.data else None,
                anaesthetist_id=int(form.anaesthetist_id.data) if form.anaesthetist_id.data else None,
                endoscopist_provided=True,
                assistant_provided=True,
                nurse_provided=True,
                technician_provided=True,
                anaesthetist_provided=True,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedure_execution/team.html", form=form, session=session)

        flash("Team assignment updated.", "success")
        return redirect(url_for("procedure_execution.view_session", session_id=session.id))

    return render_template("procedure_execution/team.html", form=form, session=session)


@bp.route("/<int:session_id>/times", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_times(session_id):
    session = services.get_session(current_user, session_id)
    form = TimeTrackingForm(obj=session)
    if form.validate_on_submit():
        try:
            services.update_times(
                current_user,
                session,
                patient_in_at=form.patient_in_at.data,
                procedure_start_at=form.procedure_start_at.data,
                procedure_finish_at=form.procedure_finish_at.data,
                patient_out_at=form.patient_out_at.data,
                patient_in_provided=True,
                procedure_start_provided=True,
                procedure_finish_provided=True,
                patient_out_provided=True,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedure_execution/times.html", form=form, session=session)

        flash("Time tracking updated.", "success")
        return redirect(url_for("procedure_execution.view_session", session_id=session.id))

    return render_template("procedure_execution/times.html", form=form, session=session)


@bp.route("/<int:session_id>/sedation", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_sedation(session_id):
    session = services.get_session(current_user, session_id)
    form = SedationForm(sedation_category=session.sedation_category or "")
    if form.validate_on_submit():
        try:
            services.update_sedation(
                current_user,
                session,
                sedation_category=form.sedation_category.data or None,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedure_execution/sedation.html", form=form, session=session)

        flash("Sedation category updated.", "success")
        return redirect(url_for("procedure_execution.view_session", session_id=session.id))

    return render_template("procedure_execution/sedation.html", form=form, session=session)


@bp.route("/<int:session_id>/checklist", methods=["GET", "POST"])
@login_required
@handle_service_errors
def edit_checklist(session_id):
    session = services.get_session(current_user, session_id)
    form = ChecklistForm(
        consent_confirmed=session.consent_confirmed,
        identity_confirmed=session.identity_confirmed,
        indication_confirmed=session.indication_confirmed,
        anticoagulants_reviewed=session.anticoagulants_reviewed,
    )
    if form.validate_on_submit():
        try:
            services.update_checklist(
                current_user,
                session,
                consent_confirmed=form.consent_confirmed.data,
                identity_confirmed=form.identity_confirmed.data,
                indication_confirmed=form.indication_confirmed.data,
                anticoagulants_reviewed=form.anticoagulants_reviewed.data,
            )
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedure_execution/checklist.html", form=form, session=session)

        flash("Safety checklist updated.", "success")
        return redirect(url_for("procedure_execution.view_session", session_id=session.id))

    return render_template("procedure_execution/checklist.html", form=form, session=session)


@bp.route("/<int:session_id>/outcome", methods=["GET", "POST"])
@login_required
@handle_service_errors
def set_outcome(session_id):
    session = services.get_session(current_user, session_id)
    form = OutcomeForm(outcome=session.outcome or "")
    if form.validate_on_submit():
        try:
            services.set_outcome(current_user, session, outcome=form.outcome.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedure_execution/outcome.html", form=form, session=session)

        flash("Procedure outcome recorded.", "success")
        return redirect(url_for("procedure_execution.view_session", session_id=session.id))

    return render_template("procedure_execution/outcome.html", form=form, session=session)


@bp.route("/<int:session_id>/cancel", methods=["GET", "POST"])
@login_required
@handle_service_errors
def cancel_session(session_id):
    session = services.get_session(current_user, session_id)
    form = CancelSessionForm()
    if form.validate_on_submit():
        try:
            services.cancel_session(current_user, session, reason=form.reason.data)
        except ValidationError as e:
            flash(str(e), "danger")
            return render_template("procedure_execution/cancel.html", form=form, session=session)

        flash("Procedure execution cancelled.", "success")
        return redirect(url_for("procedure_execution.view_session", session_id=session.id))

    return render_template("procedure_execution/cancel.html", form=form, session=session)
