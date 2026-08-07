"""Phase 7E — Workforce Identity & Duty Management constants."""

# Account lifecycle statuses (training / temporary accounts)
STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_EXPIRED = "expired"
STATUS_SUSPENDED = "suspended"
STATUS_CLOSED = "closed"
ACCOUNT_STATUSES = (
    STATUS_PENDING,
    STATUS_ACTIVE,
    STATUS_EXPIRED,
    STATUS_SUSPENDED,
    STATUS_CLOSED,
)

# Invitation statuses
INVITATION_PENDING = "pending"
INVITATION_ACCEPTED = "accepted"
INVITATION_EXPIRED = "expired"
INVITATION_REVOKED = "revoked"
INVITATION_STATUSES = (
    INVITATION_PENDING,
    INVITATION_ACCEPTED,
    INVITATION_EXPIRED,
    INVITATION_REVOKED,
)

# Shift swap statuses
SWAP_PENDING = "pending"
SWAP_APPROVED = "approved"
SWAP_REJECTED = "rejected"
SWAP_CANCELLED = "cancelled"
SWAP_STATUSES = (SWAP_PENDING, SWAP_APPROVED, SWAP_REJECTED, SWAP_CANCELLED)

# Roles that require time-limited account lifecycle
TRAINING_ROLE_CODES = frozenset(
    {
        "house_officer",
        "postgraduate_trainee",
        "senior_registrar",
        "visiting_trainee",
    }
)

DEFAULT_INVITATION_VALIDITY_DAYS = 14

ROLE_TRAINING_COORDINATOR = "training_coordinator"
ROLE_DUTY_COORDINATOR = "duty_coordinator"

# Duty display groupings for today's team view
DUTY_ROLE_GROUPS = (
    ("head_of_department", "Consultant"),
    ("core_consultant", "Consultant"),
    ("consultant", "Consultant"),
    ("postgraduate_trainee", "Postgraduate Trainee"),
    ("senior_registrar", "Trainee"),
    ("house_officer", "House Officer"),
    ("visiting_trainee", "Trainee"),
    ("endoscopy_technician", "Endoscopy Technician"),
    ("endoscopy_nurse", "Endoscopy Nurse"),
    ("nurse", "Nurse"),
)
