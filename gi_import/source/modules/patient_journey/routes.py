"""Patient Journey HTTP routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors

from . import services

bp = Blueprint("patient_journey", __name__, url_prefix="/patient-journey")


@bp.route("/patients/<int:patient_id>/timeline", methods=["GET"])
@login_required
@handle_service_errors
def patient_timeline(patient_id: int):
    return jsonify({"timeline": services.get_patient_timeline(current_user, patient_id)})


@bp.route("/patients/<int:patient_id>", methods=["GET"])
@login_required
@handle_service_errors
def patient_journey(patient_id: int):
    encounter_id = request.args.get("encounter_id", type=int)
    return jsonify(services.get_journey_view(current_user, patient_id, encounter_id=encounter_id))


@bp.route("/encounters/<int:encounter_id>/follow-up", methods=["POST"])
@login_required
@handle_service_errors
def create_follow_up(encounter_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        plan = services.create_follow_up_plan(
            current_user,
            encounter_id,
            related_condition=payload.get("related_condition"),
            recommended_interval_days=payload.get("recommended_interval_days"),
            recommended_interval_text=payload.get("recommended_interval_text"),
            reason=payload.get("reason"),
            responsible_physician_id=payload.get("responsible_physician_id"),
        )
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"follow_up_plan": services.follow_up_to_dict(plan)}), 201


@bp.route("/follow-up/<int:plan_id>/status", methods=["POST"])
@login_required
@handle_service_errors
def update_follow_up_status(plan_id: int):
    payload = request.get_json(silent=True) or {}
    plan = services.update_follow_up_status(current_user, plan_id, status=payload.get("status", ""))
    return jsonify({"follow_up_plan": services.follow_up_to_dict(plan)})


@bp.route("/follow-up/<int:plan_id>/events", methods=["POST"])
@login_required
@handle_service_errors
def record_follow_up_event(plan_id: int):
    payload = request.get_json(silent=True) or {}
    event = services.record_follow_up_event(
        current_user,
        plan_id,
        clinical_update=payload.get("clinical_update"),
        new_findings=payload.get("new_findings"),
        symptoms_status=payload.get("symptoms_status"),
        investigation_updates=payload.get("investigation_updates"),
        physician_assessment=payload.get("physician_assessment"),
        next_action=payload.get("next_action"),
        encounter_id=payload.get("encounter_id"),
    )
    return jsonify({"event": services.event_to_dict(event)}), 201


@bp.route("/encounters/<int:encounter_id>/outcome", methods=["POST"])
@login_required
@handle_service_errors
def record_outcome(encounter_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        record = services.record_outcome(
            current_user,
            encounter_id,
            outcome=payload.get("outcome", ""),
            notes=payload.get("notes"),
            follow_up_plan_id=payload.get("follow_up_plan_id"),
            follow_up_event_id=payload.get("follow_up_event_id"),
        )
    except (ValidationError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"outcome": services.outcome_to_dict(record)}), 201


@bp.route("/encounters/<int:encounter_id>/summary/generate", methods=["POST"])
@login_required
@handle_service_errors
def generate_summary(encounter_id: int):
    draft = services.generate_summary_draft(current_user, encounter_id)
    return jsonify({"summary": services.summary_to_dict(draft)}), 201


@bp.route("/summaries/<int:draft_id>/approve", methods=["POST"])
@login_required
@handle_service_errors
def approve_summary(draft_id: int):
    payload = request.get_json(silent=True) or {}
    draft = services.approve_summary(current_user, draft_id, approved_text=payload.get("approved_text"))
    return jsonify({"summary": services.summary_to_dict(draft)})


@bp.route("/summaries/<int:draft_id>/reject", methods=["POST"])
@login_required
@handle_service_errors
def reject_summary(draft_id: int):
    payload = request.get_json(silent=True) or {}
    draft = services.reject_summary(current_user, draft_id, reason=payload.get("reason"))
    return jsonify({"summary": services.summary_to_dict(draft)})


@bp.route("/encounters/<int:encounter_id>/close", methods=["POST"])
@login_required
@handle_service_errors
def close_encounter(encounter_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        encounter = services.physician_close_encounter(current_user, encounter_id, notes=payload.get("notes"))
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"encounter_id": encounter.id, "status": encounter.status})
