# backend/schemas/employer_schemas.py
# Employer portal schemas.
#
# Architecture Reference: docs/backend.md Section 12.1 (Employer Service Design)
# Dashboard: docs/backend.md lines 1624-1635 (Employer Dashboard Response Schema)
# Endpoints: docs/backend.md Section 28.1 (Employer Portal Endpoints)
# Profile Update: docs/backend.md line 3448-3451

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmployerProfile(BaseModel):
    """
    Employer profile response.

    Docs Section 12.1 (get_employer_profile):
    { company_name, industry, country, job_title, ... }
    Excludes internal user security fields.
    """

    id: UUID
    user_id: UUID
    company_name: str
    company_website: str | None = None
    industry: str | None = None
    company_size: str | None = None
    country: str | None = None
    city: str | None = None
    is_verified: bool
    verified_at: datetime | None = None
    job_title: str | None = None
    department: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployerProfileUpdate(BaseModel):
    """
    Employer profile update request.

    Docs Section 12.1 (update_employer_profile) / Section 28.1:
    PUT /employer/profile { company_name, industry, country, job_title }
    All fields optional — update only provided fields.
    """

    company_name: str | None = None
    company_website: str | None = None
    industry: str | None = None
    company_size: str | None = None
    country: str | None = None
    city: str | None = None
    job_title: str | None = None
    department: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class VerificationSummaryStats(BaseModel):
    """
    Verification count statistics for employer dashboard.

    Docs Section 12.1 (lines 1627-1633):
    { total_verifications, authentic_count, tampered_count, revoked_count, not_found_count }
    """

    total_verifications: int = 0
    authentic_count: int = 0
    tampered_count: int = 0
    revoked_count: int = 0
    not_found_count: int = 0


class EmployerDashboard(BaseModel):
    """
    Employer dashboard response.

    Docs Section 12.1 (lines 1624-1635):
    { employer_profile, verification_summary, recent_verifications: List[VerificationLogSummary] }
    """

    employer_profile: EmployerProfile
    verification_summary: VerificationSummaryStats
    recent_verifications: list = Field(default_factory=list)
