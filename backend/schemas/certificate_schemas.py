# backend/schemas/certificate_schemas.py
# Certificate issuance, confirmation, and revocation schemas.
#
# Architecture Reference:
#   docs/backend.md Section 14.1 (Certificate Issuance Service)
#   docs/backend.md Section 15.1 (Certificate Revocation Service)
#   docs/backend.md Section 28.1 (Endpoint specifications)
#   docs/backend.md Section 22.1 (Validation rules)
#
# Validation Rules (from Section 22.1):
#   sha256_hash: ^[0-9a-f]{64}$
#   tx_hash: ^0x[0-9a-fA-F]{64}$
#   issue_date: not in the future
#   degree_title: <= 300 chars
#   field_of_study: <= 300 chars
#   revocation reason: min 10, max 500 chars

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from core.constants import (
    DEGREE_TITLE_MAX_LENGTH,
    FIELD_OF_STUDY_MAX_LENGTH,
    HASH_FORMAT_REGEX,
    REVOCATION_REASON_MAX_LENGTH,
    REVOCATION_REASON_MIN_LENGTH,
    TX_HASH_REGEX,
    BlockchainStatus,
)


# ─── Issuance ────────────────────────────────────────────────────────────────


class CertificateIssueRequest(BaseModel):
    """
    Certificate issuance metadata (accompanying the PDF file upload).

    Docs Section 14.1 (lines 1698-1721):
    File upload (UploadFile) is handled at the router layer (Phase 7).
    This schema validates only the metadata fields.

    Validation:
    - recipient_email: valid email format
    - degree_title: not empty, <= 300 chars
    - field_of_study: not empty, <= 300 chars
    - issue_date: valid date, not in the future
    """

    recipient_email: EmailStr
    degree_title: str = Field(..., min_length=1, max_length=DEGREE_TITLE_MAX_LENGTH)
    field_of_study: str = Field(..., min_length=1, max_length=FIELD_OF_STUDY_MAX_LENGTH)
    issue_date: date
    expiry_date: date | None = None
    grade_classification: str | None = None
    honors: str | None = None

    @field_validator("recipient_email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower()

    @field_validator("issue_date")
    @classmethod
    def validate_issue_date_not_future(cls, v: date) -> date:
        """Docs Section 22.1: issue_date cannot be in the future."""
        if v > date.today():
            raise ValueError("Issue date cannot be in the future")
        return v

    model_config = ConfigDict(str_strip_whitespace=True)


class CertificateDraftResponse(BaseModel):
    """
    Response after Phase 1 (upload_and_hash_certificate).

    Docs Section 14.1 (lines 1779-1785):
    { certificate_id, certificate_uid, sha256_hash, blockchain_status }
    """

    certificate_id: UUID
    certificate_uid: str
    sha256_hash: str
    blockchain_status: BlockchainStatus


# ─── Blockchain Confirmation ─────────────────────────────────────────────────


class ConfirmHashRequest(BaseModel):
    """
    Request to confirm blockchain hash storage.

    Docs Section 14.1 (lines 1793-1795, Section 28.1):
    { certificate_id, blockchain_tx_hash }
    """

    certificate_id: UUID
    blockchain_tx_hash: str

    @field_validator("blockchain_tx_hash")
    @classmethod
    def validate_tx_hash(cls, v: str) -> str:
        """Docs Section 22.1: tx_hash regex ^0x[0-9a-fA-F]{64}$."""
        if not TX_HASH_REGEX.match(v):
            raise ValueError(
                "Invalid transaction hash format. Expected: 0x followed by 64 hex characters"
            )
        return v


class BlockchainProof(BaseModel):
    """
    Blockchain proof sub-schema within confirmation responses.

    Docs Section 14.1 (lines 1858-1863):
    { tx_hash, block_number, confirmed_at, issuer_address }
    """

    tx_hash: str
    block_number: int
    confirmed_at: datetime
    issuer_address: str


class QRCodeInfo(BaseModel):
    """
    QR code sub-schema within confirmation responses.

    Docs Section 14.1 (line 1864):
    { token, verification_url, qr_image_url }
    """

    token: str
    verification_url: str
    qr_image_url: str


class CertificateConfirmedResponse(BaseModel):
    """
    Response after Phase 2 (confirm_blockchain_storage) — successful case.

    Docs Section 14.1 (lines 1854-1865):
    { status, certificate, blockchain, qr_code }
    """

    status: str = "CONFIRMED"
    certificate: CertificateSummary  # forward ref resolved below
    blockchain: BlockchainProof
    qr_code: QRCodeInfo


# ─── Certificate Views ───────────────────────────────────────────────────────


class CertificateSummary(BaseModel):
    """
    Certificate summary for list views (university dashboard, student list).

    Docs Section 13 (CertificateSummary):
    Overview model for dashboard lists.
    """

    id: UUID
    certificate_uid: str
    recipient_name: str
    degree_title: str
    field_of_study: str
    issue_date: date
    blockchain_status: BlockchainStatus
    is_active: bool
    university_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CertificateDetail(BaseModel):
    """
    Full certificate detail response.

    Docs Section 13 (CertificateDetail / Section 28.1 GET /certificates/{id}):
    Full model including blockchain transactions and QR code data.
    """

    id: UUID
    certificate_uid: str
    university_id: UUID
    student_id: UUID
    issued_by: UUID
    recipient_name: str
    recipient_email_snapshot: str
    degree_title: str
    field_of_study: str
    grade_classification: str | None = None
    honors: str | None = None
    issue_date: date
    expiry_date: date | None = None
    academic_year: str | None = None
    sha256_hash: str
    blockchain_status: BlockchainStatus
    file_original_name: str
    file_size_bytes: int
    file_mime_type: str
    is_active: bool
    revocation_reason: str | None = None
    revoked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    blockchain_proof: BlockchainProof | None = None
    qr_code: QRCodeInfo | None = None

    model_config = ConfigDict(from_attributes=True)


# ─── Revocation ──────────────────────────────────────────────────────────────


class RevokeRequest(BaseModel):
    """
    Certificate revocation request (Phase 1: initiate_revocation).

    Docs Section 15.1 (line 1893):
    { reason: str (required, min 10 chars, max 500 chars) }
    """

    reason: str = Field(
        ...,
        min_length=REVOCATION_REASON_MIN_LENGTH,
        max_length=REVOCATION_REASON_MAX_LENGTH,
    )


class RevocationInitiatedResponse(BaseModel):
    """
    Response after revocation Phase 1 (initiate_revocation).

    Docs Section 15.1 (lines 1930-1936):
    { certificate_id, certificate_uid, university_wallet_address, message }
    """

    certificate_id: UUID
    certificate_uid: str
    university_wallet_address: str
    message: str = "Sign the revocation transaction in MetaMask"


class ConfirmRevocationRequest(BaseModel):
    """
    Request to confirm blockchain revocation (Phase 2).

    Docs Section 15.1 (lines 1942-1944, Section 28.1):
    { blockchain_tx_hash }
    """

    blockchain_tx_hash: str

    @field_validator("blockchain_tx_hash")
    @classmethod
    def validate_tx_hash(cls, v: str) -> str:
        """Docs Section 22.1: tx_hash regex ^0x[0-9a-fA-F]{64}$."""
        if not TX_HASH_REGEX.match(v):
            raise ValueError(
                "Invalid transaction hash format. Expected: 0x followed by 64 hex characters"
            )
        return v


class CertificateRevokedResponse(BaseModel):
    """
    Response after revocation Phase 2 (confirm_revocation) — success.

    Docs Section 15.1 (line 1962):
    { status: "REVOKED", certificate_id, revoked_at }
    """

    status: str = "REVOKED"
    certificate_id: UUID
    revoked_at: datetime


# ─── Forward Reference Resolution ───────────────────────────────────────────
# CertificateConfirmedResponse uses CertificateSummary which is defined after it.
CertificateConfirmedResponse.model_rebuild()
