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
#   If blockchain is unreachable, NEVER return AUTHENTIC.

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import (
    BlockchainStatus,
    TransactionType,
    VerificationMethod,
    VerificationResult,
)
from core.exceptions import (
    BlockchainConnectionError,
    BlockchainTimeoutError,
)
from repositories import (
    BlockchainTransactionRepository,
    CertificateRepository,
    QRVerificationRepository,
    VerificationLogRepository,
)
from utils.hash_service import compare_hashes, generate_hash_from_file

logger = logging.getLogger(__name__)


async def verify_by_file_upload(
    file_bytes: bytes,
    cert_uid_hint: str | None,
    current_user,
    request_ip: str | None,
    user_agent: str | None,
    db: AsyncSession,
    blockchain_service=None,
) -> dict:
    """
    Verification Flow A: File upload verification.

    Docs Section 16.1 (verify_by_file_upload):
    1. Compute hash of submitted file
    2. Find certificate in DB (by uid hint or hash)
    3. If not found: result=NOT_FOUND
    4. If not CONFIRMED: result=PENDING_CHAIN or REVOKED
    5. Blockchain verification (authoritative) or DB fallback
    6. Record verification log
    7. Return VerificationResult

    Args:
        file_bytes: Raw bytes of the uploaded PDF.
        cert_uid_hint: Optional certificate UID for targeted lookup.
        current_user: Authenticated employer user.
        request_ip: Client IP address.
        user_agent: Client user agent string.
        db: Async database session.
        blockchain_service: Optional BlockchainService instance.

    Returns:
        Dict matching VerificationResponse schema.
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

        # 4. Not confirmed on blockchain
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

        # 5. Authoritative blockchain verification
        blockchain_verified = False
        blockchain_proof = None
        tamper_evidence = None

        if blockchain_service is not None:
            try:
                # Call BlockchainService.verify_certificate()
                chain_result = blockchain_service.verify_certificate(
                    certificate.certificate_uid, submitted_hash
                )

                # Decision matrix (docs Section 16.1):
                #   chain_result.status == "REVOKED" -> REVOKED
                #   chain_result.is_valid and status == "ACTIVE" -> AUTHENTIC
                #   not chain_result.is_valid and status == "ACTIVE" -> TAMPERED
                if chain_result.status == "REVOKED":
                    result = VerificationResult.REVOKED
                elif chain_result.is_valid and chain_result.status == "ACTIVE":
                    result = VerificationResult.AUTHENTIC
                else:
                    result = VerificationResult.TAMPERED

                blockchain_verified = True

                # Get on-chain record for proof construction
                chain_record = blockchain_service.get_certificate_record(
                    certificate.certificate_uid
                )

                # Get block_number from DB transaction record
                block_number = await _get_block_number(db, certificate.id)

                if chain_record is not None:
                    blockchain_proof = {
                        "verified": True,
                        "tx_hash": await _get_store_tx_hash(db, certificate.id),
                        "block_number": block_number,
                        "issuer_address": chain_record.issuing_university,
                        "stored_at": chain_record.issued_at,
                    }
                    tamper_evidence = {
                        "submitted_hash": submitted_hash,
                        "stored_hash": chain_record.certificate_hash,
                        "match": chain_result.is_valid,
                    }
                else:
                    # Record exists in DB but not on chain — unusual
                    tamper_evidence = {
                        "submitted_hash": submitted_hash,
                        "stored_hash": certificate.sha256_hash,
                        "match": chain_result.is_valid,
                    }

            except (BlockchainConnectionError, BlockchainTimeoutError) as exc:
                # Fallback: blockchain unreachable
                # GOLDEN RULE: NEVER return AUTHENTIC when blockchain is down
                logger.warning(
                    "blockchain_unreachable_during_verification",
                    extra={
                        "certificate_uid": certificate.certificate_uid,
                        "error": str(exc),
                    },
                )
                blockchain_verified = False
                # DB-level fallback (informational only, not authoritative)
                hash_match = compare_hashes(submitted_hash, certificate.sha256_hash)
                if not certificate.is_active:
                    result = VerificationResult.REVOKED
                elif hash_match:
                    # Cannot confirm AUTHENTIC without blockchain
                    result = VerificationResult.PENDING_CHAIN
                else:
                    result = VerificationResult.TAMPERED

                tamper_evidence = {
                    "submitted_hash": submitted_hash,
                    "stored_hash": certificate.sha256_hash,
                    "match": hash_match,
                }
        else:
            # No blockchain_service provided — cannot verify authoritatively.
            # GOLDEN RULE: NEVER return AUTHENTIC without blockchain verification.
            hash_match = compare_hashes(submitted_hash, certificate.sha256_hash)
            if not certificate.is_active:
                result = VerificationResult.REVOKED
            elif not hash_match:
                result = VerificationResult.TAMPERED
            else:
                # Hash matches DB but blockchain not consulted — unverified
                result = VerificationResult.PENDING_CHAIN

            tamper_evidence = {
                "submitted_hash": submitted_hash,
                "stored_hash": certificate.sha256_hash,
                "match": hash_match if hash_match is not None else False,
            }

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
            hash_match=compare_hashes(submitted_hash, certificate.sha256_hash),
            blockchain_verified=blockchain_verified,
            blockchain_tx_hash=await _get_store_tx_hash(db, certificate.id),
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
        hash_match=compare_hashes(submitted_hash, certificate.sha256_hash),
        processing_time_ms=processing_time,
        blockchain_proof=blockchain_proof,
        tamper_evidence=tamper_evidence,
    )


async def verify_by_qr_token(
    token: str,
    request_ip: str | None,
    user_agent: str | None,
    db: AsyncSession,
    blockchain_service=None,
) -> dict:
    """
    Verification Flow B: QR token verification (public, no auth).

    Docs Section 16.1 (verify_by_qr_token):
    1. Look up QR token
    2. Check QR is active
    3. Load certificate
    4. Blockchain verification (authoritative) or DB fallback
    5. Increment QR scan count
    6. Record verification log
    7. Return PublicVerificationResult

    Args:
        token: QR token string.
        request_ip: Client IP.
        user_agent: Client user agent.
        db: Async database session.
        blockchain_service: Optional BlockchainService instance.

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

        # 4. Determine result via blockchain or DB fallback
        blockchain_verified = False
        blockchain_proof = None

        if certificate.blockchain_status == BlockchainStatus.CONFIRMED and \
           blockchain_service is not None:
            try:
                # On-chain canonical check using the stored hash
                chain_result = blockchain_service.verify_certificate(
                    certificate.certificate_uid, certificate.sha256_hash
                )

                if chain_result.status == "REVOKED":
                    result = VerificationResult.REVOKED
                elif chain_result.is_valid and chain_result.status == "ACTIVE":
                    result = VerificationResult.AUTHENTIC
                else:
                    result = VerificationResult.TAMPERED

                blockchain_verified = True

                # Get on-chain record for proof
                chain_record = blockchain_service.get_certificate_record(
                    certificate.certificate_uid
                )
                block_number = await _get_block_number(db, certificate.id)

                if chain_record is not None:
                    blockchain_proof = {
                        "verified": True,
                        "tx_hash": await _get_store_tx_hash(db, certificate.id),
                        "block_number": block_number,
                        "issuer_address": chain_record.issuing_university,
                        "stored_at": chain_record.issued_at,
                    }

            except (BlockchainConnectionError, BlockchainTimeoutError) as exc:
                logger.warning(
                    "blockchain_unreachable_during_qr_verification",
                    extra={
                        "certificate_uid": certificate.certificate_uid,
                        "error": str(exc),
                    },
                )
                blockchain_verified = False
                # DB fallback — NEVER return AUTHENTIC without blockchain
                if not certificate.is_active or \
                   certificate.blockchain_status == BlockchainStatus.REVOKED:
                    result = VerificationResult.REVOKED
                else:
                    result = VerificationResult.PENDING_CHAIN
        else:
            # No blockchain_service or not CONFIRMED — cannot verify authoritatively.
            # GOLDEN RULE: NEVER return AUTHENTIC without blockchain verification.
            if certificate.blockchain_status == BlockchainStatus.REVOKED or \
               not certificate.is_active:
                result = VerificationResult.REVOKED
            else:
                # DB says CONFIRMED but blockchain not consulted — unverified
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
            blockchain_verified=blockchain_verified,
            blockchain_tx_hash=await _get_store_tx_hash(db, certificate.id),
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
        blockchain_proof=blockchain_proof,
    )


