# backend/repositories/base_repository.py
# Generic base repository providing standard CRUD operations.
#
# Architecture Reference: docs/backend.md Section 5.1 (Repository Design Pattern)
# Build Order: implementation-roadmap.md Sprint 4, Phase 4
#
# Base Repository Interface (from docs):
#   get_by_id(id: UUID) → Model | None
#   create(data: dict) → Model
#   update(id: UUID, data: dict) → Model
#   delete(id: UUID) → None (soft delete where applicable)
#   list(filters: dict, pagination) → (List[Model], int)
#
# Transaction Rules (Section 5.1):
#   Services control transaction boundaries.
#   Repositories receive the async session as a parameter.
#   Repositories do NOT commit or rollback — services do.
#
# Insert Pattern (Section 20.1):
#   db.add(record) → await db.flush() → await db.refresh(record)
#   flush() retrieves generated ID/defaults without committing.

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository providing standard CRUD operations.

    All domain repositories extend this class and set the ``model``
    class variable to their ORM model. Repositories receive the
    ``AsyncSession`` per method call — they do NOT hold session state
    and do NOT commit or rollback transactions.

    Type Parameters:
        ModelType: The SQLAlchemy ORM model class.
    """

    model: type[ModelType]

    @classmethod
    async def get_by_id(
        cls, db: AsyncSession, id: uuid.UUID
    ) -> ModelType | None:
        """
        Fetch a single entity by its UUID primary key.

        Args:
            db: Async database session.
            id: UUID primary key.

        Returns:
            The ORM model instance, or None if not found.
        """
        stmt = select(cls.model).where(cls.model.id == id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def create(cls, db: AsyncSession, data: dict[str, Any]) -> ModelType:
        """
        Insert a new entity from a dictionary of column values.

        Uses flush() to retrieve generated defaults (UUID, timestamps)
        without committing the transaction.

        Args:
            db: Async database session.
            data: Dictionary mapping column names to values.

        Returns:
            The newly created ORM model instance with generated defaults.
        """
        instance = cls.model(**data)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    @classmethod
    async def update(
        cls, db: AsyncSession, id: uuid.UUID, data: dict[str, Any]
    ) -> ModelType | None:
        """
        Update an existing entity's attributes by UUID.

        Args:
            db: Async database session.
            id: UUID primary key of the entity to update.
            data: Dictionary of column names to new values.

        Returns:
            The updated ORM model instance, or None if entity not found.
        """
        stmt = select(cls.model).where(cls.model.id == id)
        result = await db.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance is None:
            return None
        for key, value in data.items():
            setattr(instance, key, value)
        await db.flush()
        await db.refresh(instance)
        return instance

    @classmethod
    async def delete(cls, db: AsyncSession, id: uuid.UUID) -> None:
        """
        Delete an entity by UUID.

        Performs soft delete (sets ``is_active = False``) when the model
        has an ``is_active`` column. Otherwise performs a hard delete.

        Args:
            db: Async database session.
            id: UUID primary key of the entity to delete.
        """
        stmt = select(cls.model).where(cls.model.id == id)
        result = await db.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance is None:
            return
        if hasattr(instance, "is_active"):
            instance.is_active = False
            await db.flush()
        else:
            await db.delete(instance)
            await db.flush()

    @classmethod
    async def list(
        cls,
        db: AsyncSession,
        filters: dict[str, Any] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ModelType], int]:
        """
        Paginated listing with optional filtering.

        Pagination follows docs/backend.md Section 29.1:
        default page=1 (skip=0), limit=20, max limit=100.

        Args:
            db: Async database session.
            filters: Optional dict of {column_name: value} equality filters.
            skip: Number of records to skip (offset).
            limit: Maximum number of records to return.

        Returns:
            Tuple of (items, total_count).
        """
        stmt = select(cls.model)
        if filters:
            for key, value in filters.items():
                if hasattr(cls.model, key):
                    stmt = stmt.where(getattr(cls.model, key) == value)

        # Total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Paginated items
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total
