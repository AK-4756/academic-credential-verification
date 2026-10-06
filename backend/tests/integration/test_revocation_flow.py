# backend/tests/integration/test_revocation_flow.py
# P10 Integration Tests — Certificate Revocation Flow
#
# Two-phase revocation workflow tested against credential_db_test.
#
# Phase 1: initiate_revocation()
#   - Uses settings.CONTRACT_ADDRESS for the REVOKE_HASH tx to_address / contract_address
#   - Stores user-provided reason in tx.error_message
#
# Phase 2: confirm_revocation()
#   - Verifies TX receipt + on-chain REVOKED status
#   - Passes original reason to CertificateRepository.revoke() (Defect #4 fix)
#
# KEY: ALL calls to revocation service must patch CONTRACT_ADDRESS because
#      initiate_revocation() stores it in blockchain_transactions.to_address
#      which has a CHECK constraint ^0x[a-fA-F0-9]{40}$.

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.constants import BlockchainStatus, TransactionStatus, TransactionType, UserRole
from core.exceptions import (
    CertificateAlreadyRevokedError,
    CertificateNotFoundError,
    OwnershipViolationError,
    ServiceError,
    UnconfirmedCertificateError,
)
from core.security import hash_password
from models.student_model import Student
from models.university_model import University
from models.user_model import User
from repositories import (
    BlockchainTransactionRepository,
    CertificateRepository,
)
from services import certificate_issuance_service, certificate_revocation_service

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SAMPLE_PDF = b"%PDF-1.4 revocation integration test content " + b"y" * 200
SAMPLE_PDF_HASH = hashlib.sha256(SAMPLE_PDF).hexdigest()

WALLET_ADDRESS = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
CONTRACT_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
TX_HASH_STORE = "0x" + "11" * 32
TX_HASH_REVOKE = "0x" + "22" * 32


def _patches(tmp_path=None):
    """Patch CONTRACT_ADDRESS (and optionally UPLOAD_ROOT) on the settings object."""
    kwargs = {"CONTRACT_ADDRESS": CONTRACT_ADDRESS}
    if tmp_path is not None:
        kwargs["UPLOAD_ROOT"] = str(tmp_path)
    return patch.multiple(settings, **kwargs)


def _make_receipt(status: int = 1):
    r = MagicMock()
    r.status = status
    r.block_number = 200
    r.block_hash = "0x" + "ff" * 32
    r.gas_used = 60000
    r.effective_gas_price = 1_000_000_000
    return r


def _issuance_bc_mock():
    m = MagicMock()
    m.is_authorized_issuer.return_value = True
    m.get_transaction_receipt.return_value = _make_receipt(1)
    rec = MagicMock()
    rec.exists = True
    rec.certificate_hash = SAMPLE_PDF_HASH
    rec.issuing_university = WALLET_ADDRESS
    rec.issued_at = datetime.now(timezone.utc)
    rec.status = "ACTIVE"
    m.get_certificate_record.return_value = rec
    return m


def _revocation_bc_mock(receipt_status: int = 1, receipt_none: bool = False,
                         chain_status: str = "REVOKED"):
    m = MagicMock()
    m.is_authorized_issuer.return_value = True
    if receipt_none:
        m.get_transaction_receipt.return_value = None
    else:
        m.get_transaction_receipt.return_value = _make_receipt(receipt_status)
    rec = MagicMock()
    rec.exists = True
    rec.certificate_hash = SAMPLE_PDF_HASH
    rec.issuing_university = WALLET_ADDRESS
    rec.issued_at = datetime.now(timezone.utc)
    rec.revoked_at = datetime.now(timezone.utc)
    rec.status = chain_status
    m.get_certificate_record.return_value = rec
    return m


