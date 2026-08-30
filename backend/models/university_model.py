# backend/models/university_model.py
# ORM model for the 'universities' table.
#
# Schema Reference: docs/database.md TABLE 1 (lines 554–635)
# Index Reference: docs/database.md Section 6 (idx_universities_*)

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.certificate_model import Certificate
    from models.student_model import Student
    from models.user_model import User


class University(UUIDMixin, TimestampMixin, Base):
    """
    Issuing institution entity.

    Wallet address is the Ethereum account authorized to sign
    storeCertificate() transactions on the CertificateRegistry smart contract.

    Table: universities
    """

    __tablename__ = "universities"

    # ─── Identity ─────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(300), nullable=False, unique=True, comment="Full institution name"
    )
    short_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        comment="Uppercase abbreviation for certificate_uid (e.g. MIT, OXFORD)",
    )
    country: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Country of the institution"
    )
    official_email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment="Official contact email"
    )
    website_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Institution website URL"
    )
    registration_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        comment="Government registration number",
    )

    # ─── Blockchain Identity ──────────────────────────────────
    wallet_address: Mapped[Optional[str]] = mapped_column(
        String(42),
        nullable=True,
        unique=True,
        comment="Checksummed Ethereum address (42 chars)",
    )

    # ─── Verification Status ──────────────────────────────────
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Verified by SUPER_ADMIN"
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="Timestamp of verification"
    )
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID of SUPER_ADMIN who verified (not a FK to avoid circular dep)",
    )

    # ─── Metadata ─────────────────────────────────────────────
    address_line: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Physical address"
    )
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="Contact phone number"
    )
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Logo image URL"
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Flexible additional attributes"
    )

    # ─── Soft Delete ──────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Soft delete flag"
    )
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="Timestamp of deactivation"
    )

    # ─── Relationships ────────────────────────────────────────
    users: Mapped[list[User]] = relationship(
        "User", back_populates="university", lazy="selectin"
    )
    certificates: Mapped[list[Certificate]] = relationship(
        "Certificate", back_populates="university", lazy="selectin"
    )
    students: Mapped[list[Student]] = relationship(
        "Student",
        back_populates="current_university",
        foreign_keys="Student.current_university_id",
        lazy="selectin",
    )

    # ─── Table Args (Constraints + Indexes) ───────────────────
    __table_args__ = (
        # Check constraints from database.md
        CheckConstraint(
            "wallet_address IS NULL OR wallet_address ~ '^0x[0-9a-fA-F]{40}$'",
            name="chk_universities_wallet_format",
        ),
        CheckConstraint(
            "short_code = UPPER(short_code)",
            name="chk_universities_short_code_uppercase",
        ),
        CheckConstraint(
            "LENGTH(short_code) BETWEEN 2 AND 20",
            name="chk_universities_short_code_length",
        ),
        CheckConstraint(
            "(is_verified = FALSE AND verified_at IS NULL) "
            "OR (is_verified = TRUE AND verified_at IS NOT NULL)",
            name="chk_universities_verified_consistency",
        ),
        CheckConstraint(
            "official_email ~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'",
            name="chk_universities_email_format",
        ),
        CheckConstraint(
            "website_url IS NULL OR website_url ~ '^https?://'",
            name="chk_universities_website_format",
        ),
        # Indexes from database.md Section 6
        Index(
            "idx_universities_is_verified",
            "is_verified",
            postgresql_where="is_verified = FALSE",
        ),
        Index("idx_universities_country", "country"),
        Index(
            "idx_universities_is_active",
            "is_active",
            postgresql_where="is_active = FALSE",
        ),
        {"comment": "Issuing institution entities"},
    )
