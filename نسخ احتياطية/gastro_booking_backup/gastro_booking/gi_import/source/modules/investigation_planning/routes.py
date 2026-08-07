"""Investigation Planning HTTP routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors

from . import services

bp = Blueprint("investigation_planning", __name__, url_prefix="/investigation-planning")


@bp.route("/encounters/<int:encounter_id>/generate", methods=["POST"])
@login_required
@handle_service_errors
def generate_plan(encounter_id: int):
    try:
        plan = services.generate_plan(current_user, encounter_id)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"plan": services.plan_to_dict(plan)}), 201


@bp.route("/encounters/<int:encounter_id>", methods=["GET"])
@login_required
@handle_service_errors
def get_encounter_plan(encounter_id: int):
    return jsonify(services.get_plan_view(current_user, encounter_id))


@bp.route("/plans/<int:plan_id>/review", methods=["POST"])
@login_required
@handle_service_errors
def review_plan(plan_id: int):
    plan = services.review_plan(current_user, plan_id)
    return jsonify({"plan": services.plan_to_dict(plan)})


@bp.route("/plans/<int:plan_id>/approve", methods=["POST"])
@login_required
@handle_service_errors
def approve_plan(plan_id: int):
    plan = services.approve_plan(current_user, plan_id)
    return jsonify({"plan": services.plan_to_dict(plan)})


@bp.route("/plans/<int:plan_id>/reject", methods=["POST"])
@login_required
@handle_service_errors
def reject_plan(plan_id: int):
    payload = request.get_json(silent=True) or {}
    plan = services.reject_plan(current_user, plan_id, reason=payload.get("reason"))
    return jsonify({"plan": services.plan_to_dict(plan)})


@bp.route("/suggestions/<int:suggestion_id>/accept", methods=["POST"])
@login_required
@handle_service_errors
def accept_suggestion(suggestion_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.accept_suggestion(current_user, suggestion_id, reason=payload.get("reason"))
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/suggestions/<int:suggestion_id>/reject", methods=["POST"])
@login_required
@handle_service_errors
def reject_suggestion(suggestion_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.reject_suggestion(current_user, suggestion_id, reason=payload.get("reason"))
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/suggestions/<int:suggestion_id>/modify", methods=["POST"])
@login_required
@handle_service_errors
def modify_suggestion(suggestion_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.modify_suggestion(
        current_user,
        suggestion_id,
        investigation_name=payload.get("investigation_name"),
        priority=payload.get("priority"),
        reason=payload.get("reason"),
    )
    return jsonify({"decision": services.decision_to_dict(decision)})


@bp.route("/encounters/<int:encounter_id>/manual", methods=["POST"])
@login_required
@handle_service_errors
def add_manual(encounter_id: int):
    payload = request.get_json(silent=True) or {}
    decision = services.add_manual_investigation(
        current_user,
        encounter_id,
        investigation_name=payload.get("investigation_name", ""),
        category=payload.get("category"),
        priority=payload.get("priority"),
        reason=payload.get("reason"),
    )
    return jsonify({"decision": services.decision_to_dict(decision)}), 201
