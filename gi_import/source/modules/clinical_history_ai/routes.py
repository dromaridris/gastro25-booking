"""Clinical History AI HTTP routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors

from . import services

bp = Blueprint("clinical_history_ai", __name__, url_prefix="/clinical-history-ai")


@bp.route("/encounters/<int:encounter_id>/start", methods=["POST"])
@login_required
@handle_service_errors
def start_session(encounter_id: int):
    try:
        session = services.start_from_encounter(current_user, encounter_id)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"session": services.session_to_dict(session)}), 201


@bp.route("/encounters/<int:encounter_id>/session", methods=["GET"])
@login_required
@handle_service_errors
def get_encounter_session(encounter_id: int):
    session = services.get_session_for_encounter(current_user, encounter_id)
    if session is None:
        return jsonify({"session": None})
    return jsonify({"session": services.session_to_dict(session)})


@bp.route("/sessions/<int:session_id>", methods=["GET"])
@login_required
@handle_service_errors
def get_session(session_id: int):
    session = services.get_session(current_user, session_id)
    return jsonify({"session": services.session_to_dict(session)})


@bp.route("/sessions/<int:session_id>/questions", methods=["GET"])
@login_required
@handle_service_errors
def next_questions(session_id: int):
    limit = min(int(request.args.get("limit", 5)), 20)
    specialty_code = request.args.get("specialty_code")
    questions = services.get_next_questions(
        current_user, session_id, limit=limit, specialty_code=specialty_code
    )
    return jsonify({"questions": questions})


@bp.route("/sessions/<int:session_id>/answers", methods=["POST"])
@login_required
@handle_service_errors
def save_answers(session_id: int):
    payload = request.get_json(silent=True) or {}
    session = services.save_answers(current_user, session_id, payload.get("answers") or {})
    return jsonify({"session": services.session_to_dict(session)})


@bp.route("/sessions/<int:session_id>/generate", methods=["POST"])
@login_required
@handle_service_errors
def generate_draft(session_id: int):
    try:
        draft = services.generate_history_draft(current_user, session_id)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"draft": services.draft_to_dict(draft)}), 201


@bp.route("/sessions/<int:session_id>/regenerate", methods=["POST"])
@login_required
@handle_service_errors
def regenerate_draft(session_id: int):
    draft = services.regenerate_draft(current_user, session_id)
    return jsonify({"draft": services.draft_to_dict(draft)})


@bp.route("/sessions/<int:session_id>/discard", methods=["POST"])
@login_required
@handle_service_errors
def discard_session(session_id: int):
    session = services.discard_session(current_user, session_id)
    return jsonify({"session": services.session_to_dict(session)})


@bp.route("/drafts/<int:draft_id>/review", methods=["POST"])
@login_required
@handle_service_errors
def review_draft(draft_id: int):
    draft = services.review_draft(current_user, draft_id)
    return jsonify({"draft": services.draft_to_dict(draft)})


@bp.route("/drafts/<int:draft_id>", methods=["PUT"])
@login_required
@handle_service_errors
def edit_draft(draft_id: int):
    payload = request.get_json(silent=True) or {}
    draft = services.edit_draft(current_user, draft_id, sections=payload.get("sections") or {})
    return jsonify({"draft": services.draft_to_dict(draft)})


@bp.route("/drafts/<int:draft_id>/approve", methods=["POST"])
@login_required
@handle_service_errors
def approve_draft(draft_id: int):
    draft = services.approve_draft(current_user, draft_id)
    return jsonify({"draft": services.draft_to_dict(draft)})


@bp.route("/drafts/<int:draft_id>/reject", methods=["POST"])
@login_required
@handle_service_errors
def reject_draft(draft_id: int):
    payload = request.get_json(silent=True) or {}
    draft = services.reject_draft(current_user, draft_id, reason=payload.get("reason"))
    return jsonify({"draft": services.draft_to_dict(draft)})
