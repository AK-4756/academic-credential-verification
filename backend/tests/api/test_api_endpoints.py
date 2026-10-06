# backend/tests/api/test_api_endpoints.py
# P11b Part 2 — Backend API Endpoint Integration Tests
#
# Tests every live API endpoint using httpx.AsyncClient + ASGITransport.
# Uses the existing svc_db fixture for DB setup/teardown (per-test truncation).
# The api_client creates a SEPARATE fresh session factory for each request
# so production services can freely use `async with db.begin()` without
# conflicting with the svc_db session used for test setup.
#
# Endpoint inventory (32 API endpoints + 1 system = 33 routes):
#
# SYSTEM (1)      GET  /health
# AUTH (4)        POST /api/v1/auth/{register,login,refresh,logout}
# UNIVERSITIES (4) GET/PUT /api/v1/universities/...
# CERTIFICATES (6) GET/POST /api/v1/certificates/...
# STUDENT (5)     GET/POST /api/v1/student/credentials/...
# EMPLOYER (5)    GET/PUT  /api/v1/employer/...
# VERIFICATION (3) POST/GET /api/v1/verify/...
# QR (2)          POST/GET /api/v1/qr/...
# LOGS (2)        GET /api/v1/logs/...

from __future__ import annotations

import hashlib
import io
import os
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.constants import BlockchainStatus, TransactionStatus, TransactionType, UserRole
from core.security import create_access_token, hash_password
from models.blockchain_transaction_model import BlockchainTransaction
from models.certificate_model import Certificate
from models.employer_model import Employer
from models.qr_verification_model import QRVerification
from models.student_model import Student
from models.university_model import University
from models.user_model import User

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE_PDF_PATH = BACKEND_DIR / "tests" / "fixtures" / "sample.pdf"
SAMPLE_PDF = SAMPLE_PDF_PATH.read_bytes()
SAMPLE_HASH = hashlib.sha256(SAMPLE_PDF).hexdigest()

VALID_WALLET = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
FAKE_TX_HASH = "0x" + "ab" * 32


# ---------------------------------------------------------------------------
# JWT helper — creates a real token for a User model object
# ---------------------------------------------------------------------------

