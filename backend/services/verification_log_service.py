# backend/services/verification_log_service.py
# Verification log service — append-only audit log for verification events.
#
# Architecture Reference: docs/backend.md Section 16.1 (Verification logging)
# Directory Reference: docs/backend.md Section 27.1 (services/verification_log_service.py)
#
# Append-only: logs are never updated or deleted.
# The verification_service.py uses _record_log() internally,
# but this service is exposed for direct log operations.

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import VerificationLogRepository


async def create_verification_log(
    log_data: dict,
    db: AsyncSession,
):
    """
    Create a verification log entry.

    Append-only — no update or delete operations.

    Args:
        log_data: Dict with verification log fields.
        db: Async database session.

    Returns:
        VerificationLog ORM instance.
    """
    async with db.begin():
        log = await VerificationLogRepository.create(db, log_data)
    return log


async def get_logs_for_certificate(
    certificate_id: UUID,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = None,
) -> tuple:
    """
    Get paginated verification logs for a certificate.

    Args:
        certificate_id: Certificate UUID.
        skip: Offset for pagination.
        limit: Page size.
        db: Async database session.

    Returns:
        Tuple of (list[VerificationLog], total_count).
    """
    return await VerificationLogRepository.get_by_certificate(
        db, certificate_id, skip=skip, limit=limit
    )


async def get_logs_by_verifier(
    verifier_id: UUID,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = None,
) -> tuple:
    """
    Get paginated verification logs by verifier.

    Args:
        verifier_id: Verifier user UUID.
        skip: Offset for pagination.
        limit: Page size.
        db: Async database session.

    Returns:
        Tuple of (list[VerificationLog], total_count).
    """
    return await VerificationLogRepository.get_by_verifier(
        db, verifier_id, skip=skip, limit=limit
    )
