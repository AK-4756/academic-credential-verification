# backend/repositories/student_repository.py
# Data access for the 'students' table.
#
# Architecture Reference: docs/backend.md Section 5.2 (Repository 03)
# Model Reference: models/student_model.py
#
# Methods (4 total):
#   Inherited: get_by_id, create, update, delete, list
#   Domain:    get_by_user_id

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.student_model import Student
from repositories.base_repository import BaseRepository


class StudentRepository(BaseRepository[Student]):
    """Repository for Student profile entity."""

    model = Student

    @classmethod
    async def get_by_user_id(
        cls, db: AsyncSession, user_id: uuid.UUID
    ) -> Student | None:
        """
        Fetch a student profile by its linked user ID (UNIQUE lookup).

        The students table has a one-to-one relationship with users
        via the user_id foreign key.

        Args:
            db: Async database session.
            user_id: UUID of the associated User.

        Returns:
            The Student profile, or None if not found.
        """
        stmt = select(Student).where(Student.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
