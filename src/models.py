"""MediTrack — Shared domain models."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from exceptions import AuthError

VALID_ROLES = {'admin', 'provider', 'receptionist', 'patient'}


@dataclass
class User:
    """Represents an authenticated system user.

    Attributes:
        user_id:    Unique identifier (UUID string).
        username:   Login handle; must be unique.
        role:       One of 'admin', 'provider', 'receptionist', 'patient'.
        full_name:  Display name.
        is_active:  Whether the account is enabled.
        created_at: Timestamp of account creation.

    Testing notes:
        - Role-based access control is exercised in patients.deactivate_patient(),
          appointments.reschedule_appointment(), and records.add_record().
        - Boundary: role not in VALID_ROLES should raise ValidationError on construction.
        - State: is_active=False should be treated as unauthorized by callers.
    """
    user_id: str
    username: str
    role: str
    full_name: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        from exceptions import ValidationError
        if self.role not in VALID_ROLES:
            raise ValidationError(
                f"Invalid role '{self.role}'. Valid roles: {sorted(VALID_ROLES)}"
            )
        if not self.username or not isinstance(self.username, str):
            raise ValidationError("username must be a non-empty string")

    def require_role(self, *allowed_roles: str) -> None:
        """Raise AuthError if this user's role is not in allowed_roles.

        Usage:
            user.require_role('admin', 'provider')
        """
        if self.role not in allowed_roles:
            raise AuthError(
                f"Role '{self.role}' not permitted. Required: {sorted(allowed_roles)}"
            )

    def __repr__(self) -> str:
        return f"User(username={self.username!r}, role={self.role!r})"
