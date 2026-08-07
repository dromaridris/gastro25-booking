"""Clinical Intake HTTP routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors

from . import services

bp = Blueprint("clinical_intake", __name__, url_prefix="/clinical-intake")


@bp.route("/search")
@login_required
@handle_service_errors
def search_complaints():
    query = request.args.get("q", "")
    specialty_code = request.args.get("specialty_code")
    limit = min(int(request.args.get("limit", 10)), 25)
    results = services.search_complaints(
        current_user,
        query,
        specialty_code=specialty_code,
        limit=limit,
    )
    return jsonify({"query": query, "results": results})


@bp.route("/encounters/<int:encounter_id>", methods=["GET"])
@login_required
@handle_service_errors
def get_encounter_intake(encounter_id: int):
    record = services.get_intake_for_encounter(current_user, encounter_id)
    if record is None:
        return jsonify({"intake": None})
    return jsonify({"intake": services.intake_to_dict(record)})


@bp.route("/encounters/<int:encounter_id>", methods=["POST"])
@login_required
@handle_service_errors
def create_encounter_intake(encounter_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        record = services.create_intake(
            current_user,
            encounter_id=encounter_id,
            chief_complaint=payload.get("chief_complaint", ""),
            complaint_entry_id=payload.get("complaint_entry_id"),
            symptom_onset=payload.get("symptom_onset"),
            priority=payload.get("priority"),
            allow_unknown=bool(payload.get("allow_unknown", False)),
            specialty_code=payload.get("specialty_code"),
        )
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"intake": services.intake_to_dict(record)}), 201


@bp.route("/<int:intake_id>", methods=["PUT"])
@login_required
@handle_service_errors
def update_intake(intake_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        record = services.update_intake(
            current_user,
            intake_id,
            chief_complaint=payload.get("chief_complaint"),
            complaint_entry_id=payload.get("complaint_entry_id"),
            symptom_onset=payload.get("symptom_onset"),
            priority=payload.get("priority"),
            allow_unknown=bool(payload.get("allow_unknown", False)),
            specialty_code=payload.get("specialty_code"),
        )
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"intake": services.intake_to_dict(record)})
