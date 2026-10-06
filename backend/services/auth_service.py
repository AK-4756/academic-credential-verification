# backend/services/auth_service.py
# Authentication service — registration, login, token refresh, logout.
#
# Architecture Reference: docs/backend.md Section 7.1 (Authentication Service Design)
# Directory Reference: docs/backend.md Section 27.1 (services/auth_service.py)
#
# Transaction boundaries: Services own commit/rollback via `async with db.begin():`.
# Repositories only flush() — they never commit.
#
# Security invariants:
#   - Same error message for wrong email AND wrong password (user enumeration prevention)
#   - Account lock after 5 consecutive failures (10-minute lockout)
#   - Refresh token rotation (single-use; old revoked when new issued)
#   - Password hashes never returned in responses

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.constants import MAX_FAILED_LOGIN_ATTEMPTS, UserRole
from core.exceptions import (
    AccountLockedError,
    DuplicateEmailError,
    InvalidCredentialsError,
    UniversityNotFoundError,
    UnverifiedUniversityError,
    UserNotFoundError,
)
from core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from repositories import (
    EmployerRepository,
    RefreshTokenRepository,
    StudentRepository,
    UniversityRepository,
    UserRepository,
)


# ─── Registration ────────────────────────────────────────────────────────────


async def register_user(
    registration_data: dict,
    db: AsyncSession,
) -> dict:
    """
    Register a new user account.

    Docs Section 7.1 (Registration Workflow):
    1. Check email uniqueness
    2. Hash password
    3. Create User record
    4. If STUDENT: create Student profile
    5. If EMPLOYER: create Employer profile
    6. If UNIVERSITY_ADMIN: verify university exists and is verified

    Args:
        registration_data: Dict with email, password, first_name, last_name,
                          role, university_code (optional), company_name (optional).
        db: Async database session.

    Returns:
        Dict with user_id, email, role, message.

    Raises:
        DuplicateEmailError: If email is already registered.
        UniversityNotFoundError: If UNIVERSITY_ADMIN's university_code is invalid.
        UnverifiedUniversityError: If UNIVERSITY_ADMIN's university is not verified.
    """
    email = registration_data["email"]
    role = registration_data["role"]

    async with db.begin():
        # 1. Check email uniqueness
        existing = await UserRepository.get_by_email(db, email)
        if existing is not None:
            raise DuplicateEmailError()

        # 2. Hash password
        password_hash = hash_password(registration_data["password"])

        # 3. Prepare user data
        user_data = {
            "email": email,
            "password_hash": password_hash,
            "first_name": registration_data["first_name"],
            "last_name": registration_data["last_name"],
            "role": role,
        }

        # If UNIVERSITY_ADMIN, verify university exists and is verified
        university_id = None
        if role == UserRole.UNIVERSITY_ADMIN:
            university_code = registration_data.get("university_code")
            university = await UniversityRepository.get_by_short_code(
                db, university_code
            )
            if university is None:
                raise UniversityNotFoundError(
                    message=f"University with code '{university_code}' not found"
                )
            if not university.is_verified:
                raise UnverifiedUniversityError()
            university_id = university.id
            user_data["university_id"] = university_id

        # 4. Create user
        user = await UserRepository.create(db, user_data)

        # 5. Create role-specific profile
        if role == UserRole.STUDENT:
            await StudentRepository.create(db, {"user_id": user.id})

        elif role == UserRole.EMPLOYER:
            company_name = registration_data.get("company_name", "")
            await EmployerRepository.create(
                db, {"user_id": user.id, "company_name": company_name}
            )

    return {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "message": "Registration successful",
    }


# ─── Login ───────────────────────────────────────────────────────────────────


