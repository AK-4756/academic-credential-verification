# backend/repositories/certificate_repository.py
# Data access for the 'certificates' table.
#
# Architecture Reference: docs/backend.md Section 5.2 (Repository 05)
# Model Reference: models/certificate_model.py
#
# Methods (10 total):
#   Inherited: get_by_id, create, delete, list
#   Domain:    get_by_uid, get_by_hash, update_blockchain_status,
#              get_by_student, get_by_university, revoke,
#              get_next_uid_sequence, get_confirmed_count_by_university
#
# Critical queries:
#   get_by_hash: indexed lookup for verification flow
#   get_by_uid: maps to blockchain contract key
#   get_next_uid_sequence: atomic sequence generation

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import BlockchainStatus
from models.certificate_model import Certificate
from repositories.base_repository import BaseRepository

_UTC = timezone.utc


class CertificateRepository(BaseRepository[Certificate]):
    """Repository for Certificate entity CRUD and lifecycle queries."""

    model = Certificate

    @classmethod
    async def get_by_uid(
        cls, db: AsyncSession, certificate_uid: str
    ) -> Certificate | None:
        """
        Fetch a certificate by its human-readable UID (UNIQUE lookup).

        Format: SHORTCODE-YYYY-NNNNN (e.g., "MIT-2025-00142").
        Maps to the blockchain contract key.

        Args:
            db: Async database session.
            certificate_uid: Certificate UID string.

        Returns:
            The Certificate instance, or None if not found.
        """
        stmt = select(Certificate).where(
            Certificate.certificate_uid == certificate_uid
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_hash(
        cls, db: AsyncSession, sha256_hash: str
    ) -> Certificate | None:
        """
        Fetch a certificate by its SHA-256 file hash (UNIQUE, indexed).

        Primary lookup method for the verification flow.

        Args:
            db: Async database session.
            sha256_hash: 64-char lowercase hex SHA-256 digest.

        Returns:
            The Certificate instance, or None if not found.
        """
        stmt = select(Certificate).where(
            Certificate.sha256_hash == sha256_hash
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def update_blockchain_status(
        cls,
        db: AsyncSession,
        cert_id: uuid.UUID,
        status: BlockchainStatus,
        tx_hash: str | None = None,
    ) -> Certificate | None:
        """
        Update a certificate's blockchain lifecycle status.

        Called after blockchain transaction confirmation or failure.

        Args:
            db: Async database session.
            cert_id: UUID of the certificate.
            status: New BlockchainStatus enum value.
            tx_hash: Ethereum transaction hash (optional).

        Returns:
            The updated Certificate, or None if not found.
        """
        stmt = select(Certificate).where(Certificate.id == cert_id)
        result = await db.execute(stmt)
        cert = result.scalar_one_or_none()
        if cert is None:
            return None
        cert.blockchain_status = status
        await db.flush()
        await db.refresh(cert)
        return cert

    @classmethod
    async def get_by_student(
        cls,
        db: AsyncSession,
        student_id: uuid.UUID,
        active_only: bool = True,
    ) -> list[Certificate]:
        """
        Fetch all certificates for a student.

        Args:
            db: Async database session.
            student_id: UUID of the student (FK to users.id).
            active_only: If True, exclude revoked certificates.

        Returns:
            List of Certificate instances.
        """
        stmt = select(Certificate).where(
            Certificate.student_id == student_id
        )
        if active_only:
            stmt = stmt.where(Certificate.is_active.is_(True))
        stmt = stmt.order_by(desc(Certificate.issue_date))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_by_university(
        cls,
        db: AsyncSession,
        university_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        filters: dict | None = None,
    ) -> tuple[list[Certificate], int]:
        """
        Paginated listing of certificates for a university.

        Args:
            db: Async database session.
            university_id: UUID of the issuing university.
            skip: Number of records to skip (offset).
            limit: Maximum records to return.
            filters: Optional additional equality filters.

        Returns:
            Tuple of (certificates, total_count).
        """
        stmt = select(Certificate).where(
            Certificate.university_id == university_id
        )
        if filters:
            for key, value in filters.items():
                if hasattr(Certificate, key):
                    stmt = stmt.where(getattr(Certificate, key) == value)

        # Total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Paginated items
        stmt = stmt.order_by(desc(Certificate.issue_date))
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    @classmethod
    async def revoke(
        cls,
        db: AsyncSession,
        cert_id: uuid.UUID,
        reason: str,
        revoked_by: uuid.UUID,
    ) -> Certificate | None:
        """
        Revoke a certificate.

        Sets is_active=False, records revocation reason, revoker, timestamp,
        and updates blockchain_status to REVOKED.

        Args:
            db: Async database session.
            cert_id: UUID of the certificate to revoke.
            reason: Human-readable revocation reason.
            revoked_by: UUID of the admin performing revocation.

        Returns:
            The revoked Certificate, or None if not found.
        """
        stmt = select(Certificate).where(Certificate.id == cert_id)
        result = await db.execute(stmt)
        cert = result.scalar_one_or_none()
        if cert is None:
            return None
        cert.is_active = False
        cert.revocation_reason = reason
        cert.revoked_by = revoked_by
        cert.revoked_at = datetime.now(tz=_UTC)
        cert.blockchain_status = BlockchainStatus.REVOKED
        await db.flush()
        await db.refresh(cert)
        return cert

    @classmethod
    async def get_next_uid_sequence(
        cls, db: AsyncSession, university_short_code: str, year: int
    ) -> int:
        """
        Get the next available sequence number for certificate UID generation.

        UID format: SHORTCODE-YYYY-NNNNN. Finds the maximum existing
        sequence for the given short code and year, then returns max + 1.

        Concurrency note (from docs Section 10.1): If concurrent issuances
        produce a duplicate UID, the UNIQUE constraint on certificate_uid
        triggers a conflict, allowing the service to retry safely.

        Args:
            db: Async database session.
            university_short_code: Uppercase university abbreviation.
            year: 4-digit issuance year.

        Returns:
            Next sequence number (1-based).
        """
        prefix = f"{university_short_code}-{year}-"
        stmt = (
            select(Certificate.certificate_uid)
            .where(Certificate.certificate_uid.like(f"{prefix}%"))
            .order_by(desc(Certificate.certificate_uid))
            .limit(1)
        )
        max_uid = (await db.execute(stmt)).scalar_one_or_none()
        if max_uid is None:
            return 1
        # Extract the 5-digit sequence from "SHORTCODE-YYYY-NNNNN"
        sequence_str = max_uid.rsplit("-", 1)[-1]
        return int(sequence_str) + 1

    @classmethod
    async def get_confirmed_count_by_university(
        cls, db: AsyncSession, university_id: uuid.UUID
    ) -> int:
        """
        Count certificates with CONFIRMED blockchain status for a university.

        Args:
            db: Async database session.
            university_id: UUID of the university.

        Returns:
            Count of confirmed certificates.
        """
        stmt = (
            select(func.count())
            .select_from(Certificate)
            .where(
                Certificate.university_id == university_id,
                Certificate.blockchain_status == BlockchainStatus.CONFIRMED,
            )
        )
        result = (await db.execute(stmt)).scalar() or 0
        return result
