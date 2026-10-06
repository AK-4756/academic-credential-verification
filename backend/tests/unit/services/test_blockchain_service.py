# backend/tests/unit/services/test_blockchain_service.py
# Sprint 4 D11: Unit tests for BlockchainService with mocked Web3/contract.
#
# All Web3 interactions are mocked - no real Ethereum node needed.
# Tests verify:
#   - Contract call delegation and result parsing
#   - Hash format validation
#   - Address validation
#   - Retry logic
#   - Circuit breaker behavior
#   - Return type construction (dataclasses from blockchain.schemas)

import os
import sys
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from blockchain.schemas import (
    BlockchainVerificationResult,
    ChainCertificateRecord,
    TransactionReceipt,
)
from core.constants import (
    BLOCKCHAIN_CIRCUIT_BREAKER_THRESHOLD,
    BLOCKCHAIN_MAX_RETRIES,
)
from core.exceptions import (
    BlockchainAddressError,
    BlockchainConnectionError,
    BlockchainContractError,
    BlockchainHashFormatError,
    BlockchainTimeoutError,
)

pytestmark = pytest.mark.unit

# ─── Helpers ─────────────────────────────────────────────────────────────────

VALID_HASH = "a" * 64
VALID_CERT_UID = "TEST-2025-00001"
VALID_ADDRESS = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
PROVIDER_URL = "http://127.0.0.1:8545"


@pytest.fixture
def mock_web3():
    """Create a mock Web3 instance."""
    w3 = MagicMock()
    w3.is_connected.return_value = True
    return w3


@pytest.fixture
def mock_contract():
    """Create a mock contract instance."""
    return MagicMock()


@pytest.fixture
def blockchain_service(mock_web3, mock_contract):
    """
    Create a BlockchainService with mocked Web3 and contract.

    Patches the web3_client functions so __init__ doesn't make real connections.
    """
    with patch("blockchain.blockchain_service.create_web3_instance") as mock_create, \
         patch("blockchain.blockchain_service.load_contract_abi") as mock_abi, \
         patch("blockchain.blockchain_service.get_contract") as mock_get_contract:

        mock_create.return_value = mock_web3
        mock_abi.return_value = [{"type": "function", "name": "test"}]
        mock_get_contract.return_value = mock_contract

        from blockchain.blockchain_service import BlockchainService
        service = BlockchainService(
            provider_url=PROVIDER_URL,
            contract_address=CONTRACT_ADDRESS,
            chain_id=31337,
        )
    return service


# ═══════════════════════════════════════════════════════════════════════════════
#  verify_certificate
# ═══════════════════════════════════════════════════════════════════════════════


class TestVerifyCertificate:
    """Tests for BlockchainService.verify_certificate()."""

    def test_verify_certificate_valid_active(self, blockchain_service, mock_contract):
        """Returns is_valid=True, status='ACTIVE' when contract returns (True, 0)."""
        mock_contract.functions.verifyCertificate.return_value.call.return_value = (True, 0)

        result = blockchain_service.verify_certificate(VALID_CERT_UID, VALID_HASH)

        assert isinstance(result, BlockchainVerificationResult)
        assert result.is_valid is True
        assert result.status == "ACTIVE"
        assert result.cert_uid == VALID_CERT_UID

    def test_verify_certificate_hash_mismatch(self, blockchain_service, mock_contract):
        """Returns is_valid=False, status='ACTIVE' when hashes differ."""
        mock_contract.functions.verifyCertificate.return_value.call.return_value = (False, 0)

        result = blockchain_service.verify_certificate(VALID_CERT_UID, VALID_HASH)

        assert result.is_valid is False
        assert result.status == "ACTIVE"

    def test_verify_certificate_revoked(self, blockchain_service, mock_contract):
        """Returns is_valid=False, status='REVOKED' when cert is revoked."""
        mock_contract.functions.verifyCertificate.return_value.call.return_value = (False, 1)

        result = blockchain_service.verify_certificate(VALID_CERT_UID, VALID_HASH)

        assert result.is_valid is False
        assert result.status == "REVOKED"

    def test_verify_certificate_invalid_hash_format(self, blockchain_service):
        """Raises BlockchainHashFormatError for non-64-hex input."""
        with pytest.raises(BlockchainHashFormatError):
            blockchain_service.verify_certificate(VALID_CERT_UID, "invalid_hash")

    def test_verify_certificate_uppercase_hash_rejected(self, blockchain_service):
        """Uppercase hex is rejected by HASH_FORMAT_REGEX."""
        with pytest.raises(BlockchainHashFormatError):
            blockchain_service.verify_certificate(VALID_CERT_UID, "A" * 64)


