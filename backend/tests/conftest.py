# backend/tests/conftest.py
# Root conftest.py for the backend test suite.
#
# Provides fixtures for:
#   - Test database engine and sessions (PostgreSQL credential_db_test)
#   - FastAPI app with dependency overrides
#   - httpx.AsyncClient with ASGITransport
#   - Test users (super_admin, university_admin, student, employer)
#   - JWT auth headers for each role
#   - Mock BlockchainService
#   - PDF file fixtures and known hashes

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import os
import sys
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Ensure backend/ is on sys.path so imports resolve correctly
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Set environment before importing app modules
os.environ.setdefault("ENVIRONMENT", "development")

from core.config import settings
from core.constants import UserRole
from core.security import create_access_token, hash_password
from dependencies.database import get_db
from models.employer_model import Employer
from models.student_model import Student
from models.university_model import University
from models.user_model import User

# ---------------------------------------------------------------------------
# RSA keypair for test JWT tokens
# ---------------------------------------------------------------------------
# Generate a test-only RSA keypair at import time. This avoids depending on
# production keys or .env files.  We override settings so that
# core.security.create_access_token / verify_token use these keys.

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_test_private_key_obj = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
TEST_JWT_PRIVATE_KEY = _test_private_key_obj.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode("utf-8")

TEST_JWT_PUBLIC_KEY = (
    _test_private_key_obj.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode("utf-8")
)

# Patch settings so create_access_token / verify_token use the test keypair
settings.JWT_PRIVATE_KEY = TEST_JWT_PRIVATE_KEY
settings.JWT_PUBLIC_KEY = TEST_JWT_PUBLIC_KEY

# ---------------------------------------------------------------------------
# Test database URL
# ---------------------------------------------------------------------------
# Derive from the production DATABASE_URL by replacing the database name.

_prod_url = settings.DATABASE_URL
if "/credential_db" in _prod_url:
    TEST_DATABASE_URL = _prod_url.replace("/credential_db", "/credential_db_test")
else:
    # Fallback: append _test
    TEST_DATABASE_URL = _prod_url.rstrip("/") + "_test"


# ---------------------------------------------------------------------------
# Fixtures directory
# ---------------------------------------------------------------------------
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# ═══════════════════════════════════════════════════════════════════════════════
#  Session-scoped fixtures (run once per test session)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session", autouse=True)
def _run_migrations():
    """Run Alembic migrations once per test session (sync fixture, no loop issues)."""
    import subprocess

    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    subprocess.run(
        [
            sys.executable, "-m", "alembic",
            "-c", str(BACKEND_DIR / "alembic" / "alembic.ini"),
            "upgrade", "head",
        ],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )



@pytest.fixture(scope="session")
def sample_pdf_bytes() -> bytes:
    """Load the minimal valid PDF fixture."""
    return (FIXTURES_DIR / "sample.pdf").read_bytes()


@pytest.fixture(scope="session")
def corrupted_file_bytes() -> bytes:
    """Non-PDF binary content for negative tests."""
    return b"This is not a PDF file. Just plain text.\x00\x01\x02"


@pytest.fixture(scope="session")
def empty_file_bytes() -> bytes:
    """Zero-byte content for empty file tests."""
    return b""


@pytest.fixture(scope="session")
def known_hash(sample_pdf_bytes: bytes) -> str:
    """Pre-computed SHA-256 hash of the sample PDF."""
    return hashlib.sha256(sample_pdf_bytes).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
#  Function-scoped fixtures (run per test)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Per-test database session with rollback cleanup.

    Creates a fresh engine per test (avoids event-loop conflicts) and
    uses SQLAlchemy's autobegin. After the test, everything is rolled
    back so the database stays clean.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_size=2,
        max_overflow=0,
        echo=False,
    )

    session = AsyncSession(engine, expire_on_commit=False)

    yield session

    await session.rollback()
    await session.close()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    httpx.AsyncClient wrapping the FastAPI app with test DB override.
    """
    from main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ─── Test data fixtures ──────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def test_university(db_session: AsyncSession) -> University:
    """Create a test university in the database."""
    uni = University(
        id=uuid4(),
        name="Test University",
        short_code="TESTU",
        country="US",
        official_email="admin@testuniversity.edu",
        is_verified=True,
        verified_at=datetime.utcnow(),
        is_active=True,
        wallet_address="0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
    )
    db_session.add(uni)
    await db_session.flush()
    return uni


@pytest_asyncio.fixture
async def test_admin_user(
    db_session: AsyncSession, test_university: University
) -> User:
    """Create a UNIVERSITY_ADMIN user linked to test_university."""
    user = User(
        id=uuid4(),
        email="admin@testuniversity.edu",
        password_hash=hash_password("TestPassword123!"),
        first_name="Admin",
        last_name="User",
        role=UserRole.UNIVERSITY_ADMIN,
        university_id=test_university.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_student_user(db_session: AsyncSession) -> User:
    """Create a STUDENT user."""
    user = User(
        id=uuid4(),
        email="student@test.edu",
        password_hash=hash_password("TestPassword123!"),
        first_name="Student",
        last_name="User",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_employer_user(db_session: AsyncSession) -> User:
    """Create an EMPLOYER user."""
    user = User(
        id=uuid4(),
        email="employer@company.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Employer",
        last_name="User",
        role=UserRole.EMPLOYER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_super_admin(db_session: AsyncSession) -> User:
    """Create a SUPER_ADMIN user."""
    user = User(
        id=uuid4(),
        email="superadmin@platform.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Super",
        last_name="Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ─── Auth header fixtures ────────────────────────────────────────────────────


@pytest.fixture
def auth_headers_admin(test_admin_user: User) -> dict[str, str]:
    """Authorization headers for university admin."""
    token = create_access_token(
        subject=str(test_admin_user.id),
        role=test_admin_user.role.value if hasattr(test_admin_user.role, 'value') else str(test_admin_user.role),
        university_id=str(test_admin_user.university_id) if test_admin_user.university_id else None,
        email=test_admin_user.email,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_student(test_student_user: User) -> dict[str, str]:
    """Authorization headers for student."""
    token = create_access_token(
        subject=str(test_student_user.id),
        role=test_student_user.role.value if hasattr(test_student_user.role, 'value') else str(test_student_user.role),
        email=test_student_user.email,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_employer(test_employer_user: User) -> dict[str, str]:
    """Authorization headers for employer."""
    token = create_access_token(
        subject=str(test_employer_user.id),
        role=test_employer_user.role.value if hasattr(test_employer_user.role, 'value') else str(test_employer_user.role),
        email=test_employer_user.email,
    )
    return {"Authorization": f"Bearer {token}"}


# ─── Mock blockchain service ────────────────────────────────────────────────


@pytest.fixture
def mock_blockchain_service() -> MagicMock:
    """
    MagicMock of BlockchainService with sensible defaults.

    Override specific return values per-test as needed:
        mock_blockchain_service.verify_certificate.return_value = ...
    """
    mock = MagicMock()
    mock.is_connected.return_value = True
    mock.get_certificate_count.return_value = 0
    mock.is_authorized_issuer.return_value = True
    mock.verify_certificate.return_value = MagicMock(
        is_valid=True, status="ACTIVE", cert_uid="TEST-001"
    )
    mock.get_certificate_record.return_value = None
    mock.get_transaction_receipt.return_value = MagicMock(
        tx_hash="0x" + "ab" * 32,
        status=1,
        block_number=1,
        block_hash="0x" + "cd" * 32,
        gas_used=50000,
        effective_gas_price=1000000000,
    )
    return mock