async def authenticate_user(
    email: str,
    password: str,
    request_ip: str,
    db: AsyncSession,
) -> dict:
    """
    Authenticate user and issue access + refresh tokens.

    Docs Section 7.1 (Login Workflow):
    1. Find user by email (same error for missing email and wrong password)
    2. Check account lock
    3. Verify password (increment failed attempts on failure)
    4. Check account is active
    5. Reset failed attempts
    6. Update last login
    7. Generate access + refresh tokens

    Args:
        email: User's email address.
        password: User's plaintext password.
        request_ip: Client IP address for last_login tracking.
        db: Async database session.

    Returns:
        Dict with access_token, token_type, refresh_token (raw), user info.

    Raises:
        InvalidCredentialsError: Wrong email or password (generic message).
        AccountLockedError: Account temporarily locked.

    Transaction design:
        Two sequential transactions are used deliberately so that failed-
        login-attempt tracking is committed to the database BEFORE the
        InvalidCredentialsError is raised.  A single transaction would roll
        back the increment when the exception propagates out of the
        `async with db.begin():` block, making the lockout feature non-
        functional.  Block 1 commits the failure record; Block 2 commits
        the success data.  The exception is raised between the two blocks.
    """
    # ── Block 1: credential check + failure persistence ──────────────────────
    # Exits BEFORE raising so that the transaction commits the increment/lock.
    # The `_password_ok` flag carries the result out of the block.
    user = None
    _password_ok = True

    async with db.begin():
        # 1. Find user
        user = await UserRepository.get_by_email(db, email)
        if user is None:
            raise InvalidCredentialsError()

        # 2. Check account lock
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise AccountLockedError()

        # 3. Verify password
        if not verify_password(password, user.password_hash):
            _password_ok = False
            attempts = await UserRepository.increment_failed_attempts(db, user.id)
            if attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                lock_until = datetime.now(timezone.utc) + timedelta(minutes=10)
                await UserRepository.set_account_lock(db, user.id, lock_until)
        # Block exits here WITHOUT raising → transaction commits,
        # persisting the incremented counter and/or locked_until.

    # Raise AFTER Block 1 has committed so the failure record is durable.
    if not _password_ok:
        raise InvalidCredentialsError()

    # ── Block 2: success path ─────────────────────────────────────────────────
    async with db.begin():
        # 4. Check account is active
        if not user.is_active:
            raise InvalidCredentialsError()

        # 5. Reset failed attempts
        await UserRepository.reset_failed_attempts(db, user.id)

        # 6. Update last login
        await UserRepository.update_last_login(db, user.id, request_ip)

        # 7. Generate tokens
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            university_id=str(user.university_id) if user.university_id else None,
            email=user.email,
        )

        refresh_token_raw = generate_refresh_token()
        refresh_token_hashed = hash_token(refresh_token_raw)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

        await RefreshTokenRepository.create(
            db,
            user_id=user.id,
            token_hash=refresh_token_hashed,
            expires_at=expires_at,
            ip=request_ip,
        )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token_raw,
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "university_id": user.university_id,
        },
    }



# ─── Token Refresh ───────────────────────────────────────────────────────────


async def refresh_access_token(
    refresh_token_raw: str,
    request_ip: str,
    db: AsyncSession,
) -> dict:
    """
    Refresh access token using a valid refresh token.

    Docs Section 7.1 (Token Refresh Workflow):
    1. Hash the incoming refresh token
    2. Look up stored token by hash
    3. Check not revoked and not expired
    4. Load user
    5. Rotate: revoke old token, create new token pair

    Args:
        refresh_token_raw: The raw refresh token string from cookie.
        request_ip: Client IP for new token record.
        db: Async database session.

    Returns:
        Dict with access_token, token_type, new_refresh_token (raw).

    Raises:
        InvalidCredentialsError: Invalid, revoked, or expired refresh token.
    """
    token_hashed = hash_token(refresh_token_raw)

    async with db.begin():
        stored = await RefreshTokenRepository.get_by_token_hash(db, token_hashed)
        if stored is None:
            raise InvalidCredentialsError(message="Invalid refresh token")

        if stored.is_revoked:
            raise InvalidCredentialsError(message="Refresh token has been revoked")

        if stored.expires_at < datetime.now(timezone.utc):
            raise InvalidCredentialsError(message="Refresh token has expired")

        # Load user
        user = await UserRepository.get_by_id(db, stored.user_id)
        if user is None or not user.is_active:
            raise InvalidCredentialsError(message="User account is not available")

        # Generate new token pair
        new_access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            university_id=str(user.university_id) if user.university_id else None,
            email=user.email,
        )

        new_refresh_raw = generate_refresh_token()
        new_refresh_hashed = hash_token(new_refresh_raw)
        new_expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )

        new_token = await RefreshTokenRepository.create(
            db,
            user_id=user.id,
            token_hash=new_refresh_hashed,
            expires_at=new_expires_at,
            ip=request_ip,
        )

        # Revoke old token (rotation)
        await RefreshTokenRepository.revoke(
            db, stored.id, replaced_by_id=new_token.id
        )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": new_refresh_raw,
    }


# ─── Logout ──────────────────────────────────────────────────────────────────


async def logout(
    refresh_token_raw: str,
    db: AsyncSession,
) -> None:
    """
    Logout by revoking the refresh token.

    Docs Section 7.1 (Logout Workflow):
    Access token expires naturally (no server-side revocation for MVP).

    Args:
        refresh_token_raw: The raw refresh token string from cookie.
        db: Async database session.
    """
    token_hashed = hash_token(refresh_token_raw)

    async with db.begin():
        stored = await RefreshTokenRepository.get_by_token_hash(db, token_hashed)
        if stored is not None and not stored.is_revoked:
            await RefreshTokenRepository.revoke(db, stored.id)
