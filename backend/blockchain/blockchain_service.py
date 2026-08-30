# backend/blockchain/blockchain_service.py
# BlockchainService — read-only Ethereum RPC client for CertificateRegistry.
#
# Architecture Reference: docs/backend.md Section 18.1 (Blockchain Integration Service)
# Directory Reference: docs/backend.md Section 27.1 (blockchain/blockchain_service.py)
# Build Order: implementation-roadmap.md Phase 6.5 (Infrastructure Services)
#
# ARCHITECTURE PRINCIPLE (from docs):
#   The backend blockchain service is READ-ONLY.
#   All 5 public methods use eth_call (free, no gas, no private key).
#   The backend NEVER signs or submits blockchain transactions.
#   MetaMask on the frontend handles all write operations.
#
# RESILIENCE STRATEGY (from docs Section 18.1):
#   - Retry: Up to 3 retries with exponential backoff for connection errors
#   - Timeout: 30-second timeout on all RPC calls
#   - Circuit breaker: After 5 consecutive failures, pause blockchain queries
#     for 60 seconds (prevents cascade failure)
#   - Fallback: If blockchain is unreachable during verification,
#     return result with blockchain_verified=False and error message.
#     Do NOT return AUTHENTIC if blockchain cannot be confirmed.
#
# PUBLIC METHODS (5):
#   verify_certificate(cert_uid, submitted_hash_hex) -> BlockchainVerificationResult
#   get_certificate_record(cert_uid) -> ChainCertificateRecord | None
#   get_transaction_receipt(tx_hash) -> TransactionReceipt | None
#   is_authorized_issuer(wallet_address) -> bool
#   get_certificate_count() -> int

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from web3 import Web3
from web3.exceptions import (
    ContractLogicError,
    TimeExhausted,
    TransactionNotFound,
)

from blockchain.schemas import (
    BlockchainVerificationResult,
    ChainCertificateRecord,
    TransactionReceipt,
)
from blockchain.web3_client import (
    create_web3_instance,
    get_contract,
    load_contract_abi,
)
from core.constants import (
    BLOCKCHAIN_CIRCUIT_BREAKER_PAUSE_SECONDS,
    BLOCKCHAIN_CIRCUIT_BREAKER_THRESHOLD,
    BLOCKCHAIN_MAX_RETRIES,
    BLOCKCHAIN_RPC_TIMEOUT_SECONDS,
    HASH_FORMAT_REGEX,
    WALLET_ADDRESS_REGEX,
)
from core.exceptions import (
    BlockchainAddressError,
    BlockchainConnectionError,
    BlockchainContractError,
    BlockchainHashFormatError,
    BlockchainTimeoutError,
)

logger = logging.getLogger(__name__)

# Contract CertificateStatus enum values (from CertificateRegistry.sol)
_CHAIN_STATUS_MAP = {
    0: "ACTIVE",
    1: "REVOKED",
}


