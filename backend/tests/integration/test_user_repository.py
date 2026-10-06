# backend/tests/integration/test_user_repository.py
# P8: Database integration tests for UserRepository.
#
# Tests run against the real credential_db_test PostgreSQL database.
# Each test runs in a savepoint that is rolled back after the test.

import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.constants import UserRole
from core.security import hash_password
from models.university_model import University
from models.user_model import User
from repositories.user_repository import UserRepository

pytestmark = [pytest.mark.database, pytest.mark.integration]


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _create_university(db: AsyncSession) -> University:
    """Insert a minimal university for FK constraints."""
    uni = University(
        id=uuid4(),
        name=f"Uni-{uuid4().hex[:8]}",
        short_code=uuid4().hex[:6].upper(),
        country="US",
        official_email=f"{uuid4().hex[:8]}@uni.edu",
        is_verified=True,
        verified_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(uni)
    await db.flush()
    return uni


async def _create_user(
    db: AsyncSession,
    role: UserRole = UserRole.STUDENT,
    university_id=None,
    email: str | None = None,
    is_active: bool = True,
) -> User:
    """Insert a test user."""
    user = User(
        id=uuid4(),
        email=email or f"{uuid4().hex[:10]}@test.com",
        password_hash=hash_password("TestPass123!"),
        first_name="Test",
        last_name="User",
        role=role,
        university_id=university_id,
        is_active=is_active,
    )
    db.add(user)
    await db.flush()
    return user


# ═══════════════════════════════════════════════════════════════════════════════
#  BaseRepository inherited methods (via UserRepository)
# ═══════════════════════════════════════════════════════════════════════════════


class TestBaseRepositoryMethods:
    """Tests for inherited get_by_id, create, update, delete, list."""

    async def test_get_by_id(self, db_session: AsyncSession):
        """Fetch a user by UUID returns the correct record."""
        user = await _create_user(db_session)
        found = await UserRepository.get_by_id(db_session, user.id)
        assert found is not None
        assert found.id == user.id
        assert found.email == user.email

    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Non-existent UUID returns None."""
        found = await UserRepository.get_by_id(db_session, uuid4())
        assert found is None

    async def test_create(self, db_session: AsyncSession):
        """Create inserts a record and returns it with generated defaults."""
        data = {
            "email": f"{uuid4().hex[:10]}@create.test",
            "password_hash": hash_password("CreateTest1!"),
            "first_name": "Created",
            "last_name": "User",
            "role": UserRole.STUDENT,
        }
        user = await UserRepository.create(db_session, data)
        assert user.id is not None
        assert user.email == data["email"]
        assert user.is_active is True  # Default from model
        assert user.failed_login_attempts == 0  # Default from model

    async def test_update(self, db_session: AsyncSession):
        """Update modifies attributes and returns the updated record."""
        user = await _create_user(db_session)
        updated = await UserRepository.update(
            db_session, user.id, {"first_name": "Updated"}
        )
        assert updated is not None
        assert updated.first_name == "Updated"
        assert updated.id == user.id

    async def test_delete_soft(self, db_session: AsyncSession):
        """Delete sets is_active=False (soft delete)."""
        user = await _create_user(db_session)
        assert user.is_active is True
        await UserRepository.delete(db_session, user.id)
        # Re-fetch to verify
        deleted = await UserRepository.get_by_id(db_session, user.id)
        assert deleted is not None
        assert deleted.is_active is False

    async def test_list_with_pagination(self, db_session: AsyncSession):
        """List returns paginated results with total count."""
        # Create 3 users
        for _ in range(3):
            await _create_user(db_session)
        items, total = await UserRepository.list(db_session, skip=0, limit=2)
        assert len(items) <= 2
        assert total >= 3


# ═══════════════════════════════════════════════════════════════════════════════
#  UserRepository domain methods
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetByEmail:
    """Tests for UserRepository.get_by_email."""

    async def test_get_by_email_found(self, db_session: AsyncSession):
        """Returns user when email matches."""
        user = await _create_user(db_session, email="findme@test.com")
        found = await UserRepository.get_by_email(db_session, "findme@test.com")
        assert found is not None
        assert found.id == user.id

    async def test_get_by_email_not_found(self, db_session: AsyncSession):
        """Returns None when email doesn't exist."""
        found = await UserRepository.get_by_email(db_session, "nobody@test.com")
        assert found is None


class TestLoginTracking:
    """Tests for update_last_login, increment/reset failed attempts, set_account_lock."""

    async def test_update_last_login(self, db_session: AsyncSession):
        """Records login timestamp and IP."""
        user = await _create_user(db_session)
        await UserRepository.update_last_login(db_session, user.id, "192.168.1.1")
        await db_session.refresh(user)
        assert str(user.last_login_ip) == "192.168.1.1"
        assert user.last_login_at is not None

    async def test_increment_failed_attempts(self, db_session: AsyncSession):
        """Atomically increments and returns the new count."""
        user = await _create_user(db_session)
        assert user.failed_login_attempts == 0
        count = await UserRepository.increment_failed_attempts(db_session, user.id)
        assert count == 1
        count = await UserRepository.increment_failed_attempts(db_session, user.id)
        assert count == 2

    async def test_reset_failed_attempts(self, db_session: AsyncSession):
        """Resets the counter to zero."""
        user = await _create_user(db_session)
        await UserRepository.increment_failed_attempts(db_session, user.id)
        await UserRepository.increment_failed_attempts(db_session, user.id)
        await UserRepository.reset_failed_attempts(db_session, user.id)
        await db_session.refresh(user)
        assert user.failed_login_attempts == 0

    async def test_set_account_lock(self, db_session: AsyncSession):
        """Sets locked_until timestamp."""
        user = await _create_user(db_session)
        lock_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        await UserRepository.set_account_lock(db_session, user.id, lock_until)
        await db_session.refresh(user)
        assert user.locked_until is not None
        # locked_until should be close to the set time
        assert abs((user.locked_until - lock_until).total_seconds()) < 2


class TestRoleAndUniversityQueries:
    """Tests for get_active_users_by_role and get_by_university_id."""

    async def test_get_active_users_by_role(self, db_session: AsyncSession):
        """Returns only active users with the specified role."""
        await _create_user(db_session, role=UserRole.STUDENT, is_active=True)
        await _create_user(db_session, role=UserRole.STUDENT, is_active=False)
        await _create_user(db_session, role=UserRole.EMPLOYER, is_active=True)

        students = await UserRepository.get_active_users_by_role(
            db_session, UserRole.STUDENT
        )
        # At least 1 active student
        assert len(students) >= 1
        for s in students:
            assert s.role == UserRole.STUDENT
            assert s.is_active is True

    async def test_get_by_university_id(self, db_session: AsyncSession):
        """Returns all users affiliated with a university."""
        uni = await _create_university(db_session)
        u1 = await _create_user(
            db_session, role=UserRole.UNIVERSITY_ADMIN, university_id=uni.id
        )
        u2 = await _create_user(
            db_session, role=UserRole.UNIVERSITY_ADMIN, university_id=uni.id
        )
        # Create a user for a different university
        await _create_user(db_session, role=UserRole.STUDENT)

        users = await UserRepository.get_by_university_id(db_session, uni.id)
        user_ids = {u.id for u in users}
        assert u1.id in user_ids
        assert u2.id in user_ids
