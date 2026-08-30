# backend/dependencies/services.py
# Service dependency factories for FastAPI dependency injection.
#
# Architecture Reference: docs/backend.md Section 6 (Dependency Injection)
# Build Order: implementation-roadmap.md Sprint 4, Phase 3 (stubs) + Phase 8 (blockchain)
#
# Singleton Pattern (from docs Section 18.1):
#   BlockchainService is instantiated once at application startup
#   and reused across all requests via FastAPI dependency injection.
#   Web3 connection is thread-safe and connection-pooled.
#
# Dependencies:
#   get_blockchain_service() -> BlockchainService
#       Singleton Web3.py wrapper for Ethereum RPC interactions.
#       Used by: certificate issuance, revocation, verification routes.
#       Documented in: backend.md Section 18 (Blockchain Integration Service)

from __future__ import annotations

import logging
from pathlib import Path

from core.config import settings
from core.exceptions import BlockchainConnectionError

logger = logging.getLogger(__name__)

# ─── BlockchainService Singleton ─────────────────────────────────────────────

_blockchain_service = None
_blockchain_init_error: str | None = None


def get_blockchain_service():
    """
    Get the singleton BlockchainService instance.

    The service is lazily initialized on first call. If the blockchain
    RPC endpoint is unavailable or the contract address is not configured,
    initialization will fail gracefully and subsequent calls will raise
    BlockchainConnectionError.

    Returns:
        BlockchainService: The singleton instance.

    Raises:
        BlockchainConnectionError: If the service could not be initialized.
    """
    global _blockchain_service, _blockchain_init_error

    if _blockchain_service is not None:
        return _blockchain_service

    if _blockchain_init_error is not None:
        raise BlockchainConnectionError(
            message=f"BlockchainService unavailable: {_blockchain_init_error}"
        )

    # Guard: contract address must be configured
    if not settings.CONTRACT_ADDRESS:
        _blockchain_init_error = (
            "CONTRACT_ADDRESS not configured in environment"
        )
        logger.warning(
            "blockchain_service_not_configured",
            extra={"reason": _blockchain_init_error},
        )
        raise BlockchainConnectionError(
            message=f"BlockchainService unavailable: {_blockchain_init_error}"
        )

    try:
        from blockchain.blockchain_service import BlockchainService

        abi_path = str(
            Path(__file__).parent.parent / "blockchain" / "abi" / "CertificateRegistry.json"
        )

        _blockchain_service = BlockchainService(
            provider_url=settings.BLOCKCHAIN_RPC_URL,
            contract_address=settings.CONTRACT_ADDRESS,
            chain_id=settings.NETWORK_CHAIN_ID,
            abi_path=abi_path,
        )

        logger.info(
            "blockchain_service_initialized",
            extra={
                "provider_url": settings.BLOCKCHAIN_RPC_URL,
                "contract_address": settings.CONTRACT_ADDRESS,
                "chain_id": settings.NETWORK_CHAIN_ID,
            },
        )

        return _blockchain_service

    except Exception as exc:
        _blockchain_init_error = str(exc)
        logger.error(
            "blockchain_service_init_failed",
            extra={"error": _blockchain_init_error},
        )
        raise BlockchainConnectionError(
            message=f"BlockchainService initialization failed: {exc}"
        ) from exc
