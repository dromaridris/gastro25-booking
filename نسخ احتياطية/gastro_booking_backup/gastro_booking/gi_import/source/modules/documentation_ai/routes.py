"""Clinical Documentation Intelligence HTTP routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors

from . import services

bp = Blueprint("documentation_ai", __name__, url_prefix="/documentation-ai")


@bp.route("/templates", methods=["GET"])
@login_required
@handle_service_errors
def list_templates():
    return jsonify({"templates": services.list_templates(current_user)})


@bp.route("/encounters/<int:encounter_id>/generate", methods=["POST"])
@login_required
@handle_service_errors
def generate_document(encounter_id: int):
    payload = request.get_json(silent=True) or {}
    template_key = payload.get("template_key", "doc.progress.gi")
    try:
        doc = services.generate_document(current_user, encounter_id, template_key=template_key)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"document": services.document_to_dict(doc)}), 201


@bp.route("/documents/<int:document_id>", methods=["GET"])
@login_required
@handle_service_errors
def get_document(document_id: int):
    return jsonify(services.get_document_view(current_user, document_id))


@bp.route("/sections/<int:section_id>/edit", methods=["POST"])
@login_required
@handle_service_errors
def edit_section(section_id: int):
    payload = request.get_json(silent=True) or {}
    section = services.edit_section(current_user, section_id, content=payload.get("content", ""), notes=payload.get("notes"))
    return jsonify({"section": services.section_to_dict(section)})


@bp.route("/sections/<int:section_id>/regenerate", methods=["POST"])
@login_required
@handle_service_errors
def regenerate_section(section_id: int):
    section = services.regenerate_section(current_user, section_id)
    return jsonify({"section": services.section_to_dict(section)})


@bp.route("/documents/<int:document_id>/approve", methods=["POST"])
@login_required
@handle_service_errors
def approve_document(document_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        doc = services.approve_document(current_user, document_id, notes=payload.get("notes"))
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"document": services.document_to_dict(doc)})


@bp.route("/documents/<int:document_id>/reject", methods=["POST"])
@login_required
@handle_service_errors
def reject_document(document_id: int):
    payload = request.get_json(silent=True) or {}
    doc = services.reject_document(current_user, document_id, reason=payload.get("reason"))
    return jsonify({"document": services.document_to_dict(doc)})


@bp.route("/documents/<int:document_id>/manual-section", methods=["POST"])
@login_required
@handle_service_errors
def add_manual_section(document_id: int):
    payload = request.get_json(silent=True) or {}
    section = services.add_manual_section(
        current_user,
        document_id,
        section_key=payload.get("section_key", "manual"),
        section_name=payload.get("section_name", "Manual Section"),
        content=payload.get("content", ""),
    )
    return jsonify({"section": services.section_to_dict(section)}), 201


@bp.route("/documents/<int:document_id>/sign", methods=["POST"])
@login_required
@handle_service_errors
def sign_document(document_id: int):
    try:
        signed = services.sign_document(current_user, document_id)
    except ValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"signed_document": services.signed_document_to_dict(signed)})
