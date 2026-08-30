# backend/services/verification_service.py
# Certificate verification — file upload and QR token flows.
#
# Architecture Reference: docs/backend.md Section 16.1 (Verification Service)
# Directory Reference: docs/backend.md Section 27.1 (services/verification_service.py)
#
# Two verification flows:
#   A. verify_by_file_upload() — Employer uploads PDF, service computes hash
#   B. verify_by_qr_token() — Public scans QR code, service looks up token
#
# GOLDEN RULE (from docs):
#   Blockchain is ALWAYS the source of truth.
#   Database sha256_hash is NEVER the comparison baseline.
#   When blockchain is unavailable, result includes blockchain_verified=False.
#
# Note: Full blockchain verification (BlockchainService.verify_certificate,
# get_certificate_record) requires the blockchain/ package. For now, the
# service performs database-level verification and records logs.
# Blockchain integration will be wired when blockchain/ is implemented.

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import (
    BlockchainStatus,
    VerificationMethod,
    VerificationResult,
)
from repositories import (
    CertificateRepository,
    QRVerificationRepository,
    VerificationLogRepository,
)
from utils.hash_service import compare_hashes, generate_hash_from_file


async def verify_by_file_upload(
    file_bytes: bytes,
    cert_uid_hint: str | None,
    current_user,
    request_ip: str | None,
    user_agent: str | None,
    db: AsyncSession,
) -> dict:
    """
    Verification Flow A: File upload verification.

    Docs Section 16.1 (verify_by_file_upload):
    1. Compute hash of submitted file
    2. Find certificate in DB (by uid hint or hash)
    3. If not found: result=NOT_FOUND
    4. If not CONFIRMED: result=PENDING_CHAIN
    5. Compare hashes (database-level, blockchain deferred)
    6. Record verification log
    7. Return VerificationResult

    Args:
        file_bytes: Raw bytes of the uploaded PDF.
        cert_uid_hint: Optional certificate UID for targeted lookup.
        current_user: Authenticated employer user.
        request_ip: Client IP address.
        user_agent: Client user agent string.
        db: Async database session.

    Returns:
        Dict matching VerificationResultResponse schema.
    """
    start_time = time.monotonic()
    verification_id = uuid4()

    # 1. Compute hash of submitted file
    submitted_hash = generate_hash_from_file(file_bytes)

    async with db.begin():
        # 2. Find certificate
        certificate = None
        if cert_uid_hint:
            certificate = await CertificateRepository.get_by_uid(
                db, cert_uid_hint
            )
        if certificate is None:
            certificate = await CertificateRepository.get_by_hash(
                db, submitted_hash
            )

        processing_time = int((time.monotonic() - start_time) * 1000)

        # 3. Not found
        if certificate is None:
            await _record_log(
                db,
                verification_id=verification_id,
                certificate_id=None,
                certificate_uid_queried=cert_uid_hint,
                verifier_user_id=current_user.id,
                method=VerificationMethod.FILE_UPLOAD,
                result=VerificationResult.NOT_FOUND,
                submitted_hash=submitted_hash,
                ip_address=request_ip,
                user_agent=user_agent,
                processing_time_ms=processing_time,
            )

            return _build_result(
                verification_id=verification_id,
                result=VerificationResult.NOT_FOUND,
                processing_time_ms=processing_time,
            )

        # 4. Not confirmed
        if certificate.blockchain_status != BlockchainStatus.CONFIRMED:
            if certificate.blockchain_status == BlockchainStatus.REVOKED:
                result = VerificationResult.REVOKED
            else:
                result = VerificationResult.PENDING_CHAIN

            await _record_log(
                db,
                verification_id=verification_id,
                certificate_id=certificate.id,
                certificate_uid_queried=certificate.certificate_uid,
                verifier_user_id=current_user.id,
                method=VerificationMethod.FILE_UPLOAD,
                result=result,
                submitted_hash=submitted_hash,
                stored_hash=certificate.sha256_hash,
                hash_match=compare_hashes(submitted_hash, certificate.sha256_hash),
                ip_address=request_ip,
                user_agent=user_agent,
                processing_time_ms=processing_time,
                university_name=getattr(certificate, 'university_name', None),
                degree_title=certificate.degree_title,
                recipient_name=certificate.recipient_name,
            )

            return _build_result(
                verification_id=verification_id,
                result=result,
                certificate=certificate,
                submitted_hash=submitted_hash,
                processing_time_ms=processing_time,
            )

        # 5. Compare hashes (database-level for now)
        hash_match = compare_hashes(submitted_hash, certificate.sha256_hash)

        if not certificate.is_active:
            result = VerificationResult.REVOKED
        elif hash_match:
            result = VerificationResult.AUTHENTIC
        else:
            result = VerificationResult.TAMPERED

        processing_time = int((time.monotonic() - start_time) * 1000)

        # 6. Record log
        await _record_log(
            db,
            verification_id=verification_id,
            certificate_id=certificate.id,
            certificate_uid_queried=certificate.certificate_uid,
            verifier_user_id=current_user.id,
            method=VerificationMethod.FILE_UPLOAD,
            result=result,
            submitted_hash=submitted_hash,
            stored_hash=certificate.sha256_hash,
            hash_match=hash_match,
            blockchain_verified=False,  # True when BlockchainService integrated
            ip_address=request_ip,
            user_agent=user_agent,
            processing_time_ms=processing_time,
            university_name=getattr(certificate, 'university_name', None),
            degree_title=certificate.degree_title,
            recipient_name=certificate.recipient_name,
        )

    # 7. Return result
    return _build_result(
        verification_id=verification_id,
        result=result,
        certificate=certificate,
        submitted_hash=submitted_hash,
        hash_match=hash_match,
        processing_time_ms=processing_time,
    )


