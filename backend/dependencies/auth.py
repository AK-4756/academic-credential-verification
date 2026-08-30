# backend/dependencies/auth.py
# JWT authentication dependencies for FastAPI route protection.
#
# Architecture Reference: docs/backend.md Section 6.3 (get_current_user)
# Build Order: implementation-roadmap.md Sprint 4, Phase 3 (created),
#              Sprint 4, Phase 4 (repository integration)
#
# Provides:
#   oauth2_scheme          — FastAPI OAuth2 Bearer token extractor
#   get_current_user       — Validate JWT, load User from DB, check is_active
#   get_current_active_user — Explicit active-user gate for route signatures
#   get_university_admin_user — Composite: role + university validation
#
# Design Decision (from docs): Authentication is implemented as FastAPI
# dependencies, NOT as global middleware. This forces explicit per-route
# opt-in and avoids the exclusion-list antipattern.
#
# Phase 4 Integration: User and University lookups now use
# UserRepository / UniversityRepository per docs/backend.md Section 6.3
# line 1041: "Query DB: UserRepository.get_by_id(user_id)"

from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import UserRole
from core.exceptions import (
    AuthenticationError,
    InsufficientPermissionsError,
    TokenExpiredError,
    TokenInvalidError,
    UniversityNotFoundError,
)
from core.security import verify_token
from dependencies.database import get_db
from models.university_model import University
from models.user_model import User
from repositories.university_repository import UniversityRepository
from repositories.user_repository import UserRepository

# ─── OAuth2 Scheme ────────────────────────────────────────────────────────────
# tokenUrl must match the documented login endpoint (POST /api/v1/auth/login).
# This enables the "Authorize" button in Swagger UI and automatic Bearer
# token extraction from the Authorization header.

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ─── Core Authentication Dependency ──────────────────────────────────────────


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Authenticate a request via Bearer JWT token.

    Flow:
        1. Extracts Bearer token from the Authorization header (via oauth2_scheme).
        2. Verifies RS256 JWT signature and expiration (via core.security.verify_token).
        3. Extracts ``sub`` claim (user UUID) from the decoded payload.
        4. Loads the user from the database by UUID.
        5. Validates the user account is active.

    Args:
        token: JWT access token, extracted from the Authorization header.
        db: Async database session, injected by FastAPI.

    Returns:
        The authenticated User ORM model instance.

    Raises:
        TokenExpiredError: JWT has expired (HTTP 401, code TOKEN_EXPIRED).
        TokenInvalidError: JWT is malformed or has invalid signature (HTTP 401, code TOKEN_INVALID).
        AuthenticationError: User not found or account is disabled (HTTP 401).
    """
    # Step 1-2: Decode and verify JWT (RS256 signature + expiration)
    # verify_token raises TokenExpiredError or TokenInvalidError on failure
    payload = verify_token(token)

    # Step 3: Extract user UUID from the 'sub' claim
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise TokenInvalidError()

    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, AttributeError) as exc:
        raise TokenInvalidError() from exc

    # Step 4: Load user from database
    # docs/backend.md Section 6.3, line 1041: UserRepository.get_by_id(user_id)
    user = await UserRepository.get_by_id(db, user_id)

    if user is None:
        raise AuthenticationError(message="User not found")

    # Step 5: Validate account is active
    if not user.is_active:
        raise AuthenticationError(message="Account is disabled")

    return user


# ─── Active User Dependency ──────────────────────────────────────────────────


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Confirm the authenticated user's account is active.

    This is a thin wrapper over ``get_current_user`` that makes the
    active-user requirement explicit in route signatures. The check is
    defense-in-depth since ``get_current_user`` already validates this.

    Args:
        current_user: The authenticated user (injected via get_current_user).

    Returns:
        The authenticated, active User.

    Raises:
        AuthenticationError: If the user account is disabled (HTTP 401).
    """
    if not current_user.is_active:
        raise AuthenticationError(message="Account is disabled")
    return current_user


# ─── University Admin Composite Dependency ───────────────────────────────────


async def get_university_admin_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, University]:
    """
    Validate that the current user is a UNIVERSITY_ADMIN with an active university.

    Composite dependency that:
        1. Verifies the user's role is UNIVERSITY_ADMIN.
        2. Confirms the user has an associated university_id.
        3. Loads the university and checks it exists and is active.

    Used by certificate issuance, QR generation, and university management routes.

    Args:
        current_user: The authenticated user (injected via get_current_user).
        db: Async database session, injected by FastAPI.

    Returns:
        Tuple of (User, University) — the admin and their university.

    Raises:
        InsufficientPermissionsError: User is not a UNIVERSITY_ADMIN (HTTP 403).
        AuthenticationError: University admin has no associated university (HTTP 401).
        UniversityNotFoundError: Associated university does not exist (HTTP 404).
        AuthenticationError: Associated university is deactivated (HTTP 401).
    """
    if current_user.role != UserRole.UNIVERSITY_ADMIN:
        raise InsufficientPermissionsError()

    if current_user.university_id is None:
        raise AuthenticationError(
            message="University admin has no associated university"
        )

    # Load university via repository (Phase 4 integration)
    university = await UniversityRepository.get_by_id(
        db, current_user.university_id
    )

    if university is None:
        raise UniversityNotFoundError()

    if not university.is_active:
        raise AuthenticationError(message="Associated university is deactivated")

    return current_user, university
