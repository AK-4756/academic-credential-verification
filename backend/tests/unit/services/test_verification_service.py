import sys

backend_dir = r"d:\AI(NON-IMP)\Decentralized Blockchain\academic-credential-verification\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from core.constants import BlockchainStatus, VerificationResult
from services.verification_service import verify_by_file_upload, verify_by_qr_token


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock()
    ctx.__aexit__ = AsyncMock(return_value=None)
    db.begin.return_value = ctx
    return db

@pytest.fixture
def current_user():
    user = MagicMock()
    user.id = uuid4()
    return user


@pytest.mark.unit
@patch("services.verification_service.CertificateRepository")
@patch("services.verification_service.VerificationLogRepository")
@patch("services.verification_service.generate_hash_from_file")
@patch("services.verification_service.compare_hashes")
@patch("services.verification_service._get_block_number", new_callable=AsyncMock)
@patch("services.verification_service._get_store_tx_hash", new_callable=AsyncMock)
async def test_verify_authentic_result(mock_tx_hash, mock_block, mock_compare, mock_hash, mock_log_repo, mock_cert_repo, mock_db, current_user):
    mock_hash.return_value = "fakehash"
    mock_cert = MagicMock()
    mock_cert.id = uuid4()
    mock_cert.blockchain_status = BlockchainStatus.CONFIRMED
    mock_cert.sha256_hash = "fakehash"
    mock_cert.certificate_uid = "uid-1"
    mock_cert_repo.get_by_uid = AsyncMock(return_value=mock_cert)
    mock_cert_repo.get_by_hash = AsyncMock(return_value=mock_cert)

    mock_bc_service = MagicMock()
    mock_chain_result = MagicMock()
    mock_chain_result.status = "ACTIVE"
    mock_chain_result.is_valid = True
    mock_bc_service.verify_certificate.return_value = mock_chain_result

    mock_chain_record = MagicMock()
    mock_bc_service.get_certificate_record.return_value = mock_chain_record

    mock_block.return_value = 100
    mock_tx_hash.return_value = "0x" + "ab" * 32
    mock_log_repo.create = AsyncMock()

    result = await verify_by_file_upload(b"fake", "uid-1", current_user, "1.2.3.4", "agent", mock_db, mock_bc_service)
    assert result["result"] == VerificationResult.AUTHENTIC

@pytest.mark.unit
@patch("services.verification_service.CertificateRepository")
@patch("services.verification_service.VerificationLogRepository")
@patch("services.verification_service.generate_hash_from_file")
@patch("services.verification_service._get_block_number", new_callable=AsyncMock)
@patch("services.verification_service._get_store_tx_hash", new_callable=AsyncMock)
async def test_verify_tampered_result(mock_tx_hash, mock_block, mock_hash, mock_log_repo, mock_cert_repo, mock_db, current_user):
    mock_hash.return_value = "fakehash"
    mock_cert = MagicMock()
    mock_cert.id = uuid4()
    mock_cert.blockchain_status = BlockchainStatus.CONFIRMED
    mock_cert.sha256_hash = "fakehash"
    mock_cert_repo.get_by_uid = AsyncMock(return_value=mock_cert)

    mock_bc_service = MagicMock()
    mock_chain_result = MagicMock()
    mock_chain_result.status = "ACTIVE"
    mock_chain_result.is_valid = False
    mock_bc_service.verify_certificate.return_value = mock_chain_result
    mock_tx_hash.return_value = ""
    mock_log_repo.create = AsyncMock()

    result = await verify_by_file_upload(b"fake", "uid-1", current_user, "1.2.3.4", "agent", mock_db, mock_bc_service)
    assert result["result"] == VerificationResult.TAMPERED

@pytest.mark.unit
@patch("services.verification_service.CertificateRepository")
@patch("services.verification_service.VerificationLogRepository")
@patch("services.verification_service.generate_hash_from_file")
@patch("services.verification_service._get_block_number", new_callable=AsyncMock)
@patch("services.verification_service._get_store_tx_hash", new_callable=AsyncMock)
async def test_verify_revoked_result(mock_tx_hash, mock_block, mock_hash, mock_log_repo, mock_cert_repo, mock_db, current_user):
    mock_hash.return_value = "fakehash"
    mock_cert = MagicMock()
    mock_cert.id = uuid4()
    mock_cert.blockchain_status = BlockchainStatus.CONFIRMED
    mock_cert.sha256_hash = "fakehash"
    mock_cert_repo.get_by_uid = AsyncMock(return_value=mock_cert)

    mock_bc_service = MagicMock()
    mock_chain_result = MagicMock()
    mock_chain_result.status = "REVOKED"
    mock_bc_service.verify_certificate.return_value = mock_chain_result
    mock_tx_hash.return_value = ""
    mock_log_repo.create = AsyncMock()

    result = await verify_by_file_upload(b"fake", "uid-1", current_user, "1.2.3.4", "agent", mock_db, mock_bc_service)
    assert result["result"] == VerificationResult.REVOKED


@pytest.mark.unit
@patch("services.verification_service.CertificateRepository")
@patch("services.verification_service.VerificationLogRepository")
@patch("services.verification_service.generate_hash_from_file")
async def test_verify_not_found_result(mock_hash, mock_log_repo, mock_cert_repo, mock_db, current_user):
    mock_hash.return_value = "fakehash"
    mock_cert_repo.get_by_uid = AsyncMock(return_value=None)
    mock_cert_repo.get_by_hash = AsyncMock(return_value=None)
    mock_log_repo.create = AsyncMock()

    result = await verify_by_file_upload(b"fake", "uid-1", current_user, "1.2.3.4", "agent", mock_db, None)
    assert result["result"] == VerificationResult.NOT_FOUND

