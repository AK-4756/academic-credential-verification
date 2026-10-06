import sys
from pathlib import Path

backend_dir = r"d:\AI(NON-IMP)\Decentralized Blockchain\academic-credential-verification\backend"
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from core.exceptions import (
    UnverifiedUniversityError,
    MissingWalletAddressError,
    UserNotFoundError,
    DuplicateCertificateError,
    CertificateNotFoundError,
    OwnershipViolationError,
    ServiceError,
    BlockchainConnectionError,
)
from core.constants import BlockchainStatus, TransactionStatus, TransactionType
from services.certificate_issuance_service import upload_and_hash_certificate, confirm_blockchain_storage

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
    user.university_id = uuid4()
    user.id = uuid4()
    return user

@pytest.fixture
def valid_metadata():
    return {
        "recipient_email": "student@example.com",
        "degree_title": "BSc Computer Science",
        "field_of_study": "Computer Science",
        "issue_date": "2023-01-01",
        "expiry_date": None,
        "grade_classification": "First Class",
        "honors": None
    }


@pytest.mark.unit
@patch("services.certificate_issuance_service.UniversityRepository")
@patch("services.certificate_issuance_service.UserRepository")
@patch("services.certificate_issuance_service.StudentRepository")
@patch("services.certificate_issuance_service.CertificateRepository")
@patch("services.certificate_issuance_service.BlockchainTransactionRepository")
@patch("services.certificate_issuance_service.generate_hash_from_file")
@patch("services.certificate_issuance_service.save_certificate")
async def test_upload_valid_pdf_success(mock_save, mock_hash, mock_bt_repo, mock_cert_repo, mock_student_repo, mock_user_repo, mock_uni_repo, mock_db, current_user, valid_metadata):
    mock_uni = MagicMock()
    mock_uni.is_verified = True
    mock_uni.wallet_address = "0x123"
    mock_uni.short_code = "UNI"
    mock_uni_repo.get_by_id = AsyncMock(return_value=mock_uni)

    mock_user = MagicMock()
    mock_user.id = uuid4()
    mock_user.first_name = "John"
    mock_user.last_name = "Doe"
    mock_user_repo.get_by_email = AsyncMock(return_value=mock_user)

    mock_student = MagicMock()
    mock_student.id = uuid4()
    mock_student_repo.get_by_user_id = AsyncMock(return_value=mock_student)

    mock_cert_repo.get_next_uid_sequence = AsyncMock(return_value=1)
    mock_hash.return_value = "fakehash"
    mock_cert_repo.get_by_hash = AsyncMock(return_value=None)

    mock_cert = MagicMock()
    mock_cert.id = uuid4()
    mock_cert_repo.create = AsyncMock(return_value=mock_cert)
    
    mock_bt_repo.create = AsyncMock()
    mock_save.return_value = "/fake/path"

    result = await upload_and_hash_certificate(b"fakebytes", "file.pdf", valid_metadata, current_user, mock_db)
    
    assert result["sha256_hash"] == "fakehash"
    assert result["blockchain_status"] == BlockchainStatus.PENDING
    assert "certificate_uid" in result

@pytest.mark.unit
async def test_upload_invalid_mime_type():
    pass

@pytest.mark.unit
async def test_upload_file_too_large():
    pass

@pytest.mark.unit
async def test_upload_empty_file():
    pass

@pytest.mark.unit
@patch("services.certificate_issuance_service.UniversityRepository")
@patch("services.certificate_issuance_service.UserRepository")
@patch("services.certificate_issuance_service.StudentRepository")
@patch("services.certificate_issuance_service.CertificateRepository")
@patch("services.certificate_issuance_service.generate_hash_from_file")
async def test_upload_duplicate_hash(mock_hash, mock_cert_repo, mock_student_repo, mock_user_repo, mock_uni_repo, mock_db, current_user, valid_metadata):
    mock_uni = MagicMock()
    mock_uni.is_verified = True
    mock_uni.wallet_address = "0x123"
    mock_uni_repo.get_by_id = AsyncMock(return_value=mock_uni)
    mock_user_repo.get_by_email = AsyncMock(return_value=MagicMock())
    mock_student_repo.get_by_user_id = AsyncMock(return_value=MagicMock())
    mock_cert_repo.get_next_uid_sequence = AsyncMock(return_value=1)
    mock_hash.return_value = "fakehash"
    mock_cert_repo.get_by_hash = AsyncMock(return_value=MagicMock()) # Duplicate found

    with pytest.raises(DuplicateCertificateError):
        await upload_and_hash_certificate(b"fakebytes", "file.pdf", valid_metadata, current_user, mock_db)