async def verify_by_qr_token(
    token: str,
    request_ip: str | None,
    user_agent: str | None,
    db: AsyncSession,
) -> dict:
    """
    Verification Flow B: QR token verification (public, no auth).

    Docs Section 16.1 (verify_by_qr_token):
    1. Look up QR token
    2. Check QR is active
    3. Load certificate
    4. Determine result (database-level, blockchain deferred)
    5. Increment QR scan count
    6. Record verification log
    7. Return PublicVerificationResult

    Args:
        token: QR token string.
        request_ip: Client IP.
        user_agent: Client user agent.
        db: Async database session.

    Returns:
        Dict matching PublicVerificationResult schema.
    """
    start_time = time.monotonic()
    verification_id = uuid4()

    async with db.begin():
        # 1. Look up QR token
        qr = await QRVerificationRepository.get_by_token(db, token)

        processing_time = int((time.monotonic() - start_time) * 1000)

        if qr is None:
            return _build_result(
                verification_id=verification_id,
                result=VerificationResult.NOT_FOUND,
                processing_time_ms=processing_time,
            )

        # 2. Check QR is active and not expired
        if not qr.is_active:
            return _build_result(
                verification_id=verification_id,
                result=VerificationResult.NOT_FOUND,
                processing_time_ms=processing_time,
            )

        if qr.expires_at and qr.expires_at < datetime.now(timezone.utc):
            return _build_result(
                verification_id=verification_id,
                result=VerificationResult.NOT_FOUND,
                processing_time_ms=processing_time,
            )

        # 3. Load certificate
        certificate = await CertificateRepository.get_by_id(db, qr.certificate_id)
        if certificate is None:
            return _build_result(
                verification_id=verification_id,
                result=VerificationResult.NOT_FOUND,
                processing_time_ms=processing_time,
            )

        # 4. Determine result
        if certificate.blockchain_status == BlockchainStatus.REVOKED or \
           not certificate.is_active:
            result = VerificationResult.REVOKED
        elif certificate.blockchain_status == BlockchainStatus.CONFIRMED:
            result = VerificationResult.AUTHENTIC
        else:
            result = VerificationResult.PENDING_CHAIN

        processing_time = int((time.monotonic() - start_time) * 1000)

        # 5. Increment scan count
        await QRVerificationRepository.increment_scan_count(db, qr.id)

        # 6. Record log
        await _record_log(
            db,
            verification_id=verification_id,
            certificate_id=certificate.id,
            certificate_uid_queried=certificate.certificate_uid,
            verifier_user_id=None,  # Public/unauthenticated scan
            qr_verification_id=qr.id,
            method=VerificationMethod.QR_SCAN,
            result=result,
            submitted_hash=None,  # No file uploaded
            stored_hash=certificate.sha256_hash,
            blockchain_verified=False,
            ip_address=request_ip,
            user_agent=user_agent,
            processing_time_ms=processing_time,
            university_name=getattr(certificate, 'university_name', None),
            degree_title=certificate.degree_title,
            recipient_name=certificate.recipient_name,
        )

    # 7. Return public result
    return _build_result(
        verification_id=verification_id,
        result=result,
        certificate=certificate,
        processing_time_ms=processing_time,
    )


