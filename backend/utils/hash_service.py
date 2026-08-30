# backend/utils/hash_service.py
# SHA-256 hashing service — deterministic fingerprinting of certificate PDF files.
#
# Architecture Reference: docs/backend.md Section 19.1 (SHA-256 Hashing Service)
# Directory Reference: docs/backend.md Section 27.1 (utils/hash_service.py)
# Build Order: implementation-roadmap.md Sprint 4, Phase 6 (infrastructure services)
#
# Library: hashlib (Python standard library) — no external dependencies.
#
# Hash Determinism Contract (from docs):
#   Same file bytes ALWAYS produce the same hash.
#   File must NOT be transformed before hashing.
#   Hash must be computed before the file is saved.

from __future__ import annotations

import hashlib
import hmac

from core.constants import HASH_FORMAT_REGEX


def generate_hash_from_file(file_bytes: bytes) -> str:
    """
    Compute SHA-256 hash of raw certificate PDF bytes.

    Docs Section 19.1:
    - Input: Raw bytes of the certificate PDF file
    - Output: 64-character lowercase hex string
    - Reads complete file into memory (not chunked)
    - hashlib.sha256().hexdigest() returns lowercase by default

    Args:
        file_bytes: Raw bytes of the file.

    Returns:
        64-character lowercase hex string (SHA-256 digest).
    """
    return hashlib.sha256(file_bytes).hexdigest()


def generate_hash_from_bytes(data: bytes) -> str:
    """
    Compute SHA-256 hash of arbitrary bytes.

    Docs Section 19.1:
    Same as generate_hash_from_file but accepts any bytes.
    Used for hashing tokens, metadata (internal operations).

    Args:
        data: Raw bytes to hash.

    Returns:
        64-character lowercase hex string.
    """
    return hashlib.sha256(data).hexdigest()


def compare_hashes(hash_a: str, hash_b: str) -> bool:
    """
    Constant-time hash comparison to prevent timing attacks.

    Docs Section 19.1:
    Uses hmac.compare_digest for constant-time comparison.
    A byte-by-byte comparison (==) returns early on first mismatch,
    leaking information. Constant-time comparison always takes
    the same time regardless of where the mismatch occurs.

    Args:
        hash_a: First 64-char lowercase hex string.
        hash_b: Second 64-char lowercase hex string.

    Returns:
        True if the hashes are equal.
    """
    return hmac.compare_digest(hash_a, hash_b)


def validate_hash_format(hash_string: str) -> bool:
    """
    Validate that a string is a valid SHA-256 hex digest.

    Docs Section 19.1:
    Regex: ^[0-9a-f]{64}$

    Args:
        hash_string: The string to validate.

    Returns:
        True if the string is exactly 64 lowercase hex characters.
    """
    return bool(HASH_FORMAT_REGEX.match(hash_string))


def bytes32_to_hex(bytes32_value: bytes) -> str:
    """
    Convert bytes32 from blockchain ABI decoding to 64-char hex string.

    Docs Section 19.1:
    Used by BlockchainService when reading hash from contract.

    Args:
        bytes32_value: 32 bytes from blockchain ABI.

    Returns:
        64-character lowercase hex string (no 0x prefix).
    """
    return bytes32_value.hex()


def hex_to_bytes32(hex_string: str) -> bytes:
    """
    Convert 64-char hex string to 32 bytes.

    Docs Section 19.1:
    Used when constructing blockchain calls (Web3.py accepts bytes).

    Args:
        hex_string: 64-character hex string (no 0x prefix).

    Returns:
        32 bytes.
    """
    return bytes.fromhex(hex_string)
