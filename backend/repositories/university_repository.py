# backend/repositories/university_repository.py
# Data access for the 'universities' table.
#
# Architecture Reference: docs/backend.md Section 5.2 (Repository 02)
# Model Reference: models/university_model.py
#
# Methods (10 total):
#   Inherited: get_by_id, create, update, delete, list
#   Domain:    get_by_name, get_by_short_code, get_by_wallet_address,
#              set_verified, update_wallet_address,
#              get_all_verified, get_all_unverified

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.university_model import University
from repositories.base_repository import BaseRepository

_UTC = timezone.utc


class UniversityRepository(BaseRepository[University]):
    """Repository for University entity CRUD and verification queries."""

    model = University

    @classmethod
    async def get_by_name(
        cls, db: AsyncSession, name: str
    ) -> University | None:
        """
        Fetch a university by its full name (UNIQUE lookup).

        Args:
            db: Async database session.
            name: Full institution name.

        Returns:
            The University instance, or None if not found.
        """
        stmt = select(University).where(University.name == name)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_short_code(
        cls, db: AsyncSession, short_code: str
    ) -> University | None:
        """
        Fetch a university by its short code (UNIQUE lookup).

        Short codes are uppercase abbreviations used in certificate UIDs
        (e.g., "MIT", "OXFORD").

        Args:
            db: Async database session.
            short_code: Uppercase institution abbreviation.

        Returns:
            The University instance, or None if not found.
        """
        stmt = select(University).where(University.short_code == short_code)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_wallet_address(
        cls, db: AsyncSession, wallet_address: str
    ) -> University | None:
        """
        Fetch a university by its Ethereum wallet address (UNIQUE lookup).

        Args:
            db: Async database session.
            wallet_address: Checksummed Ethereum address (42 chars).

        Returns:
            The University instance, or None if not found.
        """
        stmt = select(University).where(
            University.wallet_address == wallet_address
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def set_verified(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        verified_by: uuid.UUID,
    ) -> University | None:
        """
        Mark a university as verified by a SUPER_ADMIN.

        Sets is_verified=True, verified_at=now(), verified_by=admin_id.

        Args:
            db: Async database session.
            university_id: UUID of the university to verify.
            verified_by: UUID of the SUPER_ADMIN performing verification.

        Returns:
            The updated University, or None if not found.
        """
        stmt = select(University).where(University.id == university_id)
        result = await db.execute(stmt)
        university = result.scalar_one_or_none()
        if university is None:
            return None
        university.is_verified = True
        university.verified_at = datetime.now(tz=_UTC)
        university.verified_by = verified_by
        await db.flush()
        await db.refresh(university)
        return university

    @classmethod
    async def update_wallet_address(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        wallet_address: str,
    ) -> University | None:
        """
        Set or update a university's Ethereum wallet address.

        Args:
            db: Async database session.
            university_id: UUID of the university.
            wallet_address: Checksummed Ethereum address (42 chars).

        Returns:
            The updated University, or None if not found.
        """
        stmt = select(University).where(University.id == university_id)
        result = await db.execute(stmt)
        university = result.scalar_one_or_none()
        if university is None:
            return None
        university.wallet_address = wallet_address
        await db.flush()
        await db.refresh(university)
        return university

    @classmethod
    async def get_all_verified(cls, db: AsyncSession) -> list[University]:
        """
        Fetch all verified and active universities.

        Args:
            db: Async database session.

        Returns:
            List of verified, active University instances.
        """
        stmt = select(University).where(
            University.is_verified.is_(True),
            University.is_active.is_(True),
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_all_unverified(cls, db: AsyncSession) -> list[University]:
        """
        Fetch all unverified and active universities.

        Used by SUPER_ADMIN for the verification queue.

        Args:
            db: Async database session.

        Returns:
            List of unverified, active University instances.
        """
        stmt = select(University).where(
            University.is_verified.is_(False),
            University.is_active.is_(True),
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
