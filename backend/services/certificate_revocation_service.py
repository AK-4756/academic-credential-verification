# backend/services/certificate_revocation_service.py
# Certificate revocation — two-phase workflow (initiate -> confirm on chain).
#
# Architecture Reference: docs/backend.md Section 15.1 (Certificate Revocation Service)
# Directory Reference: docs/backend.md Section 27.1 (services/certificate_revocation_service.py)
#
# Phase 1: initiate_revocation()
#   - Validates ownership, CONFIRMED status, active state, wallet
#   - Blockchain pre-flight: is_authorized_issuer + get_certificate_record
#   - Creates REVOKE_HASH blockchain transaction record
#   - Returns { certificate_id, certificate_uid, university_wallet_address }
#
# Phase 2: confirm_revocation()
#   - Validates TX receipt via BlockchainService
#   - Validates on-chain status is REVOKED
#   - Updates certificate to REVOKED, deactivates cert

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

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
    CertificateAlreadyRevokedError,
    CertificateNotFoundError,
    MissingWalletAddressError,
    OwnershipViolationError,
    ServiceError,
    UnconfirmedCertificateError,
    UniversityNotFoundError,
)
from repositories import (
    BlockchainTransactionRepository,
    CertificateRepository,
    UniversityRepository,
)

logger = logging.getLogger(__name__)


async def initiate_revocation(
    cert_id: UUID,
    reason: str,
    current_user,
    db: AsyncSession,
    blockchain_service=None,
) -> dict:
    """
    Phase 1: Initiate certificate revocation.

    Docs Section 15.1 (Phase 1: initiate_revocation):
    1. Load and validate certificate (exists, ownership)
    2. Validate status is CONFIRMED and is_active
    3. Validate university wallet is configured
    4. Blockchain pre-flight: is_authorized_issuer + get_certificate_record
    5. Create REVOKE_HASH blockchain transaction record
    6. Return info for frontend MetaMask signing

    Args:
        cert_id: Certificate UUID to revoke.
        reason: Revocation reason (10-500 chars, validated by schema).
        current_user: Authenticated UNIVERSITY_ADMIN user.
        db: Async database session.
        blockchain_service: Optional BlockchainService for pre-flight checks.

    Returns:
        Dict with certificate_id, certificate_uid, university_wallet_address.

    Raises:
        CertificateNotFoundError: If certificate not found.
        OwnershipViolationError: If university doesn't own this certificate.
        UnconfirmedCertificateError: If certificate is not CONFIRMED.
        CertificateAlreadyRevokedError: If already revoked.
        MissingWalletAddressError: If university has no wallet.
        ServiceError: If blockchain pre-flight checks fail.
    """
    async with db.begin():
        # 1. Load and validate
        certificate = await CertificateRepository.get_by_id(db, cert_id)
        if certificate is None:
            raise CertificateNotFoundError()

        if certificate.university_id != current_user.university_id:
            raise OwnershipViolationError()

        # 2. Status checks — order matters:
        #    (a) is_active=False means the certificate is already revoked.
        #        This must be checked BEFORE the blockchain_status guard because
        #        a REVOKED cert has blockchain_status=REVOKED (≠ CONFIRMED), and
        #        without this ordering the wrong error would be raised.
        #    (b) blockchain_status≠CONFIRMED but is_active=True means the cert
        #        is PENDING/SUBMITTED and has not been confirmed on-chain yet.
        if not certificate.is_active:
            raise CertificateAlreadyRevokedError()

        if certificate.blockchain_status != BlockchainStatus.CONFIRMED:
            raise UnconfirmedCertificateError(
                message="Cannot revoke unconfirmed certificate"
            )

        # 3. Validate university wallet
        university = await UniversityRepository.get_by_id(
            db, current_user.university_id
        )
        if university is None:
            raise UniversityNotFoundError()

        if not university.wallet_address:
            raise MissingWalletAddressError()

        # 4. Blockchain pre-flight checks (if service available)
        if blockchain_service is not None:
            try:
                # Check issuer is still authorized on contract
                is_auth = blockchain_service.is_authorized_issuer(
                    university.wallet_address
                )
                if not is_auth:
                    raise ServiceError(
                        message="University wallet is no longer authorized "
                        "on smart contract"
                    )

                # Check on-chain record state
                record = blockchain_service.get_certificate_record(
                    certificate.certificate_uid
                )
                if record is None or not record.exists:
                    raise ServiceError(
                        message="Certificate record not found on blockchain"
                    )

                if record.status == "REVOKED":
                    raise CertificateAlreadyRevokedError()

                # Check issuer match
                if record.issuing_university.lower() != \
                   university.wallet_address.lower():
                    raise OwnershipViolationError(
                        message="University wallet does not match "
                        "original issuing wallet on blockchain"
                    )

            except (BlockchainConnectionError, BlockchainTimeoutError) as exc:
                # Graceful degradation: proceed with DB-only checks
                logger.warning(
                    "blockchain_preflight_unavailable",
                    extra={
                        "certificate_uid": certificate.certificate_uid,
                        "error": str(exc),
                    },
                )

        # 5. Create revocation blockchain transaction record
        tx_data = {
            "certificate_id": cert_id,
            "tx_type": TransactionType.REVOKE_HASH,
            "from_address": university.wallet_address,
            "to_address": settings.CONTRACT_ADDRESS,
            "contract_address": settings.CONTRACT_ADDRESS,
            "network_name": settings.NETWORK_NAME,
            "network_chain_id": settings.NETWORK_CHAIN_ID,
            "status": TransactionStatus.PENDING,
            # Store the user-supplied revocation reason so Phase 2 can
            # retrieve it and write it to the certificate record.
            # error_message is repurposed here as a revocation_note for
            # PENDING records; it is overwritten with the real error (if any)
            # only on FAILED status, which clears the PENDING state.
            "error_message": reason,
        }
        await BlockchainTransactionRepository.create(db, tx_data)

    return {
        "certificate_id": cert_id,
        "certificate_uid": certificate.certificate_uid,
        "university_wallet_address": university.wallet_address,
        "message": "Sign the revocation transaction in MetaMask",
    }


