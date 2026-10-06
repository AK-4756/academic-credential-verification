# backend/tests/integration/test_verification_flow.py
# P10 Integration Tests — Certificate Verification Flow
#
# Two verification paths tested against credential_db_test:
#   A. verify_by_file_upload()  — hash submitted bytes, consult blockchain
#   B. verify_by_qr_token()     — look up QR token, consult blockchain
#
# GOLDEN RULE: When blockchain is unavailable or None, NEVER return AUTHENTIC.
#
# All BlockchainService methods are SYNCHRONOUS → MagicMock (not AsyncMock).
#
# IMPORTANT: After svc_db.rollback(), all ORM objects are expired. Any
# attribute access after rollback will trigger a lazy-load which fails
# inside an async greenlet context. Capture needed values BEFORE rollback.

from __future__ import annotations

import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.constants import BlockchainStatus, UserRole, VerificationMethod, VerificationResult
from core.security import hash_password
from models.qr_verification_model import QRVerification
from models.student_model import Student
from models.university_model import University
from models.user_model import User
from models.verification_log_model import VerificationLog
from repositories import (
    CertificateRepository,
    QRVerificationRepository,
)
from services import certificate_issuance_service, verification_service

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SAMPLE_PDF = b"%PDF-1.4 verification integration test content " + b"v" * 200
SAMPLE_PDF_HASH = hashlib.sha256(SAMPLE_PDF).hexdigest()

TAMPERED_PDF = b"%PDF-1.4 tampered content " + b"t" * 200

WALLET_ADDRESS = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
CONTRACT_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
TX_HASH = "0x" + "33" * 32


def _patches(tmp_path=None):
    kwargs = {"CONTRACT_ADDRESS": CONTRACT_ADDRESS}
    if tmp_path is not None:
        kwargs["UPLOAD_ROOT"] = str(tmp_path)
    return patch.multiple(settings, **kwargs)


def _issuance_bc_mock():
    m = MagicMock()
    m.is_authorized_issuer.return_value = True
    r = MagicMock()
    r.status = 1
    r.block_number = 100
    r.block_hash = "0x" + "ef" * 32
    r.gas_used = 50000
    r.effective_gas_price = 1_000_000_000
    m.get_transaction_receipt.return_value = r
    rec = MagicMock()
    rec.exists = True
    rec.certificate_hash = SAMPLE_PDF_HASH
    rec.issuing_university = WALLET_ADDRESS
    rec.issued_at = datetime.now(timezone.utc)
    rec.status = "ACTIVE"
    m.get_certificate_record.return_value = rec
    return m


def _verification_bc_mock(is_valid: bool = True, status: str = "ACTIVE"):
    m = MagicMock()
    chain_result = MagicMock()
    chain_result.is_valid = is_valid
    chain_result.status = status
    chain_result.cert_uid = "VTEST"
    m.verify_certificate.return_value = chain_result
    rec = MagicMock()
    rec.exists = True
    rec.certificate_hash = SAMPLE_PDF_HASH
    rec.issuing_university = WALLET_ADDRESS
    rec.issued_at = datetime.now(timezone.utc)
    rec.status = status
    m.get_certificate_record.return_value = rec
    return m


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def verifier_user(svc_db: AsyncSession):
    """An EMPLOYER user acting as the verifier."""
    user = User(
        id=uuid4(), email="verifier@company.com",
        password_hash=hash_password("Pass123!"),
        first_name="Verify", last_name="Er",
        role=UserRole.EMPLOYER, is_active=True,
    )
    async with svc_db.begin():
        svc_db.add(user)
    return user


