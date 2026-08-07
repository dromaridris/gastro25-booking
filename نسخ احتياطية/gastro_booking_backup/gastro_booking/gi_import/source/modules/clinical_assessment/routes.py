"""Clinical Assessment HTTP routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors

from . import services

bp = Blueprint("clinical_assessment", __name__, url_prefix="/clinical-assessment")


@bp.route("/encounters/<int:encounter_id>/generate", methods=["POST"])
@login_required
@handle_service_errors
def generate_assessment(encounter_id: int):
    try:
        run = services.generate_assessment(current_user, encounter_id)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"assessment": services.run_to_dict(run)}), 201


@bp.route("/encounters/<int:encounter_id>", methods=["GET"])
@login_required
@handle_service_errors
def get_encounter_assessment(encounter_id: int):
    return jsonify(services.get_final_assessment(current_user, encounter_id))


@bp.route("/runs/<int:run_id>/suggestions", methods=["GET"])
@login_required
@handle_service_errors
def list_suggestions(run_id: int):
    suggestions = services.list_suggestions(current_user, run_id)
    return jsonify({"suggestions": [services.suggestion_to_dict(s) for s in suggestions]})


@bp.route("/suggestions/<int:suggestion_id>/accept", methods=["POST"])
@login_required
@handle_service_errors
def accept_suggestion(suggestion_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.accept_suggestion(current_user, suggestion_id, notes=payload.get("notes"))
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/suggestions/<int:suggestion_id>/reject", methods=["POST"])
@login_required
@handle_service_errors
def reject_suggestion(suggestion_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.reject_suggestion(current_user, suggestion_id, notes=payload.get("notes"))
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/suggestions/<int:suggestion_id>/modify", methods=["POST"])
@login_required
@handle_service_errors
def modify_suggestion(suggestion_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.modify_suggestion(
        current_user,
        suggestion_id,
        diagnosis_name=payload.get("diagnosis_name", ""),
        notes=payload.get("notes"),
    )
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/suggestions/<int:suggestion_id>/confirm", methods=["POST"])
@login_required
@handle_service_errors
def confirm_suggestion(suggestion_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.confirm_diagnosis(current_user, suggestion_id, notes=payload.get("notes"))
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/suggestions/<int:suggestion_id>/suspect", methods=["POST"])
@login_required
@handle_service_errors
def suspect_suggestion(suggestion_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.mark_suspected(current_user, suggestion_id, notes=payload.get("notes"))
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/encounters/<int:encounter_id>/manual", methods=["POST"])
@login_required
@handle_service_errors
def add_manual_diagnosis(encounter_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.add_manual_diagnosis(
        current_user,
        encounter_id,
        diagnosis_name=payload.get("diagnosis_name", ""),
        notes=payload.get("notes"),
    )
    return jsonify({"decision": services.decision_to_dict(decision)}), 201