# ---------------------------------------------------------------------------
# Shared fixture: CONFIRMED certificate ready for revocation
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def confirmed_cert_setup(svc_db: AsyncSession, tmp_path):
    """
    Creates university + admin + student + CONFIRMED certificate.
    Returns (university, admin, student_user, cert_id).
    """
    university = University(
        id=uuid4(), name="Revocation Test University", short_code="RTU",
        country="US", official_email="admin@rtu.edu",
        is_verified=True, verified_at=datetime.utcnow(),
        is_active=True, wallet_address=WALLET_ADDRESS,
    )
    admin = User(
        id=uuid4(), email="admin@rtu.edu", password_hash=hash_password("Pass123!"),
        first_name="Admin", last_name="R",
        role=UserRole.UNIVERSITY_ADMIN, university_id=university.id, is_active=True,
    )
    student_user = User(
        id=uuid4(), email="student@rtu.edu", password_hash=hash_password("Pass123!"),
        first_name="Bob", last_name="Student", role=UserRole.STUDENT, is_active=True,
    )
    async with svc_db.begin():
        svc_db.add(university)
        svc_db.add(admin)
        svc_db.add(student_user)

    student_profile = Student(id=uuid4(), user_id=student_user.id)
    async with svc_db.begin():
        svc_db.add(student_profile)

    # Phase 1 issuance
    with _patches(tmp_path):
        phase1 = await certificate_issuance_service.upload_and_hash_certificate(
            file_bytes=SAMPLE_PDF,
            file_original_name="cert.pdf",
            metadata={
                "recipient_email": student_user.email,
                "degree_title": "PhD Physics",
                "field_of_study": "Physics",
                "issue_date": date.today(),
            },
            current_user=admin,
            db=svc_db,
        )
    cert_id = phase1["certificate_id"]
    await svc_db.rollback()

    # Phase 2 confirmation
    with _patches(tmp_path):
        await certificate_issuance_service.confirm_blockchain_storage(
            cert_id=cert_id,
            blockchain_tx_hash=TX_HASH_STORE,
            current_user=admin,
            db=svc_db,
            blockchain_service=_issuance_bc_mock(),
        )
    await svc_db.rollback()

    return university, admin, student_user, cert_id


# ---------------------------------------------------------------------------
# Phase 1: initiate_revocation() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initiate_success(svc_db, confirmed_cert_setup, tmp_path):
    """Phase 1 returns wallet address and message."""
    university, admin, _, cert_id = confirmed_cert_setup

    with _patches(tmp_path):
        result = await certificate_revocation_service.initiate_revocation(
            cert_id=cert_id, reason="Degree was falsified",
            current_user=admin, db=svc_db,
        )

    assert result["university_wallet_address"] == WALLET_ADDRESS
    assert str(result["certificate_id"]) == str(cert_id)
    assert "message" in result


@pytest.mark.asyncio
async def test_initiate_creates_revoke_hash_tx(svc_db, confirmed_cert_setup, tmp_path):
    """Phase 1 creates a REVOKE_HASH tx with status=PENDING and tx_hash=NULL."""
    _, admin, _, cert_id = confirmed_cert_setup

    with _patches(tmp_path):
        await certificate_revocation_service.initiate_revocation(
            cert_id=cert_id, reason="Requirements not completed",
            current_user=admin, db=svc_db,
        )
    await svc_db.rollback()

    txs = await BlockchainTransactionRepository.get_by_certificate_id(svc_db, cert_id)
    revoke_txs = [t for t in txs if t.tx_type == TransactionType.REVOKE_HASH]
    assert len(revoke_txs) == 1
    assert revoke_txs[0].status == TransactionStatus.PENDING
    assert revoke_txs[0].tx_hash is None


@pytest.mark.asyncio
async def test_initiate_not_found_raises(svc_db, confirmed_cert_setup, tmp_path):
    """Unknown cert_id raises CertificateNotFoundError."""
    _, admin, _, _ = confirmed_cert_setup

    with _patches(tmp_path):
        with pytest.raises(CertificateNotFoundError):
            await certificate_revocation_service.initiate_revocation(
                cert_id=uuid4(), reason="Test",
                current_user=admin, db=svc_db,
            )


# A second distinct Ethereum wallet address — differs from WALLET_ADDRESS so it
# passes the universities.wallet_address UNIQUE constraint.
_OTHER_WALLET = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"


@pytest.mark.asyncio
async def test_initiate_ownership_violation(svc_db, confirmed_cert_setup, tmp_path):
    """Admin from a different university raises OwnershipViolationError."""
    _, _, _, cert_id = confirmed_cert_setup

    other_uni = University(
        id=uuid4(), name="Other Uni", short_code="OU", country="US",
        official_email="admin@ou.edu",
        is_verified=True, verified_at=datetime.utcnow(),
        is_active=True, wallet_address=_OTHER_WALLET,
    )
    other_admin = User(
        id=uuid4(), email="admin@ou.edu", password_hash=hash_password("Pass123!"),
        first_name="Other", last_name="Admin",
        role=UserRole.UNIVERSITY_ADMIN, university_id=other_uni.id, is_active=True,
    )
    async with svc_db.begin():
        svc_db.add(other_uni)
        svc_db.add(other_admin)

    with _patches(tmp_path):
        with pytest.raises(OwnershipViolationError):
            await certificate_revocation_service.initiate_revocation(
                cert_id=cert_id, reason="Wrong admin",
                current_user=other_admin, db=svc_db,
            )


