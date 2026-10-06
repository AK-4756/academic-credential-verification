# backend/services/certificate_issuance_service.py
# Certificate issuance — two-phase workflow (upload+hash -> confirm on chain).
#
# Architecture Reference: docs/backend.md Section 14.1 (Certificate Issuance Service)
# Directory Reference: docs/backend.md Section 27.1 (services/certificate_issuance_service.py)
#
# Phase 1: upload_and_hash_certificate()
#   - Validates file, metadata, issuer
#   - Computes SHA-256 hash
#   - Checks hash uniqueness
#   - Saves file to disk
#   - Creates DB records (Certificate + BlockchainTransaction)
#   - Returns { certificate_id, certificate_uid, sha256_hash, blockchain_status }
#
# Phase 2: confirm_blockchain_storage()
#   - Validates TX receipt via BlockchainService.get_transaction_receipt()
#   - Cross-validates on-chain record (hash integrity + issuer match)
#   - Updates status to CONFIRMED
#   - Auto-generates QR code

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.constants import (
    BlockchainStatus,
    TransactionStatus,
    TransactionType,
)
from core.exceptions import (
    BlockchainConnectionError,
    BlockchainTimeoutError,
    CertificateNotFoundError,
    DuplicateCertificateError,
    MissingWalletAddressError,
    OwnershipViolationError,
    ServiceError,
    UnverifiedUniversityError,
    UserNotFoundError,
)
from repositories import (
    BlockchainTransactionRepository,
    CertificateRepository,
    StudentRepository,
    UniversityRepository,
    UserRepository,
)
from services import qr_verification_service
from utils.file_storage_service import save_certificate
from utils.hash_service import generate_hash_from_file

logger = logging.getLogger(__name__)


async def upload_and_hash_certificate(
    file_bytes: bytes,
    file_original_name: str,
    metadata: dict,
    current_user,
    db: AsyncSession,
) -> dict:
    """
    Phase 1: Upload, hash, and create certificate record.

    Docs Section 14.1 (Phase 1: upload_and_hash_certificate):
    1. Validate issuer (university verified, wallet configured)
    2. Look up student by recipient_email
    3. Generate certificate_uid
    4. Compute SHA-256 hash
    5. Check hash uniqueness
    6. Save file to disk
    7. Create Certificate record (PENDING)
    8. Create BlockchainTransaction record (PENDING)

    Args:
        file_bytes: Raw PDF bytes (already validated at router layer).
        file_original_name: Original filename.
        metadata: CertificateIssueRequest fields as dict.
        current_user: Authenticated UNIVERSITY_ADMIN user.
        db: Async database session.

    Returns:
        Dict with certificate_id, certificate_uid, sha256_hash, blockchain_status.

    Raises:
        UnverifiedUniversityError: If issuing university is not verified.
        MissingWalletAddressError: If university has no wallet configured.
        UserNotFoundError: If recipient student not found.
        DuplicateCertificateError: If same PDF hash already exists.
    """
    async with db.begin():
        # 1. Validate issuer
        university = await UniversityRepository.get_by_id(
            db, current_user.university_id
        )
        if university is None or not university.is_verified:
            raise UnverifiedUniversityError()

        if not university.wallet_address:
            raise MissingWalletAddressError()

        # 2. Look up student by recipient_email
        recipient_email = metadata["recipient_email"]
        student_user = await UserRepository.get_by_email(db, recipient_email)
        if student_user is None:
            raise UserNotFoundError(
                message="No student account found with this email. "
                "Student must register first."
            )

        student = await StudentRepository.get_by_user_id(db, student_user.id)
        if student is None:
            raise UserNotFoundError(
                message="No student profile found for this email"
            )

        # 3. Generate certificate_uid
        year = date.today().year
        sequence = await CertificateRepository.get_next_uid_sequence(
            db, university.short_code, year
        )
        certificate_uid = f"{university.short_code}-{year}-{sequence:05d}"

        # 4. Compute SHA-256 hash
        sha256_hash = generate_hash_from_file(file_bytes)

        # 5. Check hash uniqueness
        existing = await CertificateRepository.get_by_hash(db, sha256_hash)
        if existing is not None:
            raise DuplicateCertificateError()

        # 6. Save file to disk
        cert_id = uuid4()
        file_path = save_certificate(
            file_bytes, current_user.university_id, cert_id
        )

        # 7. Create Certificate record
        cert_data = {
            "id": cert_id,
            "certificate_uid": certificate_uid,
            "university_id": current_user.university_id,
            "student_id": student_user.id,
            "issued_by": current_user.id,
            "recipient_name": f"{student_user.first_name} {student_user.last_name}",
            "recipient_email_snapshot": recipient_email,
            "degree_title": metadata["degree_title"],
            "field_of_study": metadata["field_of_study"],
            "issue_date": metadata["issue_date"],
            "expiry_date": metadata.get("expiry_date"),
            "grade_classification": metadata.get("grade_classification"),
            "honors": metadata.get("honors"),
            "sha256_hash": sha256_hash,
            "blockchain_status": BlockchainStatus.PENDING,
            "file_path": file_path,
            "file_original_name": file_original_name,
            "file_size_bytes": len(file_bytes),
        }
        certificate = await CertificateRepository.create(db, cert_data)

        # 8. Create BlockchainTransaction record
        tx_data = {
            "certificate_id": certificate.id,
            "tx_type": TransactionType.STORE_HASH,
            "from_address": university.wallet_address,
            "to_address": settings.CONTRACT_ADDRESS,
            "contract_address": settings.CONTRACT_ADDRESS,
            "network_name": settings.NETWORK_NAME,
            "network_chain_id": settings.NETWORK_CHAIN_ID,
            "certificate_hash_stored": sha256_hash,
            "status": TransactionStatus.PENDING,
        }
        await BlockchainTransactionRepository.create(db, tx_data)

    return {
        "certificate_id": certificate.id,
        "certificate_uid": certificate_uid,
        "sha256_hash": sha256_hash,
        "blockchain_status": BlockchainStatus.PENDING,
    }


