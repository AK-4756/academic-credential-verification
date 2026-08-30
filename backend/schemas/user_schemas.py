# backend/schemas/user_schemas.py
# User profile and management schemas.
#
# Architecture Reference: docs/backend.md Section 9.1 (User Service Design)
# Schema Reference: docs/backend.md lines 1414-1428 (User Profile Response Schema)
# Security Rule: NEVER include password_hash, reset_token_hash, email_verify_token
#   (docs/backend.md line 1426-1427, Design Decision A line 1433)

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import PASSWORD_MIN_LENGTH, UserRole


class UserSummary(BaseModel):
    """
    Compact user representation for references and login responses.

    Docs Section 7.1 (login response):
    { id, email, role, first_name, last_name, university_id }
    """

    id: UUID
    email: str
    role: UserRole
    first_name: str
    last_name: str
    university_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    """
    Full user profile response schema.

    Docs Section 9.1 (lines 1414-1428):
    { id, email, role, first_name, last_name, is_active, is_email_verified,
      last_login_at, university_id, created_at }

    SECURITY: password_hash, reset_token_hash, email_verify_token are NEVER included.
    """

    id: UUID
    email: str
    role: UserRole
    first_name: str
    last_name: str
    is_active: bool
    is_email_verified: bool
    last_login_at: datetime | None = None
    university_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChangePasswordRequest(BaseModel):
    """
    Password change request.

    Docs Section 9.1 (change_password service method):
    { old_password, new_password }
    """

    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """
        Docs Section 22.1 (password validation):
        - Min 8 characters
        - At least one uppercase
        - At least one lowercase
        - At least one number
        - Special characters optional for MVP
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v
