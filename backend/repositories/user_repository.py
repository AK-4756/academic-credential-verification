# backend/repositories/user_repository.py
# Data access for the 'users' table.
#
# Architecture Reference: docs/backend.md Section 5.2 (Repository 01)
# Model Reference: models/user_model.py
#
# Methods (10 total):
#   Inherited: get_by_id, create, update, delete, list
#   Domain:    get_by_email, update_last_login, increment_failed_attempts,
#              reset_failed_attempts, set_account_lock,
#              get_active_users_by_role, get_by_university_id

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import UserRole
from models.user_model import User
from repositories.base_repository import BaseRepository

_UTC = timezone.utc


class UserRepository(BaseRepository[User]):
    """Repository for User entity CRUD and authentication-related queries."""

    model = User

    @classmethod
    async def get_by_email(
        cls, db: AsyncSession, email: str
    ) -> User | None:
        """
        Fetch a user by email address (UNIQUE lookup).

        Used in every authentication flow: login, registration
        duplicate check, password reset.

        Args:
            db: Async database session.
            email: Email address (case-sensitive, stored lowercase).

        Returns:
            The User instance, or None if not found.
        """
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def update_last_login(
        cls, db: AsyncSession, user_id: uuid.UUID, ip_address: str
    ) -> None:
        """
        Record a successful login timestamp and IP.

        Args:
            db: Async database session.
            user_id: UUID of the user who logged in.
            ip_address: Client IP address of the login request.
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                last_login_at=datetime.now(tz=_UTC),
                last_login_ip=ip_address,
            )
        )
        await db.execute(stmt)

    @classmethod
    async def increment_failed_attempts(
        cls, db: AsyncSession, user_id: uuid.UUID
    ) -> int:
        """
        Atomically increment the failed login attempt counter.

        Uses SQL-level increment to avoid race conditions under
        concurrent login attempts.

        Args:
            db: Async database session.
            user_id: UUID of the user.

        Returns:
            The new failed_login_attempts count (for lockout threshold check).
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=User.failed_login_attempts + 1)
            .returning(User.failed_login_attempts)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    @classmethod
    async def reset_failed_attempts(
        cls, db: AsyncSession, user_id: uuid.UUID
    ) -> None:
        """
        Reset the failed login attempt counter to zero.

        Called after a successful login.

        Args:
            db: Async database session.
            user_id: UUID of the user.
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(failed_login_attempts=0)
        )
        await db.execute(stmt)

    @classmethod
    async def set_account_lock(
        cls, db: AsyncSession, user_id: uuid.UUID, locked_until: datetime
    ) -> None:
        """
        Lock a user account until a specified timestamp.

        Triggered when failed_login_attempts reaches the lockout
        threshold (MAX_FAILED_LOGIN_ATTEMPTS from constants).

        Args:
            db: Async database session.
            user_id: UUID of the user.
            locked_until: Datetime until which the account is locked.
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(locked_until=locked_until)
        )
        await db.execute(stmt)

    @classmethod
    async def get_active_users_by_role(
        cls, db: AsyncSession, role: UserRole
    ) -> list[User]:
        """
        Fetch all active users with a specific role.

        Args:
            db: Async database session.
            role: UserRole enum value to filter by.

        Returns:
            List of active User instances with the specified role.
        """
        stmt = select(User).where(User.role == role, User.is_active.is_(True))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_by_university_id(
        cls, db: AsyncSession, university_id: uuid.UUID
    ) -> list[User]:
        """
        Fetch all users affiliated with a university.

        Used for university admin management.

        Args:
            db: Async database session.
            university_id: UUID of the university.

        Returns:
            List of User instances affiliated with the university.
        """
        stmt = select(User).where(User.university_id == university_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())