@pytest.mark.unit
@patch("services.verification_service.CertificateRepository")
@patch("services.verification_service.VerificationLogRepository")
@patch("services.verification_service.generate_hash_from_file")
@patch("services.verification_service.compare_hashes")
async def test_verify_pending_chain_result(mock_compare, mock_hash, mock_log_repo, mock_cert_repo, mock_db, current_user):
    mock_hash.return_value = "fakehash"
    mock_cert = MagicMock()
    mock_cert.blockchain_status = BlockchainStatus.PENDING
    mock_cert_repo.get_by_uid = AsyncMock(return_value=mock_cert)
    mock_log_repo.create = AsyncMock()

    result = await verify_by_file_upload(b"fake", "uid-1", current_user, "1.2.3.4", "agent", mock_db, None)
    assert result["result"] == VerificationResult.PENDING_CHAIN

@pytest.mark.unit
@patch("services.verification_service.QRVerificationRepository")
@patch("services.verification_service.CertificateRepository")
@patch("services.verification_service.VerificationLogRepository")
@patch("services.verification_service._get_block_number", new_callable=AsyncMock)
@patch("services.verification_service._get_store_tx_hash", new_callable=AsyncMock)
async def test_verify_qr_token_success(mock_tx_hash, mock_block, mock_log_repo, mock_cert_repo, mock_qr_repo, mock_db):
    mock_qr = MagicMock()
    mock_qr.is_active = True
    mock_qr.expires_at = None
    mock_qr.certificate_id = uuid4()
    mock_qr_repo.get_by_token = AsyncMock(return_value=mock_qr)
    mock_qr_repo.increment_scan_count = AsyncMock()

    mock_cert = MagicMock()
    mock_cert.blockchain_status = BlockchainStatus.CONFIRMED
    mock_cert_repo.get_by_id = AsyncMock(return_value=mock_cert)

    mock_bc_service = MagicMock()
    mock_chain_result = MagicMock()
    mock_chain_result.status = "ACTIVE"
    mock_chain_result.is_valid = True
    mock_bc_service.verify_certificate.return_value = mock_chain_result

    mock_tx_hash.return_value = "0x" + "ab" * 32
    mock_log_repo.create = AsyncMock()

    result = await verify_by_qr_token("token", "ip", "agent", mock_db, mock_bc_service)
    assert result["result"] == VerificationResult.AUTHENTIC

@pytest.mark.unit
@patch("services.verification_service.QRVerificationRepository")
async def test_verify_qr_token_not_found(mock_qr_repo, mock_db):
    mock_qr_repo.get_by_token = AsyncMock(return_value=None)

    result = await verify_by_qr_token("token", "ip", "agent", mock_db, None)
    assert result["result"] == VerificationResult.NOT_FOUND

@pytest.mark.unit
@patch("services.verification_service.QRVerificationRepository")
async def test_verify_qr_token_expired(mock_qr_repo, mock_db):
    mock_qr = MagicMock()
    mock_qr.is_active = True
    mock_qr.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    mock_qr_repo.get_by_token = AsyncMock(return_value=mock_qr)

    result = await verify_by_qr_token("token", "ip", "agent", mock_db, None)
    assert result["result"] == VerificationResult.NOT_FOUND


@pytest.mark.unit
@patch("services.verification_service.CertificateRepository")
@patch("services.verification_service.VerificationLogRepository")
@patch("services.verification_service.generate_hash_from_file")
@patch("services.verification_service._get_block_number", new_callable=AsyncMock)
@patch("services.verification_service._get_store_tx_hash", new_callable=AsyncMock)
async def test_verification_log_created_on_success(mock_tx_hash, mock_block, mock_hash, mock_log_repo, mock_cert_repo, mock_db, current_user):
    mock_hash.return_value = "fakehash"
    mock_cert = MagicMock()
    mock_cert.blockchain_status = BlockchainStatus.CONFIRMED
    mock_cert.sha256_hash = "fakehash"
    mock_cert_repo.get_by_uid = AsyncMock(return_value=mock_cert)

    mock_bc_service = MagicMock()
    mock_chain_result = MagicMock()
    mock_chain_result.status = "ACTIVE"
    mock_chain_result.is_valid = True
    mock_bc_service.verify_certificate.return_value = mock_chain_result

    mock_tx_hash.return_value = ""
    mock_log_repo.create = AsyncMock()

    await verify_by_file_upload(b"fake", "uid-1", current_user, "1.2.3.4", "agent", mock_db, mock_bc_service)

    assert mock_log_repo.create.called


@pytest.mark.unit
@patch("services.verification_service.CertificateRepository")
@patch("services.verification_service.VerificationLogRepository")
@patch("services.verification_service.generate_hash_from_file")
async def test_verification_log_created_on_failure(mock_hash, mock_log_repo, mock_cert_repo, mock_db, current_user):
    mock_hash.return_value = "fakehash"
    mock_cert_repo.get_by_uid = AsyncMock(return_value=None)
    mock_cert_repo.get_by_hash = AsyncMock(return_value=None)

    mock_log_repo.create = AsyncMock()

    await verify_by_file_upload(b"fake", "uid-1", current_user, "1.2.3.4", "agent", mock_db, None)

    assert mock_log_repo.create.called
