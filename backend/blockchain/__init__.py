# backend/blockchain/__init__.py
# Blockchain integration package — Web3.py client for Ethereum RPC.
#
# Architecture Reference: docs/backend.md Section 18.1 (Blockchain Integration Service)
# Directory Reference: docs/backend.md Section 27.1 (blockchain/)
# Build Order: implementation-roadmap.md Phase 6.5 (Infrastructure Services)
#
# Architecture Principle (from docs):
#   The backend blockchain service is READ-ONLY for certificate operations.
#   It READS from the blockchain (eth_call - free, no gas).
#   It does NOT write to the blockchain (MetaMask does that).
#
# Package contents:
#   web3_client.py       - Web3 connection setup + ABI loading
#   blockchain_service.py - BlockchainService class (5 public methods)
#   schemas.py           - Data classes for return types
#   abi/                 - Contract ABI JSON (copied from Hardhat artifacts)

from blockchain.blockchain_service import BlockchainService
from blockchain.schemas import (
    BlockchainVerificationResult,
    ChainCertificateRecord,
    TransactionReceipt,
)

__all__ = [
    "BlockchainService",
    "BlockchainVerificationResult",
    "ChainCertificateRecord",
    "TransactionReceipt",
]
