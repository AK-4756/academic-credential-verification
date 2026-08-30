# backend/repositories/verification_log_repository.py
# Data access for the 'verification_logs' table.
#
# Architecture Reference: docs/backend.md Section 5.2 (Repository 08)
# Model Reference: models/verification_log_model.py
#
# Methods (4 total):
#   create, get_by_certificate, get_by_verifier, get_recent_by_ip
#
# APPEND-ONLY TABLE: No update() or delete() methods by design.
# The verification_logs table is an immutable audit log — rows are
# only inserted, never modified or removed.

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.verification_log_model import VerificationLog
from repositories.base_repository import BaseRepository

_UTC = timezone.utc


class VerificationLogRepository(BaseRepository[VerificationLog]):
    """
    Repository for VerificationLog entity (append-only audit log).

    This table is append-only by design. No update() or delete()
    methods are exposed — the base class methods exist but must
    not be called by services for this entity.
    """

    model = VerificationLog

    @classmethod
    async def create(
        cls, db: AsyncSession, data: dict[str, Any]
    ) -> VerificationLog:
        """
        Insert a new verification log entry.

        Args:
            db: Async database session.
            data: Dictionary mapping column names to values.

        Returns:
            The newly created VerificationLog instance.
        """
        instance = VerificationLog(**data)
        db.add(instance)
        await db.flush()
        await db.refresh(instance)
        return instance

    @classmethod
    async def get_by_certificate(
        cls,
        db: AsyncSession,
        cert_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[VerificationLog], int]:
        """
        Paginated listing of verification logs for a certificate.

        Args:
            db: Async database session.
            cert_id: UUID of the certificate.
            skip: Number of records to skip (offset).
            limit: Maximum records to return.

        Returns:
            Tuple of (logs, total_count).
        """
        base_stmt = select(VerificationLog).where(
            VerificationLog.certificate_id == cert_id
        )

        # Total count
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Paginated items ordered by most recent first
        stmt = (
            base_stmt.order_by(desc(VerificationLog.verified_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    @classmethod
    async def get_by_verifier(
        cls,
        db: AsyncSession,
        verifier_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[VerificationLog], int]:
        """
        Paginated listing of verification logs by verifier user.

        Args:
            db: Async database session.
            verifier_id: UUID of the verifier user.
            skip: Number of records to skip (offset).
            limit: Maximum records to return.

        Returns:
            Tuple of (logs, total_count).
        """
        base_stmt = select(VerificationLog).where(
            VerificationLog.verifier_user_id == verifier_id
        )

        # Total count
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Paginated items ordered by most recent first
        stmt = (
            base_stmt.order_by(desc(VerificationLog.verified_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    @classmethod
    async def get_recent_by_ip(
        cls, db: AsyncSession, ip_address: str, minutes: int
    ) -> list[VerificationLog]:
        """
        Fetch recent verification attempts from an IP address.

        Used for rate-abuse detection in the verification flow.

        Args:
            db: Async database session.
            ip_address: Client IP address.
            minutes: Lookback window in minutes.

        Returns:
            List of VerificationLog instances from the IP within the window.
        """
        cutoff = datetime.now(tz=_UTC) - timedelta(minutes=minutes)
        stmt = (
            select(VerificationLog)
            .where(
                VerificationLog.ip_address == ip_address,
                VerificationLog.verified_at >= cutoff,
            )
            .order_by(desc(VerificationLog.verified_at))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
