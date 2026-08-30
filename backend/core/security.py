# backend/core/security.py
# JWT RS256 token operations, bcrypt password hashing, and token utilities.
#
# Architecture Reference: docs/backend.md Section 7 (Authentication Service Design)
# Build Order: implementation-roadmap.md Phase 6.1, Item 5
#
# RS256 Key Management:
#   - Private key: loaded from JWT_PRIVATE_KEY env var (PEM format)
#   - Public key: loaded from JWT_PUBLIC_KEY env var (PEM format)
#   - Algorithm: RS256 (RSA asymmetric) — pinned explicitly to prevent
#     algorithm confusion attacks (HS256 / none substitution).
#
# Password Hashing:
#   - Algorithm: bcrypt with cost factor 12
#   - Library: bcrypt (direct — passlib is incompatible with bcrypt>=4.1)
#
# Token Generation:
#   - Refresh tokens: 64-byte random via secrets.token_urlsafe
#   - Token hashing: SHA-256 (for storing refresh token hashes in DB)

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import bcrypt
from jose import JWTError, jwt

from core.config import settings
from core.constants import (
    BCRYPT_COST_FACTOR,
    JWT_ALGORITHM,
    REFRESH_TOKEN_BYTES,
)
from core.exceptions import TokenExpiredError, TokenInvalidError


# ─── Password Operations ─────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with cost factor 12.

    Uses the bcrypt library directly (passlib is incompatible with bcrypt>=4.1).
    The salt is generated automatically by bcrypt.gensalt().

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash string (includes salt and cost factor).
    """
    salt = bcrypt.gensalt(rounds=BCRYPT_COST_FACTOR)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    bcrypt.checkpw performs constant-time comparison internally,
    preventing timing-based side-channel attacks.

    Args:
        plain_password: The plaintext password to check.
        hashed_password: The stored bcrypt hash to compare against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # Invalid hash format — treat as non-matching
        return False


# ─── JWT Token Operations ────────────────────────────────────────────────────


def create_access_token(
    subject: str,
    role: str,
    university_id: str | None = None,
    email: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create an RS256-signed JWT access token.

    JWT Payload (from backend.md Section 7.1):
        sub: user ID (UUID string)
        role: RBAC role
        university_id: UUID string or null
        email: user email
        jti: unique JWT ID (for revocation tracking)
        iat: issued-at timestamp
        exp: expiration timestamp (15 minutes from now)

    Args:
        subject: The user's UUID as a string (becomes the 'sub' claim).
        role: The user's RBAC role (e.g., "UNIVERSITY_ADMIN").
        university_id: The user's university UUID, if applicable.
        email: The user's email address.
        extra_claims: Optional additional claims to include.

    Returns:
        The encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "university_id": university_id,
        "email": email,
        "jti": str(uuid4()),
        "iat": now,
        "exp": expire,
    }

    if extra_claims:
        payload.update(extra_claims)

    # Private key may contain literal \n sequences from env var — decode them
    private_key = settings.JWT_PRIVATE_KEY.replace("\\n", "\n")

    return jwt.encode(payload, private_key, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict[str, Any]:
    """
    Decode and verify an RS256-signed JWT access token.

    Security: Algorithm is explicitly pinned to ["RS256"] to prevent
    algorithm confusion attacks where an attacker could:
    - Switch to HS256 and use the public key as the HMAC secret
    - Switch to "none" and bypass verification entirely

    Args:
        token: The JWT string to verify.

    Returns:
        The decoded payload dictionary.

    Raises:
        TokenExpiredError: If the token has expired.
        TokenInvalidError: If the token is malformed or has an invalid signature.
    """
    # Public key may contain literal \n sequences from env var — decode them
    public_key = settings.JWT_PUBLIC_KEY.replace("\\n", "\n")

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[JWT_ALGORITHM],  # PINNED — never allow HS256 or none
        )
        return payload
    except JWTError as exc:
        error_msg = str(exc).lower()
        if "expired" in error_msg:
            raise TokenExpiredError() from exc
        raise TokenInvalidError() from exc


# ─── Refresh Token Operations ────────────────────────────────────────────────


def generate_refresh_token() -> str:
    """
    Generate a cryptographically secure random refresh token.

    Uses secrets.token_urlsafe for cryptographic randomness (not random.random).
    64 bytes → approximately 86 URL-safe characters.

    Returns:
        A URL-safe base64-encoded random string.
    """
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for secure storage.

    Refresh tokens are stored as SHA-256 hashes in the database.
    If the database is compromised, the raw tokens cannot be recovered.

    Args:
        token: The raw token string to hash.

    Returns:
        64-character lowercase hex string (SHA-256 digest).
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
