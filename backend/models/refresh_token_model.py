# backend/models/refresh_token_model.py
# ORM model for the 'refresh_tokens' table.
#
# Schema Reference: docs/database.md SUPPLEMENTARY (lines 1634–1674)
# Auth infrastructure for JWT refresh token rotation.

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, UUIDMixin

if TYPE_CHECKING:
    from models.user_model import User


class RefreshToken(UUIDMixin, Base):
    """
    JWT refresh token registry.

    Raw token is never stored — only its SHA-256 hash.
    Token rotation: on use, old token is revoked and replaced_by
    points to the new token.

    NOTE: Does NOT use TimestampMixin. This table has created_at
    but no updated_at (tokens are revoked, not updated).

    Table: refresh_tokens
    """

    __tablename__ = "refresh_tokens"

    # ─── Owner ────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        comment="Token owner",
    )

    # ─── Token Hash ───────────────────────────────────────────
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment="SHA-256 hash of raw refresh token (64 hex chars)",
    )

    # ─── Lifecycle ────────────────────────────────────────────
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Token revocation status"
    )
    replaced_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID of replacement token (rotation chain)",
    )

    # ─── Timestamps ───────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Token creation timestamp",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Token expiry timestamp",
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Revocation timestamp"
    )

    # ─── Context ──────────────────────────────────────────────
    created_ip: Mapped[Optional[str]] = mapped_column(
        INET, nullable=True, comment="IP at token creation"
    )

    # ─── Relationships ────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="refresh_tokens", lazy="selectin"
    )
    replacement: Mapped[Optional[RefreshToken]] = relationship(
        "RefreshToken", remote_side="RefreshToken.id", lazy="noload"
    )

    # ─── Table Args ───────────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "LENGTH(token_hash) = 64",
            name="chk_refresh_token_hash_length",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="chk_refresh_token_expiry_future",
        ),
        CheckConstraint(
            "(is_revoked = FALSE AND revoked_at IS NULL) "
            "OR (is_revoked = TRUE AND revoked_at IS NOT NULL)",
            name="chk_refresh_token_revoked_consistency",
        ),
        # Indexes
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index(
            "idx_refresh_tokens_expires_at",
            "expires_at",
            postgresql_where="is_revoked = FALSE",
        ),
        {"comment": "JWT refresh token registry (SHA-256 hashed, rotation chain)"},
    )
