# backend/core/exceptions.py
# Custom exception hierarchy — domain exceptions mapped to HTTP status codes.
#
# Architecture Reference: docs/backend.md Section 23 (Exception Handling Strategy)
#
# Design Decision (from docs): Services raise domain exceptions, NOT HTTPException.
# The global exception handler in main.py translates these to HTTP responses.
# This keeps services transport-agnostic (testable without HTTP context).
#
# Exception tree:
#   AppException (base)
#   ├── AuthenticationError (401)
#   ├── AuthorizationError (403)
#   ├── NotFoundError (404)
#   ├── ConflictError (409)
#   ├── ValidationError (422)
#   ├── ServiceError (400)
#   ├── FileError (400/500)
#   ├── BlockchainError (502/503)
#   └── InternalError (500)

from __future__ import annotations


class AppException(Exception):
    """
    Base exception for all application-specific errors.

    Every subclass maps to a specific HTTP status code and provides:
    - status_code: HTTP response status
    - error_code: Machine-readable error identifier (e.g., "CERTIFICATE_NOT_FOUND")
    - message: Human-readable, client-safe message (no internal details)
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        error_code: str | None = None,
        status_code: int | None = None,
        details: dict | list | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.error_code = error_code or self.__class__.error_code
        self.status_code = status_code or self.__class__.status_code
        self.details = details
        super().__init__(self.message)


# ─── Authentication Errors (401) ─────────────────────────────────────────────

class AuthenticationError(AppException):
    """Base authentication error — invalid credentials, expired tokens, etc."""

    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication failed"


class InvalidCredentialsError(AuthenticationError):
    """Wrong email or password. Message is intentionally generic to prevent user enumeration."""

    error_code = "INVALID_CREDENTIALS"
    message = "Invalid credentials"


class TokenExpiredError(AuthenticationError):
    """JWT access token or refresh token has expired."""

    error_code = "TOKEN_EXPIRED"
    message = "Token has expired"


class TokenInvalidError(AuthenticationError):
    """JWT token is malformed, has invalid signature, or uses wrong algorithm."""

    error_code = "TOKEN_INVALID"
    message = "Invalid token"


class AccountLockedError(AuthenticationError):
    """Account temporarily locked due to too many failed login attempts."""

    error_code = "ACCOUNT_LOCKED"
    message = "Account temporarily locked due to too many failed login attempts"


# ─── Authorization Errors (403) ──────────────────────────────────────────────

class AuthorizationError(AppException):
    """Base authorization error — user authenticated but lacks permission."""

    status_code = 403
    error_code = "AUTHORIZATION_ERROR"
    message = "You do not have permission to perform this action"


class InsufficientPermissionsError(AuthorizationError):
    """User's role does not match the required role for this endpoint."""

    error_code = "INSUFFICIENT_PERMISSIONS"
    message = "Insufficient permissions for this operation"


class OwnershipViolationError(AuthorizationError):
    """User attempting to access a resource they do not own."""

    error_code = "OWNERSHIP_VIOLATION"
    message = "You do not have access to this resource"


# ─── Not Found Errors (404) ──────────────────────────────────────────────────

class NotFoundError(AppException):
    """Base not-found error for any entity lookup that returns no result."""

    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class UserNotFoundError(NotFoundError):
    """User ID does not correspond to any existing user."""

    error_code = "USER_NOT_FOUND"
    message = "User not found"


class CertificateNotFoundError(NotFoundError):
    """Certificate ID or UID does not correspond to any existing certificate."""

    error_code = "CERTIFICATE_NOT_FOUND"
    message = "Certificate not found"


class UniversityNotFoundError(NotFoundError):
    """University ID does not correspond to any existing university."""

    error_code = "UNIVERSITY_NOT_FOUND"
    message = "University not found"


class QRTokenNotFoundError(NotFoundError):
    """QR verification token does not exist or has been deactivated."""

    error_code = "QR_TOKEN_NOT_FOUND"
    message = "QR verification token not found"


# ─── Conflict Errors (409) ───────────────────────────────────────────────────

class ConflictError(AppException):
    """Base conflict error — operation violates uniqueness or state constraints."""

    status_code = 409
    error_code = "CONFLICT"
    message = "Resource conflict"


