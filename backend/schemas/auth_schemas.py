# backend/schemas/auth_schemas.py
# Authentication and registration schemas.
#
# Architecture Reference: docs/backend.md Section 7.1 (Authentication Service Design)
# Registration: docs/backend.md lines 1131-1151
# Login: docs/backend.md lines 1158, 1190-1194
# Validation: docs/backend.md Section 22.1 (Pydantic Layer 2)
# Role Restriction: registration role in [UNIVERSITY_ADMIN, STUDENT, EMPLOYER] — line 1138

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from core.constants import PASSWORD_MIN_LENGTH, UserRole
from schemas.user_schemas import UserSummary


# ─── Registration ────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    """
    User registration request.

    Docs Section 7.1 (lines 1131-1139):
    { email, password, first_name, last_name, role,
      university_code (if UNIVERSITY_ADMIN), company_name (if EMPLOYER) }

    Role is restricted to [UNIVERSITY_ADMIN, STUDENT, EMPLOYER] — SUPER_ADMIN excluded.
    """

    email: EmailStr
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: Literal[
        UserRole.UNIVERSITY_ADMIN,
        UserRole.STUDENT,
        UserRole.EMPLOYER,
    ]
    university_code: str | None = Field(
        default=None,
        description="Required if role is UNIVERSITY_ADMIN",
    )
    company_name: str | None = Field(
        default=None,
        description="Required if role is EMPLOYER",
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Docs Section 22.1: normalize email to lowercase."""
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Docs Section 22.1 (password validation):
        - Min 8 characters (enforced by Field)
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

    model_config = ConfigDict(str_strip_whitespace=True)


class RegisterResponse(BaseModel):
    """
    Registration response.

    Docs Section 7.1 (line 1151):
    { user_id, email, role, message: "Registration successful" }
    """

    user_id: UUID
    email: str
    role: str
    message: str = "Registration successful"


# ─── Login ───────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """
    Login request.

    Docs Section 7.1 (line 1158):
    { email, password }
    """

    email: EmailStr
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase for case-insensitive matching."""
        return v.lower()


class LoginResponse(BaseModel):
    """
    Login response.

    Docs Section 7.1 (lines 1190-1192):
    Body: { access_token, token_type: "bearer",
            user: { id, email, role, first_name, last_name, university_id } }
    """

    access_token: str
    token_type: str = "bearer"
    user: UserSummary


# ─── Token Refresh ───────────────────────────────────────────────────────────


class TokenRefreshResponse(BaseModel):
    """
    Token refresh response.

    Docs Section 7.1 (lines 1222):
    Body: { access_token }
    token_type included for consistency with LoginResponse.
    """

    access_token: str
    token_type: str = "bearer"
