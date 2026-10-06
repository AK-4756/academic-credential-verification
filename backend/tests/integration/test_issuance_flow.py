# backend/tests/integration/test_issuance_flow.py
# P10 Integration Tests — Certificate Issuance Flow
#
# Tests the two-phase issuance workflow against the real credential_db_test
# PostgreSQL database using the svc_db fixture (per-test truncation).
#
# Phase 1: upload_and_hash_certificate()
#   - Creates Certificate (PENDING) + BlockchainTransaction (PENDING, tx_hash=NULL)
#   - Writes PDF to a temporary UPLOAD_ROOT directory
#
# Phase 2: confirm_blockchain_storage()
#   - Verifies TX receipt via mocked BlockchainService (sync methods)
#   - Updates Certificate → CONFIRMED, BlockchainTransaction → CONFIRMED
#   - Generates QR verification record (own transaction, after outer commit)
#
# KEY PATCHES applied in all service calls:
#   settings.UPLOAD_ROOT   → pytest tmp_path
#   settings.CONTRACT_ADDRESS → valid 0x+40hex address (empty in .env.development)
#
# All BlockchainService methods are SYNCHRONOUS → MagicMock, not AsyncMock.

from __future__ import annotations

import hashlib
import re
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.constants import BlockchainStatus, TransactionStatus, TransactionType, UserRole
from core.exceptions import (
    DuplicateCertificateError,
    MissingWalletAddressError,
    ServiceError,
    UnverifiedUniversityError,
    UserNotFoundError,
)
from core.security import hash_password
from models.blockchain_transaction_model import BlockchainTransaction
from models.certificate_model import Certificate
from models.qr_verification_model import QRVerification
from models.student_model import Student
from models.university_model import University
from models.user_model import User
from repositories import (
    BlockchainTransactionRepository,
    CertificateRepository,
    QRVerificationRepository,
)
from services import certificate_issuance_service

# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------
SAMPLE_PDF = b"%PDF-1.4 minimal test PDF content for hashing " + b"x" * 200
SAMPLE_PDF_HASH = hashlib.sha256(SAMPLE_PDF).hexdigest()

WALLET_ADDRESS = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
CONTRACT_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
TX_HASH = "0x" + "ab" * 32   # valid 66-char hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_patches(tmp_path):
    """Context manager: patch UPLOAD_ROOT + CONTRACT_ADDRESS for all service calls."""
    return patch.multiple(
        settings,
        UPLOAD_ROOT=str(tmp_path),
        CONTRACT_ADDRESS=CONTRACT_ADDRESS,
    )


def _make_receipt(status: int = 1):
    r = MagicMock()
    r.status = status
    r.block_number = 100
    r.block_hash = "0x" + "ef" * 32
    r.gas_used = 50000
    r.effective_gas_price = 1_000_000_000
    return r


def _make_chain_record(cert_hash: str = SAMPLE_PDF_HASH, issuer: str = WALLET_ADDRESS,
                        chain_status: str = "ACTIVE"):
    rec = MagicMock()
    rec.exists = True
    rec.certificate_hash = cert_hash
    rec.issuing_university = issuer
    rec.issued_at = datetime.now(timezone.utc)
    rec.status = chain_status
    return rec


def _make_blockchain_mock(
    *,
    receipt_status: int = 1,
    receipt_none: bool = False,
    cert_hash: str = SAMPLE_PDF_HASH,
    issuer: str = WALLET_ADDRESS,
    chain_status: str = "ACTIVE",
    record_exists: bool = True,
) -> MagicMock:
    """Build a synchronous MagicMock matching real BlockchainService interface."""
    mock = MagicMock()
    mock.is_authorized_issuer.return_value = True
    if receipt_none:
        mock.get_transaction_receipt.return_value = None
    else:
        mock.get_transaction_receipt.return_value = _make_receipt(receipt_status)
    if record_exists:
        mock.get_certificate_record.return_value = _make_chain_record(
            cert_hash, issuer, chain_status
        )
    else:
        mock.get_certificate_record.return_value = None
    return mock


