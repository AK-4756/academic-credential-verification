# backend/services/employer_service.py
# Employer management service — profile, verification history, dashboard.
#
# Architecture Reference: docs/backend.md Section 12.1 (Employer Service Design)
# Directory Reference: docs/backend.md Section 27.1 (services/employer_service.py)

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import VerificationResult
from core.exceptions import NotFoundError, OwnershipViolationError
from repositories import EmployerRepository, VerificationLogRepository


async def create_employer_profile(
    user_id: UUID,
    company_data: dict,
    db: AsyncSession,
):
    """
    Create an employer profile linked to a user account.

    Docs Section 12.1: create_employer_profile(user_id, company_data, db)
    Called by AuthService.register_user() when role=EMPLOYER.
    """
    data = {"user_id": user_id, **company_data}

    async with db.begin():
        employer = await EmployerRepository.create(db, data)

    return employer


async def get_employer_profile(
    user_id: UUID,
    db: AsyncSession,
):
    """
    Get employer profile by user ID.

    Docs Section 12.1: get_employer_profile(user_id, db)

    Raises:
        NotFoundError: If employer profile not found.
    """
    employer = await EmployerRepository.get_by_user_id(db, user_id)
    if employer is None:
        raise NotFoundError(message="Employer profile not found")
    return employer


async def update_employer_profile(
    user_id: UUID,
    update_data: dict,
    current_user,
    db: AsyncSession,
):
    """
    Update employer profile.

    Docs Section 12.1: update_employer_profile(user_id, data, current_user, db)
    Validates: ownership (current_user.id == user_id).

    Raises:
        OwnershipViolationError: If user tries to update another user's profile.
        NotFoundError: If employer profile not found.
    """
    if current_user.id != user_id:
        raise OwnershipViolationError()

    async with db.begin():
        employer = await EmployerRepository.get_by_user_id(db, user_id)
        if employer is None:
            raise NotFoundError(message="Employer profile not found")

        updated = await EmployerRepository.update(db, employer.id, update_data)

    return updated


async def get_employer_dashboard(
    current_user,
    db: AsyncSession,
) -> dict:
    """
    Get employer dashboard data.

    Docs Section 12.1 (Employer Dashboard):
    { employer_profile, verification_summary, recent_verifications }
    """
    employer = await EmployerRepository.get_by_user_id(db, current_user.id)
    if employer is None:
        raise NotFoundError(message="Employer profile not found")

    # Get verification history
    logs, total = await VerificationLogRepository.get_by_verifier(
        db, current_user.id, skip=0, limit=1000
    )

    # Compute stats
    stats = {
        "total_verifications": total,
        "authentic_count": 0,
        "tampered_count": 0,
        "revoked_count": 0,
        "not_found_count": 0,
    }
    for log in logs:
        if log.result == VerificationResult.AUTHENTIC:
            stats["authentic_count"] += 1
        elif log.result == VerificationResult.TAMPERED:
            stats["tampered_count"] += 1
        elif log.result == VerificationResult.REVOKED:
            stats["revoked_count"] += 1
        elif log.result == VerificationResult.NOT_FOUND:
            stats["not_found_count"] += 1

    # Recent verifications (latest 5)
    recent, _ = await VerificationLogRepository.get_by_verifier(
        db, current_user.id, skip=0, limit=5
    )

    return {
        "employer_profile": employer,
        "verification_summary": stats,
        "recent_verifications": recent,
    }


async def get_verification_history(
    current_user,
    skip: int,
    limit: int,
    db: AsyncSession,
) -> tuple:
    """
    Get paginated verification history for employer.

    Docs Section 12.1: get_verification_history(current_user, pagination, db)
    Employer-scoped: only returns logs where verifier_user_id == current_user.id.

    Returns:
        Tuple of (list[VerificationLog], total_count).
    """
    return await VerificationLogRepository.get_by_verifier(
        db, current_user.id, skip=skip, limit=limit
    )


async def get_verification_detail(
    verification_id: UUID,
    current_user,
    db: AsyncSession,
):
    """
    Get verification log detail.

    Docs Section 12.1: get_verification_result(verification_id, current_user, db)
    Validates: log.verifier_user_id == current_user.id (ownership).

    Raises:
        NotFoundError: If verification log not found.
        OwnershipViolationError: If employer does not own this verification.
    """
    log = await VerificationLogRepository.get_by_id(db, verification_id)
    if log is None:
        raise NotFoundError(message="Verification record not found")

    if log.verifier_user_id != current_user.id:
        raise OwnershipViolationError()

    return log