# ═══════════════════════════════════════════════════════════════════════════════
#  get_certificate_record
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetCertificateRecord:
    """Tests for BlockchainService.get_certificate_record()."""

    def test_get_certificate_record_exists(self, blockchain_service, mock_contract):
        """Returns populated ChainCertificateRecord when exists=True."""
        # Contract returns struct as tuple:
        # (bytes32 hash, address issuer, uint256 issuedAt, uint256 revokedAt, uint8 status, bool exists)
        mock_hash = b"\xab" * 32
        issuer_addr = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        issued_ts = 1700000000
        mock_contract.functions.getCertificateRecord.return_value.call.return_value = (
            mock_hash,       # certificateHash (bytes32)
            issuer_addr,     # issuingUniversity
            issued_ts,       # issuedAt
            0,               # revokedAt (0 = not revoked)
            0,               # status (0 = ACTIVE)
            True,            # exists
        )

        result = blockchain_service.get_certificate_record(VALID_CERT_UID)

        assert isinstance(result, ChainCertificateRecord)
        assert result.exists is True
        assert result.status == "ACTIVE"
        assert result.certificate_hash == mock_hash.hex()
        assert result.revoked_at is None
        assert isinstance(result.issued_at, datetime)

    def test_get_certificate_record_not_found(self, blockchain_service, mock_contract):
        """Returns None when exists=False."""
        mock_contract.functions.getCertificateRecord.return_value.call.return_value = (
            b"\x00" * 32, "0x" + "00" * 20, 0, 0, 0, False
        )

        result = blockchain_service.get_certificate_record("NONEXISTENT-001")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
#  get_transaction_receipt
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetTransactionReceipt:
    """Tests for BlockchainService.get_transaction_receipt()."""

    def test_get_transaction_receipt_found(self, blockchain_service, mock_web3):
        """Returns TransactionReceipt when TX is mined."""
        tx_hash = "0x" + "ab" * 32
        mock_web3.eth.get_transaction_receipt.return_value = {
            "status": 1,
            "blockNumber": 42,
            "blockHash": b"\xcd" * 32,
            "gasUsed": 50000,
            "effectiveGasPrice": 1000000000,
        }

        result = blockchain_service.get_transaction_receipt(tx_hash)

        assert isinstance(result, TransactionReceipt)
        assert result.status == 1
        assert result.block_number == 42
        assert result.gas_used == 50000

    def test_get_transaction_receipt_not_mined(self, blockchain_service, mock_web3):
        """Returns None when TX is not mined yet."""
        from web3.exceptions import TransactionNotFound
        mock_web3.eth.get_transaction_receipt.side_effect = TransactionNotFound(
            message="Transaction not found"
        )

        result = blockchain_service.get_transaction_receipt("0x" + "ff" * 32)
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
#  is_authorized_issuer
# ═══════════════════════════════════════════════════════════════════════════════


class TestIsAuthorizedIssuer:
    """Tests for BlockchainService.is_authorized_issuer()."""

    def test_is_authorized_issuer_true(self, blockchain_service, mock_contract):
        """Returns True when contract returns True."""
        mock_contract.functions.isAuthorizedIssuer.return_value.call.return_value = True

        result = blockchain_service.is_authorized_issuer(VALID_ADDRESS)
        assert result is True

    def test_is_authorized_issuer_false(self, blockchain_service, mock_contract):
        """Returns False when contract returns False."""
        mock_contract.functions.isAuthorizedIssuer.return_value.call.return_value = False

        result = blockchain_service.is_authorized_issuer(VALID_ADDRESS)
        assert result is False

    def test_is_authorized_issuer_invalid_address(self, blockchain_service):
        """Raises BlockchainAddressError for invalid wallet address."""
        with pytest.raises(BlockchainAddressError):
            blockchain_service.is_authorized_issuer("not_an_address")

    def test_is_authorized_issuer_missing_0x(self, blockchain_service):
        """Raises BlockchainAddressError when 0x prefix is missing."""
        with pytest.raises(BlockchainAddressError):
            blockchain_service.is_authorized_issuer("70997970C51812dc3A010C7d01b50e0d17dc79C8")


