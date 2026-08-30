# backend/services/student_service.py
# Student profile management.
#
# Architecture Reference: docs/backend.md Section 11.1 (Student Service Design)
# Directory Reference: docs/backend.md Section 27.1 (services/student_service.py)
#
# Note: Student credential operations are in student_credential_service.py.
# This service handles profile creation only (called by AuthService during registration).

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import StudentRepository


async def create_student_profile(
    user_id: UUID,
    profile_data: dict,
    db: AsyncSession,
):
    """
    Create a student profile linked to a user account.

    Docs Section 11.1: create_student_profile(user_id, profile_data, db)
    Called by AuthService.register_user() when role=STUDENT.

    Args:
        user_id: The user UUID.
        profile_data: Optional student-specific fields.
        db: Async database session.

    Returns:
        Student ORM instance.
    """
    data = {"user_id": user_id, **profile_data}

    async with db.begin():
        student = await StudentRepository.create(db, data)

    return student
