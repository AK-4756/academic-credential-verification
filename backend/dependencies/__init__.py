# backend/dependencies/__init__.py
# FastAPI dependency injection providers — public API.
#
# Architecture Reference: docs/backend.md Section 6 (Dependency Injection)
# Build Order: implementation-roadmap.md Sprint 4, Phase 3
#
# This package exposes all injectable dependencies used by API routers.
# Routers can import directly from this package for convenience:
#
#   from dependencies import get_db, get_current_user, require_role, limiter
#
# Or import from specific submodules for explicitness:
#
#   from dependencies.auth import get_current_user
#   from dependencies.rbac import require_role

from dependencies.auth import (
    get_current_active_user,
    get_current_user,
    get_university_admin_user,
    oauth2_scheme,
)
from dependencies.database import get_db
from dependencies.rate_limiting import limiter, rate_limit_exceeded_handler
from dependencies.rbac import (
    require_role,
    require_super_admin,
    require_university_admin,
)
from dependencies.services import get_blockchain_service

__all__ = [
    # Database
    "get_db",
    # Authentication
    "oauth2_scheme",
    "get_current_user",
    "get_current_active_user",
    "get_university_admin_user",
    # Authorization (RBAC)
    "require_role",
    "require_super_admin",
    "require_university_admin",
    # Rate Limiting
    "limiter",
    "rate_limit_exceeded_handler",
    # Services
    "get_blockchain_service",
]

