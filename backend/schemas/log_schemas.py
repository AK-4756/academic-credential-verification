# backend/schemas/log_schemas.py
# Audit and verification log schemas.
#
# Architecture Reference: docs/backend.md Section 12.1, Section 28.1
# Endpoints:
#   GET /logs/ → PaginatedList[VerificationLogSummary]  (university admin)
#   GET /logs/{certificate_id} → PaginatedList[VerificationLogDetail]  (university admin / student)
#   GET /employer/verifications → PaginatedList[VerificationSummary]  (employer)
#   GET /employer/verifications/{id} → VerificationDetail  (employer)
# Directory: docs/backend.md Section 27.1 (schemas/log_schemas.py)

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.constants import VerificationMethod, VerificationResult


# ─── University Admin Views ──────────────────────────────────────────────────


class VerificationLogSummary(BaseModel):
    """
    Verification log list item for university admin views.

    Docs Section 28.1 (GET /logs/):
    Basic metadata of a past verification scan.
    """

    id: UUID
    certificate_id: UUID | None = None
    certificate_uid_queried: str | None = None
    verification_method: VerificationMethod
    result: VerificationResult
    verified_at: datetime
    ip_address: str | None = None

    model_config = ConfigDict(from_attributes=True)


class VerificationLogDetail(BaseModel):
    """
    Full verification log detail for university admin views.

    Docs Section 28.1 (GET /logs/{certificate_id}):
    Comprehensive log of a verification event.
    """

    id: UUID
    certificate_id: UUID | None = None
    certificate_uid_queried: str | None = None
    verifier_user_id: UUID | None = None
    qr_verification_id: UUID | None = None
    verification_method: VerificationMethod
    result: VerificationResult
    submitted_hash: str | None = None
    stored_hash: str | None = None
    hash_match: bool | None = None
    blockchain_verified: bool
    blockchain_tx_hash: str | None = None
    blockchain_query_time_ms: int | None = None
    university_name_snapshot: str | None = None
    degree_title_snapshot: str | None = None
    recipient_name_snapshot: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    country_code: str | None = None
    referrer_url: str | None = None
    processing_time_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    verified_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Employer Views ──────────────────────────────────────────────────────────


class VerificationSummary(BaseModel):
    """
    Employer-centric verification list item.

    Docs Section 28.1 (GET /employer/verifications):
    Compact view of a past verification event.
    """

    id: UUID
    certificate_uid_queried: str | None = None
    result: VerificationResult
    verified_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerificationDetail(BaseModel):
    """
    Employer-centric full verification detail.

    Docs Section 28.1 (GET /employer/verifications/{id}):
    Full detail including certificate info, blockchain proof, tamper evidence.
    """

    id: UUID
    certificate_uid_queried: str | None = None
    verification_method: VerificationMethod
    result: VerificationResult
    submitted_hash: str | None = None
    stored_hash: str | None = None
    hash_match: bool | None = None
    blockchain_verified: bool
    blockchain_tx_hash: str | None = None
    blockchain_query_time_ms: int | None = None
    university_name_snapshot: str | None = None
    degree_title_snapshot: str | None = None
    recipient_name_snapshot: str | None = None
    processing_time_ms: int | None = None
    verified_at: datetime

    model_config = ConfigDict(from_attributes=True)
