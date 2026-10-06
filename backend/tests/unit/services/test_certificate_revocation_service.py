# backend/tests/unit/services/test_certificate_revocation_service.py
# Unit tests for certificate_revocation_service.py
#
# Functions tested:
#   initiate_revocation(cert_id, reason, current_user, db, blockchain_service=None) -> dict
#   confirm_revocation(cert_id, blockchain_tx_hash, current_user, db, blockchain_service) -> dict

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from core.constants import BlockchainStatus, TransactionStatus, TransactionType
from core.exceptions import (
    CertificateAlreadyRevokedError,
    CertificateNotFoundError,
    MissingWalletAddressError,
    OwnershipViolationError,
    ServiceError,
    UnconfirmedCertificateError,
)

pytestmark = pytest.mark.unit


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def db():
    """Mock AsyncSession. begin() returns an async context manager."""
    session = MagicMock()
    ctx = AsyncMock()
    session.begin.return_value = ctx
    return session


@pytest.fixture
def university_id():
    return uuid4()


@pytest.fixture
def current_user(university_id):
    """Mock university admin user."""
    user = MagicMock()
    user.id = uuid4()
    user.university_id = university_id
    user.role = "UNIVERSITY_ADMIN"
    return user


@pytest.fixture
def confirmed_certificate(university_id):
    """Mock confirmed, active certificate owned by the user's university."""
    cert = MagicMock()
    cert.id = uuid4()
    cert.certificate_uid = "TEST-2025-00001"
    cert.university_id = university_id
    cert.blockchain_status = BlockchainStatus.CONFIRMED
    cert.is_active = True
    return cert


@pytest.fixture
def university_with_wallet(university_id):
    """Mock university with wallet address."""
    uni = MagicMock()
    uni.id = university_id
    uni.wallet_address = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    return uni


@pytest.fixture
def mock_blockchain():
    """Mock BlockchainService with passing pre-flight checks."""
    bs = MagicMock()
    bs.is_authorized_issuer.return_value = True
    record = MagicMock()
    record.exists = True
    record.status = "ACTIVE"
    record.issuing_university = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
    record.revoked_at = None
    bs.get_certificate_record.return_value = record
    return bs


# ═══════════════════════════════════════════════════════════════════════════════
#  initiate_revocation
# ═══════════════════════════════════════════════════════════════════════════════


