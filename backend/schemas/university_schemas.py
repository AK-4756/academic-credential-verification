# backend/schemas/university_schemas.py
# University management schemas.
#
# Architecture Reference: docs/backend.md Section 10.1 (University Service Design)
# Wallet Validation: docs/backend.md Section 22.1 — regex ^0x[0-9a-fA-F]{40}$
# Dashboard: docs/backend.md Section 28.1 endpoint GET /universities/dashboard
# Directory: docs/backend.md Section 27.1 (schemas/university_schemas.py)

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import WALLET_ADDRESS_REGEX


class UniversitySummary(BaseModel):
    """
    Compact university representation for lists.

    Public fields appropriate for list views.
    """

    id: UUID
    name: str
    short_code: str
    country: str
    is_verified: bool
    logo_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UniversityDetail(BaseModel):
    """
    Comprehensive university profile.

    All public university fields; excludes internal audit-only fields.
    """

    id: UUID
    name: str
    short_code: str
    country: str
    official_email: str
    website_url: str | None = None
    registration_number: str | None = None
    wallet_address: str | None = None
    is_verified: bool
    verified_at: datetime | None = None
    address_line: str | None = None
    phone_number: str | None = None
    logo_url: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UniversityCertificateStats(BaseModel):
    """
    Certificate count statistics for the university dashboard.

    Derived from docs/backend.md Section 10.1 (get_university_dashboard_data):
    University + certificate counts by status.
    """

    total: int = 0
    confirmed: int = 0
    pending: int = 0
    revoked: int = 0
    failed: int = 0


class UniversityDashboard(BaseModel):
    """
    University dashboard response.

    Docs Section 10.1 (get_university_dashboard_data):
    Returns: UniversityDashboard (university + stats)
    Docs Section 28.1 endpoint spec includes recent_certificates.
    """

    university: UniversityDetail
    stats: UniversityCertificateStats
    recent_certificates: list = Field(default_factory=list)


class WalletUpdateRequest(BaseModel):
    """
    Wallet address update request.

    Docs Section 10.1 (update_wallet_address):
    { wallet_address } — validated format: 0x + 40 hex chars
    Docs Section 22.1: regex ^0x[0-9a-fA-F]{40}$
    """

    wallet_address: str

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet_address(cls, v: str) -> str:
        """Validate Ethereum wallet address format (0x + 40 hex chars)."""
        if not WALLET_ADDRESS_REGEX.match(v):
            raise ValueError(
                "Invalid wallet address format. Expected: 0x followed by 40 hex characters"
            )
        return v
