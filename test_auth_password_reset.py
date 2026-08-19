"""Auth helpers — password reset approval rules."""

from app import (
    ROLE_ADMIN,
    ROLE_HOD,
    can_approve_password_reset,
)

class _U:
    def __init__(self, id_, role):
        self._d = {'id': id_, 'role': role}

    def __getitem__(self, k):
        return self._d[k]

admin1 = _U(1, ROLE_ADMIN)
admin2 = _U(2, ROLE_ADMIN)
hod = _U(3, ROLE_HOD)
user = _U(4, 'registrar')

assert can_approve_password_reset(admin1, user)
assert can_approve_password_reset(hod, user)
assert not can_approve_password_reset(admin1, admin1)
assert can_approve_password_reset(admin2, admin1)
assert not can_approve_password_reset(hod, admin1)

print('Auth password reset tests passed')
