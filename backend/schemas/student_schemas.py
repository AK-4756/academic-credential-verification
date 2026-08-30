# backend/schemas/student_schemas.py
# Student portal schemas.
#
# Architecture Reference: docs/backend.md Section 11.1 (Student Service Design)
# Dashboard: docs/backend.md lines 1568-1578 (Student Dashboard Response Schema)
# Endpoints: docs/backend.md Section 28.1 (Student Portal Endpoints)
# ShareLink: docs/backend.md line 1562-1566, Section 28.1 lines 3430-3434

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.constants import BlockchainStatus
from schemas.certificate_schemas import CertificateSummary, QRCodeInfo


class StudentProfile(BaseModel):
    """
    Student profile view.

    Student-specific fields from the Student ORM model + user-level info.
    """

    id: UUID
    user_id: UUID
    student_id_number: str | None = None
    date_of_birth: date | None = None
    nationality: str | None = None
    gender: str | None = None
    enrollment_year: int | None = None
    graduation_year: int | None = None
    primary_major: str | None = None
    secondary_major: str | None = None
    current_university_id: UUID | None = None
    profile_photo_url: str | None = None
    linkedin_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CredentialSummary(BaseModel):
    """
    Student-facing certificate list item.

    Docs Section 11.1 (get_my_credentials):
    Basic certificate info + blockchain_status + QR availability.
    Includes PENDING and REVOKED states.
    """

    id: UUID
    certificate_uid: str
    degree_title: str
    field_of_study: str
    university_name: str | None = None
    issue_date: date
    blockchain_status: BlockchainStatus
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CredentialDetail(BaseModel):
    """
    Student-facing certificate detail.

    Docs Section 11.1 (get_credential_detail) / Section 28.1:
    { certificate, qr_code, verification_url }
    """

    certificate: CertificateSummary
    qr_code: QRCodeInfo | None = None
    verification_url: str | None = None


class CredentialSummaryStats(BaseModel):
    """
    Credential count statistics for student dashboard.

    Docs Section 11.1 (lines 1571-1576):
    { total_credentials, confirmed_credentials, revoked_credentials, pending_credentials }
    """

    total_credentials: int = 0
    confirmed_credentials: int = 0
    revoked_credentials: int = 0
    pending_credentials: int = 0


class StudentDashboard(BaseModel):
    """
    Student dashboard response.

    Docs Section 11.1 (lines 1568-1578):
    { student_profile, credential_summary, recent_credentials: List[CertificateSummary] }
    """

    student_profile: StudentProfile
    credential_summary: CredentialSummaryStats
    recent_credentials: list[CertificateSummary] = Field(default_factory=list)


class ShareLinkResponse(BaseModel):
    """
    Share link response for student credential sharing.

    Docs Section 11.1 (line 1566) / Section 28.1 (lines 3432-3434):
    { verification_url, qr_image_url, qr_token, expires_at }
    """

    verification_url: str
    qr_image_url: str
    qr_token: str
    expires_at: datetime | None = None
