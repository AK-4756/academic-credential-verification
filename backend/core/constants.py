# backend/core/constants.py
# Application-wide constants — single source of truth for magic values.
#
# Architecture Reference: docs/backend.md Section 27 (core/constants.py)
# Values sourced from: docs/backend.md Sections 19, 21, 22; docs/database.md Section 4.1
#
# Rule: Every constant has a comment citing where the value originates.
# Rule: No magic numbers in service/repository code — import from here.

import enum
import re


# ─── File Upload Constants ────────────────────────────────────────────────────
# Source: backend.md Section 21 (File Storage Strategy)

MAX_FILE_SIZE_BYTES: int = 10_485_760  # 10 MB — configurable via env var
MAX_VERIFICATION_FILE_SIZE_BYTES: int = 52_428_800  # 50 MB — verifiers slightly higher limit
ALLOWED_MIME_TYPES: frozenset[str] = frozenset({"application/pdf"})
ALLOWED_FILE_EXTENSIONS: frozenset[str] = frozenset({".pdf"})

# ─── SHA-256 Hash Constants ──────────────────────────────────────────────────
# Source: backend.md Section 19 (SHA-256 Hashing Service)

HASH_HEX_LENGTH: int = 64  # SHA-256 produces 64 lowercase hex chars
HASH_BYTES_LENGTH: int = 32  # SHA-256 produces 32 bytes
HASH_FORMAT_REGEX: re.Pattern[str] = re.compile(r"^[0-9a-f]{64}$")

# ─── Blockchain Constants ────────────────────────────────────────────────────
# Source: backend.md Section 18 (Blockchain Integration Service)

WALLET_ADDRESS_REGEX: re.Pattern[str] = re.compile(r"^0x[0-9a-fA-F]{40}$")
TX_HASH_REGEX: re.Pattern[str] = re.compile(r"^0x[0-9a-fA-F]{64}$")
BLOCKCHAIN_RPC_TIMEOUT_SECONDS: int = 30
BLOCKCHAIN_MAX_RETRIES: int = 3
BLOCKCHAIN_CIRCUIT_BREAKER_THRESHOLD: int = 5
BLOCKCHAIN_CIRCUIT_BREAKER_PAUSE_SECONDS: int = 60

# ─── Certificate UID Constants ───────────────────────────────────────────────
# Source: database.md Section 4.6, backend.md Section 10
# Format: {SHORT_CODE}-{YEAR}-{SEQUENCE:05d}  e.g., "MIT-2025-00142"

CERTIFICATE_UID_REGEX: re.Pattern[str] = re.compile(
    r"^[A-Z0-9]+-[0-9]{4}-[0-9]{5}$"
)
CERTIFICATE_UID_SEQUENCE_DIGITS: int = 5

# ─── Authentication Constants ────────────────────────────────────────────────
# Source: backend.md Section 7 (Authentication Service Design)

PASSWORD_MIN_LENGTH: int = 8
MAX_FAILED_LOGIN_ATTEMPTS: int = 5
ACCOUNT_LOCKOUT_MINUTES: int = 10
BCRYPT_COST_FACTOR: int = 12
REFRESH_TOKEN_BYTES: int = 64  # 64 bytes → URL-safe base64 string
JWT_ALGORITHM: str = "RS256"

# ─── Rate Limiting Constants ────────────────────────────────────────────────
# Source: backend.md Section 6.2 (Middleware Stack)

RATE_LIMIT_LOGIN: str = "5/minute"
RATE_LIMIT_REGISTER: str = "10/minute"
RATE_LIMIT_REFRESH: str = "20/minute"
RATE_LIMIT_CERTIFICATE_UPLOAD: str = "10/minute"
RATE_LIMIT_REVOKE: str = "5/minute"
RATE_LIMIT_VERIFY_UPLOAD: str = "10/minute"
RATE_LIMIT_QR_SCAN: str = "30/minute"
RATE_LIMIT_GENERAL: str = "100/minute"

# ─── Pagination Constants ───────────────────────────────────────────────────

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# ─── Validation Constants ───────────────────────────────────────────────────
# Source: backend.md Section 15 (Revocation), Section 14 (Issuance)

REVOCATION_REASON_MIN_LENGTH: int = 10
REVOCATION_REASON_MAX_LENGTH: int = 500
DEGREE_TITLE_MAX_LENGTH: int = 300
FIELD_OF_STUDY_MAX_LENGTH: int = 300

# ─── QR Code Constants ──────────────────────────────────────────────────────
# Source: backend.md Section 17 (QR Verification Service)

QR_TOKEN_BYTES: int = 48  # 48 bytes → 64 chars URL-safe base64
QR_IMAGE_SIZE: int = 400  # 400x400 pixels
QR_ERROR_CORRECTION: str = "M"  # Level M — 15% error correction
QR_BORDER_MODULES: int = 4  # Standard minimum border


# ─── ENUM Types (Python mirrors of PostgreSQL ENUMs) ─────────────────────────
# Source: database.md Section 4.1 (ENUM Type Definitions)
# These MUST match the PostgreSQL ENUM values exactly.


class UserRole(str, enum.Enum):
    """Roles for RBAC — matches PostgreSQL user_role ENUM."""

    SUPER_ADMIN = "SUPER_ADMIN"
    UNIVERSITY_ADMIN = "UNIVERSITY_ADMIN"
    STUDENT = "STUDENT"
    EMPLOYER = "EMPLOYER"


class BlockchainStatus(str, enum.Enum):
    """Certificate lifecycle on blockchain — matches PostgreSQL blockchain_status ENUM."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"


class TransactionType(str, enum.Enum):
    """Blockchain transaction types — matches PostgreSQL transaction_type ENUM."""

    STORE_HASH = "STORE_HASH"
    REVOKE_HASH = "REVOKE_HASH"
    AUTHORIZE_ISSUER = "AUTHORIZE_ISSUER"


class TransactionStatus(str, enum.Enum):
    """Blockchain TX status — matches PostgreSQL transaction_status ENUM."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    REPLACED = "REPLACED"


class VerificationMethod(str, enum.Enum):
    """How a verification was initiated — matches PostgreSQL verification_method ENUM."""

    FILE_UPLOAD = "FILE_UPLOAD"
    QR_SCAN = "QR_SCAN"
    MANUAL_ID_LOOKUP = "MANUAL_ID_LOOKUP"


class VerificationResult(str, enum.Enum):
    """Outcome of a verification attempt — matches PostgreSQL verification_result ENUM."""

    AUTHENTIC = "AUTHENTIC"
    TAMPERED = "TAMPERED"
    REVOKED = "REVOKED"
    NOT_FOUND = "NOT_FOUND"
    PENDING_CHAIN = "PENDING_CHAIN"
    ERROR = "ERROR"