class TestInitiateRevocation:
    """Tests for initiate_revocation."""

    @patch("services.certificate_revocation_service.BlockchainTransactionRepository")
    @patch("services.certificate_revocation_service.UniversityRepository")
    @patch("services.certificate_revocation_service.CertificateRepository")
    async def test_initiate_revocation_success(
        self, mock_cert_repo, mock_uni_repo, mock_tx_repo,
        db, current_user, confirmed_certificate, university_with_wallet,
    ):
        """Successfully initiates revocation for a valid certificate."""
        from services.certificate_revocation_service import initiate_revocation

        mock_cert_repo.get_by_id = AsyncMock(return_value=confirmed_certificate)
        mock_uni_repo.get_by_id = AsyncMock(return_value=university_with_wallet)
        mock_tx_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))

        result = await initiate_revocation(
            confirmed_certificate.id, "Test revocation", current_user, db
        )

        assert result["certificate_id"] == confirmed_certificate.id
        assert result["certificate_uid"] == confirmed_certificate.certificate_uid
        assert "university_wallet_address" in result
        mock_tx_repo.create.assert_awaited_once()

    @patch("services.certificate_revocation_service.CertificateRepository")
    async def test_initiate_revocation_not_found(
        self, mock_cert_repo, db, current_user
    ):
        """Raises CertificateNotFoundError if certificate doesn't exist."""
        from services.certificate_revocation_service import initiate_revocation

        mock_cert_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CertificateNotFoundError):
            await initiate_revocation(uuid4(), "reason", current_user, db)

    @patch("services.certificate_revocation_service.CertificateRepository")
    async def test_initiate_revocation_ownership_violation(
        self, mock_cert_repo, db, current_user
    ):
        """Raises OwnershipViolationError if different university."""
        from services.certificate_revocation_service import initiate_revocation

        cert = MagicMock()
        cert.university_id = uuid4()  # Different university
        mock_cert_repo.get_by_id = AsyncMock(return_value=cert)

        with pytest.raises(OwnershipViolationError):
            await initiate_revocation(uuid4(), "reason", current_user, db)

    @patch("services.certificate_revocation_service.CertificateRepository")
    async def test_initiate_revocation_already_revoked(
        self, mock_cert_repo, db, current_user, confirmed_certificate
    ):
        """Raises CertificateAlreadyRevokedError if not active."""
        from services.certificate_revocation_service import initiate_revocation

        confirmed_certificate.is_active = False
        mock_cert_repo.get_by_id = AsyncMock(return_value=confirmed_certificate)

        with pytest.raises(CertificateAlreadyRevokedError):
            await initiate_revocation(
                confirmed_certificate.id, "reason", current_user, db
            )

    @patch("services.certificate_revocation_service.UniversityRepository")
    @patch("services.certificate_revocation_service.CertificateRepository")
    async def test_initiate_revocation_missing_wallet(
        self, mock_cert_repo, mock_uni_repo,
        db, current_user, confirmed_certificate,
    ):
        """Raises MissingWalletAddressError if university has no wallet."""
        from services.certificate_revocation_service import initiate_revocation

        mock_cert_repo.get_by_id = AsyncMock(return_value=confirmed_certificate)
        uni_no_wallet = MagicMock()
        uni_no_wallet.wallet_address = None
        mock_uni_repo.get_by_id = AsyncMock(return_value=uni_no_wallet)

        with pytest.raises(MissingWalletAddressError):
            await initiate_revocation(
                confirmed_certificate.id, "reason", current_user, db
            )

    @patch("services.certificate_revocation_service.BlockchainTransactionRepository")
    @patch("services.certificate_revocation_service.UniversityRepository")
    @patch("services.certificate_revocation_service.CertificateRepository")
    async def test_initiate_revocation_unconfirmed(
        self, mock_cert_repo, mock_uni_repo, mock_tx_repo,
        db, current_user, university_id
    ):
        """Raises UnconfirmedCertificateError for PENDING certificate."""
        from services.certificate_revocation_service import initiate_revocation

        cert = MagicMock()
        cert.id = uuid4()
        cert.university_id = university_id
        cert.blockchain_status = BlockchainStatus.PENDING
        cert.is_active = True
        mock_cert_repo.get_by_id = AsyncMock(return_value=cert)

        with pytest.raises(UnconfirmedCertificateError):
            await initiate_revocation(cert.id, "reason", current_user, db)


# ═══════════════════════════════════════════════════════════════════════════════
#  confirm_revocation
# ═══════════════════════════════════════════════════════════════════════════════


