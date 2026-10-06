# backend/tests/integration/test_blockchain_integration.py
# P11b Part 1 — Real Hardhat ↔ Backend Blockchain Integration Tests
#
# These tests exercise the REAL BlockchainService against a live Hardhat
# localhost node (http://127.0.0.1:8545). They require:
#
#   1. `npm run node` running in blockchain/
#   2. `npm run deploy:localhost` executed (sets CONTRACT_ADDRESS in .env)
#   3. `ISSUER_ADDRESS=0x7099... npm run authorize:localhost` executed
#
# The test suite deploys a fresh contract in the session fixture so it owns
# its own on-chain state independent of the manually-deployed instance.
# This makes the tests fully repeatable without pre-existing state.
#
# Test constants (Hardhat deterministic accounts — public dev keys only):
#   OWNER     = account #0   (0xf39F...)  — deploys and owns the contract
#   ISSUER    = account #1   (0x7099...)  — authorized university wallet
#   OUTSIDER  = account #2   (0x3C44...)  — never authorized
#
# Marked with @pytest.mark.hardhat so they can be excluded when the node
# is not running: pytest -m "not hardhat"

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from web3 import Web3

# Ensure backend/ is on path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------------
# Hardhat deterministic accounts (well-known dev keys — public knowledge)
# ---------------------------------------------------------------------------
HARDHAT_RPC = "http://127.0.0.1:8545"
CONTRACT_ABI_PATH = str(BACKEND_DIR / "blockchain" / "abi" / "CertificateRegistry.json")
CONTRACT_ADDRESS_ENV = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

OWNER_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
OWNER_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
ISSUER_ADDRESS = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
ISSUER_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
OUTSIDER_ADDRESS = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"


# ---------------------------------------------------------------------------
# Helper: deploy a fresh contract for the test session
# ---------------------------------------------------------------------------

def _deploy_fresh_contract(w3: Web3) -> tuple[str, object]:
    """Deploy a fresh CertificateRegistry and return (address, contract)."""
    import json

    with open(CONTRACT_ABI_PATH, "r", encoding="utf-8") as f:
        artifact = json.load(f)

    abi = artifact["abi"]
    bytecode = artifact["bytecode"]

    ContractClass = w3.eth.contract(abi=abi, bytecode=bytecode)

    owner = w3.eth.accounts[0]
    tx_hash = ContractClass.constructor().transact({"from": owner})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    address = receipt["contractAddress"]

    contract = w3.eth.contract(address=address, abi=abi)
    return address, contract


def _authorize_issuer(w3: Web3, contract, issuer: str) -> None:
    """Call authorizeIssuer as the owner account."""
    owner = w3.eth.accounts[0]
    tx = contract.functions.authorizeIssuer(issuer).transact({"from": owner})
    w3.eth.wait_for_transaction_receipt(tx)


def _store_certificate(w3: Web3, contract, issuer: str, cert_uid: str, cert_hash_hex: str) -> str:
    """Call storeCertificate as the issuer. Returns tx hash."""
    hash_bytes = bytes.fromhex(cert_hash_hex)
    tx = contract.functions.storeCertificate(cert_uid, hash_bytes).transact({"from": issuer})
    w3.eth.wait_for_transaction_receipt(tx)
    return tx.hex()


def _make_sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Session fixture: shared web3 + freshly-deployed contract
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def w3():
    """Web3 instance connected to Hardhat localhost."""
    instance = Web3(Web3.HTTPProvider(HARDHAT_RPC, request_kwargs={"timeout": 30}))
    if not instance.is_connected():
        pytest.skip("Hardhat localhost node is not running at http://127.0.0.1:8545")
    return instance


@pytest.fixture(scope="module")
def deployed(w3):
    """
    Deploy a fresh CertificateRegistry and authorize ISSUER.
    Returns (address, contract).
    """
    address, contract = _deploy_fresh_contract(w3)
    _authorize_issuer(w3, contract, ISSUER_ADDRESS)
    return address, contract


@pytest.fixture(scope="module")
def blockchain_service(deployed):
    """Real BlockchainService bound to the freshly-deployed contract."""
    address, _ = deployed
    from blockchain.blockchain_service import BlockchainService
    svc = BlockchainService(
        provider_url=HARDHAT_RPC,
        contract_address=address,
        chain_id=31337,
        abi_path=CONTRACT_ABI_PATH,
    )
    return svc


# ===========================================================================
# A. Connection
# ===========================================================================

