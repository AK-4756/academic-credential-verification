# backend/services/certificate_revocation_service.py
# Certificate revocation — two-phase workflow (initiate → confirm on chain).
#
# Architecture Reference: docs/backend.md Section 15.1 (Certificate Revocation Service)
# Directory Reference: docs/backend.md Section 27.1 (services/certificate_revocation_service.py)
#
# Phase 1: initiate_revocation()
#   - Validates ownership, CONFIRMED status, active state, wallet
#   - Creates REVOKE_HASH blockchain transaction record
#   - Returns { certificate_id, certificate_uid, university_wallet_address }
#
# Phase 2: confirm_revocation()
#   - Validates TX, updates certificate to REVOKED, deactivates cert

from __future__ import annotations

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


async def initiate_revocation(
    cert_id: UUID,
    reason: str,
    current_user,
    db: AsyncSession,
) -> dict:
    """
    Phase 1: Initiate certificate revocation.

    Docs Section 15.1 (Phase 1: initiate_revocation):
    1. Load and validate certificate (exists, ownership)
    2. Validate status is CONFIRMED and is_active
    3. Validate university wallet is configured
    4. Create REVOKE_HASH blockchain transaction record
    5. Return info for frontend MetaMask signing

    Args:
        cert_id: Certificate UUID to revoke.
        reason: Revocation reason (10-500 chars, validated by schema).
        current_user: Authenticated UNIVERSITY_ADMIN user.
        db: Async database session.

    Returns:
        Dict with certificate_id, certificate_uid, university_wallet_address.

    Raises:
        CertificateNotFoundError: If certificate not found.
        OwnershipViolationError: If university doesn't own this certificate.
        UnconfirmedCertificateError: If certificate is not CONFIRMED.
        CertificateAlreadyRevokedError: If already revoked.
        MissingWalletAddressError: If university has no wallet.
    """
    async with db.begin():
        # 1. Load and validate
        certificate = await CertificateRepository.get_by_id(db, cert_id)
        if certificate is None:
            raise CertificateNotFoundError()

        if certificate.university_id != current_user.university_id:
            raise OwnershipViolationError()

        # 2. Status checks
        if certificate.blockchain_status != BlockchainStatus.CONFIRMED:
            raise UnconfirmedCertificateError(
                message="Cannot revoke unconfirmed certificate"
            )

        if not certificate.is_active:
            raise CertificateAlreadyRevokedError()

        # 3. Validate university wallet
        university = await UniversityRepository.get_by_id(
            db, current_user.university_id
        )
        if university is None:
            raise UniversityNotFoundError()

        if not university.wallet_address:
            raise MissingWalletAddressError()

        # 4. Create revocation blockchain transaction record
        tx_data = {
            "certificate_id": cert_id,
            "tx_type": TransactionType.REVOKE_HASH,
            "from_address": university.wallet_address,
            "to_address": settings.CONTRACT_ADDRESS,
            "contract_address": settings.CONTRACT_ADDRESS,
            "network_name": settings.NETWORK_NAME,
            "network_chain_id": settings.NETWORK_CHAIN_ID,
            "status": TransactionStatus.PENDING,
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
) -> dict:
    """
    Phase 2: Confirm revocation after MetaMask TX.

    Docs Section 15.1 (Phase 2: confirm_revocation):
    1. Load and validate certificate + ownership
    2. Revoke certificate in DB (is_active=False, blockchain_status=REVOKED)
    3. Update blockchain transaction status
    4. Return { status: REVOKED, certificate_id, revoked_at }

    Note: Full blockchain verification (get_certificate_record, check
    record.status == REVOKED) requires BlockchainService integration.

    Raises:
        CertificateNotFoundError: If certificate not found.
        OwnershipViolationError: If university doesn't own this certificate.
        CertificateAlreadyRevokedError: If already revoked.
    """
    async with db.begin():
        certificate = await CertificateRepository.get_by_id(db, cert_id)
        if certificate is None:
            raise CertificateNotFoundError()

        if certificate.university_id != current_user.university_id:
            raise OwnershipViolationError()

        if not certificate.is_active:
            raise CertificateAlreadyRevokedError()

        # Revoke in DB
        revoked_cert = await CertificateRepository.revoke(
            db, cert_id, reason="Revocation confirmed on blockchain",
            revoked_by=current_user.id
        )

        # Update blockchain transaction
        txs = await BlockchainTransactionRepository.get_by_certificate_id(
            db, cert_id
        )
        for tx in txs:
            if tx.tx_type == TransactionType.REVOKE_HASH and \
               tx.status == TransactionStatus.PENDING:
                await BlockchainTransactionRepository.update_status(
                    db,
                    tx.id,
                    TransactionStatus.CONFIRMED,
                    block_data={"tx_hash": blockchain_tx_hash},
                )
                break

    return {
        "status": "REVOKED",
        "certificate_id": cert_id,
        "revoked_at": datetime.now(timezone.utc),
    }