class TestConfirmRevocation:
    """Tests for confirm_revocation."""

    @patch("services.certificate_revocation_service.BlockchainTransactionRepository")
    @patch("services.certificate_revocation_service.CertificateRepository")
    async def test_confirm_revocation_success(
        self, mock_cert_repo, mock_tx_repo,
        db, current_user, confirmed_certificate, mock_blockchain,
    ):
        """Successfully confirms revocation when TX succeeded and status=REVOKED."""
        from services.certificate_revocation_service import confirm_revocation

        mock_cert_repo.get_by_id = AsyncMock(return_value=confirmed_certificate)
        mock_cert_repo.revoke = AsyncMock()

        revoke_tx = MagicMock()
        revoke_tx.id = uuid4()
        revoke_tx.tx_type = TransactionType.REVOKE_HASH
        revoke_tx.status = TransactionStatus.PENDING
        mock_tx_repo.get_by_certificate_id = AsyncMock(return_value=[revoke_tx])
        mock_tx_repo.update_status = AsyncMock()

        # Set blockchain to return REVOKED status
        receipt = MagicMock(status=1, block_number=100, block_hash="0xabc",
                           gas_used=50000, effective_gas_price=1000000000)
        mock_blockchain.get_transaction_receipt.return_value = receipt

        record = MagicMock(exists=True, status="REVOKED",
                           revoked_at=datetime.now(timezone.utc))
        mock_blockchain.get_certificate_record.return_value = record

        result = await confirm_revocation(
            confirmed_certificate.id, "0x" + "ab" * 32,
            current_user, db, mock_blockchain,
        )

        assert result["status"] == "REVOKED"
        mock_cert_repo.revoke.assert_awaited_once()

    @patch("services.certificate_revocation_service.BlockchainTransactionRepository")
    @patch("services.certificate_revocation_service.CertificateRepository")
    async def test_confirm_revocation_tx_not_mined(
        self, mock_cert_repo, mock_tx_repo,
        db, current_user, confirmed_certificate, mock_blockchain,
    ):
        """Returns SUBMITTED when TX is not yet mined."""
        from services.certificate_revocation_service import confirm_revocation

        mock_cert_repo.get_by_id = AsyncMock(return_value=confirmed_certificate)

        revoke_tx = MagicMock()
        revoke_tx.id = uuid4()
        revoke_tx.tx_type = TransactionType.REVOKE_HASH
        revoke_tx.status = TransactionStatus.PENDING
        mock_tx_repo.get_by_certificate_id = AsyncMock(return_value=[revoke_tx])
        mock_tx_repo.update_status = AsyncMock()

        mock_blockchain.get_transaction_receipt.return_value = None

        result = await confirm_revocation(
            confirmed_certificate.id, "0x" + "ab" * 32,
            current_user, db, mock_blockchain,
        )

        assert result["status"] == "SUBMITTED"

    @patch("services.certificate_revocation_service.BlockchainTransactionRepository")
    @patch("services.certificate_revocation_service.CertificateRepository")
    async def test_confirm_revocation_tx_failed(
        self, mock_cert_repo, mock_tx_repo,
        db, current_user, confirmed_certificate, mock_blockchain,
    ):
        """Raises ServiceError when TX reverted (status=0)."""
        from services.certificate_revocation_service import confirm_revocation

        mock_cert_repo.get_by_id = AsyncMock(return_value=confirmed_certificate)

        revoke_tx = MagicMock()
        revoke_tx.id = uuid4()
        revoke_tx.tx_type = TransactionType.REVOKE_HASH
        revoke_tx.status = TransactionStatus.PENDING
        mock_tx_repo.get_by_certificate_id = AsyncMock(return_value=[revoke_tx])
        mock_tx_repo.update_status = AsyncMock()

        receipt = MagicMock(status=0, block_number=100)
        mock_blockchain.get_transaction_receipt.return_value = receipt

        with pytest.raises(ServiceError, match="reverted"):
            await confirm_revocation(
                confirmed_certificate.id, "0x" + "ab" * 32,
                current_user, db, mock_blockchain,
            )

    @patch("services.certificate_revocation_service.CertificateRepository")
    async def test_confirm_revocation_ownership_violation(
        self, mock_cert_repo, db, current_user, mock_blockchain
    ):
        """Raises OwnershipViolationError if different university."""
        from services.certificate_revocation_service import confirm_revocation

        cert = MagicMock()
        cert.university_id = uuid4()  # Different university
        cert.is_active = True
        mock_cert_repo.get_by_id = AsyncMock(return_value=cert)

        with pytest.raises(OwnershipViolationError):
            await confirm_revocation(
                uuid4(), "0x" + "ab" * 32,
                current_user, db, mock_blockchain,
            )
