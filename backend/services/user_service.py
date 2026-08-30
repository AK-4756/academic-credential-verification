# backend/services/user_service.py
# User management service — profile, password change, account deactivation.
#
# Architecture Reference: docs/backend.md Section 9.1 (User Service Design)
# Directory Reference: docs/backend.md Section 27.1 (services/user_service.py)
#
# Ownership checks are in the service layer per Design Decision A (Section 8):
#   "Ownership checks are implemented in the service layer, not in the
#    repository layer or API layer."

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import UserRole
from core.exceptions import (
    InvalidCredentialsError,
    OwnershipViolationError,
    UserNotFoundError,
)
from core.security import hash_password, verify_password
from repositories import RefreshTokenRepository, UserRepository


async def get_user_by_id(
    user_id: UUID,
    db: AsyncSession,
):
    """
    Get user by ID. Validates existence and active status.

    Docs Section 9.1: get_user_by_id(user_id, db)

    Raises:
        UserNotFoundError: If user does not exist or is inactive.
    """
    user = await UserRepository.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise UserNotFoundError()
    return user


async def update_profile(
    user_id: UUID,
    update_data: dict,
    current_user,
    db: AsyncSession,
):
    """
    Update user profile. Self-update only.

    Docs Section 9.1: update_profile(user_id, update_data, current_user, db)
    Validates: current_user.id == user_id (self-update only)

    Raises:
        OwnershipViolationError: If user tries to update another user's profile.
        UserNotFoundError: If user not found.
    """
    if current_user.id != user_id:
        raise OwnershipViolationError()

    async with db.begin():
        updated = await UserRepository.update(db, user_id, update_data)
        if updated is None:
            raise UserNotFoundError()

    return updated


async def change_password(
    user_id: UUID,
    old_password: str,
    new_password: str,
    current_user,
    db: AsyncSession,
) -> None:
    """
    Change user password.

    Docs Section 9.1: change_password(user_id, old_password, new_password, current_user, db)
    1. Validates ownership (current_user.id == user_id)
    2. Validates old password matches stored hash
    3. Hashes new password
    4. Updates password_hash + password_changed_at
    5. Revokes ALL refresh tokens (security best practice)

    Raises:
        OwnershipViolationError: If user tries to change another user's password.
        InvalidCredentialsError: If old password is incorrect.
        UserNotFoundError: If user not found.
    """
    if current_user.id != user_id:
        raise OwnershipViolationError()

    async with db.begin():
        user = await UserRepository.get_by_id(db, user_id)
        if user is None:
            raise UserNotFoundError()

        if not verify_password(old_password, user.password_hash):
            raise InvalidCredentialsError(message="Current password is incorrect")

        new_hash = hash_password(new_password)
        await UserRepository.update(db, user_id, {"password_hash": new_hash})

        # Revoke all refresh tokens — forces re-login on all devices
        await RefreshTokenRepository.revoke_all_for_user(db, user_id)


async def deactivate_account(
    user_id: UUID,
    current_user,
    db: AsyncSession,
) -> None:
    """
    Deactivate (soft-delete) a user account.

    Docs Section 9.1: deactivate_account(user_id, current_user, db)
    Validates: ownership (self) or SUPER_ADMIN role.
    Soft deletes user (is_active = False) and revokes all refresh tokens.

    Raises:
        OwnershipViolationError: If non-SUPER_ADMIN tries to deactivate another user.
        UserNotFoundError: If user not found.
    """
    if current_user.id != user_id and current_user.role != UserRole.SUPER_ADMIN:
        raise OwnershipViolationError()

    async with db.begin():
        user = await UserRepository.get_by_id(db, user_id)
        if user is None:
            raise UserNotFoundError()

        await UserRepository.delete(db, user_id)
        await RefreshTokenRepository.revoke_all_for_user(db, user_id)
