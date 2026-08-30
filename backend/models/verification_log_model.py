# backend/models/verification_log_model.py
# ORM model for the 'verification_logs' table.
#
# Schema Reference: docs/database.md TABLE 8 (lines 1474–1600)
# IMPORTANT: This table is APPEND-ONLY. No updated_at column.
# No update trigger. Rows are NEVER updated after INSERT.

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    desc,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM, INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import VerificationMethod, VerificationResult
from database.base import Base, UUIDMixin

if TYPE_CHECKING:
    from models.certificate_model import Certificate
    from models.qr_verification_model import QRVerification
    from models.user_model import User


class VerificationLog(UUIDMixin, Base):
    """
    Immutable audit log of every verification attempt.

    Rows are NEVER updated after INSERT — enforced by application convention.
    certificate_id is NULLABLE because tampered/not_found checks may not
    resolve to a known certificate. verifier_user_id is NULLABLE for
    public QR scans.

    NOTE: Does NOT use TimestampMixin because this table has no updated_at
    column (append-only by design).

    Table: verification_logs
    """

    __tablename__ = "verification_logs"

    # ─── What was verified ────────────────────────────────────
    certificate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certificates.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        comment="NULL for NOT_FOUND verifications",
    )
    certificate_uid_queried: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="UID searched by verifier"
    )

    # ─── Who verified ─────────────────────────────────────────
    verifier_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        comment="NULL for public QR scans",
    )

    # ─── QR Reference ─────────────────────────────────────────
    qr_verification_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("qr_verifications.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        comment="QR code used (if QR_SCAN method)",
    )

    # ─── How it was verified ──────────────────────────────────
    verification_method: Mapped[VerificationMethod] = mapped_column(
        ENUM(VerificationMethod, name="verification_method", create_type=False),
        nullable=False,
        comment="FILE_UPLOAD | QR_SCAN | MANUAL_ID_LOOKUP",
    )

    # ─── The Result ───────────────────────────────────────────
    result: Mapped[VerificationResult] = mapped_column(
        ENUM(VerificationResult, name="verification_result", create_type=False),
        nullable=False,
        comment="AUTHENTIC | TAMPERED | REVOKED | NOT_FOUND | PENDING_CHAIN | ERROR",
    )

    # ─── Cryptographic Evidence ───────────────────────────────
    submitted_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="SHA-256 hash from uploaded file"
    )
    stored_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="SHA-256 hash from blockchain"
    )
    hash_match: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, comment="TRUE if submitted == stored"
    )

    # ─── Blockchain Confirmation ──────────────────────────────
    blockchain_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="FALSE",
        comment="Whether blockchain was queried",
    )
    blockchain_tx_hash: Mapped[Optional[str]] = mapped_column(
        String(66), nullable=True, comment="TX hash of on-chain record"
    )
    blockchain_query_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Blockchain query latency in ms"
    )

    # ─── Snapshot for Self-Contained Audit ────────────────────
    university_name_snapshot: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True, comment="University name at verification time"
    )
    degree_title_snapshot: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True, comment="Degree title at verification time"
    )
    recipient_name_snapshot: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True, comment="Recipient name at verification time"
    )

    # ─── Network Context ─────────────────────────────────────
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET, nullable=True, comment="Verifier IP address"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Browser/client user agent"
    )
    country_code: Mapped[Optional[str]] = mapped_column(
        CHAR(2), nullable=True, comment="ISO 3166-1 alpha-2 country code"
    )
    referrer_url: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True, comment="HTTP referrer URL"
    )

    # ─── Performance ──────────────────────────────────────────
    processing_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Total processing time in ms"
    )

    # ─── Error Tracking ───────────────────────────────────────
    error_code: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Machine-readable error code"
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Human-readable error message"
    )

    # ─── When ─────────────────────────────────────────────────
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Verification timestamp",
    )

    # ─── Relationships ────────────────────────────────────────
    certificate: Mapped[Optional[Certificate]] = relationship(
        "Certificate", back_populates="verification_logs", lazy="selectin"
    )
    verifier: Mapped[Optional[User]] = relationship(
        "User",
        back_populates="verification_logs",
        foreign_keys=[verifier_user_id],
        lazy="selectin",
    )
    qr_verification: Mapped[Optional[QRVerification]] = relationship(
        "QRVerification",
        back_populates="verification_logs",
        foreign_keys=[qr_verification_id],
        lazy="selectin",
    )

    # ─── Table Args ───────────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "submitted_hash IS NULL OR submitted_hash ~ '^[0-9a-f]{64}$'",
            name="chk_vlog_submitted_hash_format",
        ),
        CheckConstraint(
            "stored_hash IS NULL OR stored_hash ~ '^[0-9a-f]{64}$'",
            name="chk_vlog_stored_hash_format",
        ),
        CheckConstraint(
            "blockchain_tx_hash IS NULL "
            "OR blockchain_tx_hash ~ '^0x[0-9a-fA-F]{64}$'",
            name="chk_vlog_blockchain_tx_format",
        ),
        CheckConstraint(
            "hash_match IS NULL "
            "OR (submitted_hash IS NOT NULL AND stored_hash IS NOT NULL)",
            name="chk_vlog_hash_match_consistency",
        ),
        CheckConstraint(
            "result != 'TAMPERED' "
            "OR (submitted_hash IS NOT NULL AND stored_hash IS NOT NULL)",
            name="chk_vlog_tampered_has_both_hashes",
        ),
        CheckConstraint(
            "result != 'AUTHENTIC' OR hash_match = TRUE",
            name="chk_vlog_authentic_hash_match",
        ),
        CheckConstraint(
            "verification_method != 'QR_SCAN' OR qr_verification_id IS NOT NULL",
            name="chk_vlog_qr_method_has_qr_id",
        ),
        CheckConstraint(
            "processing_time_ms IS NULL OR processing_time_ms >= 0",
            name="chk_vlog_processing_time_positive",
        ),
        CheckConstraint(
            "country_code IS NULL OR country_code ~ '^[A-Z]{2}$'",
            name="chk_vlog_country_code_format",
        ),
        # Indexes
        Index(
            "idx_vlog_certificate_id",
            "certificate_id",
            postgresql_where="certificate_id IS NOT NULL",
        ),
        Index(
            "idx_vlog_verifier_user_id",
            "verifier_user_id",
            postgresql_where="verifier_user_id IS NOT NULL",
        ),
        Index("idx_vlog_result", "result"),
        Index("idx_vlog_verified_at", desc("verified_at")),
        Index("idx_vlog_method", "verification_method"),
        Index("idx_vlog_ip_address", "ip_address"),
        Index(
            "idx_vlog_qr_verification_id",
            "qr_verification_id",
            postgresql_where="qr_verification_id IS NOT NULL",
        ),
        Index(
            "idx_vlog_certificate_verified_at",
            "certificate_id",
            desc("verified_at"),
            postgresql_where="certificate_id IS NOT NULL",
        ),
        Index("idx_vlog_result_verified_at", "result", desc("verified_at")),
        Index(
            "idx_vlog_tampered_only",
            desc("verified_at"),
            postgresql_where="result = 'TAMPERED'",
        ),
        {
            "comment": "Immutable audit log of every verification attempt (append-only)"
        },
    )
