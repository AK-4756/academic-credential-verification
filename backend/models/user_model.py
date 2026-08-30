# backend/models/user_model.py
# ORM model for the 'users' table.
#
# Schema Reference: docs/database.md TABLE 2 (lines 671–769)
# Index Reference: docs/database.md Section 6 (idx_users_*)

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
    SmallInteger,
    String,
    desc,
)
from sqlalchemy.dialects.postgresql import ENUM, INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import UserRole
from database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.certificate_model import Certificate
    from models.employer_model import Employer
    from models.qr_verification_model import QRVerification
    from models.refresh_token_model import RefreshToken
    from models.student_model import Student
    from models.university_model import University
    from models.verification_log_model import VerificationLog


class User(UUIDMixin, TimestampMixin, Base):
    """
    Central authentication identity for all actors.

    Roles: SUPER_ADMIN, UNIVERSITY_ADMIN, STUDENT, EMPLOYER.
    Authentication logic is role-agnostic. Role-specific attributes
    live in dedicated extension tables (students, employers).

    Table: users
    """

    __tablename__ = "users"

    # ─── Authentication Identity ──────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment="Login email (lowercase)"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="bcrypt hash (cost 12)"
    )

    # ─── Role and Institutional Affiliation ───────────────────
    role: Mapped[UserRole] = mapped_column(
        ENUM(UserRole, name="user_role", create_type=False),
        nullable=False,
        comment="RBAC role",
    )
    university_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        comment="Required for UNIVERSITY_ADMIN, NULL for STUDENT/EMPLOYER",
    )

    # ─── Personal Identity ────────────────────────────────────
    first_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="First name"
    )
    last_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Last name"
    )
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="Phone number"
    )

    # ─── Account Status ───────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="Account active flag"
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Email verification status"
    )
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Email verification timestamp"
    )
    email_verify_token: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="Email verification token"
    )
    email_verify_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Email verification token expiry",
    )

    # ─── Security Controls ────────────────────────────────────
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last successful login"
    )
    last_login_ip: Mapped[Optional[str]] = mapped_column(
        INET, nullable=True, comment="IP of last successful login"
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="Consecutive failed logins"
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account locked until this timestamp",
    )
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last password change"
    )

    # ─── Password Reset ───────────────────────────────────────
    reset_token_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="SHA-256 hash of reset token"
    )
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Reset token expiry"
    )

    # ─── Relationships ────────────────────────────────────────
    university: Mapped[Optional[University]] = relationship(
        "University", back_populates="users", lazy="selectin"
    )
    student_profile: Mapped[Optional[Student]] = relationship(
        "Student", back_populates="user", uselist=False, lazy="selectin"
    )
    employer_profile: Mapped[Optional[Employer]] = relationship(
        "Employer", back_populates="user", uselist=False, lazy="selectin"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", lazy="noload"
    )
    issued_certificates: Mapped[list[Certificate]] = relationship(
        "Certificate",
        back_populates="issuer",
        foreign_keys="Certificate.issued_by",
        lazy="noload",
    )
    student_certificates: Mapped[list[Certificate]] = relationship(
        "Certificate",
        back_populates="student",
        foreign_keys="Certificate.student_id",
        lazy="noload",
    )
    qr_generations: Mapped[list[QRVerification]] = relationship(
        "QRVerification",
        back_populates="generator",
        foreign_keys="QRVerification.generated_by",
        lazy="noload",
    )
    verification_logs: Mapped[list[VerificationLog]] = relationship(
        "VerificationLog",
        back_populates="verifier",
        foreign_keys="VerificationLog.verifier_user_id",
        lazy="noload",
    )

    # ─── Table Args ───────────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "email ~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'",
            name="chk_users_email_format",
        ),
        CheckConstraint(
            "email = LOWER(email)",
            name="chk_users_email_lowercase",
        ),
        CheckConstraint(
            "LENGTH(TRIM(first_name)) > 0 AND LENGTH(TRIM(last_name)) > 0",
            name="chk_users_names_not_empty",
        ),
        CheckConstraint(
            "role != 'UNIVERSITY_ADMIN' OR university_id IS NOT NULL",
            name="chk_users_university_admin_requires_university",
        ),
        CheckConstraint(
            "role != 'STUDENT' OR university_id IS NULL",
            name="chk_users_student_no_university",
        ),
        CheckConstraint(
            "role != 'EMPLOYER' OR university_id IS NULL",
            name="chk_users_employer_no_university",
        ),
        CheckConstraint(
            "failed_login_attempts >= 0",
            name="chk_users_failed_attempts_non_negative",
        ),
        CheckConstraint(
            "(is_email_verified = FALSE AND email_verified_at IS NULL) "
            "OR (is_email_verified = TRUE AND email_verified_at IS NOT NULL)",
            name="chk_users_email_verified_consistency",
        ),
        CheckConstraint(
            "locked_until IS NULL OR locked_until > created_at",
            name="chk_users_lock_consistency",
        ),
        # Indexes
        Index("idx_users_role", "role"),
        Index(
            "idx_users_university_id",
            "university_id",
            postgresql_where="university_id IS NOT NULL",
        ),
        Index(
            "idx_users_is_active", "is_active", postgresql_where="is_active = FALSE"
        ),
        Index(
            "idx_users_locked_until",
            "locked_until",
            postgresql_where="locked_until IS NOT NULL",
        ),
        Index("idx_users_role_university", "role", "university_id"),
        Index("idx_users_created_at", desc("created_at")),
        {"comment": "Central authentication identity for all actors"},
    )
