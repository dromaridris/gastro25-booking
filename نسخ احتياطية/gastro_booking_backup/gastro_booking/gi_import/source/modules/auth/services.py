"""
Service layer for authentication only. User administration (create,
update, role change, deactivate) lives in app/modules/users/services.py —
kept separate because authentication ("who is this") and user
administration ("who may manage accounts") are different concerns with
different permission models: authenticate() has no permission gate at
all (anyone with valid credentials may log in), while every function in
users/services.py is gated by the "user:manage" permission.
"""

from app.core.exceptions import ValidationError
from app.modules.auth.models import User


def authenticate(email: str, password: str) -> User:
    user = User.query.filter_by(email=email.lower().strip()).first()
    if user is None or not user.check_password(password):
        raise ValidationError("Invalid email or password.")
    if not user.is_active:
        raise ValidationError("This account has been deactivated.")
    from app.modules.workforce_identity import lifecycle_services

    lifecycle_services.enforce_login_lifecycle(user)
    return user