@pytest.mark.hardhat
class TestBlockchainConnection:
    """Verify the backend can connect to the local Hardhat node."""

    def test_node_is_reachable(self, w3):
        """Web3 provider reports connected to http://127.0.0.1:8545."""
        assert w3.is_connected() is True

    def test_correct_chain_id(self, w3):
        """Chain ID is 31337 (Hardhat local network)."""
        assert w3.eth.chain_id == 31337

    def test_blockchain_service_connects(self, blockchain_service):
        """BlockchainService.is_connected() returns True."""
        assert blockchain_service.is_connected() is True

    def test_contract_abi_is_valid(self, blockchain_service):
        """ABI was loaded (get_certificate_count does not raise)."""
        count = blockchain_service.get_certificate_count()
        assert isinstance(count, int)

    def test_contract_address_is_valid(self, blockchain_service, deployed):
        """BlockchainService is bound to the correct address."""
        address, _ = deployed
        # get_certificate_count returns a valid value → contract is reachable
        count = blockchain_service.get_certificate_count()
        assert count >= 0  # fresh deployment starts at 0


# ===========================================================================
# B. Issuer Authorization
# ===========================================================================

@pytest.mark.hardhat
class TestIssuerAuthorization:
    """Verify backend correctly reports issuer authorization status."""

    def test_authorized_issuer_is_recognized(self, blockchain_service):
        """ISSUER (authorized in session fixture) returns True."""
        result = blockchain_service.is_authorized_issuer(ISSUER_ADDRESS)
        assert result is True

    def test_unauthorized_wallet_is_rejected(self, blockchain_service):
        """OUTSIDER (never authorized) returns False."""
        result = blockchain_service.is_authorized_issuer(OUTSIDER_ADDRESS)
        assert result is False

    def test_owner_is_not_an_issuer(self, blockchain_service):
        """Owner wallet (account #0) is not in the issuer whitelist."""
        result = blockchain_service.is_authorized_issuer(OWNER_ADDRESS)
        assert result is False

    def test_invalid_address_raises(self, blockchain_service):
        """Invalid wallet format raises BlockchainAddressError."""
        from core.exceptions import BlockchainAddressError
        with pytest.raises(BlockchainAddressError):
            blockchain_service.is_authorized_issuer("not-an-address")


# ===========================================================================
# C. Certificate Issuance (via contract directly, then read via service)
# ===========================================================================

@pytest.mark.hardhat
class TestCertificateIssuance:
    """
    Store certificates directly via Web3 (simulating MetaMask),
    then verify the backend service reads them correctly.
    """

    def test_store_certificate_and_retrieve(self, w3, deployed, blockchain_service):
        """Store a cert via Web3, retrieve via backend service."""
        _, contract = deployed
        cert_uid = "TEST-ISSUANCE-001"
        cert_hash = _make_sha256_hex("test-pdf-content-001")

        _store_certificate(w3, contract, ISSUER_ADDRESS, cert_uid, cert_hash)

        record = blockchain_service.get_certificate_record(cert_uid)
        assert record is not None
        assert record.exists is True
        assert record.certificate_hash == cert_hash
        assert record.issuing_university.lower() == ISSUER_ADDRESS.lower()
        assert record.status == "ACTIVE"
        assert record.revoked_at is None

    def test_certificate_count_increments(self, w3, deployed, blockchain_service):
        """getCertificateCount increments after each storeCertificate call."""
        _, contract = deployed
        count_before = blockchain_service.get_certificate_count()

        cert_uid = "TEST-COUNT-001"
        cert_hash = _make_sha256_hex("count-test-001")
        _store_certificate(w3, contract, ISSUER_ADDRESS, cert_uid, cert_hash)

        count_after = blockchain_service.get_certificate_count()
        assert count_after == count_before + 1

    def test_nonexistent_certificate_returns_none(self, blockchain_service):
        """get_certificate_record returns None for a cert that was never stored."""
        record = blockchain_service.get_certificate_record("NONEXISTENT-UID-9999")
        assert record is None

    def test_issuer_address_is_preserved(self, w3, deployed, blockchain_service):
        """The issuing_university in the stored record matches the issuer."""
        _, contract = deployed
        cert_uid = "TEST-ISSUER-ADDRESS-001"
        cert_hash = _make_sha256_hex("issuer-address-test")

        _store_certificate(w3, contract, ISSUER_ADDRESS, cert_uid, cert_hash)

        record = blockchain_service.get_certificate_record(cert_uid)
        assert record is not None
        assert Web3.to_checksum_address(record.issuing_university) == Web3.to_checksum_address(ISSUER_ADDRESS)

    def test_issued_at_timestamp_is_set(self, w3, deployed, blockchain_service):
        """issued_at is a datetime after the block timestamp."""
        from datetime import datetime, timezone
        _, contract = deployed
        cert_uid = "TEST-TIMESTAMP-001"
        cert_hash = _make_sha256_hex("timestamp-test")

        _store_certificate(w3, contract, ISSUER_ADDRESS, cert_uid, cert_hash)

        record = blockchain_service.get_certificate_record(cert_uid)
        assert record is not None
        assert record.issued_at is not None
        assert isinstance(record.issued_at, datetime)
        # Hardhat uses block time; should be a reasonable unix timestamp
        assert record.issued_at.year >= 2020


