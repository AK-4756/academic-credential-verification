# backend/services/student_credential_service.py
# Student credential view service — credential listing, detail, sharing, dashboard.
#
# Architecture Reference: docs/backend.md Section 11.1 (Student Service Design)
# Directory Reference: docs/backend.md Section 27.1 (services/student_credential_service.py)
#
# Students are passive recipients — they don't create certificates.
# This service provides the student's view of their credential portfolio.

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import BlockchainStatus
from core.exceptions import (
    CertificateNotFoundError,
    OwnershipViolationError,
    UnconfirmedCertificateError,
)
from repositories import (
    CertificateRepository,
    QRVerificationRepository,
    StudentRepository,
)


async def get_my_credentials(
    student_id: UUID,
    db: AsyncSession,
) -> list:
    """
    Get all credentials for a student (including revoked).

    Docs Section 11.1: get_my_credentials(current_user, db)
    Returns ALL certificates (active and revoked).
    Revoked certificates show with REVOKED status indicator.

    Args:
        student_id: The student's user ID used to look up their student record.
        db: Async database session.

    Returns:
        List of Certificate ORM instances.
    """
    student = await StudentRepository.get_by_user_id(db, student_id)
    if student is None:
        return []

    # active_only=False: include revoked certificates
    certificates = await CertificateRepository.get_by_student(
        db, student.id, active_only=False
    )
    return certificates


async def get_credential_detail(
    cert_id: UUID,
    current_user,
    db: AsyncSession,
) -> dict:
    """
    Get full credential detail for a student.

    Docs Section 11.1: get_credential_detail(cert_id, current_user, db)
    Validates: certificate.student_id matches current_user's student ID.
    Loads QR code info if available.

    Raises:
        CertificateNotFoundError: If certificate does not exist.
        OwnershipViolationError: If student does not own this certificate.
    """
    certificate = await CertificateRepository.get_by_id(db, cert_id)
    if certificate is None:
        raise CertificateNotFoundError()

    # Ownership check: student's student record must match
    student = await StudentRepository.get_by_user_id(db, current_user.id)
    if student is None or certificate.student_id != student.id:
        raise OwnershipViolationError()

    # Load QR code if available
    qr = await QRVerificationRepository.get_active_by_certificate(db, cert_id)

    return {
        "certificate": certificate,
        "qr_code": qr,
        "verification_url": (
            f"{_get_verification_base_url()}/{qr.token}" if qr else None
        ),
    }


async def get_share_link(
    cert_id: UUID,
    current_user,
    db: AsyncSession,
) -> dict:
    """
    Get or generate a share link for a credential.

    Docs Section 11.1: get_share_link(cert_id, current_user, db)
    Validates: ownership + CONFIRMED status.
    If no QR exists: the router layer should trigger QR generation first.

    Raises:
        CertificateNotFoundError: If certificate does not exist.
        OwnershipViolationError: If student does not own this certificate.
        UnconfirmedCertificateError: If certificate is not CONFIRMED.
    """
    certificate = await CertificateRepository.get_by_id(db, cert_id)
    if certificate is None:
        raise CertificateNotFoundError()

    student = await StudentRepository.get_by_user_id(db, current_user.id)
    if student is None or certificate.student_id != student.id:
        raise OwnershipViolationError()

    if certificate.blockchain_status != BlockchainStatus.CONFIRMED:
        raise UnconfirmedCertificateError()

    qr = await QRVerificationRepository.get_active_by_certificate(db, cert_id)

    base_url = _get_verification_base_url()
    if qr:
        return {
            "verification_url": f"{base_url}/{qr.token}",
            "qr_image_url": f"/api/v1/qr/image/{qr.token}",
            "qr_token": qr.token,
            "expires_at": qr.expires_at,
        }

    # No QR exists — return indicator that QR generation is needed
    return {
        "verification_url": None,
        "qr_image_url": None,
        "qr_token": None,
        "expires_at": None,
    }


async def get_student_dashboard(
    current_user,
    db: AsyncSession,
) -> dict:
    """
    Get student dashboard data.

    Docs Section 11.1 (Student Dashboard):
    { student_profile, credential_summary, recent_credentials }
    """
    student = await StudentRepository.get_by_user_id(db, current_user.id)

    if student is None:
        return {
            "student_profile": None,
            "credential_summary": {
                "total_credentials": 0,
                "confirmed_credentials": 0,
                "revoked_credentials": 0,
                "pending_credentials": 0,
            },
            "recent_credentials": [],
        }

    # Get all credentials (including revoked)
    all_certs = await CertificateRepository.get_by_student(
        db, student.id, active_only=False
    )

    # Compute stats
    confirmed = sum(
        1 for c in all_certs if c.blockchain_status == BlockchainStatus.CONFIRMED
    )
    revoked = sum(
        1 for c in all_certs if c.blockchain_status == BlockchainStatus.REVOKED
    )
    pending = sum(
        1
        for c in all_certs
        if c.blockchain_status in (BlockchainStatus.PENDING, BlockchainStatus.SUBMITTED)
    )

    return {
        "student_profile": student,
        "credential_summary": {
            "total_credentials": len(all_certs),
            "confirmed_credentials": confirmed,
            "revoked_credentials": revoked,
            "pending_credentials": pending,
        },
        "recent_credentials": all_certs[:5],
    }


def _get_verification_base_url() -> str:
    """Get the base URL for verification links."""
    from core.config import settings

    return settings.VERIFICATION_BASE_URL
