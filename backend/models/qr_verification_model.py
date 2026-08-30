# backend/models/qr_verification_model.py
# ORM model for the 'qr_verifications' table.
#
# Schema Reference: docs/database.md TABLE 7 (lines 1357–1446)

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.certificate_model import Certificate
    from models.user_model import User
    from models.verification_log_model import VerificationLog


class QRVerification(UUIDMixin, TimestampMixin, Base):
    """
    QR code artifact table.

    Each active certificate has one QR code. The token column is a
    cryptographically random opaque value — it encodes no information
    about the certificate. Anyone with the URL can verify without
    authentication; the token is the access key.

    Table: qr_verifications
    """

    __tablename__ = "qr_verifications"

    # ─── Link to Certificate ──────────────────────────────────
    certificate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certificates.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        comment="Certificate this QR code represents",
    )

    # ─── QR Token ─────────────────────────────────────────────
    token: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        comment="Cryptographically random opaque token (min 32 chars)",
    )

    # ─── URLs ─────────────────────────────────────────────────
    verification_url: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="Full verification URL"
    )

    # ─── QR Image ─────────────────────────────────────────────
    qr_image_path: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True, comment="Server path to QR image file"
    )
    qr_image_size_px: Mapped[Optional[int]] = mapped_column(
        SmallInteger, nullable=True, comment="QR image dimensions (square)"
    )

    # ─── Usage Tracking ───────────────────────────────────────
    total_scan_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Monotonically increasing scan counter",
    )
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last scan timestamp"
    )
    last_scanned_ip: Mapped[Optional[str]] = mapped_column(
        INET, nullable=True, comment="IP of last scan"
    )

    # ─── Lifecycle ────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Active/deactivated"
    )
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Deactivation timestamp"
    )
    deactivated_reason: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Reason for deactivation"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Expiry timestamp (if applicable)"
    )

    # ─── Generation Metadata ──────────────────────────────────
    generated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        comment="Admin who generated this QR code",
    )

    # ─── Relationships ────────────────────────────────────────
    certificate: Mapped[Certificate] = relationship(
        "Certificate", back_populates="qr_verifications", lazy="selectin"
    )
    generator: Mapped[User] = relationship(
        "User",
        back_populates="qr_generations",
        foreign_keys=[generated_by],
        lazy="selectin",
    )
    verification_logs: Mapped[list[VerificationLog]] = relationship(
        "VerificationLog", back_populates="qr_verification", lazy="noload"
    )

    # ─── Table Args ───────────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "LENGTH(token) >= 32",
            name="chk_qr_token_length",
        ),
        CheckConstraint(
            "verification_url ~ '^https?://'",
            name="chk_qr_url_format",
        ),
        CheckConstraint(
            "total_scan_count >= 0",
            name="chk_qr_scan_count_non_negative",
        ),
        CheckConstraint(
            "qr_image_size_px IS NULL OR qr_image_size_px > 0",
            name="chk_qr_image_size_positive",
        ),
        CheckConstraint(
            "(is_active = TRUE AND deactivated_at IS NULL) "
            "OR (is_active = FALSE AND deactivated_at IS NOT NULL)",
            name="chk_qr_deactivation_consistency",
        ),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at",
            name="chk_qr_expiry_future",
        ),
        CheckConstraint(
            "(total_scan_count = 0 AND last_scanned_at IS NULL) "
            "OR (total_scan_count > 0 AND last_scanned_at IS NOT NULL)",
            name="chk_qr_scan_consistency",
        ),
        # Partial unique index: one active QR per certificate
        Index(
            "uq_qr_one_active_per_certificate",
            "certificate_id",
            unique=True,
            postgresql_where="is_active = TRUE",
        ),
        # Regular indexes
        Index("idx_qr_certificate_id", "certificate_id"),
        Index("idx_qr_is_active", "is_active", postgresql_where="is_active = TRUE"),
        Index(
            "idx_qr_expires_at",
            "expires_at",
            postgresql_where="expires_at IS NOT NULL",
        ),
        Index("idx_qr_generated_by", "generated_by"),
        {"comment": "QR code artifacts for certificate verification"},
    )