@pytest.mark.asyncio
async def test_initiate_unconfirmed_raises(svc_db, tmp_path):
    """PENDING certificate raises UnconfirmedCertificateError on initiate."""
    university = University(
        id=uuid4(), name="Unconfirmed Test Uni", short_code="UCU", country="US",
        official_email="admin@ucu.edu",
        is_verified=True, verified_at=datetime.utcnow(),
        is_active=True, wallet_address=WALLET_ADDRESS,
    )
    admin = User(
        id=uuid4(), email="admin@ucu.edu", password_hash=hash_password("Pass123!"),
        first_name="Admin", last_name="UC",
        role=UserRole.UNIVERSITY_ADMIN, university_id=university.id, is_active=True,
    )
    student_user = User(
        id=uuid4(), email="student@ucu.edu", password_hash=hash_password("Pass123!"),
        first_name="Carl", last_name="Student", role=UserRole.STUDENT, is_active=True,
    )
    async with svc_db.begin():
        svc_db.add(university)
        svc_db.add(admin)
        svc_db.add(student_user)
    student_profile = Student(id=uuid4(), user_id=student_user.id)
    async with svc_db.begin():
        svc_db.add(student_profile)

    # Phase 1 issuance only — cert stays PENDING
    pdf = b"%PDF-1.4 pending " + b"p" * 150
    with _patches(tmp_path):
        result = await certificate_issuance_service.upload_and_hash_certificate(
            file_bytes=pdf, file_original_name="pending.pdf",
            metadata={
                "recipient_email": student_user.email,
                "degree_title": "Pending",
                "field_of_study": "Pending",
                "issue_date": date.today(),
            },
            current_user=admin, db=svc_db,
        )
    cert_id = result["certificate_id"]
    await svc_db.rollback()

    with _patches(tmp_path):
        with pytest.raises(UnconfirmedCertificateError):
            await certificate_revocation_service.initiate_revocation(
                cert_id=cert_id, reason="Cannot revoke PENDING",
                current_user=admin, db=svc_db,
            )


@pytest.mark.asyncio
async def test_initiate_already_revoked_raises(svc_db, confirmed_cert_setup, tmp_path):
    """Calling initiate_revocation on an already-revoked cert raises CertificateAlreadyRevokedError."""
    _, admin, _, cert_id = confirmed_cert_setup

    # Phase 1 revocation
    with _patches(tmp_path):
        await certificate_revocation_service.initiate_revocation(
            cert_id=cert_id, reason="First revocation",
            current_user=admin, db=svc_db,
        )
    await svc_db.rollback()

    # Phase 2 confirmation
    with _patches(tmp_path):
        await certificate_revocation_service.confirm_revocation(
            cert_id=cert_id, blockchain_tx_hash=TX_HASH_REVOKE,
            current_user=admin, db=svc_db,
            blockchain_service=_revocation_bc_mock(),
        )
    await svc_db.rollback()

    # Try Phase 1 again
    with _patches(tmp_path):
        with pytest.raises(CertificateAlreadyRevokedError):
            await certificate_revocation_service.initiate_revocation(
                cert_id=cert_id, reason="Second attempt",
                current_user=admin, db=svc_db,
            )


# ---------------------------------------------------------------------------
# Phase 2: confirm_revocation() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_confirm_success(svc_db, confirmed_cert_setup, tmp_path):
    """Full Phase 2 happy path: result has status=REVOKED."""
    _, admin, _, cert_id = confirmed_cert_setup

    with _patches(tmp_path):
        await certificate_revocation_service.initiate_revocation(
            cert_id=cert_id, reason="Confirmed revocation",
            current_user=admin, db=svc_db,
        )
    await svc_db.rollback()

    with _patches(tmp_path):
        result = await certificate_revocation_service.confirm_revocation(
            cert_id=cert_id, blockchain_tx_hash=TX_HASH_REVOKE,
            current_user=admin, db=svc_db,
            blockchain_service=_revocation_bc_mock(),
        )

    assert result["status"] == "REVOKED"
    assert str(result["certificate_id"]) == str(cert_id)
    assert result["revoked_at"] is not None


