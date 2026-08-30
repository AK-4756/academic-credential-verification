# backend/models/student_model.py
# ORM model for the 'students' table.
#
# Schema Reference: docs/database.md TABLE 3 (lines 801–881)
# Relationship: One-to-one with users via user_id

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    SmallInteger,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.university_model import University
    from models.user_model import User


class Student(UUIDMixin, TimestampMixin, Base):
    """
    Student-specific profile data extending the users table.

    One-to-one with users via user_id. A user with role=STUDENT
    must have a corresponding row in this table.

    Table: students
    """

    __tablename__ = "students"

    # ─── Link to users ────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        comment="One-to-one link to users table",
    )

    # ─── Student Identity ─────────────────────────────────────
    student_id_number: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Institutional student ID (e.g. MIT-20230042)"
    )
    date_of_birth: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="Date of birth"
    )
    nationality: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Nationality"
    )
    gender: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="Gender"
    )

    # ─── Academic Profile ─────────────────────────────────────
    enrollment_year: Mapped[Optional[int]] = mapped_column(
        SmallInteger, nullable=True, comment="Year of enrollment"
    )
    graduation_year: Mapped[Optional[int]] = mapped_column(
        SmallInteger, nullable=True, comment="Year of graduation"
    )
    primary_major: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Primary field of study"
    )
    secondary_major: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Secondary field of study"
    )
    current_university_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("universities.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        comment="Current/most-recent university affiliation",
    )

    # ─── Profile Data ─────────────────────────────────────────
    profile_photo_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Profile photo URL"
    )
    linkedin_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="LinkedIn profile URL"
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Flexible additional attributes"
    )

    # ─── Relationships ────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="student_profile", lazy="selectin"
    )
    current_university: Mapped[Optional[University]] = relationship(
        "University",
        back_populates="students",
        foreign_keys=[current_university_id],
        lazy="selectin",
    )

    # ─── Table Args ───────────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "graduation_year IS NULL OR enrollment_year IS NULL "
            "OR graduation_year >= enrollment_year",
            name="chk_students_graduation_after_enrollment",
        ),
        CheckConstraint(
            "enrollment_year IS NULL "
            "OR (enrollment_year BETWEEN 1900 AND EXTRACT(YEAR FROM NOW())::INT + 5)",
            name="chk_students_enrollment_year_range",
        ),
        CheckConstraint(
            "graduation_year IS NULL "
            "OR (graduation_year BETWEEN 1900 AND EXTRACT(YEAR FROM NOW())::INT + 10)",
            name="chk_students_graduation_year_range",
        ),
        CheckConstraint(
            "date_of_birth IS NULL "
            "OR (date_of_birth < CURRENT_DATE AND date_of_birth > '1900-01-01')",
            name="chk_students_dob_reasonable",
        ),
        CheckConstraint(
            "linkedin_url IS NULL "
            "OR linkedin_url ~ '^https?://(www\\.)?linkedin\\.com/'",
            name="chk_students_linkedin_format",
        ),
        # Indexes
        Index(
            "idx_students_current_university",
            "current_university_id",
            postgresql_where="current_university_id IS NOT NULL",
        ),
        Index("idx_students_graduation_year", "graduation_year"),
        Index("idx_students_nationality", "nationality"),
        {"comment": "Student-specific profile data extending users"},
    )
