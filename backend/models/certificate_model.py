# backend/models/certificate_model.py
# ORM model for the 'certificates' table.
#
# Schema Reference: docs/database.md TABLE 5 (lines 994–1133)
# The core credential entity bridging off-chain records to on-chain hashes.

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    desc,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import BlockchainStatus
from database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.blockchain_transaction_model import BlockchainTransaction
    from models.qr_verification_model import QRVerification
    from models.university_model import University
    from models.user_model import User
    from models.verification_log_model import VerificationLog


class Certificate(UUIDMixin, TimestampMixin, Base):
    """
    Core credential entity.

    The sha256_hash column is the cryptographic bridge between this off-chain
    record and the on-chain CertificateRegistry contract. Core fields are
    immutable after blockchain_status = CONFIRMED (enforced by DB trigger).

    Table: certificates
    """

    __tablename__ = "certificates"

    # ─── Human-Readable Identifier ────────────────────────────
    certificate_uid: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        comment="Format: SHORTCODE-YYYY-NNNNN (e.g. MIT-2025-00142)",
    )

    # ─── Institutional Relationships ──────────────────────────
    university_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        comment="Issuing university",
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        comment="Recipient student (FK to users, not students table)",
    )
    issued_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        comment="UNIVERSITY_ADMIN who issued this certificate",
    )

    # ─── Credential Content (Immutable snapshot at issuance) ──
    recipient_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="SNAPSHOT: Student name at issuance (denormalized)",
    )
    recipient_email_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="SNAPSHOT: Student email at issuance",
    )
    degree_title: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="Degree title"
    )
    field_of_study: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="Field of study"
    )
    grade_classification: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Grade/classification (e.g. First Class)"
    )
    honors: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Honors (e.g. cum laude)"
    )
    issue_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="Certificate issue date"
    )
    expiry_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Certificate expiry date (if applicable)"
    )
    academic_year: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Academic year (e.g. 2024-2025)"
    )

    # ─── Cryptographic Integrity ──────────────────────────────
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment="SHA-256 hex digest of PDF binary (64 lowercase hex chars)",
    )

    # ─── Blockchain Anchoring ─────────────────────────────────
    blockchain_status: Mapped[BlockchainStatus] = mapped_column(
        ENUM(BlockchainStatus, name="blockchain_status", create_type=False),
        nullable=False,
        default=BlockchainStatus.PENDING,
        server_default="PENDING",
        comment="Current blockchain lifecycle state",
    )

    # ─── File Storage ─────────────────────────────────────────
    file_path: Mapped[str] = mapped_column(
        String(1000), nullable=False, comment="Server file path"
    )
    file_original_name: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Original upload filename"
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="File size in bytes (>0, ≤52428800)"
    )
    file_mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="application/pdf",
        server_default="application/pdf",
        comment="MIME type of certificate file",
    )

    # ─── Flexible Metadata ────────────────────────────────────
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Flexible additional attributes"
    )

    # ─── Lifecycle / Revocation ───────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="FALSE = revoked"
    )
    revocation_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Reason for revocation"
    )
    revoked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        comment="Admin who revoked this certificate",
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Revocation timestamp"
    )

    # ─── Relationships ────────────────────────────────────────
    university: Mapped[University] = relationship(
        "University", back_populates="certificates", lazy="selectin"
    )
    student: Mapped[User] = relationship(
        "User",
        back_populates="student_certificates",
        foreign_keys=[student_id],
        lazy="selectin",
    )
    issuer: Mapped[User] = relationship(
        "User",
        back_populates="issued_certificates",
        foreign_keys=[issued_by],
        lazy="selectin",
    )
    revoker: Mapped[Optional[User]] = relationship(
        "User", foreign_keys=[revoked_by], lazy="selectin"
    )
    blockchain_transactions: Mapped[list[BlockchainTransaction]] = relationship(
        "BlockchainTransaction", back_populates="certificate", lazy="noload"
    )
    qr_verifications: Mapped[list[QRVerification]] = relationship(
        "QRVerification", back_populates="certificate", lazy="noload"
    )
    verification_logs: Mapped[list[VerificationLog]] = relationship(
        "VerificationLog", back_populates="certificate", lazy="noload"
    )

    # ─── Table Args ───────────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "certificate_uid ~ '^[A-Z0-9]+-[0-9]{4}-[0-9]{5}$'",
            name="chk_certificates_uid_format",
        ),
        CheckConstraint(
            "sha256_hash ~ '^[0-9a-f]{64}$'",
            name="chk_certificates_sha256_format",
        ),
        CheckConstraint(
            "sha256_hash = LOWER(sha256_hash)",
            name="chk_certificates_sha256_lowercase",
        ),
        CheckConstraint(
            "expiry_date IS NULL OR expiry_date > issue_date",
            name="chk_certificates_expiry_after_issue",
        ),
        CheckConstraint(
            "issue_date >= '1900-01-01' AND issue_date <= CURRENT_DATE + INTERVAL '1 day'",
            name="chk_certificates_issue_date_reasonable",
        ),
        CheckConstraint(
            "file_size_bytes > 0",
            name="chk_certificates_file_size_positive",
        ),
        CheckConstraint(
            "file_size_bytes <= 52428800",
            name="chk_certificates_file_size_limit",
        ),
        CheckConstraint(
            "file_mime_type IN ('application/pdf', 'application/x-pdf')",
            name="chk_certificates_mime_type",
        ),
        CheckConstraint(
            "(is_active = TRUE AND revocation_reason IS NULL "
            "AND revoked_by IS NULL AND revoked_at IS NULL) "
            "OR (is_active = FALSE AND revocation_reason IS NOT NULL "
            "AND revoked_by IS NOT NULL AND revoked_at IS NOT NULL)",
            name="chk_certificates_revocation_consistency",
        ),
        CheckConstraint(
            "NOT (is_active = FALSE AND blockchain_status != 'REVOKED')",
            name="chk_certificates_blockchain_status_revoked_sync",
        ),
        CheckConstraint(
            "LENGTH(TRIM(recipient_name)) > 0",
            name="chk_certificates_recipient_name_not_empty",
        ),
        CheckConstraint(
            "LENGTH(TRIM(degree_title)) > 0",
            name="chk_certificates_degree_not_empty",
        ),
        # Indexes
        Index("idx_certificates_university_id", "university_id"),
        Index("idx_certificates_student_id", "student_id"),
        Index("idx_certificates_issued_by", "issued_by"),
        Index("idx_certificates_blockchain_status", "blockchain_status"),
        Index("idx_certificates_issue_date", desc("issue_date")),
        Index(
            "idx_certificates_is_active",
            "is_active",
            postgresql_where="is_active = FALSE",
        ),
        Index("idx_certificates_university_status", "university_id", "blockchain_status"),
        Index("idx_certificates_student_active", "student_id", "is_active"),
        Index("idx_certificates_university_issue_date", "university_id", desc("issue_date")),
        Index("idx_certificates_created_at", desc("created_at")),
        Index("idx_certificates_metadata_gin", "extra_metadata", postgresql_using="gin"),
        {"comment": "Core credential entity bridging off-chain to on-chain"},
    )
