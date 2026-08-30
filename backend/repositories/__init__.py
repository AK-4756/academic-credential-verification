# backend/repositories/__init__.py
# Repository layer package — public API.
#
# Architecture Reference: docs/backend.md Section 5.2 (Repository Catalog)
# Directory Reference: docs/backend.md Section 27.1
# Build Order: implementation-roadmap.md Sprint 4, Phase 4
#
# This package exposes all 9 domain repositories + the generic base.
# Services import directly from this package:
#
#   from repositories import UserRepository, CertificateRepository
#
# Or from specific submodules:
#
#   from repositories.user_repository import UserRepository

from repositories.base_repository import BaseRepository
from repositories.blockchain_transaction_repository import (
    BlockchainTransactionRepository,
)
from repositories.certificate_repository import CertificateRepository
from repositories.employer_repository import EmployerRepository
from repositories.qr_verification_repository import QRVerificationRepository
from repositories.refresh_token_repository import RefreshTokenRepository
from repositories.student_repository import StudentRepository
from repositories.university_repository import UniversityRepository
from repositories.user_repository import UserRepository
from repositories.verification_log_repository import VerificationLogRepository

__all__ = [
    # Base
    "BaseRepository",
    # Domain Repositories (9 total — matches docs/backend.md Section 5.2)
    "UserRepository",
    "UniversityRepository",
    "StudentRepository",
    "EmployerRepository",
    "CertificateRepository",
    "BlockchainTransactionRepository",
    "QRVerificationRepository",
    "VerificationLogRepository",
    "RefreshTokenRepository",
]