# ─── Private Helpers ─────────────────────────────────────────────────────────


async def _record_log(
    db: AsyncSession,
    *,
    verification_id: UUID,
    certificate_id: UUID | None,
    certificate_uid_queried: str | None,
    verifier_user_id: UUID | None,
    method: VerificationMethod,
    result: VerificationResult,
    submitted_hash: str | None = None,
    stored_hash: str | None = None,
    hash_match: bool | None = None,
    blockchain_verified: bool = False,
    blockchain_tx_hash: str | None = None,
    qr_verification_id: UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    processing_time_ms: int | None = None,
    university_name: str | None = None,
    degree_title: str | None = None,
    recipient_name: str | None = None,
) -> None:
    """Record a verification log entry."""
    log_data = {
        "certificate_id": certificate_id,
        "certificate_uid_queried": certificate_uid_queried,
        "verifier_user_id": verifier_user_id,
        "qr_verification_id": qr_verification_id,
        "verification_method": method,
        "result": result,
        "submitted_hash": submitted_hash,
        "stored_hash": stored_hash,
        "hash_match": hash_match,
        "blockchain_verified": blockchain_verified,
        "blockchain_tx_hash": blockchain_tx_hash,
        "university_name_snapshot": university_name,
        "degree_title_snapshot": degree_title,
        "recipient_name_snapshot": recipient_name,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "processing_time_ms": processing_time_ms,
        "verified_at": datetime.now(timezone.utc),
    }
    await VerificationLogRepository.create(db, log_data)


def _build_result(
    *,
    verification_id: UUID,
    result: VerificationResult,
    certificate=None,
    submitted_hash: str | None = None,
    hash_match: bool | None = None,
    processing_time_ms: int = 0,
) -> dict:
    """Build a verification result dict."""
    cert_info = None
    if certificate is not None:
        cert_info = {
            "certificate_uid": certificate.certificate_uid,
            "recipient_name": certificate.recipient_name,
            "degree_title": certificate.degree_title,
            "university_name": getattr(certificate, 'university_name', None),
            "issue_date": certificate.issue_date,
            "is_active": certificate.is_active,
        }

    tamper_evidence = None
    if submitted_hash is not None and certificate is not None:
        tamper_evidence = {
            "submitted_hash": submitted_hash,
            "stored_hash": certificate.sha256_hash,
            "match": hash_match if hash_match is not None else False,
        }

    return {
        "verification_id": verification_id,
        "result": result,
        "certificate": cert_info,
        "blockchain_proof": None,  # Populated when BlockchainService integrated
        "tamper_evidence": tamper_evidence,
        "verified_at": datetime.now(timezone.utc),
        "processing_time_ms": processing_time_ms,
    }