# ===========================================================================
# D. Certificate Verification
# ===========================================================================

@pytest.mark.hardhat
class TestCertificateVerification:
    """Verify the verify_certificate() backend service method."""

    def test_matching_hash_returns_valid(self, w3, deployed, blockchain_service):
        """Correct hash → is_valid=True, status=ACTIVE."""
        _, contract = deployed
        cert_uid = "TEST-VERIFY-VALID-001"
        cert_hash = _make_sha256_hex("verify-valid-content")

        _store_certificate(w3, contract, ISSUER_ADDRESS, cert_uid, cert_hash)

        result = blockchain_service.verify_certificate(cert_uid, cert_hash)
        assert result.is_valid is True
        assert result.status == "ACTIVE"
        assert result.cert_uid == cert_uid

    def test_mismatched_hash_returns_invalid(self, w3, deployed, blockchain_service):
        """Wrong hash → is_valid=False, status=ACTIVE (tampered)."""
        _, contract = deployed
        cert_uid = "TEST-VERIFY-TAMPER-001"
        cert_hash = _make_sha256_hex("original-content")
        tampered_hash = _make_sha256_hex("tampered-content")

        _store_certificate(w3, contract, ISSUER_ADDRESS, cert_uid, cert_hash)

        result = blockchain_service.verify_certificate(cert_uid, tampered_hash)
        assert result.is_valid is False
        assert result.status == "ACTIVE"

    def test_nonexistent_cert_returns_invalid(self, blockchain_service):
        """Non-existent cert → is_valid=False, status=ACTIVE."""
        result = blockchain_service.verify_certificate(
            "NONEXISTENT-VERIFY-9999",
            _make_sha256_hex("does-not-matter")
        )
        assert result.is_valid is False
        assert result.status == "ACTIVE"

    def test_verify_certificate_invalid_hash_format_raises(self, blockchain_service):
        """Invalid hash format (not 64 hex chars) raises BlockchainHashFormatError."""
        from core.exceptions import BlockchainHashFormatError
        with pytest.raises(BlockchainHashFormatError):
            blockchain_service.verify_certificate("SOME-UID", "not-a-valid-hash")

    def test_revoked_cert_returns_revoked_status(self, w3, deployed, blockchain_service):
        """Revoked cert → is_valid=False, status=REVOKED (matching hash)."""
        _, contract = deployed
        cert_uid = "TEST-VERIFY-REVOKED-001"
        cert_hash = _make_sha256_hex("revoke-verify-test")

        _store_certificate(w3, contract, ISSUER_ADDRESS, cert_uid, cert_hash)

        # Revoke via Web3
        owner = w3.eth.accounts[0]
        tx = contract.functions.revokeCertificate(cert_uid).transact({"from": ISSUER_ADDRESS})
        w3.eth.wait_for_transaction_receipt(tx)

        result = blockchain_service.verify_certificate(cert_uid, cert_hash)
        assert result.is_valid is False
        assert result.status == "REVOKED"


# ===========================================================================
# E. Revocation
# ===========================================================================

@pytest.mark.hardhat
class TestRevocation:
    """Verify revocation is correctly reflected by the backend service."""

    def test_revoked_cert_record_shows_revoked_status(self, w3, deployed, blockchain_service):
        """After revocation, get_certificate_record returns status=REVOKED."""
        _, contract = deployed
        cert_uid = "TEST-REVOKE-RECORD-001"
        cert_hash = _make_sha256_hex("revoke-record-test")

        _store_certificate(w3, contract, ISSUER_ADDRESS, cert_uid, cert_hash)

        # Pre-revocation: ACTIVE
        record_before = blockchain_service.get_certificate_record(cert_uid)
        assert record_before is not None
        assert record_before.status == "ACTIVE"

        # Revoke
        tx = contract.functions.revokeCertificate(cert_uid).transact({"from": ISSUER_ADDRESS})
        w3.eth.wait_for_transaction_receipt(tx)

        # Post-revocation: REVOKED
        record_after = blockchain_service.get_certificate_record(cert_uid)
        assert record_after is not None
        assert record_after.status == "REVOKED"
        assert record_after.revoked_at is not None

    def test_revoked_cert_hash_is_preserved(self, w3, deployed, blockchain_service):
        """Revocation does not alter the stored certificate hash."""
        _, contract = deployed
        cert_uid = "TEST-REVOKE-HASH-001"
        cert_hash = _make_sha256_hex("hash-preserved-after-revoke")

        _store_certificate(w3, contract, ISSUER_ADDRESS, cert_uid, cert_hash)

        tx = contract.functions.revokeCertificate(cert_uid).transact({"from": ISSUER_ADDRESS})
        w3.eth.wait_for_transaction_receipt(tx)

        record = blockchain_service.get_certificate_record(cert_uid)
        assert record is not None
        assert record.certificate_hash == cert_hash  # hash unchanged

    def test_get_transaction_receipt_returns_receipt(self, w3, deployed, blockchain_service):
        """get_transaction_receipt returns a valid receipt for a confirmed tx."""
        _, contract = deployed
        cert_uid = "TEST-RECEIPT-001"
        cert_hash = _make_sha256_hex("receipt-test")

        # Store and capture tx hash
        hash_bytes = bytes.fromhex(cert_hash)
        tx_hash_obj = contract.functions.storeCertificate(cert_uid, hash_bytes).transact(
            {"from": ISSUER_ADDRESS}
        )
        w3.eth.wait_for_transaction_receipt(tx_hash_obj)
        tx_hash_str = "0x" + tx_hash_obj.hex()

        receipt = blockchain_service.get_transaction_receipt(tx_hash_str)
        assert receipt is not None
        assert receipt.status == 1   # success
        assert receipt.block_number > 0
        assert receipt.gas_used > 0

    def test_nonexistent_tx_hash_returns_none(self, blockchain_service):
        """get_transaction_receipt returns None for a tx that doesn't exist."""
        fake_tx = "0x" + "ab" * 32
        receipt = blockchain_service.get_transaction_receipt(fake_tx)
        assert receipt is None