class DuplicateEmailError(ConflictError):
    """Email address is already registered to another account."""

    error_code = "DUPLICATE_EMAIL"
    message = "An account with this email already exists"


class DuplicateCertificateError(ConflictError):
    """Certificate hash or UID already exists in the system."""

    error_code = "DUPLICATE_CERTIFICATE"
    message = "A certificate with this hash already exists"


class CertificateAlreadyRevokedError(ConflictError):
    """Attempting to revoke a certificate that is already revoked."""

    error_code = "CERTIFICATE_ALREADY_REVOKED"
    message = "Certificate has already been revoked"


class UniversityAlreadyVerifiedError(ConflictError):
    """Attempting to verify a university that is already verified."""

    error_code = "UNIVERSITY_ALREADY_VERIFIED"
    message = "University is already verified"


# ─── Service Errors (400) ────────────────────────────────────────────────────

class ServiceError(AppException):
    """Base business rule violation — request is syntactically valid but logically wrong."""

    status_code = 400
    error_code = "SERVICE_ERROR"
    message = "Business rule violation"


class UnconfirmedCertificateError(ServiceError):
    """Operation requires a CONFIRMED certificate but the certificate is in another state."""

    error_code = "UNCONFIRMED_CERTIFICATE"
    message = "Certificate is not yet confirmed on the blockchain"


class UnverifiedUniversityError(ServiceError):
    """Operation requires a verified university but the university is unverified."""

    error_code = "UNVERIFIED_UNIVERSITY"
    message = "University has not been verified by the platform administrator"


class MissingWalletAddressError(ServiceError):
    """University does not have a wallet address configured."""

    error_code = "MISSING_WALLET_ADDRESS"
    message = "University does not have a wallet address configured"


# ─── File Errors (400/500) ───────────────────────────────────────────────────

class FileError(AppException):
    """Base file operation error."""

    status_code = 400
    error_code = "FILE_ERROR"
    message = "File operation failed"


class InvalidFileTypeError(FileError):
    """Uploaded file MIME type is not in the allowed list."""

    error_code = "INVALID_FILE_TYPE"
    message = "Invalid file type. Only PDF files are accepted"


class FileTooLargeError(FileError):
    """Uploaded file exceeds the maximum allowed size."""

    error_code = "FILE_TOO_LARGE"
    message = "File exceeds maximum allowed size"


class FileNotFoundOnDiskError(FileError):
    """File path in database does not correspond to an existing file on disk."""

    status_code = 500
    error_code = "FILE_NOT_FOUND_ON_DISK"
    message = "Certificate file could not be located"


# ─── Blockchain Errors (502/503) ─────────────────────────────────────────────

class BlockchainError(AppException):
    """Base blockchain infrastructure error."""

    status_code = 502
    error_code = "BLOCKCHAIN_ERROR"
    message = "Blockchain service error"


class BlockchainConnectionError(BlockchainError):
    """Cannot reach the Ethereum RPC endpoint."""

    status_code = 503
    error_code = "BLOCKCHAIN_CONNECTION_ERROR"
    message = "Cannot connect to blockchain network"


class BlockchainTimeoutError(BlockchainError):
    """Blockchain RPC call exceeded the configured timeout."""

    status_code = 504
    error_code = "BLOCKCHAIN_TIMEOUT"
    message = "Blockchain request timed out"



class BlockchainContractError(BlockchainError):
    """Smart contract reverted or returned unexpected data."""

    error_code = "BLOCKCHAIN_CONTRACT_ERROR"
    message = "Smart contract interaction failed"


class BlockchainHashFormatError(BlockchainError):
    """Invalid hash format for blockchain conversion (not 64-char hex)."""

    status_code = 400
    error_code = "BLOCKCHAIN_HASH_FORMAT_ERROR"
    message = "Invalid hash format for blockchain operation"


class BlockchainAddressError(BlockchainError):
    """Invalid Ethereum address format."""

    status_code = 400
    error_code = "BLOCKCHAIN_ADDRESS_ERROR"
    message = "Invalid Ethereum address"


# ─── Internal Errors (500) ───────────────────────────────────────────────────

class InternalError(AppException):
    """Unexpected internal error — catch-all for unclassified failures."""

    status_code = 500
    error_code = "INTERNAL_ERROR"
    message = "An unexpected error occurred"

