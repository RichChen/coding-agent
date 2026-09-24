"""Auth rules API surface."""

from __future__ import annotations

from auth_rules.models import User
from auth_rules.policy import merge_policies
from auth_rules.tokens import parse_token

__all__ = ["User", "check_role", "merge_policies", "parse_token"]


def check_role(user: User, required: str) -> bool:
    """Return whether the user has the required role."""
    return required in user.roles