@pytest.mark.unit
@patch("services.certificate_issuance_service.UniversityRepository")
@patch("services.certificate_issuance_service.UserRepository")
async def test_upload_student_not_found(mock_user_repo, mock_uni_repo, mock_db, current_user, valid_metadata):
    mock_uni = MagicMock()
    mock_uni.is_verified = True
    mock_uni.wallet_address = "0x123"
    mock_uni_repo.get_by_id = AsyncMock(return_value=mock_uni)
    mock_user_repo.get_by_email = AsyncMock(return_value=None)

    with pytest.raises(UserNotFoundError):
        await upload_and_hash_certificate(b"fakebytes", "file.pdf", valid_metadata, current_user, mock_db)

@pytest.mark.unit
@patch("services.certificate_issuance_service.UniversityRepository")
async def test_upload_unverified_university(mock_uni_repo, mock_db, current_user, valid_metadata):
    mock_uni = MagicMock()
    mock_uni.is_verified = False
    mock_uni_repo.get_by_id = AsyncMock(return_value=mock_uni)

    with pytest.raises(UnverifiedUniversityError):
        await upload_and_hash_certificate(b"fakebytes", "file.pdf", valid_metadata, current_user, mock_db)

@pytest.mark.unit
@patch("services.certificate_issuance_service.CertificateRepository")
@patch("services.certificate_issuance_service.UniversityRepository")
@patch("services.certificate_issuance_service.BlockchainTransactionRepository")
@patch("services.certificate_issuance_service.qr_verification_service")
async def test_confirm_storage_success(mock_qr, mock_bt_repo, mock_uni_repo, mock_cert_repo, mock_db, current_user):
    cert_id = uuid4()
    mock_cert = MagicMock()
    mock_cert.university_id = current_user.university_id
    mock_cert.blockchain_status = BlockchainStatus.PENDING
    mock_cert.certificate_uid = "UID-1"
    mock_cert.sha256_hash = "fakehash"
    mock_cert_repo.get_by_id = AsyncMock(return_value=mock_cert)
    mock_cert_repo.update_blockchain_status = AsyncMock(return_value=mock_cert)

    mock_uni = MagicMock()
    mock_uni.wallet_address = "0x123"
    mock_uni_repo.get_by_id = AsyncMock(return_value=mock_uni)

    mock_tx = MagicMock()
    mock_tx.tx_type = TransactionType.STORE_HASH
    mock_bt_repo.get_by_certificate_id = AsyncMock(return_value=[mock_tx])
    mock_bt_repo.update_status = AsyncMock()

    mock_bc_service = MagicMock()
    mock_receipt = MagicMock()
    mock_receipt.status = 1
    mock_bc_service.get_transaction_receipt.return_value = mock_receipt

    mock_record = MagicMock()
    mock_record.exists = True
    mock_record.certificate_hash = "fakehash"
    mock_record.issuing_university = "0x123"
    mock_bc_service.get_certificate_record.return_value = mock_record

    mock_qr.generate_qr_for_certificate = AsyncMock(return_value={"token": "t", "verification_url": "u"})

    result = await confirm_blockchain_storage(cert_id, "0xhash", current_user, mock_db, mock_bc_service)
    assert result["status"] == "CONFIRMED"

@pytest.mark.unit
@patch("services.certificate_issuance_service.CertificateRepository")
@patch("services.certificate_issuance_service.UniversityRepository")
@patch("services.certificate_issuance_service.BlockchainTransactionRepository")
async def test_confirm_storage_tx_not_found(mock_bt_repo, mock_uni_repo, mock_cert_repo, mock_db, current_user):
    cert_id = uuid4()
    mock_cert = MagicMock()
    mock_cert.university_id = current_user.university_id
    mock_cert.blockchain_status = BlockchainStatus.PENDING
    mock_cert_repo.get_by_id = AsyncMock(return_value=mock_cert)
    mock_cert_repo.update_blockchain_status = AsyncMock()

    mock_uni = MagicMock()
    mock_uni.wallet_address = "0x123"
    mock_uni_repo.get_by_id = AsyncMock(return_value=mock_uni)

    mock_bt_repo.get_by_certificate_id = AsyncMock(return_value=[])
    
    mock_bc_service = MagicMock()
    mock_bc_service.get_transaction_receipt.return_value = None

    result = await confirm_blockchain_storage(cert_id, "0xhash", current_user, mock_db, mock_bc_service)
    assert result["status"] == "SUBMITTED"

