# backend/repositories/qr_verification_repository.py
# Data access for the 'qr_verifications' table.
#
# Architecture Reference: docs/backend.md Section 5.2 (Repository 07)
# Model Reference: models/qr_verification_model.py
#
# Methods (7 total):
#   Inherited: get_by_id, create, delete, list
#   Domain:    get_by_token, get_by_certificate_id,
#              increment_scan_count, deactivate,
#              get_active_by_certificate

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.qr_verification_model import QRVerification
from repositories.base_repository import BaseRepository

_UTC = timezone.utc


class QRVerificationRepository(BaseRepository[QRVerification]):
    """Repository for QRVerification entity managing QR code lifecycle."""

    model = QRVerification

    @classmethod
    async def get_by_token(
        cls, db: AsyncSession, token: str
    ) -> QRVerification | None:
        """
        Fetch a QR verification record by its opaque token (UNIQUE lookup).

        Primary lookup method for the QR scan verification flow.

        Args:
            db: Async database session.
            token: Cryptographically random opaque token string.

        Returns:
            The QRVerification instance, or None if not found.
        """
        stmt = select(QRVerification).where(QRVerification.token == token)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_certificate_id(
        cls, db: AsyncSession, cert_id: uuid.UUID
    ) -> QRVerification | None:
        """
        Fetch a QR verification record by certificate ID.

        A certificate may have multiple QR codes (active + deactivated).
        This returns the first match regardless of active status.

        Args:
            db: Async database session.
            cert_id: UUID of the certificate.

        Returns:
            The QRVerification instance, or None if not found.
        """
        stmt = select(QRVerification).where(
            QRVerification.certificate_id == cert_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def increment_scan_count(
        cls, db: AsyncSession, qr_id: uuid.UUID
    ) -> None:
        """
        Atomically increment the QR code scan counter and record scan time.

        Uses SQL-level increment for atomic concurrency safety.

        Args:
            db: Async database session.
            qr_id: UUID of the QR verification record.
        """
        stmt = (
            update(QRVerification)
            .where(QRVerification.id == qr_id)
            .values(
                total_scan_count=QRVerification.total_scan_count + 1,
                last_scanned_at=datetime.now(tz=_UTC),
            )
        )
        await db.execute(stmt)

    @classmethod
    async def deactivate(
        cls,
        db: AsyncSession,
        qr_id: uuid.UUID,
        reason: str | None = None,
    ) -> QRVerification | None:
        """
        Deactivate a QR code.

        Sets is_active=False, records deactivation timestamp and reason.

        Args:
            db: Async database session.
            qr_id: UUID of the QR verification record.
            reason: Optional reason for deactivation.

        Returns:
            The deactivated QRVerification, or None if not found.
        """
        stmt = select(QRVerification).where(QRVerification.id == qr_id)
        result = await db.execute(stmt)
        qr = result.scalar_one_or_none()
        if qr is None:
            return None
        qr.is_active = False
        qr.deactivated_at = datetime.now(tz=_UTC)
        qr.deactivated_reason = reason
        await db.flush()
        await db.refresh(qr)
        return qr

    @classmethod
    async def get_active_by_certificate(
        cls, db: AsyncSession, cert_id: uuid.UUID
    ) -> QRVerification | None:
        """
        Fetch the active QR code for a certificate.

        A partial unique index (uq_qr_one_active_per_certificate)
        ensures at most one active QR code per certificate.

        Args:
            db: Async database session.
            cert_id: UUID of the certificate.

        Returns:
            The active QRVerification, or None if no active QR exists.
        """
        stmt = select(QRVerification).where(
            QRVerification.certificate_id == cert_id,
            QRVerification.is_active.is_(True),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
