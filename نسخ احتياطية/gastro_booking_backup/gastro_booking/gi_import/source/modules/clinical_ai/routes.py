"""Clinical AI HTTP routes — infrastructure endpoints only."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.core.route_helpers import handle_service_errors

from .ai_services import ClinicalAIService

bp = Blueprint("clinical_ai", __name__, url_prefix="/clinical-ai")
_service = ClinicalAIService()


@bp.route("/status")
@login_required
@handle_service_errors
def status():
    data = _service.get_configuration(current_user)
    return jsonify({"status": "ok", **data})


@bp.route("/config", methods=["GET"])
@login_required
@handle_service_errors
def get_config():
    return jsonify(_service.get_configuration(current_user))


@bp.route("/config/preview", methods=["POST"])
@login_required
@handle_service_errors
def preview_config():
    payload = request.get_json(silent=True) or {}
    return jsonify(_service.update_configuration_preview(current_user, payload))


@bp.route("/sessions/run", methods=["POST"])
@login_required
@handle_service_errors
def run_session():
    payload = request.get_json(silent=True) or {}
    result = _service.execute_infrastructure_request(
        current_user,
        prompt_type=payload.get("prompt_type", "guideline_lookup"),
        patient_id=payload.get("patient_id"),
        encounter_id=payload.get("encounter_id"),
        context_sources=payload.get("context_sources"),
        topic_keys=payload.get("topic_keys"),
        object_types=payload.get("object_types"),
        provider_key=payload.get("provider_key"),
    )
    return jsonify(result)