@pytest_asyncio.fixture
async def confirmed_certificate(svc_db: AsyncSession, tmp_path):
    """
    Full chain: university + admin + student + CONFIRMED certificate + QR.
    Returns (cert_id, cert_uid, admin_user, qr_token).
    qr_token is captured before rollback to avoid MissingGreenlet on lazy load.
    """
    university = University(
        id=uuid4(), name="Verification Test Uni", short_code="VTU", country="US",
        official_email="admin@vtu.edu",
        is_verified=True, verified_at=datetime.utcnow(),
        is_active=True, wallet_address=WALLET_ADDRESS,
    )
    admin = User(
        id=uuid4(), email="admin@vtu.edu", password_hash=hash_password("Pass123!"),
        first_name="Admin", last_name="V",
        role=UserRole.UNIVERSITY_ADMIN, university_id=university.id, is_active=True,
    )
    student_user = User(
        id=uuid4(), email="student@vtu.edu", password_hash=hash_password("Pass123!"),
        first_name="Alice", last_name="Student",
        role=UserRole.STUDENT, is_active=True,
    )
    async with svc_db.begin():
        svc_db.add(university)
        svc_db.add(admin)
        svc_db.add(student_user)

    student_profile = Student(id=uuid4(), user_id=student_user.id)
    async with svc_db.begin():
        svc_db.add(student_profile)

    # Phase 1
    with _patches(tmp_path):
        phase1 = await certificate_issuance_service.upload_and_hash_certificate(
            file_bytes=SAMPLE_PDF,
            file_original_name="cert.pdf",
            metadata={
                "recipient_email": student_user.email,
                "degree_title": "BSc Physics",
                "field_of_study": "Physics",
                "issue_date": date.today(),
            },
            current_user=admin,
            db=svc_db,
        )
    cert_id = phase1["certificate_id"]
    cert_uid = phase1["certificate_uid"]
    await svc_db.rollback()

    # Phase 2 → creates QR
    with _patches(tmp_path):
        phase2_result = await certificate_issuance_service.confirm_blockchain_storage(
            cert_id=cert_id,
            blockchain_tx_hash=TX_HASH,
            current_user=admin,
            db=svc_db,
            blockchain_service=_issuance_bc_mock(),
        )
    # Capture the QR token from the response BEFORE rollback
    qr_token = phase2_result["qr_code"]["token"]
    await svc_db.rollback()

    return cert_id, cert_uid, admin, qr_token


# ---------------------------------------------------------------------------
# File upload verification tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_authentic(svc_db, confirmed_certificate, verifier_user):
    """Correct file hash + blockchain ACTIVE → AUTHENTIC."""
    cert_id, _, _, _ = confirmed_certificate

    result = await verification_service.verify_by_file_upload(
        file_bytes=SAMPLE_PDF,
        cert_uid_hint=None,
        current_user=verifier_user,
        request_ip="1.2.3.4",
        user_agent="pytest",
        db=svc_db,
        blockchain_service=_verification_bc_mock(is_valid=True, status="ACTIVE"),
    )
    assert result["result"] == VerificationResult.AUTHENTIC
    assert result["certificate"] is not None


@pytest.mark.asyncio
async def test_verify_tampered(svc_db, confirmed_certificate, verifier_user):
    """Wrong file hash + blockchain invalid → TAMPERED."""
    _, cert_uid, _, _ = confirmed_certificate

    result = await verification_service.verify_by_file_upload(
        file_bytes=TAMPERED_PDF,
        cert_uid_hint=cert_uid,
        current_user=verifier_user,
        request_ip="1.2.3.4",
        user_agent="pytest",
        db=svc_db,
        blockchain_service=_verification_bc_mock(is_valid=False, status="ACTIVE"),
    )
    assert result["result"] == VerificationResult.TAMPERED


@pytest.mark.asyncio
async def test_verify_revoked(svc_db, confirmed_certificate, verifier_user):
    """Blockchain says REVOKED → REVOKED result."""
    _, cert_uid, _, _ = confirmed_certificate

    result = await verification_service.verify_by_file_upload(
        file_bytes=SAMPLE_PDF,
        cert_uid_hint=cert_uid,
        current_user=verifier_user,
        request_ip=None,
        user_agent=None,
        db=svc_db,
        blockchain_service=_verification_bc_mock(is_valid=True, status="REVOKED"),
    )
    assert result["result"] == VerificationResult.REVOKED


@pytest.mark.asyncio
async def test_verify_not_found(svc_db, verifier_user):
    """Unknown file that matches nothing in DB → NOT_FOUND."""
    unknown_pdf = b"%PDF-1.4 completely unknown " + b"u" * 300

    result = await verification_service.verify_by_file_upload(
        file_bytes=unknown_pdf,
        cert_uid_hint=None,
        current_user=verifier_user,
        request_ip=None,
        user_agent=None,
        db=svc_db,
        blockchain_service=_verification_bc_mock(),
    )
    assert result["result"] == VerificationResult.NOT_FOUND