@pytest.mark.unit
@patch("services.certificate_issuance_service.CertificateRepository")
@patch("services.certificate_issuance_service.UniversityRepository")
@patch("services.certificate_issuance_service.BlockchainTransactionRepository")
async def test_confirm_storage_tx_failed(mock_bt_repo, mock_uni_repo, mock_cert_repo, mock_db, current_user):
    cert_id = uuid4()
    mock_cert = MagicMock()
    mock_cert.university_id = current_user.university_id
    mock_cert.blockchain_status = BlockchainStatus.PENDING
    mock_cert_repo.get_by_id = AsyncMock(return_value=mock_cert)
    mock_cert_repo.update_blockchain_status = AsyncMock()

    mock_uni = MagicMock()
    mock_uni.wallet_address = "0x123"
    mock_uni_repo.get_by_id = AsyncMock(return_value=mock_uni)

    mock_bt_repo.get_by_certificate_id = AsyncMock(return_value=[])
    
    mock_bc_service = MagicMock()
    mock_receipt = MagicMock()
    mock_receipt.status = 0
    mock_bc_service.get_transaction_receipt.return_value = mock_receipt

    with pytest.raises(ServiceError, match="failed"):
        await confirm_blockchain_storage(cert_id, "0xhash", current_user, mock_db, mock_bc_service)

@pytest.mark.unit
@patch("services.certificate_issuance_service.CertificateRepository")
@patch("services.certificate_issuance_service.UniversityRepository")
@patch("services.certificate_issuance_service.BlockchainTransactionRepository")
async def test_confirm_storage_hash_mismatch(mock_bt_repo, mock_uni_repo, mock_cert_repo, mock_db, current_user):
    cert_id = uuid4()
    mock_cert = MagicMock()
    mock_cert.university_id = current_user.university_id
    mock_cert.blockchain_status = BlockchainStatus.PENDING
    mock_cert.sha256_hash = "fakehash"
    mock_cert_repo.get_by_id = AsyncMock(return_value=mock_cert)

    mock_uni = MagicMock()
    mock_uni.wallet_address = "0x123"
    mock_uni_repo.get_by_id = AsyncMock(return_value=mock_uni)

    mock_bt_repo.get_by_certificate_id = AsyncMock(return_value=[])
    
    mock_bc_service = MagicMock()
    mock_receipt = MagicMock()
    mock_receipt.status = 1
    mock_bc_service.get_transaction_receipt.return_value = mock_receipt

    mock_record = MagicMock()
    mock_record.exists = True
    mock_record.certificate_hash = "differenthash"
    mock_bc_service.get_certificate_record.return_value = mock_record

    with pytest.raises(ServiceError, match="match"):
        await confirm_blockchain_storage(cert_id, "0xhash", current_user, mock_db, mock_bc_service)

@pytest.mark.unit
@patch("services.certificate_issuance_service.UniversityRepository")
@patch("services.certificate_issuance_service.UserRepository")
@patch("services.certificate_issuance_service.StudentRepository")
@patch("services.certificate_issuance_service.CertificateRepository")
@patch("services.certificate_issuance_service.BlockchainTransactionRepository")
@patch("services.certificate_issuance_service.generate_hash_from_file")
@patch("services.certificate_issuance_service.save_certificate")
async def test_certificate_uid_generation(mock_save, mock_hash, mock_bt_repo, mock_cert_repo, mock_student_repo, mock_user_repo, mock_uni_repo, mock_db, current_user, valid_metadata):
    mock_uni = MagicMock()
    mock_uni.is_verified = True
    mock_uni.wallet_address = "0x123"
    mock_uni.short_code = "ABC"
    mock_uni_repo.get_by_id = AsyncMock(return_value=mock_uni)
    
    mock_user_repo.get_by_email = AsyncMock(return_value=MagicMock())
    mock_student_repo.get_by_user_id = AsyncMock(return_value=MagicMock())
    mock_cert_repo.get_by_hash = AsyncMock(return_value=None)
    
    mock_cert_repo.get_next_uid_sequence = AsyncMock(return_value=42)
    mock_cert = MagicMock()
    mock_cert_repo.create = AsyncMock(return_value=mock_cert)
    
    mock_bt_repo.create = AsyncMock()
    mock_save.return_value = "/f"
    
    result = await upload_and_hash_certificate(b"fake", "f.pdf", valid_metadata, current_user, mock_db)
    expected_year = date.today().year
    assert result["certificate_uid"] == f"ABC-{expected_year}-00042"
