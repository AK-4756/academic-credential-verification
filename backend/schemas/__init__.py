# backend/schemas/__init__.py
# Pydantic schema package — re-exports all public schema classes.
#
# Architecture Reference: docs/backend.md Section 27.1 (schemas/)
# Build Order: implementation-roadmap.md Sprint 4, Phase 5

# ─── Common Schemas ──────────────────────────────────────────────────────────
from schemas.common_schemas import (
    ErrorDetail,
    ErrorResponse,
    MessageResponse,
    PaginatedData,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
    SuccessResponse,
)

# ─── Auth Schemas ────────────────────────────────────────────────────────────
from schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TokenRefreshResponse,
)

# ─── User Schemas ────────────────────────────────────────────────────────────
from schemas.user_schemas import (
    ChangePasswordRequest,
    UserProfileResponse,
    UserSummary,
)

# ─── University Schemas ──────────────────────────────────────────────────────
from schemas.university_schemas import (
    UniversityCertificateStats,
    UniversityDashboard,
    UniversityDetail,
    UniversitySummary,
    WalletUpdateRequest,
)

# ─── Student Schemas ─────────────────────────────────────────────────────────
from schemas.student_schemas import (
    CredentialDetail,
    CredentialSummary,
    CredentialSummaryStats,
    ShareLinkResponse,
    StudentDashboard,
    StudentProfile,
)

# ─── Employer Schemas ────────────────────────────────────────────────────────
from schemas.employer_schemas import (
    EmployerDashboard,
    EmployerProfile,
    EmployerProfileUpdate,
    VerificationSummaryStats,
)

# ─── Certificate Schemas ─────────────────────────────────────────────────────
from schemas.certificate_schemas import (
    BlockchainProof,
    CertificateConfirmedResponse,
    CertificateDetail,
    CertificateDraftResponse,
    CertificateIssueRequest,
    CertificateRevokedResponse,
    CertificateSummary,
    ConfirmHashRequest,
    ConfirmRevocationRequest,
    QRCodeInfo,
    RevokeRequest,
    RevocationInitiatedResponse,
)

# ─── Verification Schemas ────────────────────────────────────────────────────
from schemas.verification_schemas import (
    BlockchainVerificationProof,
    PublicVerificationResult,
    TamperEvidence,
    VerificationCertificateInfo,
    VerificationResponse,
)

# ─── QR Schemas ──────────────────────────────────────────────────────────────
from schemas.qr_schemas import QRCodeResponse

# ─── Log Schemas ─────────────────────────────────────────────────────────────
from schemas.log_schemas import (
    VerificationDetail,
    VerificationLogDetail,
    VerificationLogSummary,
    VerificationSummary,
)

__all__ = [
    # Common
    "PaginationParams",
    "PaginationMeta",
    "PaginatedData",
    "SuccessResponse",
    "PaginatedResponse",
    "ErrorDetail",
    "ErrorResponse",
    "MessageResponse",
    # Auth
    "RegisterRequest",
    "RegisterResponse",
    "LoginRequest",
    "LoginResponse",
    "TokenRefreshResponse",
    # User
    "UserSummary",
    "UserProfileResponse",
    "ChangePasswordRequest",
    # University
    "UniversitySummary",
    "UniversityDetail",
    "UniversityCertificateStats",
    "UniversityDashboard",
    "WalletUpdateRequest",
    # Student
    "StudentProfile",
    "CredentialSummary",
    "CredentialDetail",
    "CredentialSummaryStats",
    "StudentDashboard",
    "ShareLinkResponse",
    # Employer
    "EmployerProfile",
    "EmployerProfileUpdate",
    "VerificationSummaryStats",
    "EmployerDashboard",
    # Certificate
    "CertificateIssueRequest",
    "CertificateDraftResponse",
    "ConfirmHashRequest",
    "BlockchainProof",
    "QRCodeInfo",
    "CertificateConfirmedResponse",
    "CertificateSummary",
    "CertificateDetail",
    "RevokeRequest",
    "RevocationInitiatedResponse",
    "ConfirmRevocationRequest",
    "CertificateRevokedResponse",
    # Verification
    "VerificationCertificateInfo",
    "BlockchainVerificationProof",
    "TamperEvidence",
    "VerificationResponse",
    "PublicVerificationResult",
    # QR
    "QRCodeResponse",
    # Logs
    "VerificationLogSummary",
    "VerificationLogDetail",
    "VerificationSummary",
    "VerificationDetail",
]
