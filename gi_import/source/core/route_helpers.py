"""
Shared route-layer helpers. Extracted here once a second module needed
the identical error->HTTP mapping that app/modules/users/routes.py first
defined locally — per the "never duplicate code, build reusable
engines/utilities" rule, the second consumer is the signal to promote
something from "local to one module" to "shared."
"""

import functools

from flask import abort, flash

from app.core.exceptions import NotFoundError, PermissionDeniedError


def flash_form_errors(form) -> None:
    """Surface WTForms validation failures — otherwise POST looks like a no-op."""
    for field_name, errors in form.errors.items():
        field = getattr(form, field_name, None)
        label = field.label.text if field is not None and hasattr(field, "label") else field_name
        if field_name == "csrf_token":
            label = "Security token"
        for error in errors:
            flash(f"{label}: {error}", "danger")


def handle_service_errors(fn):
    """Maps service-layer exceptions to HTTP responses so routes don't
    each repeat the same try/except block:
    - PermissionDeniedError -> 403 (already audit-logged by the
      Permission Engine at the point it was raised)
    - NotFoundError -> 404
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except PermissionDeniedError:
            abort(403)
        except NotFoundError:
            abort(404)

    return wrapper