async def _run_phase1(svc_db, admin, student_user, tmp_path, pdf_bytes=None,
                      degree_title="BSc CS"):
    """Run Phase 1 issuance with all required patches and return result dict."""
    pdf = pdf_bytes or SAMPLE_PDF
    with _call_patches(tmp_path):
        result = await certificate_issuance_service.upload_and_hash_certificate(
            file_bytes=pdf,
            file_original_name="degree.pdf",
            metadata={
                "recipient_email": student_user.email,
                "degree_title": degree_title,
                "field_of_study": "CS",
                "issue_date": date.today(),
            },
            current_user=admin,
            db=svc_db,
        )
    # Phase 1 commits. Roll back any lingering read transaction so Phase 2 starts clean.
    await svc_db.rollback()
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def uni_and_admin(svc_db: AsyncSession):
    """Verified university + UNIVERSITY_ADMIN user, committed via svc_db."""
    university = University(
        id=uuid4(),
        name="Integration Test University",
        short_code="ITU",
        country="US",
        official_email="admin@itu.edu",
        is_verified=True,
        verified_at=datetime.utcnow(),
        is_active=True,
        wallet_address=WALLET_ADDRESS,
    )
    admin = User(
        id=uuid4(),
        email="admin@itu.edu",
        password_hash=hash_password("Password123!"),
        first_name="Admin",
        last_name="Issuer",
        role=UserRole.UNIVERSITY_ADMIN,
        university_id=university.id,
        is_active=True,
    )
    async with svc_db.begin():
        svc_db.add(university)
        svc_db.add(admin)
    return university, admin


@pytest_asyncio.fixture
async def student_user_and_profile(svc_db: AsyncSession):
    """STUDENT user + matching Student profile row, committed via svc_db."""
    student_user = User(
        id=uuid4(),
        email="student@itu.edu",
        password_hash=hash_password("Password123!"),
        first_name="Jane",
        last_name="Doe",
        role=UserRole.STUDENT,
        is_active=True,
    )
    async with svc_db.begin():
        svc_db.add(student_user)

    student_profile = Student(id=uuid4(), user_id=student_user.id)
    async with svc_db.begin():
        svc_db.add(student_profile)

    return student_user, student_profile


# ---------------------------------------------------------------------------
# Phase 1 tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_phase1_success(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """Phase 1 happy path: cert + blockchain_tx created, file written to disk."""
    university, admin = uni_and_admin
    student_user, _ = student_user_and_profile

    with _call_patches(tmp_path):
        result = await certificate_issuance_service.upload_and_hash_certificate(
            file_bytes=SAMPLE_PDF,
            file_original_name="degree.pdf",
            metadata={
                "recipient_email": student_user.email,
                "degree_title": "BSc Computer Science",
                "field_of_study": "Computer Science",
                "issue_date": date.today(),
            },
            current_user=admin,
            db=svc_db,
        )

    assert result["sha256_hash"] == SAMPLE_PDF_HASH
    assert result["blockchain_status"] == BlockchainStatus.PENDING
    cert_id = result["certificate_id"]

    # Certificate exists in DB
    cert = await CertificateRepository.get_by_id(svc_db, cert_id)
    assert cert is not None
    assert cert.sha256_hash == SAMPLE_PDF_HASH
    assert cert.blockchain_status == BlockchainStatus.PENDING
    # Defect #3 regression: student_id must point to users.id, not students.id
    assert cert.student_id == student_user.id

    # PENDING BlockchainTransaction with tx_hash=NULL (Defect #1 fix)
    txs = await BlockchainTransactionRepository.get_by_certificate_id(svc_db, cert_id)
    assert len(txs) == 1
    assert txs[0].tx_type == TransactionType.STORE_HASH
    assert txs[0].status == TransactionStatus.PENDING
    assert txs[0].tx_hash is None

    # File written to the temp upload dir
    expected_file = (
        tmp_path / "certificates" / str(admin.university_id) / f"{cert_id}.pdf"
    )
    assert expected_file.exists()
    assert expected_file.read_bytes() == SAMPLE_PDF


