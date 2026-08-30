# backend/services/university_service.py
# University management service — registration, verification, wallet, dashboard.
#
# Architecture Reference: docs/backend.md Section 10.1 (University Service Design)
# Directory Reference: docs/backend.md Section 27.1 (services/university_service.py)

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    ConflictError,
    MissingWalletAddressError,
    OwnershipViolationError,
    UniversityAlreadyVerifiedError,
    UniversityNotFoundError,
    UnverifiedUniversityError,
)
from repositories import CertificateRepository, UniversityRepository


async def register_university(
    data: dict,
    db: AsyncSession,
):
    """
    Register a new university (starts unverified).

    Docs Section 10.1: register_university(data, db)
    Validates name and short_code uniqueness.

    Returns:
        University ORM instance.
    """
    async with db.begin():
        # Check name uniqueness
        existing_name = await UniversityRepository.get_by_name(db, data["name"])
        if existing_name is not None:
            raise ConflictError(message="A university with this name already exists")

        # Check short_code uniqueness
        short_code = data["short_code"].upper()
        existing_code = await UniversityRepository.get_by_short_code(db, short_code)
        if existing_code is not None:
            raise ConflictError(
                message="A university with this short code already exists"
            )

        data["short_code"] = short_code
        university = await UniversityRepository.create(db, data)

    return university


async def verify_university(
    university_id: UUID,
    verifying_admin_id: UUID,
    db: AsyncSession,
):
    """
    Verify a university (SUPER_ADMIN operation).

    Docs Section 10.1: verify_university(university_id, verifying_admin_id, db)
    Sets is_verified=True, verified_at=now, verified_by=admin_id.

    Raises:
        UniversityNotFoundError: If university does not exist.
        UniversityAlreadyVerifiedError: If already verified.
    """
    async with db.begin():
        university = await UniversityRepository.get_by_id(db, university_id)
        if university is None:
            raise UniversityNotFoundError()

        if university.is_verified:
            raise UniversityAlreadyVerifiedError()

        university = await UniversityRepository.set_verified(
            db, university_id, verifying_admin_id
        )

    return university


async def update_wallet_address(
    university_id: UUID,
    wallet_address: str,
    current_user,
    db: AsyncSession,
):
    """
    Update university's Ethereum wallet address.

    Docs Section 10.1: update_wallet_address(university_id, wallet_address, current_user, db)
    Validates:
    - Ownership (current_user.university_id == university_id)
    - University is verified
    - Wallet address uniqueness across universities

    Note: BlockchainService.is_authorized_issuer() check is logged but
    does NOT block the update (wallet may be authorized separately).
    Blockchain verification deferred to router/blockchain integration.

    Raises:
        OwnershipViolationError: If user does not own this university.
        UnverifiedUniversityError: If university is not verified.
        ConflictError: If wallet address already used by another university.
    """
    if current_user.university_id != university_id:
        raise OwnershipViolationError()

    async with db.begin():
        university = await UniversityRepository.get_by_id(db, university_id)
        if university is None:
            raise UniversityNotFoundError()

        if not university.is_verified:
            raise UnverifiedUniversityError()

        # Check wallet address uniqueness
        existing = await UniversityRepository.get_by_wallet_address(
            db, wallet_address
        )
        if existing is not None and existing.id != university_id:
            raise ConflictError(
                message="This wallet address is already used by another university"
            )

        university = await UniversityRepository.update_wallet_address(
            db, university_id, wallet_address
        )

    return university


async def get_university_dashboard_data(
    university_id: UUID,
    current_user,
    db: AsyncSession,
) -> dict:
    """
    Get university dashboard data.

    Docs Section 10.1: get_university_dashboard_data(university_id, current_user, db)
    Loads university + certificate counts by status.

    Raises:
        OwnershipViolationError: If user does not own this university.
        UniversityNotFoundError: If university not found.
    """
    if current_user.university_id != university_id:
        raise OwnershipViolationError()

    university = await UniversityRepository.get_by_id(db, university_id)
    if university is None:
        raise UniversityNotFoundError()

    # Get certificate statistics
    certs, total = await CertificateRepository.get_by_university(
        db, university_id, skip=0, limit=1000
    )

    stats = {
        "total": total,
        "confirmed": 0,
        "pending": 0,
        "revoked": 0,
        "failed": 0,
    }
    for cert in certs:
        status = cert.blockchain_status
        if status == "CONFIRMED":
            stats["confirmed"] += 1
        elif status in ("PENDING", "SUBMITTED"):
            stats["pending"] += 1
        elif status == "REVOKED":
            stats["revoked"] += 1
        elif status == "FAILED":
            stats["failed"] += 1

    # Recent certificates (latest 5)
    recent, _ = await CertificateRepository.get_by_university(
        db, university_id, skip=0, limit=5
    )

    return {
        "university": university,
        "stats": stats,
        "recent_certificates": recent,
    }
