# backend/tests/unit/services/test_qr_verification_service.py
# Unit tests for qr_verification_service.py
#
# Functions tested:
#   generate_qr_for_certificate(cert_id, generated_by_user_id, db) -> dict
#   get_qr_by_token(token, db)

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from core.constants import BlockchainStatus
from core.exceptions import (
    CertificateNotFoundError,
    QRTokenNotFoundError,
    UnconfirmedCertificateError,
)

pytestmark = pytest.mark.unit

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    """Mock AsyncSession. begin() returns an async context manager."""
    session = MagicMock()
    ctx = AsyncMock()
    session.begin.return_value = ctx
    return session


@pytest.fixture
def confirmed_certificate():
    """Mock certificate with CONFIRMED blockchain_status."""
    cert = MagicMock()
    cert.id = uuid4()
    cert.certificate_uid = "TEST-2025-00001"
    cert.blockchain_status = BlockchainStatus.CONFIRMED
    cert.is_active = True
    return cert


@pytest.fixture
def pending_certificate():
    """Mock certificate with PENDING blockchain_status."""
    cert = MagicMock()
    cert.id = uuid4()
    cert.blockchain_status = BlockchainStatus.PENDING
    cert.is_active = True
    return cert


# ═══════════════════════════════════════════════════════════════════════════════
#  generate_qr_for_certificate
# ═══════════════════════════════════════════════════════════════════════════════


class TestGenerateQRForCertificate:
    """Tests for generate_qr_for_certificate."""

    @patch("services.qr_verification_service.QRVerificationRepository")
    @patch("services.qr_verification_service.CertificateRepository")
    async def test_generate_qr_success(
        self, mock_cert_repo, mock_qr_repo, db, confirmed_certificate
    ):
        """Successfully generates QR token for CONFIRMED certificate."""
        from services.qr_verification_service import generate_qr_for_certificate

        mock_cert_repo.get_by_id = AsyncMock(return_value=confirmed_certificate)
        mock_qr_repo.get_active_by_certificate = AsyncMock(return_value=None)

        qr_record = MagicMock()
        qr_record.id = uuid4()
        mock_qr_repo.create = AsyncMock(return_value=qr_record)

        result = await generate_qr_for_certificate(
            confirmed_certificate.id, uuid4(), db
        )

        assert "token" in result
        assert "verification_url" in result
        assert "qr_id" in result
        assert result["qr_id"] == qr_record.id
        mock_qr_repo.create.assert_awaited_once()

    @patch("services.qr_verification_service.CertificateRepository")
    async def test_generate_qr_certificate_not_found(self, mock_cert_repo, db):
        """Raises CertificateNotFoundError if certificate doesn't exist."""
        from services.qr_verification_service import generate_qr_for_certificate

        mock_cert_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CertificateNotFoundError):
            await generate_qr_for_certificate(uuid4(), uuid4(), db)

    @patch("services.qr_verification_service.CertificateRepository")
    async def test_generate_qr_certificate_not_confirmed(
        self, mock_cert_repo, db, pending_certificate
    ):
        """Raises UnconfirmedCertificateError if not CONFIRMED."""
        from services.qr_verification_service import generate_qr_for_certificate

        mock_cert_repo.get_by_id = AsyncMock(return_value=pending_certificate)

        with pytest.raises(UnconfirmedCertificateError):
            await generate_qr_for_certificate(
                pending_certificate.id, uuid4(), db
            )

    @patch("services.qr_verification_service.QRVerificationRepository")
    @patch("services.qr_verification_service.CertificateRepository")
    async def test_generate_qr_deactivates_existing(
        self, mock_cert_repo, mock_qr_repo, db, confirmed_certificate
    ):
        """Deactivates existing active QR before creating new one."""
        from services.qr_verification_service import generate_qr_for_certificate

        mock_cert_repo.get_by_id = AsyncMock(return_value=confirmed_certificate)

        existing_qr = MagicMock()
        existing_qr.id = uuid4()
        mock_qr_repo.get_active_by_certificate = AsyncMock(return_value=existing_qr)
        mock_qr_repo.deactivate = AsyncMock()
        mock_qr_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))

        await generate_qr_for_certificate(
            confirmed_certificate.id, uuid4(), db
        )

        mock_qr_repo.deactivate.assert_awaited_once_with(
            db, existing_qr.id, reason="Replaced by new QR code"
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  get_qr_by_token
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetQRByToken:
    """Tests for get_qr_by_token."""

    @patch("services.qr_verification_service.QRVerificationRepository")
    async def test_get_qr_by_token_success(self, mock_qr_repo, db):
        """Returns QR record when token is found."""
        from services.qr_verification_service import get_qr_by_token

        qr_record = MagicMock()
        qr_record.token = "test_token_123"
        mock_qr_repo.get_by_token = AsyncMock(return_value=qr_record)

        result = await get_qr_by_token("test_token_123", db)
        assert result == qr_record

    @patch("services.qr_verification_service.QRVerificationRepository")
    async def test_get_qr_by_token_not_found(self, mock_qr_repo, db):
        """Raises QRTokenNotFoundError when token doesn't exist."""
        from services.qr_verification_service import get_qr_by_token

        mock_qr_repo.get_by_token = AsyncMock(return_value=None)

        with pytest.raises(QRTokenNotFoundError):
            await get_qr_by_token("nonexistent_token", db)