class BlockchainService:
    """
    Read-only blockchain client for CertificateRegistry smart contract.

    Singleton instance created at startup and injected via
    FastAPI dependency injection (Depends(get_blockchain_service)).

    All methods use eth_call (free, no gas, no private key required).
    """

    def __init__(
        self,
        provider_url: str,
        contract_address: str,
        chain_id: int,
        abi_path: str | None = None,
    ) -> None:
        """
        Initialize the BlockchainService.

        Args:
            provider_url: Ethereum JSON-RPC endpoint URL.
            contract_address: Deployed CertificateRegistry contract address.
            chain_id: Expected network chain ID.
            abi_path: Path to the contract ABI JSON. Defaults to
                      blockchain/abi/CertificateRegistry.json.
        """
        self._provider_url = provider_url
        self._contract_address = contract_address
        self._chain_id = chain_id

        # Connection setup via web3_client
        self._web3 = create_web3_instance(
            provider_url=provider_url,
            timeout=BLOCKCHAIN_RPC_TIMEOUT_SECONDS,
        )

        # Load ABI and create contract instance
        abi = load_contract_abi(abi_path)
        self._contract = get_contract(self._web3, contract_address, abi)

        # Circuit breaker state
        self._consecutive_failures: int = 0
        self._last_failure_time: float = 0.0

        logger.info(
            "blockchain_service_initialized",
            extra={
                "provider_url": provider_url,
                "contract_address": contract_address,
                "chain_id": chain_id,
            },
        )

    # ─── Public Methods ──────────────────────────────────────────────────

    def verify_certificate(
        self,
        cert_uid: str,
        submitted_hash_hex: str,
    ) -> BlockchainVerificationResult:
        """
        Verify a certificate against the on-chain record.

        Docs Section 18.1 (verify_certificate):
        1. Convert hex to bytes32
        2. Call verifyCertificate(cert_uid, hash_bytes32)
        3. Interpret status (ACTIVE or REVOKED)

        Args:
            cert_uid: Certificate UID string (e.g., "MIT-2025-00142").
            submitted_hash_hex: 64-char lowercase hex string from HashService.

        Returns:
            BlockchainVerificationResult with is_valid, status, cert_uid.

        Raises:
            BlockchainHashFormatError: If hash format is invalid.
            BlockchainConnectionError: If RPC is unreachable.
            BlockchainContractError: If contract reverts.
        """
        # Validate hash format
        if not HASH_FORMAT_REGEX.match(submitted_hash_hex):
            raise BlockchainHashFormatError(
                message=f"Invalid hash format: expected 64 lowercase hex chars, "
                f"got '{submitted_hash_hex[:20]}...'"
            )

        # Convert hex to bytes32 (docs: Web3.to_bytes(hexstr="0x" + hex))
        hash_bytes32 = Web3.to_bytes(hexstr="0x" + submitted_hash_hex)

        def _call():
            return self._contract.functions.verifyCertificate(
                cert_uid, hash_bytes32
            ).call()

        result = self._execute_with_retry(_call)

        # result is tuple: (bool is_valid, uint8 status)
        is_valid = result[0]
        status_int = result[1]
        status_str = _CHAIN_STATUS_MAP.get(status_int, f"UNKNOWN({status_int})")

        return BlockchainVerificationResult(
            is_valid=is_valid,
            status=status_str,
            cert_uid=cert_uid,
        )

    def get_certificate_record(
        self,
        cert_uid: str,
    ) -> ChainCertificateRecord | None:
        """
        Retrieve the on-chain certificate record.

        Docs Section 18.1 (get_certificate_record):
        1. Call getCertificateRecord(cert_uid)
        2. If exists == False: return None
        3. Convert bytes32 hash to hex, timestamps to datetime

        Args:
            cert_uid: Certificate UID string.

        Returns:
            ChainCertificateRecord or None if not found on-chain.
        """

        def _call():
            return self._contract.functions.getCertificateRecord(
                cert_uid
            ).call()

        result = self._execute_with_retry(_call)

        # The contract returns a struct as a tuple.
        # Expected order from CertificateRegistry.sol:
        #   certificateHash (bytes32), issuingUniversity (address),
        #   issuedAt (uint256), revokedAt (uint256),
        #   status (uint8), exists (bool)
        exists = result[5]
        if not exists:
            return None

        # Convert bytes32 hash to hex string (strip 0x prefix)
        cert_hash_hex = Web3.to_hex(result[0])[2:]

        # Convert timestamps
        issued_at = datetime.fromtimestamp(result[2], tz=timezone.utc)
        revoked_at = (
            datetime.fromtimestamp(result[3], tz=timezone.utc)
            if result[3] > 0
            else None
        )

        # Checksum the university address
        issuing_university = Web3.to_checksum_address(result[1])

        status_str = _CHAIN_STATUS_MAP.get(result[4], f"UNKNOWN({result[4]})")

        return ChainCertificateRecord(
            certificate_hash=cert_hash_hex,
            issuing_university=issuing_university,
            issued_at=issued_at,
            revoked_at=revoked_at,
            status=status_str,
            exists=True,
        )

    def get_transaction_receipt(
        self,
        tx_hash: str,
    ) -> TransactionReceipt | None:
        """
        Retrieve a transaction receipt by hash.

        Docs Section 18.1 (get_transaction_receipt):
        1. Call web3.eth.get_transaction_receipt(tx_hash)
        2. If None: transaction not mined yet
        3. Extract status, block_number, block_hash, gas_used, price

        Args:
            tx_hash: Transaction hash string (0x + 64 hex chars).

        Returns:
            TransactionReceipt or None if not mined yet.
        """

        def _call():
            try:
                return self._web3.eth.get_transaction_receipt(tx_hash)
            except TransactionNotFound:
                return None

        receipt = self._execute_with_retry(_call)

        if receipt is None:
            return None

        return TransactionReceipt(
            tx_hash=tx_hash,
            status=receipt.get("status", 0),
            block_number=receipt.get("blockNumber", 0),
            block_hash=Web3.to_hex(receipt.get("blockHash", b"")),
            gas_used=receipt.get("gasUsed", 0),
            effective_gas_price=receipt.get("effectiveGasPrice", 0),
        )

    def is_authorized_issuer(
        self,
        wallet_address: str,
    ) -> bool:
        """
        Check if a wallet address is an authorized certificate issuer.

        Docs Section 18.1 (is_authorized_issuer):
        1. Checksum the address
        2. Call isAuthorizedIssuer(checksummed)

        Args:
            wallet_address: Ethereum wallet address.

        Returns:
            True if the address is authorized.

        Raises:
            BlockchainAddressError: If the address format is invalid.
        """
        if not WALLET_ADDRESS_REGEX.match(wallet_address):
            raise BlockchainAddressError(
                message=f"Invalid wallet address format: '{wallet_address}'"
            )

        try:
            checksummed = Web3.to_checksum_address(wallet_address)
        except Exception as exc:
            raise BlockchainAddressError(
                message=f"Cannot checksum address '{wallet_address}': {exc}"
            ) from exc

        def _call():
            return self._contract.functions.isAuthorizedIssuer(
                checksummed
            ).call()

        return bool(self._execute_with_retry(_call))

    def get_certificate_count(self) -> int:
        """
        Get the total number of certificates stored on-chain.

        Docs Section 18.1 (get_certificate_count):
        1. Call getCertificateCount()

        Returns:
            Integer count of certificates.
        """

        def _call():
            return self._contract.functions.getCertificateCount().call()

        return int(self._execute_with_retry(_call))

    # ─── Connection Status ───────────────────────────────────────────────

    def is_connected(self) -> bool:
        """Check if the Web3 provider is currently connected."""
        try:
            return self._web3.is_connected()
        except Exception:
            return False

    # ─── Retry + Circuit Breaker ─────────────────────────────────────────

    def _execute_with_retry(self, func, *args):
        """
        Execute a blockchain call with retry and circuit breaker.

        Docs Section 18.1 (Resilience Strategy):
        - Up to BLOCKCHAIN_MAX_RETRIES (3) attempts
        - Exponential backoff (1s, 2s, 4s)
        - Circuit breaker check before each attempt
        - On success: reset failure counter

        Args:
            func: Callable that performs the eth_call.

        Returns:
            The result of the callable.

        Raises:
            BlockchainConnectionError: If all retries exhausted or circuit open.
            BlockchainTimeoutError: If call times out.
            BlockchainContractError: If the contract reverts.
        """
        self._check_circuit_breaker()

        last_exception = None

        for attempt in range(1, BLOCKCHAIN_MAX_RETRIES + 1):
            try:
                result = func(*args)

                # Success: reset circuit breaker
                if self._consecutive_failures > 0:
                    logger.info(
                        "blockchain_circuit_breaker_reset",
                        extra={"previous_failures": self._consecutive_failures},
                    )
                self._consecutive_failures = 0
                return result

            except ContractLogicError as exc:
                # Contract revert: do NOT retry (it will revert again)
                self._record_failure()
                raise BlockchainContractError(
                    message=f"Contract reverted: {exc}"
                ) from exc

            except TimeExhausted as exc:
                self._record_failure()
                raise BlockchainTimeoutError(
                    message=f"Blockchain request timed out: {exc}"
                ) from exc

            except (ConnectionError, OSError, TimeoutError) as exc:
                last_exception = exc
                self._record_failure()

                if attempt < BLOCKCHAIN_MAX_RETRIES:
                    backoff = 2 ** (attempt - 1)  # 1s, 2s, 4s
                    logger.warning(
                        "blockchain_retry",
                        extra={
                            "attempt": attempt,
                            "max_retries": BLOCKCHAIN_MAX_RETRIES,
                            "backoff_seconds": backoff,
                            "error": str(exc),
                        },
                    )
                    time.sleep(backoff)
                    self._check_circuit_breaker()

            except Exception as exc:
                # Catch any other Web3 exceptions
                last_exception = exc
                self._record_failure()

                if attempt < BLOCKCHAIN_MAX_RETRIES:
                    backoff = 2 ** (attempt - 1)
                    logger.warning(
                        "blockchain_retry_unexpected",
                        extra={
                            "attempt": attempt,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                    )
                    time.sleep(backoff)
                    self._check_circuit_breaker()

        # All retries exhausted
        raise BlockchainConnectionError(
            message=f"All {BLOCKCHAIN_MAX_RETRIES} blockchain retries exhausted: "
            f"{last_exception}"
        ) from last_exception

    def _check_circuit_breaker(self) -> None:
        """
        Check circuit breaker state.

        Docs Section 18.1:
        After 5 consecutive failures, pause blockchain queries for 60 seconds.

        Raises:
            BlockchainConnectionError: If the circuit breaker is open.
        """
        if self._consecutive_failures < BLOCKCHAIN_CIRCUIT_BREAKER_THRESHOLD:
            return

        elapsed = time.monotonic() - self._last_failure_time

        if elapsed < BLOCKCHAIN_CIRCUIT_BREAKER_PAUSE_SECONDS:
            remaining = int(BLOCKCHAIN_CIRCUIT_BREAKER_PAUSE_SECONDS - elapsed)
            raise BlockchainConnectionError(
                message=f"Circuit breaker open: {self._consecutive_failures} "
                f"consecutive failures. Retry in {remaining}s."
            )

        # Half-open: allow one attempt through
        logger.info(
            "blockchain_circuit_breaker_half_open",
            extra={
                "consecutive_failures": self._consecutive_failures,
                "elapsed_seconds": int(elapsed),
            },
        )

    def _record_failure(self) -> None:
        """Record a failure for circuit breaker tracking."""
        self._consecutive_failures += 1
        self._last_failure_time = time.monotonic()
        logger.warning(
            "blockchain_failure_recorded",
            extra={
                "consecutive_failures": self._consecutive_failures,
                "threshold": BLOCKCHAIN_CIRCUIT_BREAKER_THRESHOLD,
            },
        )