# ─── Private Helpers ─────────────────────────────────────────────────────────


async def _get_block_number(db: AsyncSession, certificate_id: UUID) -> int:
    """
    Get block_number from the DB blockchain_transactions table for a certificate.

    Used to populate BlockchainVerificationProof.block_number without an
    additional blockchain RPC call. Returns 0 if no transaction found.
    """
    txs = await BlockchainTransactionRepository.get_by_certificate_id(
        db, certificate_id
    )
    for tx in txs:
        if tx.tx_type == TransactionType.STORE_HASH and tx.block_number:
            return tx.block_number
    return 0


async def _get_store_tx_hash(db: AsyncSession, certificate_id: UUID) -> str:
    """
    Get the Ethereum TX hash for the confirmed STORE_HASH transaction
    associated with a certificate.

    The Certificate model has no blockchain_tx_hash column; the hash lives
    in the blockchain_transactions table (relation lazy="noload").

    Returns the tx_hash string of the confirmed STORE_HASH record, or ""
    if no such record exists (e.g. certificate still PENDING/SUBMITTED).
    """
    txs = await BlockchainTransactionRepository.get_by_certificate_id(
        db, certificate_id
    )
    for tx in txs:
        if tx.tx_type == TransactionType.STORE_HASH and tx.tx_hash:
            return tx.tx_hash
    return ""


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
    blockchain_proof: dict | None = None,
    tamper_evidence: dict | None = None,
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

    # Build tamper_evidence from params if not already provided
    if tamper_evidence is None and submitted_hash is not None \
       and certificate is not None:
        tamper_evidence = {
            "submitted_hash": submitted_hash,
            "stored_hash": certificate.sha256_hash,
            "match": hash_match if hash_match is not None else False,
        }

    return {
        "verification_id": verification_id,
        "result": result,
        "certificate": cert_info,
        "blockchain_proof": blockchain_proof,
        "tamper_evidence": tamper_evidence,
        "verified_at": datetime.now(timezone.utc),
        "processing_time_ms": processing_time_ms,
    }