@pytest.mark.asyncio
async def test_confirm_cert_state_in_db(svc_db, confirmed_cert_setup, tmp_path):
    """After Phase 2, DB cert has is_active=False and blockchain_status=REVOKED."""
    _, admin, _, cert_id = confirmed_cert_setup

    with _patches(tmp_path):
        await certificate_revocation_service.initiate_revocation(
            cert_id=cert_id, reason="DB state check",
            current_user=admin, db=svc_db,
        )
    await svc_db.rollback()

    with _patches(tmp_path):
        await certificate_revocation_service.confirm_revocation(
            cert_id=cert_id, blockchain_tx_hash=TX_HASH_REVOKE,
            current_user=admin, db=svc_db,
            blockchain_service=_revocation_bc_mock(),
        )
    await svc_db.rollback()

    cert = await CertificateRepository.get_by_id(svc_db, cert_id)
    assert cert.is_active is False
    assert cert.blockchain_status == BlockchainStatus.REVOKED


@pytest.mark.asyncio
async def test_confirm_blockchain_tx_confirmed(svc_db, confirmed_cert_setup, tmp_path):
    """After Phase 2, REVOKE_HASH tx has status=CONFIRMED and tx_hash set."""
    _, admin, _, cert_id = confirmed_cert_setup

    with _patches(tmp_path):
        await certificate_revocation_service.initiate_revocation(
            cert_id=cert_id, reason="TX state check",
            current_user=admin, db=svc_db,
        )
    await svc_db.rollback()

    with _patches(tmp_path):
        await certificate_revocation_service.confirm_revocation(
            cert_id=cert_id, blockchain_tx_hash=TX_HASH_REVOKE,
            current_user=admin, db=svc_db,
            blockchain_service=_revocation_bc_mock(),
        )
    await svc_db.rollback()

    txs = await BlockchainTransactionRepository.get_by_certificate_id(svc_db, cert_id)
    revoke_tx = next(t for t in txs if t.tx_type == TransactionType.REVOKE_HASH)
    assert revoke_tx.status == TransactionStatus.CONFIRMED
    assert revoke_tx.tx_hash == TX_HASH_REVOKE


@pytest.mark.asyncio
async def test_confirm_tx_not_mined_returns_submitted(svc_db, confirmed_cert_setup, tmp_path):
    """When receipt is None (not mined), Phase 2 returns status=SUBMITTED."""
    _, admin, _, cert_id = confirmed_cert_setup

    with _patches(tmp_path):
        await certificate_revocation_service.initiate_revocation(
            cert_id=cert_id, reason="Not mined test",
            current_user=admin, db=svc_db,
        )
    await svc_db.rollback()

    with _patches(tmp_path):
        result = await certificate_revocation_service.confirm_revocation(
            cert_id=cert_id, blockchain_tx_hash=TX_HASH_REVOKE,
            current_user=admin, db=svc_db,
            blockchain_service=_revocation_bc_mock(receipt_none=True),
        )

    assert result["status"] == "SUBMITTED"


@pytest.mark.asyncio
async def test_confirm_tx_failed_raises(svc_db, confirmed_cert_setup, tmp_path):
    """When receipt.status==0, Phase 2 raises ServiceError."""
    _, admin, _, cert_id = confirmed_cert_setup

    with _patches(tmp_path):
        await certificate_revocation_service.initiate_revocation(
            cert_id=cert_id, reason="Failed tx test",
            current_user=admin, db=svc_db,
        )
    await svc_db.rollback()

    with _patches(tmp_path):
        with pytest.raises(ServiceError):
            await certificate_revocation_service.confirm_revocation(
                cert_id=cert_id, blockchain_tx_hash=TX_HASH_REVOKE,
                current_user=admin, db=svc_db,
                blockchain_service=_revocation_bc_mock(receipt_status=0),
            )


@pytest.mark.asyncio
async def test_revocation_reason_persisted(svc_db, confirmed_cert_setup, tmp_path):
    """
    REGRESSION for Defect #4: the original user-provided reason must be
    written to certificate.revocation_reason after Phase 2 confirms.

    Previously confirm_revocation() hardcoded 'Revocation confirmed on blockchain'.
    """
    _, admin, _, cert_id = confirmed_cert_setup
    original_reason = "Student plagiarized their dissertation"

    with _patches(tmp_path):
        await certificate_revocation_service.initiate_revocation(
            cert_id=cert_id, reason=original_reason,
            current_user=admin, db=svc_db,
        )
    await svc_db.rollback()

    with _patches(tmp_path):
        await certificate_revocation_service.confirm_revocation(
            cert_id=cert_id, blockchain_tx_hash=TX_HASH_REVOKE,
            current_user=admin, db=svc_db,
            blockchain_service=_revocation_bc_mock(),
        )
    await svc_db.rollback()

    cert = await CertificateRepository.get_by_id(svc_db, cert_id)
    assert cert.revocation_reason == original_reason, (
        f"Expected '{original_reason}', got '{cert.revocation_reason}'"
    )
