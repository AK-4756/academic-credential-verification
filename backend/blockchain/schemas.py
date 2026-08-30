# backend/blockchain/schemas.py
# Data classes for blockchain service return types.
#
# Architecture Reference: docs/backend.md Section 18.1
#
# These are NOT Pydantic schemas. They are plain dataclasses used
# internally by BlockchainService as method return types. They live
# in the blockchain package, not in schemas/.

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BlockchainVerificationResult:
    """Result of verify_certificate() eth_call.

    Docs Section 18.1 (verify_certificate):
      is_valid: True if hash matches the on-chain record
      status: Contract CertificateStatus ("ACTIVE" or "REVOKED")
      cert_uid: The certificate UID queried
    """

    is_valid: bool
    status: str
    cert_uid: str


@dataclass(frozen=True)
class ChainCertificateRecord:
    """On-chain certificate record from getCertificateRecord() eth_call.

    Docs Section 18.1 (get_certificate_record):
      certificate_hash: 64-char lowercase hex string
      issuing_university: Checksummed Ethereum address
      issued_at: Timestamp of on-chain issuance
      revoked_at: Timestamp of revocation (None if not revoked)
      status: Contract CertificateStatus ("ACTIVE" or "REVOKED")
      exists: True if the record exists on-chain
    """

    certificate_hash: str
    issuing_university: str
    issued_at: datetime
    revoked_at: datetime | None
    status: str
    exists: bool


@dataclass(frozen=True)
class TransactionReceipt:
    """Ethereum transaction receipt from get_transaction_receipt().

    Docs Section 18.1 (get_transaction_receipt):
      tx_hash: Transaction hash string
      status: 1=success, 0=failed
      block_number: Block in which the TX was mined
      block_hash: Hash of the block
      gas_used: Gas consumed by the transaction
      effective_gas_price: Gas price in wei
    """

    tx_hash: str
    status: int
    block_number: int
    block_hash: str
    gas_used: int
    effective_gas_price: int
