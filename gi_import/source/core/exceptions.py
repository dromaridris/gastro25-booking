"""
Domain exceptions. Routes catch these and translate to HTTP responses /
flash messages; services raise them. This keeps services free of any
knowledge of Flask, HTTP, or templates (Clean Architecture boundary).
"""


class DomainError(Exception):
    """Base class for all business-rule violations."""


class PermissionDeniedError(DomainError):
    """Raised by the service layer when an action violates the RBAC model.
    Routes should catch this and return HTTP 403."""


class ValidationError(DomainError):
    """Raised when input fails a business-rule check (not a form-field
    format check — that belongs in forms.py)."""


class NotFoundError(DomainError):
    """Raised when a service looks up a record that doesn't exist or is
    archived and the caller didn't explicitly ask to include archived
    records."""


class ArchivedRecordError(DomainError):
    """Raised when an operation is attempted on an archived (soft-deleted)
    record that isn't allowed on archived data."""