def _auth(user: User) -> dict:
    token = create_access_token(
        subject=str(user.id),
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        university_id=str(user.university_id) if user.university_id else None,
        email=user.email,
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Mock blockchain service (all methods synchronous per BlockchainService impl)
# ---------------------------------------------------------------------------

def _mock_blockchain():
    m = MagicMock()
    m.is_connected.return_value = True
    m.is_authorized_issuer.return_value = True
    m.get_certificate_count.return_value = 0
    m.verify_certificate.return_value = MagicMock(
        is_valid=True, status="ACTIVE", cert_uid="CERT-001"
    )
    m.get_certificate_record.return_value = MagicMock(
        certificate_hash=SAMPLE_HASH,
        issuing_university=VALID_WALLET,
        status="ACTIVE",
        exists=True,
        issued_at=datetime.now(timezone.utc),
        revoked_at=None,
    )
    m.get_transaction_receipt.return_value = MagicMock(
        tx_hash=FAKE_TX_HASH, status=1, block_number=10,
        block_hash="0x" + "cd" * 32, gas_used=50000, effective_gas_price=1_000_000_000,
    )
    return m


# ---------------------------------------------------------------------------
# api_client fixture — uses a SEPARATE session factory from svc_db
#
# Design:
#   - svc_db  → used by test setup helpers to commit seed data + truncation teardown
#   - api_engine → creates fresh AsyncSession per request (mimics production)
#   This avoids the "transaction already begun" conflict when services call
#   `async with db.begin()` inside an endpoint.
# ---------------------------------------------------------------------------

def _get_test_db_url() -> str:
    """Get the test database URL (same as root conftest computes)."""
    from tests.conftest import TEST_DATABASE_URL
    url = str(TEST_DATABASE_URL)
    # Ensure asyncpg driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return url



@pytest_asyncio.fixture
async def api_client(svc_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient bound to the real FastAPI app with:
    - get_db overridden to a fresh AsyncSession per request (separate from svc_db)
    - BlockchainService mocked (blockchain tests are in test_blockchain_integration.py)
    """
    from main import app
    from dependencies.services import get_blockchain_service
    from dependencies.database import get_db

    db_url = _get_test_db_url()
    api_engine = create_async_engine(db_url, pool_size=2, max_overflow=0, echo=False)
    mock_bc = _mock_blockchain()

    async def _fresh_db():
        async with AsyncSession(api_engine, expire_on_commit=False, autobegin=True) as session:
            yield session

    app.dependency_overrides[get_db] = _fresh_db
    app.dependency_overrides[get_blockchain_service] = lambda: mock_bc

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await api_engine.dispose()
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# DB setup helpers — all commit via svc_db so data is visible to fresh sessions
#
# IMPORTANT: verified_at uses naive datetime.utcnow() because the University
# model's `verified_at` column does NOT declare timezone=True (plain DateTime).
# The TimestampMixin created_at/updated_at use server-side NOW() which is fine.
# ---------------------------------------------------------------------------

async def _make_university(db: AsyncSession, short_code: str = "TSTU") -> University:
    u = University(
        id=uuid4(), name=f"Test University {short_code}", short_code=short_code,
        country="US", official_email=f"admin@{short_code.lower()}.edu",
        is_verified=True,
        verified_at=datetime.utcnow(),   # naive — column has no timezone=True
        is_active=True, wallet_address=VALID_WALLET,
    )
    async with db.begin():
        db.add(u)
    return u


async def _make_admin(db: AsyncSession, uni: University, email: str) -> User:
    u = User(
        id=uuid4(), email=email, password_hash=hash_password("Pass123!"),
        first_name="Admin", last_name="User",
        role=UserRole.UNIVERSITY_ADMIN, university_id=uni.id, is_active=True,
    )
    async with db.begin():
        db.add(u)
    return u


async def _make_student_user(db: AsyncSession, email: str) -> tuple[User, Student]:
    u = User(
        id=uuid4(), email=email, password_hash=hash_password("Pass123!"),
        first_name="Stu", last_name="Dent", role=UserRole.STUDENT, is_active=True,
    )
    s = Student(id=uuid4(), user_id=u.id)
    async with db.begin():
        db.add(u)
        db.add(s)
    return u, s


async def _make_employer_user(db: AsyncSession, email: str) -> tuple[User, Employer]:
    u = User(
        id=uuid4(), email=email, password_hash=hash_password("Pass123!"),
        first_name="Emp", last_name="Loyer", role=UserRole.EMPLOYER, is_active=True,
    )
    e = Employer(id=uuid4(), user_id=u.id, company_name="Corp Ltd")
    async with db.begin():
        db.add(u)
        db.add(e)
    return u, e


async def _make_confirmed_cert(
    db: AsyncSession, uni: University, student: Student
) -> tuple[Certificate, BlockchainTransaction]:
    cert = Certificate(
        id=uuid4(),
        certificate_uid=f"CERT-{uuid4().hex[:8].upper()}",
        university_id=uni.id,
        student_id=student.id,
        recipient_email=f"recipient-{uuid4().hex[:6]}@test.edu",
        degree_title="BSc Computer Science",
        field_of_study="Computing",
        issue_date=date(2024, 6, 1),
        certificate_hash=SAMPLE_HASH,
        file_path="uploads/test.pdf",
        blockchain_status=BlockchainStatus.CONFIRMED,
        is_active=True,
    )
    tx = BlockchainTransaction(
        id=uuid4(),
        certificate_id=cert.id,
        transaction_type=TransactionType.STORE_HASH,
        transaction_status=TransactionStatus.CONFIRMED,
        blockchain_tx_hash=FAKE_TX_HASH,
        block_number=5,
        gas_used=80000,
    )
    async with db.begin():
        db.add(cert)
        db.add(tx)
    return cert, tx


async def _make_pending_cert(
    db: AsyncSession, uni: University, student: Student
) -> Certificate:
    cert = Certificate(
        id=uuid4(),
        certificate_uid=f"PEND-{uuid4().hex[:8].upper()}",
        university_id=uni.id,
        student_id=student.id,
        recipient_email=f"pending-{uuid4().hex[:6]}@test.edu",
        degree_title="BSc Pending",
        field_of_study="Computing",
        issue_date=date(2024, 6, 1),
        certificate_hash=SAMPLE_HASH,
        file_path="uploads/pending.pdf",
        blockchain_status=BlockchainStatus.PENDING,
        is_active=True,
    )
    tx = BlockchainTransaction(
        id=uuid4(),
        certificate_id=cert.id,
        transaction_type=TransactionType.STORE_HASH,
        transaction_status=TransactionStatus.SUBMITTED,
    )
    async with db.begin():
        db.add(cert)
        db.add(tx)
    return cert


# ===========================================================================
# SYSTEM
# ===========================================================================

@pytest.mark.api
class TestSystemEndpoints:

    async def test_health_check(self, api_client):
        """GET /health → 200 {"status": "ok"}"""
        r = await api_client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ===========================================================================
# AUTH
# ===========================================================================

@pytest.mark.api
class TestAuthEndpoints:

    async def test_register_student_success(self, api_client):
        """POST /api/v1/auth/register → 201, student registered."""
        r = await api_client.post("/api/v1/auth/register", json={
            "email": f"newstudent-{uuid4().hex[:6]}@test.edu",
            "password": "SecurePass1!",
            "first_name": "New", "last_name": "Student", "role": "STUDENT",
        })
        assert r.status_code == 201
        assert r.json()["success"] is True

    async def test_register_employer_success(self, api_client):
        """POST /api/v1/auth/register → 201, employer registered."""
        r = await api_client.post("/api/v1/auth/register", json={
            "email": f"newemp-{uuid4().hex[:6]}@corp.com",
            "password": "SecurePass1!", "first_name": "Emp", "last_name": "Loyer",
            "role": "EMPLOYER", "company_name": "Corp Ltd",
        })
        assert r.status_code == 201

    async def test_register_duplicate_email_returns_409(self, api_client):
        """POST /api/v1/auth/register duplicate → 409."""
        email = f"dup-{uuid4().hex[:6]}@test.edu"
        payload = {"email": email, "password": "SecurePass1!", "first_name": "A",
                   "last_name": "B", "role": "STUDENT"}
        await api_client.post("/api/v1/auth/register", json=payload)
        r = await api_client.post("/api/v1/auth/register", json=payload)
        assert r.status_code == 409

    async def test_register_missing_field_returns_422(self, api_client):
        """POST /api/v1/auth/register missing password → 422."""
        r = await api_client.post("/api/v1/auth/register", json={
            "email": "x@test.edu", "first_name": "A", "last_name": "B", "role": "STUDENT"
        })
        assert r.status_code == 422

    async def test_login_success(self, api_client, svc_db):
        """POST /api/v1/auth/login → 200, access_token returned."""
        uni = await _make_university(svc_db, "LGN1")
        await _make_admin(svc_db, uni, f"lgnadmin-{uuid4().hex[:4]}@test.edu")
        # Re-query email since we need the exact one
        from repositories import UserRepository
        # We know the email from the fixture helper — use it
        email = f"lgnadmin-"  # need to capture from helper

        # Simpler approach: register via API then login
        email = f"logintest-{uuid4().hex[:6]}@test.edu"
        reg = await api_client.post("/api/v1/auth/register", json={
            "email": email, "password": "Pass123!", "first_name": "L",
            "last_name": "G", "role": "STUDENT",
        })
        assert reg.status_code == 201

        r = await api_client.post("/api/v1/auth/login", json={
            "email": email, "password": "Pass123!",
        })
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(self, api_client):
        """POST /api/v1/auth/login wrong password → 401."""
        email = f"wrongpass-{uuid4().hex[:6]}@test.edu"
        await api_client.post("/api/v1/auth/register", json={
            "email": email, "password": "Pass123!", "first_name": "A",
            "last_name": "B", "role": "STUDENT",
        })
        r = await api_client.post("/api/v1/auth/login", json={
            "email": email, "password": "WrongPass!",
        })
        assert r.status_code == 401

    async def test_login_nonexistent_user_returns_401(self, api_client):
        """POST /api/v1/auth/login unknown email → 401."""
        r = await api_client.post("/api/v1/auth/login", json={
            "email": f"nobody-{uuid4().hex}@test.edu", "password": "Pass123!",
        })
        assert r.status_code == 401

    async def test_refresh_without_cookie_returns_401(self, api_client):
        """POST /api/v1/auth/refresh no cookie → 401."""
        r = await api_client.post("/api/v1/auth/refresh")
        assert r.status_code == 401

    async def test_refresh_with_valid_token_succeeds(self, api_client):
        """POST /api/v1/auth/refresh valid cookie → 200 new token."""
        email = f"refresh-{uuid4().hex[:6]}@test.edu"
        await api_client.post("/api/v1/auth/register", json={
            "email": email, "password": "Pass123!", "first_name": "R",
            "last_name": "F", "role": "STUDENT",
        })
        login_r = await api_client.post("/api/v1/auth/login", json={
            "email": email, "password": "Pass123!",
        })
        assert login_r.status_code == 200
        # httpx client carries cookies automatically
        refresh_r = await api_client.post("/api/v1/auth/refresh")
        assert refresh_r.status_code == 200
        assert "access_token" in refresh_r.json()

    async def test_logout_success(self, api_client, svc_db):
        """POST /api/v1/auth/logout → 200 with auth."""
        email = f"logout-{uuid4().hex[:6]}@test.edu"
        await api_client.post("/api/v1/auth/register", json={
            "email": email, "password": "Pass123!", "first_name": "L",
            "last_name": "O", "role": "STUDENT",
        })
        login_r = await api_client.post("/api/v1/auth/login", json={
            "email": email, "password": "Pass123!",
        })
        access_token = login_r.json()["access_token"]
        r = await api_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert r.status_code == 200

    async def test_logout_without_auth_returns_401(self, api_client):
        """POST /api/v1/auth/logout no auth → 401."""
        r = await api_client.post("/api/v1/auth/logout")
        assert r.status_code == 401


# ===========================================================================
# UNIVERSITIES
# ===========================================================================

@pytest.mark.api
class TestUniversityEndpoints:

    async def test_list_universities_as_admin(self, api_client, svc_db):
        """GET /api/v1/universities/ → 200 paginated list."""
        uni = await _make_university(svc_db, "LISTU")
        admin = await _make_admin(svc_db, uni, f"listadmin-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/universities/", headers=_auth(admin))
        assert r.status_code == 200
        body = r.json()
        assert "data" in body
        assert "items" in body["data"]

    async def test_list_universities_without_auth_returns_401(self, api_client):
        """GET /api/v1/universities/ no auth → 401."""
        r = await api_client.get("/api/v1/universities/")
        assert r.status_code == 401

    async def test_get_university_by_id(self, api_client, svc_db):
        """GET /api/v1/universities/{id} → 200 detail."""
        uni = await _make_university(svc_db, "GETU")
        admin = await _make_admin(svc_db, uni, f"getadmin-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get(f"/api/v1/universities/{uni.id}", headers=_auth(admin))
        assert r.status_code == 200
        assert r.json()["data"]["id"] == str(uni.id)

    async def test_get_university_nonexistent_returns_404(self, api_client, svc_db):
        """GET /api/v1/universities/{random} → 404."""
        uni = await _make_university(svc_db, "GETU2")
        admin = await _make_admin(svc_db, uni, f"getadmin2-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get(f"/api/v1/universities/{uuid4()}", headers=_auth(admin))
        assert r.status_code == 404

    async def test_update_wallet_address(self, api_client, svc_db):
        """PUT /api/v1/universities/{id}/wallet → 200 updated."""
        uni = await _make_university(svc_db, "WALU")
        admin = await _make_admin(svc_db, uni, f"waladmin-{uuid4().hex[:4]}@test.edu")
        new_wallet = "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
        r = await api_client.put(
            f"/api/v1/universities/{uni.id}/wallet",
            json={"wallet_address": new_wallet},
            headers=_auth(admin),
        )
        assert r.status_code == 200
        assert r.json()["data"]["wallet_address"] == new_wallet

    async def test_update_wallet_wrong_university_returns_403(self, api_client, svc_db):
        """PUT /api/v1/universities/{other}/wallet → 403 ownership violation."""
        uni1 = await _make_university(svc_db, "WAL1")
        uni2 = await _make_university(svc_db, "WAL2")
        admin1 = await _make_admin(svc_db, uni1, f"waladmin3-{uuid4().hex[:4]}@test.edu")
        r = await api_client.put(
            f"/api/v1/universities/{uni2.id}/wallet",
            json={"wallet_address": "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"},
            headers=_auth(admin1),
        )
        assert r.status_code == 403

    async def test_get_university_dashboard(self, api_client, svc_db):
        """GET /api/v1/universities/{id}/dashboard → 200."""
        uni = await _make_university(svc_db, "DASHU")
        admin = await _make_admin(svc_db, uni, f"dashadmin-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get(
            f"/api/v1/universities/{uni.id}/dashboard",
            headers=_auth(admin),
        )
        assert r.status_code == 200


# ===========================================================================
# CERTIFICATES
# ===========================================================================

@pytest.mark.api
class TestCertificateEndpoints:

    async def test_upload_certificate_success(self, api_client, svc_db, tmp_path):
        """POST /api/v1/certificates/upload → 201 PENDING certificate."""
        uni = await _make_university(svc_db, "UPCRT")
        admin = await _make_admin(svc_db, uni, f"upadmin-{uuid4().hex[:4]}@test.edu")
        await _make_student_user(svc_db, f"upstudent-{uuid4().hex[:4]}@test.edu")

        with patch("core.config.settings.UPLOAD_ROOT", str(tmp_path)), \
             patch("core.config.settings.CONTRACT_ADDRESS", "0x" + "aa" * 20):
            r = await api_client.post(
                "/api/v1/certificates/upload",
                files={"file": ("cert.pdf", io.BytesIO(SAMPLE_PDF), "application/pdf")},
                data={
                    "recipient_email": f"upstudent-{uuid4().hex[:4]}@test.edu",
                    "degree_title": "BSc CS", "field_of_study": "Computing",
                    "issue_date": "2024-06-01",
                },
                headers=_auth(admin),
            )
        assert r.status_code == 201
        body = r.json()
        assert body["success"] is True
        assert "certificate_id" in body["data"]
        assert body["data"]["certificate_hash"] == SAMPLE_HASH

    async def test_upload_certificate_wrong_mime_returns_400(self, api_client, svc_db):
        """POST /api/v1/certificates/upload non-PDF → 400 (InvalidFileTypeError)."""
        uni = await _make_university(svc_db, "MIMEUP")
        admin = await _make_admin(svc_db, uni, f"mimeadmin-{uuid4().hex[:4]}@test.edu")
        r = await api_client.post(
            "/api/v1/certificates/upload",
            files={"file": ("doc.txt", io.BytesIO(b"not a pdf"), "text/plain")},
            data={
                "recipient_email": "x@test.edu", "degree_title": "BSc",
                "field_of_study": "X", "issue_date": "2024-06-01",
            },
            headers=_auth(admin),
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_FILE_TYPE"

    async def test_upload_certificate_without_auth_returns_401(self, api_client):
        """POST /api/v1/certificates/upload no auth → 401."""
        r = await api_client.post(
            "/api/v1/certificates/upload",
            files={"file": ("cert.pdf", io.BytesIO(SAMPLE_PDF), "application/pdf")},
            data={"recipient_email": "x@test.edu", "degree_title": "BSc",
                  "field_of_study": "X", "issue_date": "2024-06-01"},
        )
        assert r.status_code == 401

    async def test_list_certificates_returns_paginated(self, api_client, svc_db):
        """GET /api/v1/certificates/ → 200 paginated."""
        uni = await _make_university(svc_db, "LSTC")
        admin = await _make_admin(svc_db, uni, f"lstadmin-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/certificates/", headers=_auth(admin))
        assert r.status_code == 200
        body = r.json()
        assert "items" in body["data"]
        assert "pagination" in body["data"]

    async def test_list_certificates_wrong_role_returns_403(self, api_client, svc_db):
        """GET /api/v1/certificates/ as employer → 403."""
        emp_user, _ = await _make_employer_user(svc_db, f"listcemp-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/certificates/", headers=_auth(emp_user))
        assert r.status_code == 403

    async def test_get_certificate_detail_as_admin(self, api_client, svc_db):
        """GET /api/v1/certificates/{id} as admin → 200."""
        uni = await _make_university(svc_db, "DETC")
        admin = await _make_admin(svc_db, uni, f"detadmin-{uuid4().hex[:4]}@test.edu")
        _, student = await _make_student_user(svc_db, f"detstudent-{uuid4().hex[:4]}@test.edu")
        cert, _ = await _make_confirmed_cert(svc_db, uni, student)
        r = await api_client.get(f"/api/v1/certificates/{cert.id}", headers=_auth(admin))
        assert r.status_code == 200
        assert r.json()["data"]["id"] == str(cert.id)

    async def test_get_certificate_nonexistent_returns_404(self, api_client, svc_db):
        """GET /api/v1/certificates/{random} → 404."""
        uni = await _make_university(svc_db, "NOEXI")
        admin = await _make_admin(svc_db, uni, f"noexiadmin-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get(f"/api/v1/certificates/{uuid4()}", headers=_auth(admin))
        assert r.status_code == 404

    async def test_get_certificate_another_university_returns_403(self, api_client, svc_db):
        """GET /api/v1/certificates/{id} by wrong university → 403."""
        uni1 = await _make_university(svc_db, "UNI1C")
        uni2 = await _make_university(svc_db, "UNI2C")
        admin2 = await _make_admin(svc_db, uni2, f"admin2cert-{uuid4().hex[:4]}@test.edu")
        _, student = await _make_student_user(svc_db, f"crossstudent-{uuid4().hex[:4]}@test.edu")
        cert, _ = await _make_confirmed_cert(svc_db, uni1, student)
        r = await api_client.get(f"/api/v1/certificates/{cert.id}", headers=_auth(admin2))
        assert r.status_code == 403

    async def test_revoke_certificate_pending_returns_409(self, api_client, svc_db):
        """POST /api/v1/certificates/{id}/revoke on PENDING cert → 409."""
        uni = await _make_university(svc_db, "REVP")
        admin = await _make_admin(svc_db, uni, f"revpadmin-{uuid4().hex[:4]}@test.edu")
        _, student = await _make_student_user(svc_db, f"revpstudent-{uuid4().hex[:4]}@test.edu")
        cert = await _make_pending_cert(svc_db, uni, student)
        r = await api_client.post(
            f"/api/v1/certificates/{cert.id}/revoke",
            json={"reason": "Testing"},
            headers=_auth(admin),
        )
        assert r.status_code == 409

    async def test_revoke_certificate_confirmed_returns_200(self, api_client, svc_db):
        """POST /api/v1/certificates/{id}/revoke on CONFIRMED cert → 200."""
        uni = await _make_university(svc_db, "REVC")
        admin = await _make_admin(svc_db, uni, f"revcadmin-{uuid4().hex[:4]}@test.edu")
        _, student = await _make_student_user(svc_db, f"revcstudent-{uuid4().hex[:4]}@test.edu")
        cert, _ = await _make_confirmed_cert(svc_db, uni, student)
        r = await api_client.post(
            f"/api/v1/certificates/{cert.id}/revoke",
            json={"reason": "Fraud detected"},
            headers=_auth(admin),
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    async def test_confirm_revocation_returns_200(self, api_client, svc_db):
        """POST /api/v1/certificates/{id}/confirm-revocation → 200."""
        uni = await _make_university(svc_db, "CONRV")
        admin = await _make_admin(svc_db, uni, f"conrvadmin-{uuid4().hex[:4]}@test.edu")
        _, student = await _make_student_user(svc_db, f"conrvstudent-{uuid4().hex[:4]}@test.edu")
        cert, _ = await _make_confirmed_cert(svc_db, uni, student)

        r1 = await api_client.post(
            f"/api/v1/certificates/{cert.id}/revoke",
            json={"reason": "Testing"},
            headers=_auth(admin),
        )
        assert r1.status_code == 200

        r2 = await api_client.post(
            f"/api/v1/certificates/{cert.id}/confirm-revocation",
            json={"blockchain_tx_hash": FAKE_TX_HASH},
            headers=_auth(admin),
        )
        assert r2.status_code == 200
        assert r2.json()["data"]["is_active"] is False

    async def test_confirm_hash_without_auth_returns_401(self, api_client):
        """POST /api/v1/certificates/confirm-hash no auth → 401."""
        r = await api_client.post("/api/v1/certificates/confirm-hash", json={
            "certificate_id": str(uuid4()), "blockchain_tx_hash": FAKE_TX_HASH,
        })
        assert r.status_code == 401


# ===========================================================================
# STUDENT
# ===========================================================================

@pytest.mark.api
class TestStudentEndpoints:

    async def test_list_credentials_returns_empty(self, api_client, svc_db):
        """GET /api/v1/student/credentials → 200 empty for new student."""
        stu_user, _ = await _make_student_user(svc_db, f"liststu-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/student/credentials", headers=_auth(stu_user))
        assert r.status_code == 200
        assert r.json()["data"]["items"] == []

    async def test_list_credentials_wrong_role_returns_403(self, api_client, svc_db):
        """GET /api/v1/student/credentials as employer → 403."""
        emp_user, _ = await _make_employer_user(svc_db, f"emplist-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/student/credentials", headers=_auth(emp_user))
        assert r.status_code == 403

    async def test_get_credential_detail_success(self, api_client, svc_db):
        """GET /api/v1/student/credentials/{id} → 200 owned cert."""
        uni = await _make_university(svc_db, "STDC")
        stu_user, student = await _make_student_user(svc_db, f"stdcstu-{uuid4().hex[:4]}@test.edu")
        cert, _ = await _make_confirmed_cert(svc_db, uni, student)
        r = await api_client.get(
            f"/api/v1/student/credentials/{cert.id}", headers=_auth(stu_user)
        )
        assert r.status_code == 200

    async def test_get_credential_wrong_student_returns_403(self, api_client, svc_db):
        """GET /api/v1/student/credentials/{id} by wrong student → 403."""
        uni = await _make_university(svc_db, "STDO")
        _, student_owner = await _make_student_user(svc_db, f"owner-{uuid4().hex[:4]}@test.edu")
        stu_other, _ = await _make_student_user(svc_db, f"other-{uuid4().hex[:4]}@test.edu")
        cert, _ = await _make_confirmed_cert(svc_db, uni, student_owner)
        r = await api_client.get(
            f"/api/v1/student/credentials/{cert.id}", headers=_auth(stu_other)
        )
        assert r.status_code == 403

    async def test_download_credential_not_confirmed_returns_409(self, api_client, svc_db):
        """GET /api/v1/student/credentials/{id}/download PENDING → 409."""
        uni = await _make_university(svc_db, "DLPND")
        stu_user, student = await _make_student_user(svc_db, f"dlpstu-{uuid4().hex[:4]}@test.edu")
        cert = await _make_pending_cert(svc_db, uni, student)
        r = await api_client.get(
            f"/api/v1/student/credentials/{cert.id}/download", headers=_auth(stu_user)
        )
        assert r.status_code == 409

    async def test_share_credential_returns_share_link(self, api_client, svc_db):
        """POST /api/v1/student/credentials/{id}/share → 200 with verification_url."""
        uni = await _make_university(svc_db, "SHRU")
        stu_user, student = await _make_student_user(svc_db, f"shrstu-{uuid4().hex[:4]}@test.edu")
        cert, _ = await _make_confirmed_cert(svc_db, uni, student)
        r = await api_client.post(
            f"/api/v1/student/credentials/{cert.id}/share", headers=_auth(stu_user)
        )
        assert r.status_code == 200
        assert "verification_url" in r.json()["data"]

    async def test_student_dashboard_returns_200(self, api_client, svc_db):
        """GET /api/v1/student/dashboard → 200."""
        stu_user, _ = await _make_student_user(svc_db, f"dashstu-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/student/dashboard", headers=_auth(stu_user))
        assert r.status_code == 200


# ===========================================================================
# EMPLOYER
# ===========================================================================

@pytest.mark.api
class TestEmployerEndpoints:

    async def test_get_employer_profile(self, api_client, svc_db):
        """GET /api/v1/employer/profile → 200."""
        emp_user, _ = await _make_employer_user(svc_db, f"proemp-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/employer/profile", headers=_auth(emp_user))
        assert r.status_code == 200
        assert r.json()["data"]["company_name"] == "Corp Ltd"

    async def test_get_employer_profile_wrong_role_returns_403(self, api_client, svc_db):
        """GET /api/v1/employer/profile as student → 403."""
        stu_user, _ = await _make_student_user(svc_db, f"profstu-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/employer/profile", headers=_auth(stu_user))
        assert r.status_code == 403

    async def test_update_employer_profile(self, api_client, svc_db):
        """PUT /api/v1/employer/profile → 200 updated."""
        emp_user, _ = await _make_employer_user(svc_db, f"updemp-{uuid4().hex[:4]}@test.edu")
        r = await api_client.put(
            "/api/v1/employer/profile",
            json={"company_name": "Updated Corp"},
            headers=_auth(emp_user),
        )
        assert r.status_code == 200
        assert r.json()["data"]["company_name"] == "Updated Corp"

    async def test_employer_dashboard_returns_200(self, api_client, svc_db):
        """GET /api/v1/employer/dashboard → 200."""
        emp_user, _ = await _make_employer_user(svc_db, f"dashemp-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/employer/dashboard", headers=_auth(emp_user))
        assert r.status_code == 200

    async def test_employer_verifications_list_empty(self, api_client, svc_db):
        """GET /api/v1/employer/verifications → 200 empty list."""
        emp_user, _ = await _make_employer_user(svc_db, f"listemp-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/employer/verifications", headers=_auth(emp_user))
        assert r.status_code == 200
        assert r.json()["data"]["items"] == []

    async def test_employer_verification_detail_not_found(self, api_client, svc_db):
        """GET /api/v1/employer/verifications/{id} nonexistent → 404."""
        emp_user, _ = await _make_employer_user(svc_db, f"detemp-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get(
            f"/api/v1/employer/verifications/{uuid4()}", headers=_auth(emp_user)
        )
        assert r.status_code == 404


# ===========================================================================
# VERIFICATION
# ===========================================================================

@pytest.mark.api
class TestVerificationEndpoints:

    async def test_verify_by_upload_success(self, api_client, svc_db):
        """POST /api/v1/verify/upload → 200 verification result."""
        emp_user, _ = await _make_employer_user(svc_db, f"vryemp-{uuid4().hex[:4]}@test.edu")
        r = await api_client.post(
            "/api/v1/verify/upload",
            files={"file": ("cert.pdf", io.BytesIO(SAMPLE_PDF), "application/pdf")},
            headers=_auth(emp_user),
        )
        assert r.status_code == 200
        assert "result" in r.json()["data"]

    async def test_verify_by_upload_wrong_mime_returns_400(self, api_client, svc_db):
        """POST /api/v1/verify/upload non-PDF → 400 (InvalidFileTypeError)."""
        emp_user, _ = await _make_employer_user(svc_db, f"mimevrfy-{uuid4().hex[:4]}@test.edu")
        r = await api_client.post(
            "/api/v1/verify/upload",
            files={"file": ("doc.txt", io.BytesIO(b"not a pdf"), "text/plain")},
            headers=_auth(emp_user),
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_FILE_TYPE"

    async def test_verify_by_upload_no_auth_returns_401(self, api_client):
        """POST /api/v1/verify/upload no auth → 401."""
        r = await api_client.post(
            "/api/v1/verify/upload",
            files={"file": ("cert.pdf", io.BytesIO(SAMPLE_PDF), "application/pdf")},
        )
        assert r.status_code == 401

    async def test_verify_by_qr_invalid_token_returns_not_found_result(self, api_client):
        """GET /api/v1/verify/qr/{token} invalid token → 200 with result=NOT_FOUND."""
        r = await api_client.get("/api/v1/verify/qr/nonexistent-token-abc123")
        assert r.status_code == 200
        # The service returns a NOT_FOUND result (not a 404 HTTP error)
        assert r.json()["result"] == "NOT_FOUND"

    async def test_verify_result_by_id_not_found(self, api_client, svc_db):
        """GET /api/v1/verify/result/{id} nonexistent → 404."""
        emp_user, _ = await _make_employer_user(svc_db, f"resemp-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get(
            f"/api/v1/verify/result/{uuid4()}", headers=_auth(emp_user)
        )
        assert r.status_code == 404

    async def test_verify_result_by_id_wrong_role_returns_403(self, api_client, svc_db):
        """GET /api/v1/verify/result/{id} as student → 403."""
        stu_user, _ = await _make_student_user(svc_db, f"resstu-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get(
            f"/api/v1/verify/result/{uuid4()}", headers=_auth(stu_user)
        )
        assert r.status_code == 403


# ===========================================================================
# QR
# ===========================================================================

@pytest.mark.api
class TestQREndpoints:

    async def test_generate_qr_for_confirmed_cert(self, api_client, svc_db, tmp_path):
        """POST /api/v1/qr/generate/{id} → 200 with token and qr_image_url."""
        uni = await _make_university(svc_db, "QRGNU")
        admin = await _make_admin(svc_db, uni, f"qrgenmin-{uuid4().hex[:4]}@test.edu")
        _, student = await _make_student_user(svc_db, f"qrgstu-{uuid4().hex[:4]}@test.edu")
        cert, _ = await _make_confirmed_cert(svc_db, uni, student)

        with patch("utils.qr_image_generator.save_qr_image_for_token"):
            r = await api_client.post(
                f"/api/v1/qr/generate/{cert.id}", headers=_auth(admin)
            )
        assert r.status_code == 200
        body = r.json()
        assert "token" in body["data"]
        assert "verification_url" in body["data"]

    async def test_generate_qr_no_auth_returns_401(self, api_client):
        """POST /api/v1/qr/generate/{id} no auth → 401."""
        r = await api_client.post(f"/api/v1/qr/generate/{uuid4()}")
        assert r.status_code == 401

    async def test_get_qr_image_nonexistent_token_returns_404(self, api_client):
        """GET /api/v1/qr/{token}/image nonexistent token → 404."""
        r = await api_client.get("/api/v1/qr/nonexistent-token-xyz/image")
        assert r.status_code == 404


# ===========================================================================
# LOGS
# ===========================================================================

@pytest.mark.api
class TestLogEndpoints:

    async def test_list_logs_as_admin_returns_200(self, api_client, svc_db):
        """GET /api/v1/logs/ → 200."""
        uni = await _make_university(svc_db, "LOGLST")
        admin = await _make_admin(svc_db, uni, f"loglistadmin-{uuid4().hex[:4]}@test.edu")
        r = await api_client.get("/api/v1/logs/", headers=_auth(admin))
        assert r.status_code == 200

    async def test_list_logs_no_auth_returns_401(self, api_client):
        """GET /api/v1/logs/ no auth → 401."""
        r = await api_client.get("/api/v1/logs/")
        assert r.status_code == 401

    async def test_get_logs_for_certificate(self, api_client, svc_db):
        """GET /api/v1/logs/{certificate_id} → 200."""
        uni = await _make_university(svc_db, "LOGDET")
        admin = await _make_admin(svc_db, uni, f"logdetadmin-{uuid4().hex[:4]}@test.edu")
        _, student = await _make_student_user(svc_db, f"logdetstu-{uuid4().hex[:4]}@test.edu")
        cert, _ = await _make_confirmed_cert(svc_db, uni, student)
        r = await api_client.get(f"/api/v1/logs/{cert.id}", headers=_auth(admin))
        assert r.status_code == 200
