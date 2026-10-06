# backend/tests/unit/services/test_hash_service.py
# Sprint 4 D10: Unit tests for hash_service.
#
# Tests all 6 public functions in utils/hash_service.py.
# No mocking needed — all functions are pure (no I/O, no DB, no network).

import hashlib
import os
import sys

import pytest

# Ensure backend/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from utils.hash_service import (
    bytes32_to_hex,
    compare_hashes,
    generate_hash_from_bytes,
    generate_hash_from_file,
    hex_to_bytes32,
    validate_hash_format,
)

pytestmark = pytest.mark.unit


# ─── generate_hash_from_file / generate_hash_from_bytes ──────────────────────


class TestSHA256Generation:
    """Tests for generate_hash_from_file and generate_hash_from_bytes."""

    def test_sha256_determinism(self, sample_pdf_bytes: bytes):
        """Same input produces the same hash across multiple calls."""
        hashes = [generate_hash_from_file(sample_pdf_bytes) for _ in range(10)]
        assert len(set(hashes)) == 1, "Hash should be deterministic"

    def test_sha256_different_inputs_different_hashes(self):
        """Different inputs produce different hashes."""
        hash_a = generate_hash_from_file(b"content A")
        hash_b = generate_hash_from_file(b"content B")
        assert hash_a != hash_b

    def test_sha256_returns_64_hex_chars(self, sample_pdf_bytes: bytes):
        """Output is exactly 64 hex characters."""
        result = generate_hash_from_file(sample_pdf_bytes)
        assert len(result) == 64
        # Verify all characters are valid hex
        int(result, 16)  # Raises ValueError if not valid hex

    def test_sha256_lowercase_output(self, sample_pdf_bytes: bytes):
        """Output contains only lowercase hex characters."""
        result = generate_hash_from_file(sample_pdf_bytes)
        assert result == result.lower()
        assert all(c in "0123456789abcdef" for c in result)

    def test_generate_hash_from_bytes_matches_file(self, sample_pdf_bytes: bytes):
        """generate_hash_from_bytes produces the same result as generate_hash_from_file."""
        hash_file = generate_hash_from_file(sample_pdf_bytes)
        hash_bytes = generate_hash_from_bytes(sample_pdf_bytes)
        assert hash_file == hash_bytes

    def test_sha256_matches_stdlib(self, sample_pdf_bytes: bytes):
        """Output matches Python stdlib hashlib directly."""
        expected = hashlib.sha256(sample_pdf_bytes).hexdigest()
        actual = generate_hash_from_file(sample_pdf_bytes)
        assert actual == expected

    def test_empty_input_produces_known_hash(self):
        """Empty bytes produce the known SHA-256 of empty string."""
        # SHA-256 of empty string is well-known
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert generate_hash_from_file(b"") == expected


# ─── compare_hashes ──────────────────────────────────────────────────────────


class TestCompareHashes:
    """Tests for compare_hashes (constant-time comparison)."""

    def test_compare_hashes_match(self):
        """Identical hashes compare as equal."""
        h = generate_hash_from_file(b"test content")
        assert compare_hashes(h, h) is True

    def test_compare_hashes_no_match(self):
        """Different hashes compare as not equal."""
        h1 = generate_hash_from_file(b"content A")
        h2 = generate_hash_from_file(b"content B")
        assert compare_hashes(h1, h2) is False

    def test_compare_hashes_case_sensitive(self):
        """Comparison is case-sensitive (uppercase vs lowercase differ)."""
        h = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
        h_upper = h.upper()
        # hmac.compare_digest is case-sensitive
        assert compare_hashes(h, h_upper) is False


# ─── validate_hash_format ────────────────────────────────────────────────────


class TestValidateHashFormat:
    """Tests for validate_hash_format."""

    def test_valid_hash(self):
        """A proper 64-char lowercase hex string is valid."""
        h = generate_hash_from_file(b"test")
        assert validate_hash_format(h) is True

    def test_invalid_too_short(self):
        """A hash shorter than 64 chars is invalid."""
        assert validate_hash_format("abcdef") is False

    def test_invalid_too_long(self):
        """A hash longer than 64 chars is invalid."""
        assert validate_hash_format("a" * 65) is False

    def test_invalid_uppercase(self):
        """Uppercase hex characters should be rejected."""
        h = "A" * 64
        assert validate_hash_format(h) is False

    def test_invalid_non_hex(self):
        """Non-hex characters should be rejected."""
        h = "g" * 64
        assert validate_hash_format(h) is False

    def test_invalid_empty(self):
        """Empty string is invalid."""
        assert validate_hash_format("") is False


# ─── bytes32_to_hex / hex_to_bytes32 ─────────────────────────────────────────


class TestBytes32Conversion:
    """Tests for bytes32_to_hex and hex_to_bytes32 roundtrip."""

    def test_hex_bytes32_conversion_roundtrip(self):
        """bytes32_to_hex(hex_to_bytes32(h)) == h for valid hash."""
        h = generate_hash_from_file(b"roundtrip test content")
        assert bytes32_to_hex(hex_to_bytes32(h)) == h

    def test_hex_to_bytes32_length(self):
        """hex_to_bytes32 produces exactly 32 bytes."""
        h = "a" * 64
        result = hex_to_bytes32(h)
        assert len(result) == 32
        assert isinstance(result, bytes)

    def test_bytes32_to_hex_length(self):
        """bytes32_to_hex produces exactly 64 chars."""
        b = b"\x00" * 32
        result = bytes32_to_hex(b)
        assert len(result) == 64

    def test_known_conversion(self):
        """Verify a known hex/bytes conversion."""
        hex_str = "0000000000000000000000000000000000000000000000000000000000000001"
        b = hex_to_bytes32(hex_str)
        assert b[-1] == 1
        assert b[:-1] == b"\x00" * 31
        assert bytes32_to_hex(b) == hex_str