@pytest.mark.asyncio
async def test_phase1_uid_format(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """Certificate UID must match ^SHORT_CODE-YYYY-NNNNN pattern."""
    _, admin = uni_and_admin
    student_user, _ = student_user_and_profile

    with _call_patches(tmp_path):
        result = await certificate_issuance_service.upload_and_hash_certificate(
            file_bytes=SAMPLE_PDF,
            file_original_name="degree.pdf",
            metadata={
                "recipient_email": student_user.email,
                "degree_title": "BSc CS",
                "field_of_study": "CS",
                "issue_date": date.today(),
            },
            current_user=admin,
            db=svc_db,
        )

    uid = result["certificate_uid"]
    assert re.match(r"^[A-Z0-9]+-\d{4}-\d{5}$", uid), f"UID format wrong: {uid}"
    assert uid.startswith(f"ITU-{date.today().year}-")


@pytest.mark.asyncio
async def test_phase1_cert_state_is_pending(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """After Phase 1, DB certificate has blockchain_status=PENDING and is_active=True."""
    _, admin = uni_and_admin
    student_user, _ = student_user_and_profile

    with _call_patches(tmp_path):
        result = await certificate_issuance_service.upload_and_hash_certificate(
            file_bytes=SAMPLE_PDF,
            file_original_name="degree.pdf",
            metadata={
                "recipient_email": student_user.email,
                "degree_title": "MA History",
                "field_of_study": "History",
                "issue_date": date.today(),
            },
            current_user=admin,
            db=svc_db,
        )

    cert = await CertificateRepository.get_by_id(svc_db, result["certificate_id"])
    assert cert.blockchain_status == BlockchainStatus.PENDING
    assert cert.is_active is True


@pytest.mark.asyncio
async def test_phase1_duplicate_hash_raises(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """Uploading the same file bytes twice raises DuplicateCertificateError."""
    _, admin = uni_and_admin
    student_user, _ = student_user_and_profile

    with _call_patches(tmp_path):
        # First upload
        await certificate_issuance_service.upload_and_hash_certificate(
            file_bytes=SAMPLE_PDF,
            file_original_name="degree.pdf",
            metadata={
                "recipient_email": student_user.email,
                "degree_title": "BSc CS",
                "field_of_study": "CS",
                "issue_date": date.today(),
            },
            current_user=admin,
            db=svc_db,
        )
        await svc_db.rollback()

        # Second upload — same bytes → same hash → DuplicateCertificateError
        with pytest.raises(DuplicateCertificateError):
            await certificate_issuance_service.upload_and_hash_certificate(
                file_bytes=SAMPLE_PDF,
                file_original_name="degree_copy.pdf",
                metadata={
                    "recipient_email": student_user.email,
                    "degree_title": "MBA",
                    "field_of_study": "Business",
                    "issue_date": date.today(),
                },
                current_user=admin,
                db=svc_db,
            )


@pytest.mark.asyncio
async def test_phase1_student_not_found_raises(svc_db, uni_and_admin, tmp_path):
    """Unknown recipient email raises UserNotFoundError."""
    _, admin = uni_and_admin

    with _call_patches(tmp_path):
        with pytest.raises(UserNotFoundError):
            await certificate_issuance_service.upload_and_hash_certificate(
                file_bytes=SAMPLE_PDF,
                file_original_name="degree.pdf",
                metadata={
                    "recipient_email": "nobody@nowhere.invalid",
                    "degree_title": "BSc CS",
                    "field_of_study": "CS",
                    "issue_date": date.today(),
                },
                current_user=admin,
                db=svc_db,
            )


@pytest.mark.asyncio
async def test_phase1_unverified_university_raises(svc_db, student_user_and_profile, tmp_path):
    """University with is_verified=False raises UnverifiedUniversityError."""
    student_user, _ = student_user_and_profile

    unverified_uni = University(
        id=uuid4(), name="Unverified Uni", short_code="UVU", country="US",
        official_email="admin@uvu.edu", is_verified=False, is_active=True,
        wallet_address=WALLET_ADDRESS,
    )
    admin = User(
        id=uuid4(), email="admin@uvu.edu", password_hash=hash_password("Pass123!"),
        first_name="Admin", last_name="U", role=UserRole.UNIVERSITY_ADMIN,
        university_id=unverified_uni.id, is_active=True,
    )
    async with svc_db.begin():
        svc_db.add(unverified_uni)
        svc_db.add(admin)

    with _call_patches(tmp_path):
        with pytest.raises(UnverifiedUniversityError):
            await certificate_issuance_service.upload_and_hash_certificate(
                file_bytes=SAMPLE_PDF,
                file_original_name="degree.pdf",
                metadata={
                    "recipient_email": student_user.email,
                    "degree_title": "BSc CS",
                    "field_of_study": "CS",
                    "issue_date": date.today(),
                },
                current_user=admin,
                db=svc_db,
            )


@pytest.mark.asyncio
async def test_phase1_missing_wallet_raises(svc_db, student_user_and_profile, tmp_path):
    """University with wallet_address=None raises MissingWalletAddressError."""
    student_user, _ = student_user_and_profile

    no_wallet_uni = University(
        id=uuid4(), name="No Wallet Uni", short_code="NWU", country="US",
        official_email="admin@nwu.edu", is_verified=True, verified_at=datetime.utcnow(),
        is_active=True, wallet_address=None,
    )
    admin = User(
        id=uuid4(), email="admin@nwu.edu", password_hash=hash_password("Pass123!"),
        first_name="Admin", last_name="N", role=UserRole.UNIVERSITY_ADMIN,
        university_id=no_wallet_uni.id, is_active=True,
    )
    async with svc_db.begin():
        svc_db.add(no_wallet_uni)
        svc_db.add(admin)

    with _call_patches(tmp_path):
        with pytest.raises(MissingWalletAddressError):
            await certificate_issuance_service.upload_and_hash_certificate(
                file_bytes=SAMPLE_PDF,
                file_original_name="degree.pdf",
                metadata={
                    "recipient_email": student_user.email,
                    "degree_title": "BSc CS",
                    "field_of_study": "CS",
                    "issue_date": date.today(),
                },
                current_user=admin,
                db=svc_db,
            )


# ---------------------------------------------------------------------------
# Phase 2 tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_phase2_receipt_none_returns_submitted(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """When get_transaction_receipt returns None, Phase 2 returns status=SUBMITTED."""
    university, admin = uni_and_admin
    student_user, _ = student_user_and_profile

    phase1 = await _run_phase1(svc_db, admin, student_user, tmp_path)
    cert_id = phase1["certificate_id"]

    with _call_patches(tmp_path):
        result = await certificate_issuance_service.confirm_blockchain_storage(
            cert_id=cert_id,
            blockchain_tx_hash=TX_HASH,
            current_user=admin,
            db=svc_db,
            blockchain_service=_make_blockchain_mock(receipt_none=True),
        )

    assert result["status"] == "SUBMITTED"
    await svc_db.rollback()
    cert = await CertificateRepository.get_by_id(svc_db, cert_id)
    assert cert.blockchain_status == BlockchainStatus.SUBMITTED


@pytest.mark.asyncio
async def test_phase2_receipt_failed_raises(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """When receipt.status==0, Phase 2 raises ServiceError."""
    _, admin = uni_and_admin
    student_user, _ = student_user_and_profile
    phase1 = await _run_phase1(svc_db, admin, student_user, tmp_path)

    with _call_patches(tmp_path):
        with pytest.raises(ServiceError):
            await certificate_issuance_service.confirm_blockchain_storage(
                cert_id=phase1["certificate_id"],
                blockchain_tx_hash=TX_HASH,
                current_user=admin,
                db=svc_db,
                blockchain_service=_make_blockchain_mock(receipt_status=0),
            )


@pytest.mark.asyncio
async def test_phase2_hash_mismatch_raises(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """When chain hash != DB hash, Phase 2 raises ServiceError."""
    _, admin = uni_and_admin
    student_user, _ = student_user_and_profile
    phase1 = await _run_phase1(svc_db, admin, student_user, tmp_path)

    with _call_patches(tmp_path):
        with pytest.raises(ServiceError):
            await certificate_issuance_service.confirm_blockchain_storage(
                cert_id=phase1["certificate_id"],
                blockchain_tx_hash=TX_HASH,
                current_user=admin,
                db=svc_db,
                blockchain_service=_make_blockchain_mock(cert_hash="aa" * 32),
            )


@pytest.mark.asyncio
async def test_phase2_issuer_mismatch_raises(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """When chain issuer != university wallet, Phase 2 raises ServiceError."""
    _, admin = uni_and_admin
    student_user, _ = student_user_and_profile
    phase1 = await _run_phase1(svc_db, admin, student_user, tmp_path)

    wrong_issuer = "0x" + "de" * 19 + "ad"
    with _call_patches(tmp_path):
        with pytest.raises(ServiceError):
            await certificate_issuance_service.confirm_blockchain_storage(
                cert_id=phase1["certificate_id"],
                blockchain_tx_hash=TX_HASH,
                current_user=admin,
                db=svc_db,
                blockchain_service=_make_blockchain_mock(issuer=wrong_issuer),
            )


@pytest.mark.asyncio
async def test_phase2_success_returns_confirmed(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """Full Phase 2 happy path: result has status=CONFIRMED with certificate + QR data."""
    university, admin = uni_and_admin
    student_user, _ = student_user_and_profile
    phase1 = await _run_phase1(svc_db, admin, student_user, tmp_path)

    with _call_patches(tmp_path):
        result = await certificate_issuance_service.confirm_blockchain_storage(
            cert_id=phase1["certificate_id"],
            blockchain_tx_hash=TX_HASH,
            current_user=admin,
            db=svc_db,
            blockchain_service=_make_blockchain_mock(),
        )

    assert result["status"] == "CONFIRMED"
    assert result["certificate"]["blockchain_status"] == BlockchainStatus.CONFIRMED
    assert "token" in result["qr_code"]
    assert "verification_url" in result["qr_code"]


@pytest.mark.asyncio
async def test_phase2_cert_state_confirmed_in_db(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """After Phase 2 success, DB Certificate has blockchain_status=CONFIRMED."""
    _, admin = uni_and_admin
    student_user, _ = student_user_and_profile
    phase1 = await _run_phase1(svc_db, admin, student_user, tmp_path)
    cert_id = phase1["certificate_id"]

    with _call_patches(tmp_path):
        await certificate_issuance_service.confirm_blockchain_storage(
            cert_id=cert_id,
            blockchain_tx_hash=TX_HASH,
            current_user=admin,
            db=svc_db,
            blockchain_service=_make_blockchain_mock(),
        )

    await svc_db.rollback()
    cert = await CertificateRepository.get_by_id(svc_db, cert_id)
    assert cert.blockchain_status == BlockchainStatus.CONFIRMED
    assert cert.is_active is True


@pytest.mark.asyncio
async def test_phase2_blockchain_tx_confirmed_in_db(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """After Phase 2 success, BlockchainTransaction has status=CONFIRMED and tx_hash set."""
    _, admin = uni_and_admin
    student_user, _ = student_user_and_profile
    phase1 = await _run_phase1(svc_db, admin, student_user, tmp_path)
    cert_id = phase1["certificate_id"]

    with _call_patches(tmp_path):
        await certificate_issuance_service.confirm_blockchain_storage(
            cert_id=cert_id,
            blockchain_tx_hash=TX_HASH,
            current_user=admin,
            db=svc_db,
            blockchain_service=_make_blockchain_mock(),
        )

    await svc_db.rollback()
    txs = await BlockchainTransactionRepository.get_by_certificate_id(svc_db, cert_id)
    store_tx = next(t for t in txs if t.tx_type == TransactionType.STORE_HASH)
    assert store_tx.status == TransactionStatus.CONFIRMED
    assert store_tx.tx_hash == TX_HASH
    assert store_tx.block_number == 100


@pytest.mark.asyncio
async def test_phase2_qr_record_created(svc_db, uni_and_admin, student_user_and_profile, tmp_path):
    """After Phase 2 success, an active QR record exists for the certificate."""
    _, admin = uni_and_admin
    student_user, _ = student_user_and_profile
    phase1 = await _run_phase1(svc_db, admin, student_user, tmp_path)
    cert_id = phase1["certificate_id"]

    with _call_patches(tmp_path):
        result = await certificate_issuance_service.confirm_blockchain_storage(
            cert_id=cert_id,
            blockchain_tx_hash=TX_HASH,
            current_user=admin,
            db=svc_db,
            blockchain_service=_make_blockchain_mock(),
        )

    await svc_db.rollback()
    qr = await QRVerificationRepository.get_active_by_certificate(svc_db, cert_id)
    assert qr is not None
    assert qr.is_active is True
    assert qr.token == result["qr_code"]["token"]
    assert settings.VERIFICATION_BASE_URL in qr.verification_url