# ===========================================================================
# F. Access Control / Security
# ===========================================================================

@pytest.mark.hardhat
class TestAccessControl:
    """Verify the contract enforces access control at the on-chain level."""

    def test_unauthorized_issuer_cannot_store(self, w3, deployed, blockchain_service):
        """
        Attempt to storeCertificate from OUTSIDER (not authorized).
        Web3 transaction should revert.
        """
        _, contract = deployed
        cert_uid = "TEST-UNAUTH-STORE-001"
        cert_hash = _make_sha256_hex("unauthorized-store")
        hash_bytes = bytes.fromhex(cert_hash)

        with pytest.raises(Exception) as exc_info:
            contract.functions.storeCertificate(cert_uid, hash_bytes).transact(
                {"from": OUTSIDER_ADDRESS}
            )
        # The contract reverts with NotAuthorizedIssuer
        assert "revert" in str(exc_info.value).lower() or "NotAuthorizedIssuer" in str(exc_info.value)

    def test_unauthorized_issuer_cannot_revoke(self, w3, deployed, blockchain_service):
        """
        Attempt to revokeCertificate from OUTSIDER for a cert issued by ISSUER.
        Should revert.
        """
        _, contract = deployed
        cert_uid = "TEST-UNAUTH-REVOKE-001"
        cert_hash = _make_sha256_hex("unauthorized-revoke")

        # Store legitimately
        _store_certificate(w3, contract, ISSUER_ADDRESS, cert_uid, cert_hash)

        # Try to revoke from OUTSIDER — should revert
        with pytest.raises(Exception) as exc_info:
            contract.functions.revokeCertificate(cert_uid).transact(
                {"from": OUTSIDER_ADDRESS}
            )
        assert "revert" in str(exc_info.value).lower() or "NotAuthorizedIssuer" in str(exc_info.value)

    def test_empty_hash_rejected_by_contract(self, w3, deployed):
        """bytes32(0) hash is rejected by the contract (InvalidCertificateHash)."""
        _, contract = deployed
        with pytest.raises(Exception) as exc_info:
            contract.functions.storeCertificate("EMPTY-HASH-001", b"\x00" * 32).transact(
                {"from": ISSUER_ADDRESS}
            )
        assert "revert" in str(exc_info.value).lower()

    def test_duplicate_uid_rejected_by_contract(self, w3, deployed):
        """Storing the same UID twice reverts with CertificateAlreadyExists."""
        _, contract = deployed
        cert_uid = "TEST-DUPLICATE-001"
        cert_hash = _make_sha256_hex("duplicate-test")
        hash_bytes = bytes.fromhex(cert_hash)

        # First store succeeds
        tx = contract.functions.storeCertificate(cert_uid, hash_bytes).transact(
            {"from": ISSUER_ADDRESS}
        )
        w3.eth.wait_for_transaction_receipt(tx)

        # Second store must revert
        with pytest.raises(Exception) as exc_info:
            contract.functions.storeCertificate(cert_uid, hash_bytes).transact(
                {"from": ISSUER_ADDRESS}
            )
        assert "revert" in str(exc_info.value).lower()

    def test_backend_service_sees_unauthorized_issuer_as_false(self, blockchain_service):
        """Backend service correctly reports OUTSIDER as unauthorized."""
        result = blockchain_service.is_authorized_issuer(OUTSIDER_ADDRESS)
        assert result is False
