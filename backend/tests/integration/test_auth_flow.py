# backend/tests/integration/test_auth_flow.py
# P9: Authentication Integration Tests.
#
# Tests the complete authentication flow through the REAL service ->
# repository -> PostgreSQL database layers. No mocking of the database
# or repositories. Blockchain is not exercised here.
#
# Services under test:
#   services.auth_service.register_user
#   services.auth_service.authenticate_user
#   services.auth_service.refresh_access_token
#   services.auth_service.logout
#
# SESSION FIXTURE: svc_db (defined in tests/integration/conftest.py)
#
#   Uses AsyncSession with autobegin=False.
#   Production services call `async with db.begin():` to own their own
#   transactions. With autobegin=False, these calls work without conflict
#   regardless of what test code does between service calls -- no "A
#   transaction is already begun on this Session" errors.
#
#   CLEANUP: The autouse _truncate_tables_after_test fixture in conftest.py
#   truncates all application tables after every test.
#
# DB CONSTRAINT NOTES:
#   - chk_universities_verified_consistency: is_verified=True requires
#     verified_at IS NOT NULL.
#   - chk_employers_company_name_not_empty: company_name must be non-empty.
#   - users.email is UNIQUE; each test uses a distinct email address.

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.constants import MAX_FAILED_LOGIN_ATTEMPTS, UserRole
from core.exceptions import (
    AccountLockedError,
    DuplicateEmailError,
    InvalidCredentialsError,
    UniversityNotFoundError,
    UnverifiedUniversityError,
)
from core.security import hash_token, verify_token
from models.university_model import University
from repositories.employer_repository import EmployerRepository
from repositories.refresh_token_repository import RefreshTokenRepository
from repositories.student_repository import StudentRepository
from repositories.user_repository import UserRepository
from services.auth_service import (
    authenticate_user,
    logout,
    refresh_access_token,
    register_user,
)

pytestmark = [pytest.mark.database, pytest.mark.integration]


# ─── Test Helpers ─────────────────────────────────────────────────────────────


async def _commit_university(
    db: AsyncSession,
    *,
    is_verified: bool = True,
    short_code: str | None = None,
) -> University:
    """
    Insert and COMMIT a university row using its own transaction.

    Because svc_db has autobegin=False, we use `async with db.begin():`
    to explicitly begin and commit the insert.  The session is clean
    afterward, ready for the next service call.
    """
    sc = short_code or uuid4().hex[:6].upper()
    async with db.begin():
        uni = University(
            id=uuid4(),
            name=f"Test University {sc}",
            short_code=sc,
            country="US",
            official_email=f"admin@{sc.lower()}.edu",
            is_verified=is_verified,
            # chk_universities_verified_consistency requires verified_at when
            # is_verified=True
            verified_at=datetime.utcnow() if is_verified else None,
            is_active=True,
        )
        db.add(uni)
    return uni


def _student_reg(*, email: str | None = None) -> dict:
    """Minimal valid registration dict for STUDENT role."""
    return {
        "email": email or f"student_{uuid4().hex[:8]}@test.edu",
        "password": "TestPass1",
        "first_name": "Test",
        "last_name": "Student",
        "role": UserRole.STUDENT,
    }