@pytest.mark.asyncio
async def test_verify_golden_rule_no_blockchain(svc_db, confirmed_certificate, verifier_user):
    """
    GOLDEN RULE: even a perfect hash match must NOT return AUTHENTIC when
    blockchain_service=None. Must return PENDING_CHAIN.
    """
    result = await verification_service.verify_by_file_upload(
        file_bytes=SAMPLE_PDF,
        cert_uid_hint=None,
        current_user=verifier_user,
        request_ip=None,
        user_agent=None,
        db=svc_db,
        blockchain_service=None,
    )
    assert result["result"] != VerificationResult.AUTHENTIC, (
        "GOLDEN RULE violated: returned AUTHENTIC without blockchain"
    )
    assert result["result"] == VerificationResult.PENDING_CHAIN


@pytest.mark.asyncio
async def test_verification_log_persisted(svc_db, confirmed_certificate, verifier_user):
    """Every verify_by_file_upload call persists a VerificationLog row."""
    await verification_service.verify_by_file_upload(
        file_bytes=SAMPLE_PDF,
        cert_uid_hint=None,
        current_user=verifier_user,
        request_ip="127.0.0.1",
        user_agent="pytest-agent",
        db=svc_db,
        blockchain_service=_verification_bc_mock(is_valid=True, status="ACTIVE"),
    )

    await svc_db.rollback()
    stmt = select(VerificationLog).where(
        VerificationLog.verifier_user_id == verifier_user.id
    )
    res = await svc_db.execute(stmt)
    logs = list(res.scalars().all())
    assert len(logs) >= 1
    log = logs[0]
    assert log.result == VerificationResult.AUTHENTIC
    assert log.verification_method == VerificationMethod.FILE_UPLOAD
    assert log.submitted_hash == SAMPLE_PDF_HASH


# ---------------------------------------------------------------------------
# QR token verification tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_qr_verify_authentic(svc_db, confirmed_certificate):
    """Active QR token + blockchain ACTIVE → AUTHENTIC."""
    cert_id, _, _, qr_token = confirmed_certificate

    result = await verification_service.verify_by_qr_token(
        token=qr_token,
        request_ip="5.6.7.8",
        user_agent="QR-scanner",
        db=svc_db,
        blockchain_service=_verification_bc_mock(is_valid=True, status="ACTIVE"),
    )
    assert result["result"] == VerificationResult.AUTHENTIC


@pytest.mark.asyncio
async def test_qr_verify_not_found(svc_db):
    """Unknown token → NOT_FOUND."""
    result = await verification_service.verify_by_qr_token(
        token="completely-invalid-token-that-does-not-exist-in-db",
        request_ip=None,
        user_agent=None,
        db=svc_db,
        blockchain_service=None,
    )
    assert result["result"] == VerificationResult.NOT_FOUND


