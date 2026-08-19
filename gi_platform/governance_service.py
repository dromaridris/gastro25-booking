"""Clinical governance dashboard — HOD monitoring (adapted from GI clinical_governance)."""

from __future__ import annotations

from gi_platform import logbook_service


def get_hod_dashboard(db) -> dict:
    pending_orders = db.execute(
        """
        SELECT o.*, wp.patient_name, u.full_name AS ordered_by_name
        FROM gi_investigation_order o
        LEFT JOIN ward_patient wp ON wp.id = o.ward_patient_id
        LEFT JOIN user u ON u.id = o.created_by
        WHERE o.approval_status = 'pending_registrar'
        ORDER BY o.created_at DESC LIMIT 50
        """
    ).fetchall()
    pending_plans = db.execute(
        """
        SELECT p.*, wp.patient_name, u.full_name AS author_name
        FROM gi_management_plan p
        LEFT JOIN ward_patient wp ON wp.id = p.ward_patient_id
        LEFT JOIN user u ON u.id = p.created_by
        WHERE p.approval_status = 'pending_registrar'
        ORDER BY p.created_at DESC LIMIT 50
        """
    ).fetchall()
    trainee_log = logbook_service.staff_activity_rollups(db, limit=30)
    audit_recent = db.execute(
        "SELECT * FROM gi_audit_event ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    return {
        'pending_orders': pending_orders,
        'pending_plans': pending_plans,
        'trainee_log': trainee_log,
        'audit_recent': audit_recent,
        'pending_order_count': len(pending_orders),
        'pending_plan_count': len(pending_plans),
    }
