# backend/repositories/refresh_token_repository.py
# Data access for the 'refresh_tokens' table.
#
# Architecture Reference: docs/backend.md Section 5.2 (Repository 09)
# Model Reference: models/refresh_token_model.py
#
# Methods (5 total):
#   create (custom signature), get_by_token_hash, revoke,
#   revoke_all_for_user, delete_expired
#
# Design Notes:
#   - create() has an explicit parameter signature rather than a generic
#     dict, matching the documented interface: create(user_id, token_hash,
#     expires_at, ip) → RefreshToken
#   - revoke() marks tokens as revoked (NOT hard delete)
#   - delete_expired() performs hard delete of expired+revoked tokens
#   - Extends BaseRepository for get_by_id and list if needed

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_token_model import RefreshToken
from repositories.base_repository import BaseRepository

_UTC = timezone.utc


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository for RefreshToken entity managing JWT refresh token lifecycle."""

    model = RefreshToken

    @classmethod
    async def create(  # type: ignore[override]
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        ip: str | None = None,
    ) -> RefreshToken:
        """
        Create a new refresh token record.

        Uses explicit parameters rather than a generic dict per the
        documented interface specification.

        Args:
            db: Async database session.
            user_id: UUID of the token owner.
            token_hash: SHA-256 hash of the raw refresh token (64 hex chars).
            expires_at: Token expiry timestamp.
            ip: Client IP address at token creation (optional).

        Returns:
            The newly created RefreshToken instance.
        """
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_ip=ip,
        )
        db.add(token)
        await db.flush()
        await db.refresh(token)
        return token

    @classmethod
    async def get_by_token_hash(
        cls, db: AsyncSession, token_hash: str
    ) -> RefreshToken | None:
        """
        Fetch a refresh token by its SHA-256 hash (UNIQUE lookup).

        Primary lookup method for the token refresh flow.

        Args:
            db: Async database session.
            token_hash: SHA-256 hash of the raw token (64 hex chars).

        Returns:
            The RefreshToken instance, or None if not found.
        """
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def revoke(
        cls,
        db: AsyncSession,
        token_id: uuid.UUID,
        replaced_by_id: uuid.UUID | None = None,
    ) -> None:
        """
        Revoke a single refresh token.

        Sets is_revoked=True, revoked_at=now(), and optionally links
        to the replacement token (for rotation chain tracking).

        Args:
            db: Async database session.
            token_id: UUID of the refresh token to revoke.
            replaced_by_id: UUID of the replacement token (optional).
        """
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(
                is_revoked=True,
                revoked_at=datetime.now(tz=_UTC),
                replaced_by=replaced_by_id,
            )
        )
        await db.execute(stmt)

    @classmethod
    async def revoke_all_for_user(
        cls, db: AsyncSession, user_id: uuid.UUID
    ) -> int:
        """
        Revoke all active refresh tokens for a user.

        Used during logout-all, password change, or account lockout.

        Args:
            db: Async database session.
            user_id: UUID of the user.

        Returns:
            Count of tokens revoked.
        """
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(
                is_revoked=True,
                revoked_at=datetime.now(tz=_UTC),
            )
        )
        result = await db.execute(stmt)
        return result.rowcount

    @classmethod
    async def delete_expired(cls, db: AsyncSession) -> int:
        """
        Hard-delete expired and revoked refresh tokens.

        Cleanup operation for housekeeping. Only deletes tokens that
        are both expired AND revoked to prevent accidental data loss.

        Args:
            db: Async database session.

        Returns:
            Count of tokens deleted.
        """
        stmt = sa_delete(RefreshToken).where(
            RefreshToken.expires_at < datetime.now(tz=_UTC),
            RefreshToken.is_revoked.is_(True),
        )
        result = await db.execute(stmt)
        return result.rowcount