@pytest.mark.asyncio
async def test_qr_verify_expired(svc_db, confirmed_certificate):
    """QR with expires_at already past at service execution time → NOT_FOUND.

    Two-part strategy required by the DB constraint (expires_at > created_at):
      1. Insert a QR with expires_at = now + 60s.  This satisfies the constraint
         because the DB-assigned created_at ≈ now, so now+60s > created_at.
      2. Patch datetime.now() inside verification_service to return now + 61s, making
         the service believe the QR has already expired.
         (The original fixture QR has expires_at=None so patching alone was ineffective —
         the None guard at `if qr.expires_at and ...` short-circuits the comparison.)
    """
    cert_id, _, _, _ = confirmed_certificate

    # Step 1: deactivate the fixture's QR (expires_at=None) so it doesn't
    # interfere, and capture its generated_by before rollback.
    existing_qr = await QRVerificationRepository.get_active_by_certificate(svc_db, cert_id)
    assert existing_qr is not None
    existing_qr_id = existing_qr.id
    existing_qr_generated_by = existing_qr.generated_by  # capture before rollback expires object
    await svc_db.rollback()

    async with svc_db.begin():
        row = await svc_db.execute(
            select(QRVerification).where(QRVerification.id == existing_qr_id)
        )
        qr_obj = row.scalar_one()
        qr_obj.is_active = False
        qr_obj.deactivated_at = datetime.now(timezone.utc)
        qr_obj.deactivated_reason = "Replaced for expiry test"
    await svc_db.rollback()

    # Step 2: insert a QR with expires_at 60 seconds in the future.
    # The DB constraint (expires_at > created_at) is satisfied because
    # created_at ≈ now and now+60s >> now.
    short_token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(seconds=60)

    async with svc_db.begin():
        short_qr = QRVerification(
            certificate_id=cert_id,
            token=short_token,
            verification_url=f"http://localhost/verify/{short_token}",
            generated_by=existing_qr_generated_by,
            is_active=True,
            expires_at=expiry,
        )
        svc_db.add(short_qr)
    await svc_db.rollback()

    # Step 3: patch datetime.now() inside the service to return now+61s,
    # making expires_at (now+60s) < datetime.now() (now+61s) → True → expired.
    fake_now = now + timedelta(seconds=61)

    class _ShiftedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now

    with patch("services.verification_service.datetime", _ShiftedDatetime):
        result = await verification_service.verify_by_qr_token(
            token=short_token,
            request_ip=None,
            user_agent=None,
            db=svc_db,
            blockchain_service=_verification_bc_mock(),
        )
    assert result["result"] == VerificationResult.NOT_FOUND


@pytest.mark.asyncio
async def test_qr_verify_inactive(svc_db, confirmed_certificate):
    """Deactivated QR -> NOT_FOUND."""
    cert_id, _, _, qr_token = confirmed_certificate

    qr = await QRVerificationRepository.get_active_by_certificate(svc_db, cert_id)
    assert qr is not None
    qr_id = qr.id  # Capture PK before rollback expires the object

    # Close the autobegun read-tx before opening an explicit write transaction.
    await svc_db.rollback()

    async with svc_db.begin():
        result_row = await svc_db.execute(
            select(QRVerification).where(QRVerification.id == qr_id)
        )
        qr_obj = result_row.scalar_one()
        qr_obj.is_active = False
        qr_obj.deactivated_at = datetime.now(timezone.utc)
        qr_obj.deactivated_reason = "Test deactivation"
    await svc_db.rollback()

    result = await verification_service.verify_by_qr_token(
        token=qr_token,
        request_ip=None,
        user_agent=None,
        db=svc_db,
        blockchain_service=_verification_bc_mock(),
    )
    assert result["result"] == VerificationResult.NOT_FOUND


@pytest.mark.asyncio
async def test_qr_scan_count_increments(svc_db, confirmed_certificate):
    """Each QR scan increments total_scan_count by 1."""
    cert_id, _, _, qr_token = confirmed_certificate

    # Get initial scan count
    qr_before = await QRVerificationRepository.get_active_by_certificate(svc_db, cert_id)
    initial_count = qr_before.total_scan_count
    await svc_db.rollback()

    await verification_service.verify_by_qr_token(
        token=qr_token,
        request_ip="9.9.9.9",
        user_agent="Scanner",
        db=svc_db,
        blockchain_service=_verification_bc_mock(is_valid=True, status="ACTIVE"),
    )
    await svc_db.rollback()

    qr_after = await QRVerificationRepository.get_active_by_certificate(svc_db, cert_id)
    assert qr_after.total_scan_count == initial_count + 1


@pytest.mark.asyncio
async def test_qr_verify_golden_rule_no_blockchain(svc_db, confirmed_certificate):
    """QR path with blockchain_service=None → PENDING_CHAIN, never AUTHENTIC."""
    cert_id, _, _, qr_token = confirmed_certificate

    result = await verification_service.verify_by_qr_token(
        token=qr_token,
        request_ip=None,
        user_agent=None,
        db=svc_db,
        blockchain_service=None,
    )
    assert result["result"] != VerificationResult.AUTHENTIC
    assert result["result"] == VerificationResult.PENDING_CHAIN
