# backend/services/qr_verification_service.py
# QR verification service — QR code lifecycle management.
#
# Architecture Reference: docs/backend.md Section 17.1 (QR Verification Service)
# Directory Reference: docs/backend.md Section 27.1 (services/qr_verification_service.py)
#
# Token generation: secrets.token_urlsafe(48) -> 64-char URL-safe string
# Uniqueness: DB UNIQUE constraint + retry on collision
# Lifecycle: Created on CONFIRMED, deactivated old before creating new

from __future__ import annotations

import secrets
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.constants import BlockchainStatus
from core.exceptions import (
    CertificateNotFoundError,
    QRTokenNotFoundError,
    UnconfirmedCertificateError,
)
from repositories import CertificateRepository, QRVerificationRepository


async def generate_qr_for_certificate(
    cert_id: UUID,
    generated_by_user_id: UUID,
    db: AsyncSession,
) -> dict:
    """
    Generate a QR code token for a certificate.

    Docs Section 17.1: generate_qr_for_certificate(cert_id, generated_by_user_id, db)
    1. Validate: certificate exists and blockchain_status == CONFIRMED
    2. Deactivate existing active QR (if any)
    3. Generate: token = secrets.token_urlsafe(48) -> 64 chars
    4. Build: verification_url
    5. Create: QRVerification record

    Note: QR image generation (via qrcode library) is deferred to
    utils/qr_generator_service.py which will be implemented when
    the router needs to serve QR images.

    Args:
        cert_id: Certificate UUID.
        generated_by_user_id: User who initiated QR generation.
        db: Async database session.

    Returns:
        Dict with token, verification_url, qr_id.

    Raises:
        CertificateNotFoundError: If certificate not found.
        UnconfirmedCertificateError: If not CONFIRMED status.
    """
    async with db.begin():
        certificate = await CertificateRepository.get_by_id(db, cert_id)
        if certificate is None:
            raise CertificateNotFoundError()

        if certificate.blockchain_status != BlockchainStatus.CONFIRMED:
            raise UnconfirmedCertificateError()

        # Deactivate existing active QR
        existing_qr = await QRVerificationRepository.get_active_by_certificate(
            db, cert_id
        )
        if existing_qr is not None:
            await QRVerificationRepository.deactivate(
                db, existing_qr.id, reason="Replaced by new QR code"
            )

        # Generate token (64-char URL-safe string)
        token = secrets.token_urlsafe(48)

        verification_url = f"{settings.VERIFICATION_BASE_URL}/{token}"

        # Create QR record
        qr_data = {
            "certificate_id": cert_id,
            "token": token,
            "verification_url": verification_url,
            "generated_by": generated_by_user_id,
            "is_active": True,
        }
        qr = await QRVerificationRepository.create(db, qr_data)

    return {
        "qr_id": qr.id,
        "token": token,
        "verification_url": verification_url,
    }


async def get_qr_by_token(
    token: str,
    db: AsyncSession,
):
    """
    Look up a QR verification record by token.

    Docs Section 17.1: get_qr_by_token(token, db)

    Raises:
        QRTokenNotFoundError: If token not found.
    """
    qr = await QRVerificationRepository.get_by_token(db, token)
    if qr is None:
        raise QRTokenNotFoundError()
    return qr
