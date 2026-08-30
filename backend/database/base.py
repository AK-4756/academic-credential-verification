# backend/database/base.py
# Declarative base and shared column mixins for all ORM models.
#
# Architecture Reference: docs/backend.md Section 20 (Database Access Strategy)
# Schema Reference: docs/database.md Section 5 (All tables use UUID PK + timestamps)
#
# Design:
#   - All tables use UUID primary keys (gen_random_uuid() on PostgreSQL).
#   - All tables have created_at / updated_at TIMESTAMPTZ columns (except where
#     explicitly documented otherwise, e.g. verification_logs has no updated_at).
#   - The mixins reduce boilerplate without changing the schema.

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    """
    Declarative base for all ORM models.

    All models inherit from this base. SQLAlchemy uses Base.metadata
    to discover tables for Alembic migrations and schema reflection.
    """

    pass


class UUIDMixin:
    """
    Mixin providing a UUID primary key column.

    Every table in the documented schema uses:
        id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        comment="Unique identifier (UUID v4)",
    )


class TimestampMixin:
    """
    Mixin providing created_at and updated_at TIMESTAMPTZ columns.

    All tables except verification_logs have both columns.
    Defaults use server-side NOW() via func.now().
    updated_at is auto-set to NOW() on update via onupdate=func.now()
    (the PostgreSQL trigger does the same; this provides defense-in-depth).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Row creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last modification timestamp (UTC)",
    )
