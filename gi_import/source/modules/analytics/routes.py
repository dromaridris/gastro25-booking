"""Analytics Foundation HTTP routes."""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.core.exceptions import ValidationError
from app.core.route_helpers import handle_service_errors

from . import services
from .constants import PERIOD_CUSTOM

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _run_params_from_request() -> dict:
    args = request.args
    return {
        "period_type": args.get("period_type", PERIOD_CUSTOM),
        "date_from": _parse_datetime(args.get("date_from")),
        "date_to": _parse_datetime(args.get("date_to")),
        "department_id": int(args["department_id"]) if args.get("department_id") else None,
        "physician_id": int(args["physician_id"]) if args.get("physician_id") else None,
        "role_code": args.get("role_code"),
        "procedure_type_id": int(args["procedure_type_id"]) if args.get("procedure_type_id") else None,
        "diagnosis_category": args.get("diagnosis_category"),
        "create_snapshot": args.get("create_snapshot", "").lower() in ("1", "true", "yes"),
    }


@bp.route("/metrics", methods=["GET"])
@login_required
@handle_service_errors
def list_metrics():
    return jsonify({"metrics": services.list_metrics(current_user)})


@bp.route("/run/<metric_id>", methods=["GET"])
@login_required
@handle_service_errors
def run_metric(metric_id: str):
    params = _run_params_from_request()
    try:
        result = services.run_metric(current_user, metric_id, **params)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.route("/snapshots", methods=["GET"])
@login_required
@handle_service_errors
def list_snapshots():
    metric_id = request.args.get("metric_id")
    limit = int(request.args.get("limit", 50))
    snapshots = services.list_snapshots(current_user, metric_id=metric_id, limit=limit)
    return jsonify({"snapshots": snapshots})


@bp.route("/configure", methods=["POST"])
@login_required
@handle_service_errors
def configure_metric():
    payload = request.get_json(silent=True) or {}
    metric_id = payload.get("metric_id")
    if not metric_id:
        raise ValidationError("metric_id is required.")
    try:
        metric = services.configure_metric(
            current_user,
            metric_id,
            status=payload.get("status"),
            config=payload.get("config"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"metric": metric})
