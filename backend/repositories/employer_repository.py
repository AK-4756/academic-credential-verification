# backend/repositories/employer_repository.py
# Data access for the 'employers' table.
#
# Architecture Reference: docs/backend.md Section 5.2 (Repository 04)
# Model Reference: models/employer_model.py
#
# Methods (4 total):
#   Inherited: get_by_id, create, update, delete, list
#   Domain:    get_by_user_id

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.employer_model import Employer
from repositories.base_repository import BaseRepository


class EmployerRepository(BaseRepository[Employer]):
    """Repository for Employer profile entity."""

    model = Employer

    @classmethod
    async def get_by_user_id(
        cls, db: AsyncSession, user_id: uuid.UUID
    ) -> Employer | None:
        """
        Fetch an employer profile by its linked user ID (UNIQUE lookup).

        The employers table has a one-to-one relationship with users
        via the user_id foreign key.

        Args:
            db: Async database session.
            user_id: UUID of the associated User.

        Returns:
            The Employer profile, or None if not found.
        """
        stmt = select(Employer).where(Employer.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