async def confirm_blockchain_storage(
    cert_id: UUID,
    blockchain_tx_hash: str,
    current_user,
    db: AsyncSession,
    blockchain_service,
) -> dict:
    """
    Phase 2: Confirm blockchain storage after MetaMask TX.

    Docs Section 14.1 (Phase 2: confirm_blockchain_storage):
    1. Load certificate and validate ownership
    2. Validate status is PENDING or SUBMITTED
    3. Verify TX receipt via BlockchainService
    4. Cross-validate on-chain record (hash + issuer)
    5. Update DB records to CONFIRMED
    6. Auto-generate QR code

    Args:
        cert_id: Certificate UUID.
        blockchain_tx_hash: The blockchain transaction hash (0x + 64 hex).
        current_user: Authenticated UNIVERSITY_ADMIN user.
        db: Async database session.
        blockchain_service: BlockchainService instance for TX verification.

    Returns:
        Dict matching CertificateConfirmedResponse schema (CONFIRMED),
        or dict with status SUBMITTED/FAILED.

    Raises:
        CertificateNotFoundError: If certificate not found.
        OwnershipViolationError: If user's university doesn't match.
        ServiceError: If certificate is not in a valid state for confirmation.
        BlockchainConnectionError: If blockchain is unreachable (retry later).
    """
    async with db.begin():
        certificate = await CertificateRepository.get_by_id(db, cert_id)
        if certificate is None:
            raise CertificateNotFoundError()

        # Ownership check
        if certificate.university_id != current_user.university_id:
            raise OwnershipViolationError()

        # Status check
        if certificate.blockchain_status not in (
            BlockchainStatus.PENDING,
            BlockchainStatus.SUBMITTED,
        ):
            raise ServiceError(
                message=f"Certificate cannot be confirmed from status "
                f"'{certificate.blockchain_status}'"
            )

        # Load university for issuer wallet cross-validation
        university = await UniversityRepository.get_by_id(
            db, current_user.university_id
        )

        # Find the STORE_HASH transaction record
        txs = await BlockchainTransactionRepository.get_by_certificate_id(
            db, cert_id
        )
        store_tx = None
        for tx in txs:
            if tx.tx_type == TransactionType.STORE_HASH:
                store_tx = tx
                break

        # --- Blockchain verification ---
        try:
            # 3. Verify TX receipt
            receipt = blockchain_service.get_transaction_receipt(
                blockchain_tx_hash
            )

            # TX not mined yet
            if receipt is None:
                if store_tx:
                    await BlockchainTransactionRepository.update_status(
                        db, store_tx.id, TransactionStatus.SUBMITTED,
                        block_data={"tx_hash": blockchain_tx_hash},
                    )
                await CertificateRepository.update_blockchain_status(
                    db, cert_id, BlockchainStatus.SUBMITTED,
                    tx_hash=blockchain_tx_hash,
                )
                return {
                    "status": "SUBMITTED",
                    "message": "Transaction pending confirmation on blockchain",
                    "certificate_id": str(cert_id),
                    "blockchain_tx_hash": blockchain_tx_hash,
                }

            # TX failed/reverted on chain
            if receipt.status == 0:
                if store_tx:
                    await BlockchainTransactionRepository.update_status(
                        db, store_tx.id, TransactionStatus.FAILED,
                        block_data={
                            "tx_hash": blockchain_tx_hash,
                            "block_number": receipt.block_number,
                            "block_hash": receipt.block_hash,
                        },
                    )
                await CertificateRepository.update_blockchain_status(
                    db, cert_id, BlockchainStatus.FAILED,
                    tx_hash=blockchain_tx_hash,
                )
                raise ServiceError(
                    message="Transaction failed on blockchain (reverted)"
                )

            # 4. TX succeeded — cross-validate on-chain record
            record = blockchain_service.get_certificate_record(
                certificate.certificate_uid
            )

            # Check A: Existence
            if record is None or not record.exists:
                logger.critical(
                    "blockchain_cross_validation_missing_record",
                    extra={
                        "certificate_uid": certificate.certificate_uid,
                        "tx_hash": blockchain_tx_hash,
                    },
                )
                if store_tx:
                    await BlockchainTransactionRepository.update_status(
                        db, store_tx.id, TransactionStatus.FAILED,
                        block_data={"tx_hash": blockchain_tx_hash},
                    )
                raise ServiceError(
                    message="Certificate record missing from contract "
                    "despite successful transaction receipt"
                )

            # Check B: Hash integrity
            if record.certificate_hash.lower() != certificate.sha256_hash.lower():
                logger.critical(
                    "blockchain_cross_validation_hash_mismatch",
                    extra={
                        "certificate_uid": certificate.certificate_uid,
                        "chain_hash": record.certificate_hash,
                        "db_hash": certificate.sha256_hash,
                    },
                )
                if store_tx:
                    await BlockchainTransactionRepository.update_status(
                        db, store_tx.id, TransactionStatus.FAILED,
                        block_data={"tx_hash": blockchain_tx_hash},
                    )
                raise ServiceError(
                    message="Stored blockchain hash does not match "
                    "certificate SHA-256 hash"
                )

            # Check C: Issuer match
            if university and university.wallet_address and \
               record.issuing_university.lower() != \
               university.wallet_address.lower():
                logger.critical(
                    "blockchain_cross_validation_issuer_mismatch",
                    extra={
                        "certificate_uid": certificate.certificate_uid,
                        "chain_issuer": record.issuing_university,
                        "expected_issuer": university.wallet_address,
                    },
                )
                if store_tx:
                    await BlockchainTransactionRepository.update_status(
                        db, store_tx.id, TransactionStatus.FAILED,
                        block_data={"tx_hash": blockchain_tx_hash},
                    )
                raise ServiceError(
                    message="Issuing wallet on blockchain does not match "
                    "university wallet"
                )

            # 5. All checks passed — update DB records to CONFIRMED
            tx_fee = receipt.gas_used * receipt.effective_gas_price
            if store_tx:
                await BlockchainTransactionRepository.update_status(
                    db, store_tx.id, TransactionStatus.CONFIRMED,
                    block_data={
                        "tx_hash": blockchain_tx_hash,
                        "block_number": receipt.block_number,
                        "block_hash": receipt.block_hash,
                        "gas_used": receipt.gas_used,
                        "gas_price_wei": receipt.effective_gas_price,
                        "transaction_fee_wei": tx_fee,
                        "confirmed_at": record.issued_at,
                    },
                )

            certificate = await CertificateRepository.update_blockchain_status(
                db, cert_id, BlockchainStatus.CONFIRMED,
                tx_hash=blockchain_tx_hash,
            )

        except (BlockchainConnectionError, BlockchainTimeoutError):
            # Blockchain unreachable — do NOT mark as FAILED.
            # Keep status as-is, instruct client to retry.
            if store_tx and certificate.blockchain_status == BlockchainStatus.PENDING:
                await BlockchainTransactionRepository.update_status(
                    db, store_tx.id, TransactionStatus.SUBMITTED,
                    block_data={"tx_hash": blockchain_tx_hash},
                )
                await CertificateRepository.update_blockchain_status(
                    db, cert_id, BlockchainStatus.SUBMITTED,
                    tx_hash=blockchain_tx_hash,
                )
            raise

    # 6. Auto-generate QR code AFTER committing CONFIRMED status.
    #    generate_qr_for_certificate opens its own transaction — calling it
    #    inside the block above would trigger a nested db.begin() error.
    qr_result = await qr_verification_service.generate_qr_for_certificate(
        cert_id, current_user.id, db,
    )

    # Build response matching CertificateConfirmedResponse schema
    return {
        "status": "CONFIRMED",
        "certificate": {
            "id": str(certificate.id),
            "certificate_uid": certificate.certificate_uid,
            "recipient_name": certificate.recipient_name,
            "degree_title": certificate.degree_title,
            "field_of_study": certificate.field_of_study,
            "issue_date": certificate.issue_date,
            "blockchain_status": BlockchainStatus.CONFIRMED,
            "is_active": certificate.is_active,
        },
        "blockchain": {
            "tx_hash": blockchain_tx_hash,
            "block_number": receipt.block_number,
            "confirmed_at": record.issued_at,
            "issuer_address": record.issuing_university,
        },
        "qr_code": {
            "token": qr_result["token"],
            "verification_url": qr_result["verification_url"],
            "qr_image_url": f"/api/v1/qr/{qr_result['token']}/image",
        },
    }
