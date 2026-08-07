"""Clinical Interpretation HTTP routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors

from . import services

bp = Blueprint("clinical_interpretation", __name__, url_prefix="/clinical-interpretation")


@bp.route("/encounters/<int:encounter_id>/generate", methods=["POST"])
@login_required
@handle_service_errors
def generate_interpretation(encounter_id: int):
    try:
        run = services.generate_interpretation(current_user, encounter_id)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"run": services.run_to_dict(run)}), 201


@bp.route("/encounters/<int:encounter_id>", methods=["GET"])
@login_required
@handle_service_errors
def get_encounter_interpretation(encounter_id: int):
    return jsonify(services.get_interpretation_view(current_user, encounter_id))


@bp.route("/runs/<int:run_id>/review", methods=["POST"])
@login_required
@handle_service_errors
def review_run(run_id: int):
    run = services.review_run(current_user, run_id)
    return jsonify({"run": services.run_to_dict(run)})


@bp.route("/findings/<int:finding_id>/accept", methods=["POST"])
@login_required
@handle_service_errors
def accept_finding(finding_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.accept_finding(current_user, finding_id, notes=payload.get("notes"))
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/findings/<int:finding_id>/reject", methods=["POST"])
@login_required
@handle_service_errors
def reject_finding(finding_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.reject_finding(current_user, finding_id, notes=payload.get("notes"))
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/findings/<int:finding_id>/modify", methods=["POST"])
@login_required
@handle_service_errors
def modify_finding(finding_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.modify_finding(
        current_user,
        finding_id,
        finding_title=payload.get("finding_title"),
        explanation=payload.get("explanation"),
        notes=payload.get("notes"),
    )
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/encounters/<int:encounter_id>/manual", methods=["POST"])
@login_required
@handle_service_errors
def add_manual(encounter_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.add_manual_interpretation(
        current_user,
        encounter_id,
        finding_title=payload.get("finding_title", ""),
        explanation=payload.get("explanation"),
        notes=payload.get("notes"),
    )
    return jsonify({"decision": services.decision_to_dict(decision)})
