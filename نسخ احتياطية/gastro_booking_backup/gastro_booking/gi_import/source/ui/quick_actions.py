"""Permission-based quick actions for role home screens."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuickAction:
    label: str
    description: str
    endpoint: str
    permission: str
    icon: str = ""
    url_kwargs: dict | None = None


# Plain-language actions — only shown when the user has the matching permission.
QUICK_ACTION_DEFINITIONS: tuple[QuickAction, ...] = (
    # --- Patient care ---
    QuickAction(
        label="Add new patient",
        description="Register a new patient in the department",
        endpoint="patients.create_patient",
        permission="patient:edit",
        icon="👤",
    ),
    QuickAction(
        label="Book appointment",
        description="Open the patient list, then book from a patient record",
        endpoint="patients.list_patients",
        permission="appointment:edit",
        icon="📅",
    ),
    QuickAction(
        label="Start clinical encounter",
        description="Open the patient list, then start an encounter from a patient record",
        endpoint="patients.list_patients",
        permission="encounter:create",
        icon="🩺",
    ),
    QuickAction(
        label="Book endoscopy",
        description="Patient → Book Appointment → open appointment → Book endoscopy",
        endpoint="patients.list_patients",
        permission="procedure:edit",
        icon="🔬",
    ),
    QuickAction(
        label="Today's endoscopy list",
        description="See procedures waiting, ready, or in the room",
        endpoint="procedures.list_procedures",
        permission="procedure:view",
        icon="📋",
    ),
    QuickAction(
        label="Procedures in progress",
        description="Open the live procedure session list",
        endpoint="procedure_execution.list_sessions",
        permission="procedure_execution:view",
        icon="⚡",
    ),
    # --- Department operations ---
    QuickAction(
        label="Unit operations board",
        description="Daily overview: rooms, scopes, staff, and waiting pressure",
        endpoint="dept_ops.home",
        permission="dept_ops:view",
        icon="🏥",
    ),
    QuickAction(
        label="Endoscopy rooms",
        description="Room status board and assignments",
        endpoint="dept_ops.rooms",
        permission="dept_ops:view",
        icon="🚪",
    ),
    QuickAction(
        label="Scope inventory",
        description="Scopes, maintenance, and reprocessing status",
        endpoint="dept_ops.scopes",
        permission="dept_ops:view",
        icon="🔧",
    ),
    QuickAction(
        label="Waiting list",
        description="Patients waiting for an endoscopy slot",
        endpoint="dept_ops.waiting_list",
        permission="dept_ops:waiting_list",
        icon="⏳",
    ),
    QuickAction(
        label="Duty roster",
        description="Department on-call and duty schedule",
        endpoint="dept_ops.roster",
        permission="dept_ops:roster_manage",
        icon="📆",
    ),
    QuickAction(
        label="Department messages",
        description="Internal messages to the unit team",
        endpoint="dept_ops.messages",
        permission="dept_ops:message",
        icon="💬",
    ),
    QuickAction(
        label="Consumables stock",
        description="Inventory and low-stock alerts",
        endpoint="dept_ops.consumables",
        permission="dept_ops:consumable_manage",
        icon="📦",
    ),
    # --- Quality & governance ---
    QuickAction(
        label="Quality & safety",
        description="Incidents, KPIs, checklists, and governance dashboard",
        endpoint="clinical_governance.home",
        permission="governance:view",
        icon="🛡️",
    ),
    QuickAction(
        label="Report an incident",
        description="Log a clinical incident or near-miss",
        endpoint="clinical_governance.create_incident",
        permission="governance:incident_create",
        icon="⚠️",
    ),
    # --- Training & workforce ---
    QuickAction(
        label="My training portfolio",
        description="Review your automatically generated training record",
        endpoint="workforce.portfolio",
        permission="workforce:view_own",
        icon="📈",
    ),
    QuickAction(
        label="My duty schedule",
        description="See your upcoming duties and today's on-call team",
        endpoint="workforce_identity.my_duties",
        permission="workforce_identity:duty_view",
        icon="🕐",
    ),
    QuickAction(
        label="Training accounts",
        description="Set expiry dates and assign supervisors for trainees and house officers",
        endpoint="workforce_identity.hod_dashboard",
        permission="workforce_identity:dashboard_view",
        icon="🎓",
    ),
    QuickAction(
        label="Invite trainee or house officer",
        description="Create a registration link with a fixed account expiry date",
        endpoint="workforce_identity.create_invitation",
        permission="workforce_identity:invite_manage",
        icon="✉️",
    ),
    # --- Research & admin ---
    QuickAction(
        label="Research registry",
        description="Browse and enter research study data",
        endpoint="research.list_registries",
        permission="research:view",
        icon="🔬",
    ),
    QuickAction(
        label="User accounts",
        description="Create users and assign roles",
        endpoint="users.list_users",
        permission="user:manage",
        icon="👥",
    ),
    QuickAction(
        label="Clinical guidelines",
        description="Manage official department guideline documents",
        endpoint="knowledge_library.index",
        permission="knowledge_library:edit",
        icon="📚",
    ),
)


def visible_quick_actions(can_fn) -> list[QuickAction]:
    seen_endpoints: set[tuple[str, str]] = set()
    actions: list[QuickAction] = []
    for action in QUICK_ACTION_DEFINITIONS:
        if not can_fn(action.permission):
            continue
        key = (action.endpoint, action.permission)
        if key in seen_endpoints:
            continue
        seen_endpoints.add(key)
        actions.append(action)
    return actions