# ═══════════════════════════════════════════════════════════════════════════════
#  get_certificate_count
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetCertificateCount:
    """Tests for BlockchainService.get_certificate_count()."""

    def test_get_certificate_count(self, blockchain_service, mock_contract):
        """Returns integer from contract."""
        mock_contract.functions.getCertificateCount.return_value.call.return_value = 42

        result = blockchain_service.get_certificate_count()
        assert result == 42
        assert isinstance(result, int)


# ═══════════════════════════════════════════════════════════════════════════════
#  is_connected
# ═══════════════════════════════════════════════════════════════════════════════


class TestIsConnected:
    """Tests for BlockchainService.is_connected()."""

    def test_is_connected_true(self, blockchain_service, mock_web3):
        """Returns True when Web3 is connected."""
        mock_web3.is_connected.return_value = True
        assert blockchain_service.is_connected() is True

    def test_is_connected_false(self, blockchain_service, mock_web3):
        """Returns False when Web3 connection fails."""
        mock_web3.is_connected.return_value = False
        assert blockchain_service.is_connected() is False

    def test_is_connected_exception(self, blockchain_service, mock_web3):
        """Returns False when is_connected raises an exception."""
        mock_web3.is_connected.side_effect = Exception("connection lost")
        assert blockchain_service.is_connected() is False


# ═══════════════════════════════════════════════════════════════════════════════
#  Retry and Circuit Breaker
# ═══════════════════════════════════════════════════════════════════════════════


class TestRetryAndCircuitBreaker:
    """Tests for retry logic and circuit breaker behavior."""

    def test_retry_on_connection_error(self, blockchain_service, mock_contract):
        """Retries up to BLOCKCHAIN_MAX_RETRIES on ConnectionError."""
        mock_contract.functions.getCertificateCount.return_value.call.side_effect = [
            ConnectionError("fail 1"),
            ConnectionError("fail 2"),
            42,  # Success on 3rd try
        ]

        # Patch time.sleep to avoid real delays in tests
        with patch("blockchain.blockchain_service.time.sleep"):
            result = blockchain_service.get_certificate_count()

        assert result == 42

    def test_all_retries_exhausted(self, blockchain_service, mock_contract):
        """Raises BlockchainConnectionError when all retries fail."""
        mock_contract.functions.getCertificateCount.return_value.call.side_effect = (
            ConnectionError("persistent failure")
        )

        with patch("blockchain.blockchain_service.time.sleep"):
            with pytest.raises(BlockchainConnectionError):
                blockchain_service.get_certificate_count()

    def test_circuit_breaker_opens(self, blockchain_service, mock_contract):
        """After BLOCKCHAIN_CIRCUIT_BREAKER_THRESHOLD consecutive failures, raises immediately."""
        # Force the circuit breaker to open by simulating consecutive failures
        blockchain_service._consecutive_failures = BLOCKCHAIN_CIRCUIT_BREAKER_THRESHOLD
        blockchain_service._last_failure_time = time.time()

        with pytest.raises(BlockchainConnectionError):
            blockchain_service.get_certificate_count()

    def test_contract_revert_not_retried(self, blockchain_service, mock_contract):
        """ContractLogicError is NOT retried (it will revert again)."""
        from web3.exceptions import ContractLogicError
        mock_contract.functions.getCertificateCount.return_value.call.side_effect = (
            ContractLogicError("revert: not authorized")
        )

        with pytest.raises(BlockchainContractError):
            blockchain_service.get_certificate_count()
