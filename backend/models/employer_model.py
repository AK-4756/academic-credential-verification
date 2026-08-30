# backend/models/employer_model.py
# ORM model for the 'employers' table.
#
# Schema Reference: docs/database.md TABLE 4 (lines 908–977)
# Relationship: One-to-one with users via user_id

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.user_model import User


class Employer(UUIDMixin, TimestampMixin, Base):
    """
    Employer-specific profile data extending the users table.

    One-to-one with users via user_id. Employers perform verifications;
    their company context is captured here for audit attribution.

    Table: employers
    """

    __tablename__ = "employers"

    # ─── Link to users ────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        comment="One-to-one link to users table",
    )

    # ─── Company Identity ─────────────────────────────────────
    company_name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="Company/organization name"
    )
    company_website: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Company website URL"
    )
    industry: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Industry sector"
    )
    company_size: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Company size range"
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Company country"
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Company city"
    )

    # ─── Employer Verification ────────────────────────────────
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Employer verified flag"
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True, comment="Verification timestamp"
    )

    # ─── Contact ──────────────────────────────────────────────
    job_title: Mapped[Optional[str]] = mapped_column(
        String(150), nullable=True, comment="Contact person job title"
    )
    department: Mapped[Optional[str]] = mapped_column(
        String(150), nullable=True, comment="Contact person department"
    )

    # ─── Profile Data ─────────────────────────────────────────
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Flexible additional attributes"
    )

    # ─── Relationships ────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="employer_profile", lazy="selectin"
    )

    # ─── Table Args ───────────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "LENGTH(TRIM(company_name)) > 0",
            name="chk_employers_company_name_not_empty",
        ),
        CheckConstraint(
            "company_website IS NULL OR company_website ~ '^https?://'",
            name="chk_employers_website_format",
        ),
        CheckConstraint(
            "(is_verified = FALSE AND verified_at IS NULL) "
            "OR (is_verified = TRUE AND verified_at IS NOT NULL)",
            name="chk_employers_verified_consistency",
        ),
        CheckConstraint(
            "company_size IS NULL OR company_size IN "
            "('1-10', '11-50', '51-200', '201-500', '501-1000', '1001-5000', '5000+')",
            name="chk_employers_company_size_values",
        ),
        # Indexes
        Index("idx_employers_company_name", "company_name"),
        Index("idx_employers_country", "country"),
        Index(
            "idx_employers_is_verified",
            "is_verified",
            postgresql_where="is_verified = FALSE",
        ),
        {"comment": "Employer-specific profile data extending users"},
    )