async def confirm_revocation(
    cert_id: UUID,
    blockchain_tx_hash: str,
    current_user,
    db: AsyncSession,
    blockchain_service,
) -> dict:
    """
    Phase 2: Confirm revocation after MetaMask TX.

    Docs Section 15.1 (Phase 2: confirm_revocation):
    1. Load and validate certificate + ownership
    2. Verify TX receipt via BlockchainService
    3. Verify on-chain status is REVOKED
    4. Revoke certificate in DB
    5. Update blockchain transaction status
    6. Return { status: REVOKED, certificate_id, revoked_at }

    Args:
        cert_id: Certificate UUID.
        blockchain_tx_hash: The revocation TX hash.
        current_user: Authenticated UNIVERSITY_ADMIN user.
        db: Async database session.
        blockchain_service: BlockchainService instance for TX verification.

    Raises:
        CertificateNotFoundError: If certificate not found.
        OwnershipViolationError: If university doesn't own this certificate.
        CertificateAlreadyRevokedError: If already revoked.
        ServiceError: If TX failed or on-chain status is not REVOKED.
        BlockchainConnectionError: If blockchain is unreachable.
    """
    async with db.begin():
        certificate = await CertificateRepository.get_by_id(db, cert_id)
        if certificate is None:
            raise CertificateNotFoundError()

        if certificate.university_id != current_user.university_id:
            raise OwnershipViolationError()

        if not certificate.is_active:
            raise CertificateAlreadyRevokedError()

        # Find the REVOKE_HASH transaction record
        txs = await BlockchainTransactionRepository.get_by_certificate_id(
            db, cert_id
        )
        revoke_tx = None
        for tx in txs:
            if tx.tx_type == TransactionType.REVOKE_HASH and \
               tx.status in (TransactionStatus.PENDING, TransactionStatus.SUBMITTED):
                revoke_tx = tx
                break

        # --- Blockchain verification ---
        try:
            # 2. Verify TX receipt
            receipt = blockchain_service.get_transaction_receipt(
                blockchain_tx_hash
            )

            # TX not mined yet
            if receipt is None:
                if revoke_tx:
                    await BlockchainTransactionRepository.update_status(
                        db, revoke_tx.id, TransactionStatus.SUBMITTED,
                        block_data={"tx_hash": blockchain_tx_hash},
                    )
                return {
                    "status": "SUBMITTED",
                    "message": "Revocation transaction pending confirmation",
                    "certificate_id": cert_id,
                }

            # TX failed/reverted
            if receipt.status == 0:
                if revoke_tx:
                    await BlockchainTransactionRepository.update_status(
                        db, revoke_tx.id, TransactionStatus.FAILED,
                        block_data={
                            "tx_hash": blockchain_tx_hash,
                            "block_number": receipt.block_number,
                        },
                    )
                raise ServiceError(
                    message="Revocation transaction reverted on blockchain"
                )

            # 3. Verify on-chain status is REVOKED
            record = blockchain_service.get_certificate_record(
                certificate.certificate_uid
            )

            if record is None or not record.exists:
                raise ServiceError(
                    message="Certificate record not found on blockchain "
                    "after revocation transaction"
                )

            if record.status != "REVOKED":
                raise ServiceError(
                    message="Blockchain record does not reflect REVOKED status"
                )

            # 4. Revoke in DB — recover the original reason stored in Phase 1
            revoked_at = record.revoked_at or datetime.now(timezone.utc)
            # The user-supplied reason was stored in error_message during
            # Phase 1 (initiate_revocation). Retrieve it here; fall back to
            # a generic message if the tx record is unavailable.
            original_reason = (
                revoke_tx.error_message
                if revoke_tx and revoke_tx.error_message
                else "Revocation confirmed on blockchain"
            )
            await CertificateRepository.revoke(
                db, cert_id,
                reason=original_reason,
                revoked_by=current_user.id,
            )

            # 5. Update blockchain transaction
            if revoke_tx:
                await BlockchainTransactionRepository.update_status(
                    db, revoke_tx.id, TransactionStatus.CONFIRMED,
                    block_data={
                        "tx_hash": blockchain_tx_hash,
                        "block_number": receipt.block_number,
                        "block_hash": receipt.block_hash,
                        "gas_used": receipt.gas_used,
                        "gas_price_wei": receipt.effective_gas_price,
                        "transaction_fee_wei": receipt.gas_used * receipt.effective_gas_price,
                        "confirmed_at": revoked_at,
                    },
                )

        except (BlockchainConnectionError, BlockchainTimeoutError):
            # Blockchain unreachable — do NOT finalize revocation.
            # Keep status as-is, instruct client to retry.
            if revoke_tx:
                await BlockchainTransactionRepository.update_status(
                    db, revoke_tx.id, TransactionStatus.SUBMITTED,
                    block_data={"tx_hash": blockchain_tx_hash},
                )
            raise

    return {
        "status": "REVOKED",
        "certificate_id": cert_id,
        "revoked_at": revoked_at,
    }
