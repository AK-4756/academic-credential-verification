# backend/schemas/verification_schemas.py
# Authenticity verification schemas.
#
# Architecture Reference: docs/backend.md Section 16.1 (Verification Service)
# Result Schema: docs/backend.md lines 1987-2013 (Verification Result Schema)
# Public Result: docs/backend.md Section 28.1 line 3481 (GET /verify/qr/{token})
# Endpoint: docs/backend.md Section 28.1 lines 3470-3481

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.constants import VerificationResult as VerificationResultEnum


# ─── Verification Sub-schemas ────────────────────────────────────────────────


class VerificationCertificateInfo(BaseModel):
    """
    Certificate sub-schema within the verification result.

    Docs Section 16.1 (lines 1991-1998):
    { certificate_uid, recipient_name, degree_title, university_name,
      issue_date, is_active }
    """

    certificate_uid: str
    recipient_name: str
    degree_title: str
    university_name: str
    issue_date: date
    is_active: bool


class BlockchainVerificationProof(BaseModel):
    """
    Blockchain proof sub-schema within the verification result.

    Docs Section 16.1 (lines 1999-2005):
    { verified, tx_hash, block_number, issuer_address, stored_at }
    """

    verified: bool
    tx_hash: str
    block_number: int
    issuer_address: str
    stored_at: datetime


class TamperEvidence(BaseModel):
    """
    Tamper evidence sub-schema within the verification result.

    Docs Section 16.1 (lines 2006-2010):
    { submitted_hash, stored_hash, match }
    """

    submitted_hash: str
    stored_hash: str
    match: bool


# ─── Full Verification Result ────────────────────────────────────────────────


class VerificationResponse(BaseModel):
    """
    Full verification result (returned to authenticated employer).

    Docs Section 16.1 (lines 1987-2013):
    {
      verification_id, result, certificate | null,
      blockchain_proof | null, tamper_evidence | null,
      verified_at, processing_time_ms
    }
    """

    verification_id: UUID
    result: VerificationResultEnum
    certificate: VerificationCertificateInfo | None = None
    blockchain_proof: BlockchainVerificationProof | None = None
    tamper_evidence: TamperEvidence | None = None
    verified_at: datetime
    processing_time_ms: int


# ─── Public Verification Result ─────────────────────────────────────────────


class PublicVerificationResult(BaseModel):
    """
    Public-safe verification result for QR scans (no authentication required).

    Docs Section 28.1 (line 3481): GET /verify/qr/{token} → PublicVerificationResult
    Contains minimal PII — suitable for public consumption.
    """

    result: VerificationResultEnum
    certificate: VerificationCertificateInfo | None = None
    blockchain_proof: BlockchainVerificationProof | None = None
    verified_at: datetime
    processing_time_ms: int