def _employer_reg(
    *, email: str | None = None, company: str = "Acme Corp"
) -> dict:
    """Minimal valid registration dict for EMPLOYER role."""
    return {
        "email": email or f"employer_{uuid4().hex[:8]}@company.com",
        "password": "TestPass1",
        "first_name": "Test",
        "last_name": "Employer",
        "role": UserRole.EMPLOYER,
        "company_name": company,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 1. STUDENT REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestStudentRegistration:
    """register_user for STUDENT role -- DB-level verification."""

    @pytest.mark.asyncio
    async def test_student_registration_creates_user_and_profile(
        self, svc_db: AsyncSession
    ) -> None:
        """
        Registering a STUDENT creates a user row and a linked student profile.
        Verifies by querying the DB after the service call.
        """
        data = _student_reg(email="student_reg@example.com")

        result = await register_user(data, svc_db)

        assert result["email"] == "student_reg@example.com"
        assert result["role"] == UserRole.STUDENT
        assert result["message"] == "Registration successful"

        # Verify user row persisted
        user = await UserRepository.get_by_email(svc_db, "student_reg@example.com")
        assert user is not None
        assert user.role == UserRole.STUDENT
        assert user.is_active is True

        # Verify student profile created
        student = await StudentRepository.get_by_user_id(svc_db, user.id)
        assert student is not None
        assert student.user_id == user.id

    @pytest.mark.asyncio
    async def test_student_registration_hashes_password(
        self, svc_db: AsyncSession
    ) -> None:
        """
        The stored password_hash must not equal the plaintext password.
        bcrypt hashes start with $2b$.
        """
        data = _student_reg(email="student_pw@example.com")

        await register_user(data, svc_db)

        user = await UserRepository.get_by_email(svc_db, "student_pw@example.com")
        assert user is not None
        assert user.password_hash != "TestPass1"
        assert user.password_hash.startswith("$2")

    @pytest.mark.asyncio
    async def test_student_registration_duplicate_email_raises(
        self, svc_db: AsyncSession
    ) -> None:
        """
        Re-registering the same email must raise DuplicateEmailError and
        must not create a second user row.
        """
        data = _student_reg(email="dup@example.com")

        await register_user(data, svc_db)

        with pytest.raises(DuplicateEmailError):
            await register_user(data, svc_db)

        users = await UserRepository.get_active_users_by_role(
            svc_db, UserRole.STUDENT
        )
        dup_users = [u for u in users if u.email == "dup@example.com"]
        assert len(dup_users) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 2. EMPLOYER REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestEmployerRegistration:
    """register_user for EMPLOYER role -- DB-level verification."""

    @pytest.mark.asyncio
    async def test_employer_registration_creates_user_and_profile(
        self, svc_db: AsyncSession
    ) -> None:
        """
        Registering an EMPLOYER creates a user row and an employer profile
        with the correct company_name.
        """
        data = _employer_reg(
            email="employer_reg@company.com", company="Acme Corp"
        )

        result = await register_user(data, svc_db)

        assert result["email"] == "employer_reg@company.com"
        assert result["role"] == UserRole.EMPLOYER

        user = await UserRepository.get_by_email(
            svc_db, "employer_reg@company.com"
        )
        assert user is not None

        employer = await EmployerRepository.get_by_user_id(svc_db, user.id)
        assert employer is not None
        assert employer.user_id == user.id
        assert employer.company_name == "Acme Corp"

    @pytest.mark.asyncio
    async def test_employer_registration_persists_company_name(
        self, svc_db: AsyncSession
    ) -> None:
        """
        The company_name provided in registration data is stored verbatim
        in the employer profile row.
        """
        data = _employer_reg(
            email="emp_longname@company.com",
            company="Global Logistics and Transport International Ltd",
        )

        await register_user(data, svc_db)

        user = await UserRepository.get_by_email(
            svc_db, "emp_longname@company.com"
        )
        employer = await EmployerRepository.get_by_user_id(svc_db, user.id)
        assert employer.company_name == (
            "Global Logistics and Transport International Ltd"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. UNIVERSITY ADMIN REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestUniversityAdminRegistration:
    """register_user for UNIVERSITY_ADMIN role -- requires a verified university."""

    @pytest.mark.asyncio
    async def test_university_admin_registration_links_university(
        self, svc_db: AsyncSession
    ) -> None:
        """
        A UNIVERSITY_ADMIN registration must link the user to the university
        identified by university_code (short_code lookup).

        The university is committed via its own transaction before the service
        call so the session is in clean state when the service begins its own.
        """
        uni = await _commit_university(svc_db, short_code="TESTUNI")

        data = {
            "email": "admin@testuni.edu",
            "password": "TestPass1",
            "first_name": "Admin",
            "last_name": "User",
            "role": UserRole.UNIVERSITY_ADMIN,
            "university_code": "TESTUNI",
        }

        result = await register_user(data, svc_db)

        assert result["email"] == "admin@testuni.edu"

        user = await UserRepository.get_by_email(svc_db, "admin@testuni.edu")
        assert user is not None
        assert user.university_id == uni.id

    @pytest.mark.asyncio
    async def test_university_admin_nonexistent_code_raises(
        self, svc_db: AsyncSession
    ) -> None:
        """
        An unknown university_code must raise UniversityNotFoundError.
        No user row should be created (transaction rolls back on exception).
        """
        data = {
            "email": "admin@ghost.edu",
            "password": "TestPass1",
            "first_name": "Ghost",
            "last_name": "Admin",
            "role": UserRole.UNIVERSITY_ADMIN,
            "university_code": "DOESNOTEXIST",
        }

        with pytest.raises(UniversityNotFoundError):
            await register_user(data, svc_db)

        user = await UserRepository.get_by_email(svc_db, "admin@ghost.edu")
        assert user is None

    @pytest.mark.asyncio
    async def test_university_admin_unverified_university_raises(
        self, svc_db: AsyncSession
    ) -> None:
        """
        Registering against an unverified university must raise
        UnverifiedUniversityError. No user row should be created.
        """
        await _commit_university(
            svc_db, is_verified=False, short_code="UNVERI"
        )

        data = {
            "email": "admin@unveri.edu",
            "password": "TestPass1",
            "first_name": "Pending",
            "last_name": "Admin",
            "role": UserRole.UNIVERSITY_ADMIN,
            "university_code": "UNVERI",
        }

        with pytest.raises(UnverifiedUniversityError):
            await register_user(data, svc_db)

        user = await UserRepository.get_by_email(svc_db, "admin@unveri.edu")
        assert user is None


# ═══════════════════════════════════════════════════════════════════════════════
# 4. LOGIN (authenticate_user)
# ═══════════════════════════════════════════════════════════════════════════════


class TestLogin:
    """authenticate_user -- success and failure paths against real DB."""

    @pytest.mark.asyncio
    async def test_login_success_returns_tokens(
        self, svc_db: AsyncSession
    ) -> None:
        """
        A valid login returns:
        - A decodable RS256 access_token
        - A refresh_token string
        - Correct user info dict
        The refresh_token must be persisted (not revoked) in the DB.
        """
        data = _student_reg(email="login_ok@test.edu")
        await register_user(data, svc_db)

        result = await authenticate_user(
            "login_ok@test.edu", "TestPass1", "127.0.0.1", svc_db
        )

        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert "refresh_token" in result
        assert result["user"]["email"] == "login_ok@test.edu"
        assert result["user"]["role"] == UserRole.STUDENT

        # JWT decodes correctly
        payload = verify_token(result["access_token"])
        assert payload["email"] == "login_ok@test.edu"

        # Refresh token row persisted and not revoked
        token_hash = hash_token(result["refresh_token"])
        stored = await RefreshTokenRepository.get_by_token_hash(
            svc_db, token_hash
        )
        assert stored is not None
        assert stored.is_revoked is False

    @pytest.mark.asyncio
    async def test_login_records_last_login_ip(
        self, svc_db: AsyncSession
    ) -> None:
        """
        A successful login must update last_login_at and last_login_ip
        on the user row.
        """
        data = _student_reg(email="login_ip@test.edu")
        await register_user(data, svc_db)

        await authenticate_user(
            "login_ip@test.edu", "TestPass1", "192.168.1.100", svc_db
        )

        user = await UserRepository.get_by_email(svc_db, "login_ip@test.edu")
        assert user is not None
        assert user.last_login_at is not None
        assert str(user.last_login_ip) == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises_and_increments_counter(
        self, svc_db: AsyncSession
    ) -> None:
        """
        Wrong password must raise InvalidCredentialsError and increment
        failed_login_attempts on the user row.

        After the service commit, svc_db's identity map may hold a stale
        User object. We expire_all() to force a fresh DB read.
        """
        data = _student_reg(email="login_wrongpw@test.edu")
        await register_user(data, svc_db)

        with pytest.raises(InvalidCredentialsError):
            await authenticate_user(
                "login_wrongpw@test.edu", "WrongPass9", "127.0.0.1", svc_db
            )

        # Expire stale ORM cache; re-read from DB
        svc_db.expire_all()
        user = await UserRepository.get_by_email(svc_db, "login_wrongpw@test.edu")
        assert user is not None
        assert user.failed_login_attempts == 1

    @pytest.mark.asyncio
    async def test_login_unknown_email_raises(
        self, svc_db: AsyncSession
    ) -> None:
        """
        A completely unknown email must raise InvalidCredentialsError.
        Same error as wrong password (user enumeration prevention).
        """
        with pytest.raises(InvalidCredentialsError):
            await authenticate_user(
                "nobody@nowhere.com", "TestPass1", "127.0.0.1", svc_db
            )

    @pytest.mark.asyncio
    async def test_login_increments_and_locks_after_max_failures(
        self, svc_db: AsyncSession
    ) -> None:
        """
        After MAX_FAILED_LOGIN_ATTEMPTS (5) consecutive wrong passwords:
        - locked_until is set to a future timestamp.
        - The next attempt (even with correct password) raises AccountLockedError.
        """
        data = _student_reg(email="login_lock@test.edu")
        await register_user(data, svc_db)

        for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
            with pytest.raises(InvalidCredentialsError):
                await authenticate_user(
                    "login_lock@test.edu", "BadPass9", "127.0.0.1", svc_db
                )

        # Expire stale ORM cache; re-read from DB.
        # autobegin fires on the get_by_email read below, opening a read
        # transaction.  We must close it with rollback() before the next
        # authenticate_user call (which opens its own async with db.begin()).
        svc_db.expire_all()
        user = await UserRepository.get_by_email(svc_db, "login_lock@test.edu")
        assert user is not None
        assert user.locked_until is not None
        assert user.locked_until > datetime.now(timezone.utc)

        # Close the autobegun read-transaction before the next service call
        await svc_db.rollback()

        # Even correct password now raises AccountLockedError
        with pytest.raises(AccountLockedError):
            await authenticate_user(
                "login_lock@test.edu", "TestPass1", "127.0.0.1", svc_db
            )

    @pytest.mark.asyncio
    async def test_login_resets_failed_attempts_on_success(
        self, svc_db: AsyncSession
    ) -> None:
        """
        A successful login after a previous failure must reset
        failed_login_attempts to 0.
        """
        data = _student_reg(email="login_reset@test.edu")
        await register_user(data, svc_db)

        # One wrong attempt
        with pytest.raises(InvalidCredentialsError):
            await authenticate_user(
                "login_reset@test.edu", "WrongPass9", "127.0.0.1", svc_db
            )

        # Correct login
        await authenticate_user(
            "login_reset@test.edu", "TestPass1", "127.0.0.1", svc_db
        )

        svc_db.expire_all()
        user = await UserRepository.get_by_email(svc_db, "login_reset@test.edu")
        assert user is not None
        assert user.failed_login_attempts == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 5. TOKEN REFRESH (refresh_access_token)
# ═══════════════════════════════════════════════════════════════════════════════


class TestTokenRefresh:
    """refresh_access_token -- rotation, revocation, and error paths."""

    @pytest.mark.asyncio
    async def test_token_refresh_returns_new_tokens(
        self, svc_db: AsyncSession
    ) -> None:
        """
        A valid refresh token must:
        - Return a new access_token and a new refresh_token (different from old)
        - Mark the old refresh_token as revoked in DB
        - Persist the new refresh_token as active in DB
        """
        data = _student_reg(email="refresh_ok@test.edu")
        await register_user(data, svc_db)

        login = await authenticate_user(
            "refresh_ok@test.edu", "TestPass1", "127.0.0.1", svc_db
        )
        old_refresh = login["refresh_token"]

        result = await refresh_access_token(old_refresh, "127.0.0.1", svc_db)

        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert "refresh_token" in result
        assert result["refresh_token"] != old_refresh

        # Old token revoked
        old_stored = await RefreshTokenRepository.get_by_token_hash(
            svc_db, hash_token(old_refresh)
        )
        assert old_stored is not None
        assert old_stored.is_revoked is True

        # New token active
        new_stored = await RefreshTokenRepository.get_by_token_hash(
            svc_db, hash_token(result["refresh_token"])
        )
        assert new_stored is not None
        assert new_stored.is_revoked is False

    @pytest.mark.asyncio
    async def test_token_refresh_links_rotation_chain(
        self, svc_db: AsyncSession
    ) -> None:
        """
        After rotation, the old token's replaced_by field must point to the
        new token's ID (audit rotation chain).
        """
        data = _student_reg(email="refresh_chain@test.edu")
        await register_user(data, svc_db)

        login = await authenticate_user(
            "refresh_chain@test.edu", "TestPass1", "127.0.0.1", svc_db
        )
        old_refresh = login["refresh_token"]

        result = await refresh_access_token(old_refresh, "127.0.0.1", svc_db)

        old_stored = await RefreshTokenRepository.get_by_token_hash(
            svc_db, hash_token(old_refresh)
        )
        new_stored = await RefreshTokenRepository.get_by_token_hash(
            svc_db, hash_token(result["refresh_token"])
        )
        assert old_stored.replaced_by == new_stored.id

    @pytest.mark.asyncio
    async def test_token_refresh_revoked_token_raises(
        self, svc_db: AsyncSession
    ) -> None:
        """
        Reusing an already-rotated (revoked) refresh token must raise
        InvalidCredentialsError (prevents replay attacks).
        """
        data = _student_reg(email="refresh_revoked@test.edu")
        await register_user(data, svc_db)

        login = await authenticate_user(
            "refresh_revoked@test.edu", "TestPass1", "127.0.0.1", svc_db
        )
        old_refresh = login["refresh_token"]

        # Use once -- old token revoked
        await refresh_access_token(old_refresh, "127.0.0.1", svc_db)

        # Reuse revoked token
        with pytest.raises(InvalidCredentialsError):
            await refresh_access_token(old_refresh, "127.0.0.1", svc_db)

    @pytest.mark.asyncio
    async def test_token_refresh_unknown_token_raises(
        self, svc_db: AsyncSession
    ) -> None:
        """
        A completely unknown refresh token must raise InvalidCredentialsError.
        """
        with pytest.raises(InvalidCredentialsError):
            await refresh_access_token(
                "completely_unknown_token_not_in_db_xyz",
                "127.0.0.1",
                svc_db,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. LOGOUT
# ═══════════════════════════════════════════════════════════════════════════════


class TestLogout:
    """logout -- revocation and idempotency."""

    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token(
        self, svc_db: AsyncSession
    ) -> None:
        """
        logout() must set is_revoked=True on the token row.
        After logout, the token must not be usable for a refresh.
        """
        data = _student_reg(email="logout_ok@test.edu")
        await register_user(data, svc_db)

        login = await authenticate_user(
            "logout_ok@test.edu", "TestPass1", "127.0.0.1", svc_db
        )
        refresh = login["refresh_token"]

        await logout(refresh, svc_db)

        # Token is revoked in DB.
        # autobegin fires on the get_by_token_hash read, opening a read
        # transaction.  Close it before refresh_access_token opens its own.
        stored = await RefreshTokenRepository.get_by_token_hash(
            svc_db, hash_token(refresh)
        )
        assert stored is not None
        assert stored.is_revoked is True

        # Close the autobegun read-transaction before the next service call
        await svc_db.rollback()

        # Revoked token cannot be used for a refresh
        with pytest.raises(InvalidCredentialsError):
            await refresh_access_token(refresh, "127.0.0.1", svc_db)

    @pytest.mark.asyncio
    async def test_logout_unknown_token_is_silent(
        self, svc_db: AsyncSession
    ) -> None:
        """
        Logging out with an unknown token must not raise any exception.
        Graceful no-op prevents information leakage.
        """
        await logout("nonexistent_refresh_token_12345", svc_db)

    @pytest.mark.asyncio
    async def test_logout_already_revoked_token_is_silent(
        self, svc_db: AsyncSession
    ) -> None:
        """
        Double-logout (calling logout twice with the same token) must be
        idempotent -- no exception raised.
        """
        data = _student_reg(email="logout_double@test.edu")
        await register_user(data, svc_db)

        login = await authenticate_user(
            "logout_double@test.edu", "TestPass1", "127.0.0.1", svc_db
        )
        refresh = login["refresh_token"]

        await logout(refresh, svc_db)
        # Second logout must also succeed silently
        await logout(refresh, svc_db)
