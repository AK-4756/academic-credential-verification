# backend/dependencies/rbac.py
# Role-based access control dependency factory.
#
# Architecture Reference: docs/backend.md Section 8 (Authorization — RBAC)
# Build Order: implementation-roadmap.md Sprint 4, Phase 3
#
# Provides:
#   require_role            — Factory returning a dependency that enforces role(s)
#   require_super_admin     — Convenience: require SUPER_ADMIN role
#   require_university_admin — Convenience: require UNIVERSITY_ADMIN role
#
# Multi-Layer Authorization (from docs):
#   Layer 1 (Role Gate)     — This module (cheap, runs before DB queries)
#   Layer 2 (Ownership Gate) — Service layer (resource-level ownership checks)
#   Layer 3 (Contract Gate)  — Smart contract (on-chain issuer authorization)
#
# Usage in routers:
#   @router.post("/upload")
#   async def upload(
#       current_user: User = Depends(require_role("UNIVERSITY_ADMIN")),
#   ):
#       ...
#
#   @router.get("/admin/dashboard")
#   async def admin_dashboard(
#       current_user: User = Depends(require_role(["SUPER_ADMIN", "UNIVERSITY_ADMIN"])),
#   ):
#       ...

from __future__ import annotations

from fastapi import Depends

from core.constants import UserRole
from core.exceptions import InsufficientPermissionsError
from dependencies.auth import get_current_user
from models.user_model import User


def require_role(allowed_roles: str | list[str]):
    """
    Factory function returning a FastAPI dependency that enforces role-based access.

    The returned dependency resolves the authenticated user (via ``get_current_user``)
    and checks that the user's role is in the allowed list. This is Layer 1 of the
    documented multi-layer authorization pattern — a fast, cheap check that runs
    before any database queries for the requested resource.

    Accepts either a single role string or a list of role strings. ``UserRole``
    enum values are accepted (they extend ``str``).

    Args:
        allowed_roles: A single role string (e.g., ``"UNIVERSITY_ADMIN"``) or a
            list of role strings (e.g., ``["SUPER_ADMIN", "UNIVERSITY_ADMIN"]``).

    Returns:
        A FastAPI dependency callable that returns the authenticated ``User``
        if their role matches, or raises ``InsufficientPermissionsError``.

    Raises:
        InsufficientPermissionsError: If the user's role is not in the allowed
            list (HTTP 403, code INSUFFICIENT_PERMISSIONS).
    """
    if isinstance(allowed_roles, str):
        roles = [allowed_roles]
    else:
        roles = list(allowed_roles)

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        """Verify the authenticated user has one of the required roles."""
        if current_user.role not in roles:
            raise InsufficientPermissionsError()
        return current_user

    return role_checker


# ─── Convenience Dependencies ─────────────────────────────────────────────────
# Pre-built role dependencies for the most common single-role requirements.
# Usage: current_user: User = Depends(require_super_admin)

require_super_admin = require_role(UserRole.SUPER_ADMIN)
require_university_admin = require_role(UserRole.UNIVERSITY_ADMIN)
