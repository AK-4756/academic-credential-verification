# backend/blockchain/web3_client.py
# Web3.py connection setup and contract instance factory.
#
# Architecture Reference: docs/backend.md Section 18.1 (Connection Configuration)
# Directory Reference: docs/backend.md Section 27.1 (blockchain/web3_client.py)
# Build Order: implementation-roadmap.md Phase 6.5
#
# Responsibilities:
#   - Create Web3 HTTPProvider with configurable timeout
#   - Load contract ABI from Hardhat artifact JSON
#   - Create contract instance bound to deployed address
#
# ABI Location: backend/blockchain/abi/CertificateRegistry.json
# This file is a Hardhat compilation artifact containing an "abi" key.

from __future__ import annotations

import json
import logging
from pathlib import Path

from web3 import Web3
from web3.contract import Contract
from web3.providers import HTTPProvider

from core.constants import BLOCKCHAIN_RPC_TIMEOUT_SECONDS
from core.exceptions import BlockchainConnectionError, BlockchainContractError

logger = logging.getLogger(__name__)

# Default ABI path relative to this file
_DEFAULT_ABI_PATH = Path(__file__).parent / "abi" / "CertificateRegistry.json"


def create_web3_instance(
    provider_url: str,
    timeout: int = BLOCKCHAIN_RPC_TIMEOUT_SECONDS,
) -> Web3:
    """
    Create a Web3 instance with HTTPProvider.

    Args:
        provider_url: Ethereum JSON-RPC endpoint URL.
        timeout: Request timeout in seconds (default: 30).

    Returns:
        Configured Web3 instance.

    Raises:
        BlockchainConnectionError: If the provider URL is invalid.
    """
    try:
        provider = HTTPProvider(
            provider_url,
            request_kwargs={"timeout": timeout},
        )
        w3 = Web3(provider)
        logger.info(
            "web3_instance_created",
            extra={"provider_url": provider_url, "timeout": timeout},
        )
        return w3
    except Exception as exc:
        raise BlockchainConnectionError(
            message=f"Failed to create Web3 instance: {exc}"
        ) from exc


def load_contract_abi(abi_path: str | Path | None = None) -> list:
    """
    Load the contract ABI from a Hardhat artifact JSON file.

    The Hardhat artifact is a JSON object with top-level keys including
    "abi". This function extracts just the ABI array.

    Args:
        abi_path: Path to the ABI JSON file. Defaults to
                  blockchain/abi/CertificateRegistry.json.

    Returns:
        The contract ABI as a list of dicts.

    Raises:
        BlockchainContractError: If the ABI file is missing or malformed.
    """
    path = Path(abi_path) if abi_path else _DEFAULT_ABI_PATH

    if not path.exists():
        raise BlockchainContractError(
            message=f"Contract ABI file not found: {path}"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            artifact = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise BlockchainContractError(
            message=f"Failed to read ABI file: {exc}"
        ) from exc

    # Hardhat artifacts have the ABI under the "abi" key.
    # If the file IS already a raw ABI array, use it directly.
    if isinstance(artifact, list):
        abi = artifact
    elif isinstance(artifact, dict) and "abi" in artifact:
        abi = artifact["abi"]
    else:
        raise BlockchainContractError(
            message="ABI file does not contain an 'abi' key or ABI array"
        )

    if not abi:
        raise BlockchainContractError(message="ABI is empty")

    logger.info(
        "contract_abi_loaded",
        extra={"path": str(path), "entry_count": len(abi)},
    )
    return abi


def get_contract(
    web3: Web3,
    contract_address: str,
    abi: list,
) -> Contract:
    """
    Create a contract instance bound to a deployed address.

    Args:
        web3: Configured Web3 instance.
        contract_address: Deployed contract address (checksummed or raw).
        abi: Contract ABI as a list.

    Returns:
        Web3 Contract instance.

    Raises:
        BlockchainContractError: If the address is invalid.
    """
    try:
        checksummed = Web3.to_checksum_address(contract_address)
    except Exception as exc:
        raise BlockchainContractError(
            message=f"Invalid contract address '{contract_address}': {exc}"
        ) from exc

    contract = web3.eth.contract(address=checksummed, abi=abi)
    logger.info(
        "contract_instance_created",
        extra={"address": checksummed},
    )
    return contract
