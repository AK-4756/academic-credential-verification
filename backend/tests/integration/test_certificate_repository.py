# backend/tests/integration/test_certificate_repository.py
# P8: Database integration tests for CertificateRepository.
#
# Tests run against the real credential_db_test PostgreSQL database.
# Each test runs in a savepoint that is rolled back after the test.

import os
import sys
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.constants import BlockchainStatus, UserRole
from core.security import hash_password
from models.certificate_model import Certificate
from models.university_model import University
from models.user_model import User
from repositories.certificate_repository import CertificateRepository

pytestmark = [pytest.mark.database, pytest.mark.integration]


# ─── Helpers ─────────────────────────────────────────────────────────────────


async def _create_university(db: AsyncSession, short_code: str = None) -> University:
    """Insert a university for FK constraints."""
    sc = short_code or uuid4().hex[:6].upper()
    uni = University(
        id=uuid4(),
        name=f"University-{sc}",
        short_code=sc,
        country="US",
        official_email=f"{sc.lower()}@uni.edu",
        is_verified=True,
        verified_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(uni)
    await db.flush()
    return uni


async def _create_user(
    db: AsyncSession, university_id=None
) -> User:
    """Insert a test user (student)."""
    user = User(
        id=uuid4(),
        email=f"{uuid4().hex[:10]}@test.com",
        password_hash=hash_password("TestPass123!"),
        first_name="Test",
        last_name="Student",
        role=UserRole.STUDENT,
        university_id=university_id,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_admin(db: AsyncSession, university_id) -> User:
    """Insert a university admin user."""
    user = User(
        id=uuid4(),
        email=f"{uuid4().hex[:10]}@admin.com",
        password_hash=hash_password("AdminPass1!"),
        first_name="Admin",
        last_name="User",
        role=UserRole.UNIVERSITY_ADMIN,
        university_id=university_id,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_certificate(
    db: AsyncSession,
    university: University,
    student: User,
    admin: User,
    uid: str = None,
    sha256_hash: str = None,
    status: BlockchainStatus = BlockchainStatus.PENDING,
    is_active: bool = True,
) -> Certificate:
    """Insert a certificate with the required FK relationships."""
    import random
    seq = f"{random.randint(10000, 99999)}"
    cert_kwargs = dict(
        id=uuid4(),
        certificate_uid=uid or f"{university.short_code}-2025-{seq}",
        university_id=university.id,
        student_id=student.id,
        issued_by=admin.id,
        recipient_name=f"{student.first_name} {student.last_name}",
        recipient_email_snapshot=student.email,
        degree_title="Bachelor of Science",
        field_of_study="Computer Science",
        issue_date=date(2025, 6, 15),
        sha256_hash=sha256_hash or uuid4().hex + uuid4().hex,  # 64 hex chars
        blockchain_status=status,
        file_path=f"/uploads/{uuid4().hex}.pdf",
        file_original_name="certificate.pdf",
        file_size_bytes=12345,
        file_mime_type="application/pdf",
        is_active=is_active,
    )
    # chk_certificates_revocation_consistency requires revocation fields when inactive
    if not is_active:
        cert_kwargs["revocation_reason"] = "Test revocation"
        cert_kwargs["revoked_by"] = admin.id
        cert_kwargs["revoked_at"] = datetime.utcnow()
    cert = Certificate(**cert_kwargs)
    db.add(cert)
    await db.flush()
    return cert


# ═══════════════════════════════════════════════════════════════════════════════
#  BaseRepository inherited methods
# ═══════════════════════════════════════════════════════════════════════════════


class TestCertificateBaseMethods:
    """Tests for inherited get_by_id, create."""

    async def test_get_by_id(self, db_session: AsyncSession):
        """Fetch a certificate by UUID returns the correct record."""
        uni = await _create_university(db_session)
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)
        cert = await _create_certificate(db_session, uni, student, admin)

        found = await CertificateRepository.get_by_id(db_session, cert.id)
        assert found is not None
        assert found.id == cert.id
        assert found.certificate_uid == cert.certificate_uid

    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Non-existent UUID returns None."""
        found = await CertificateRepository.get_by_id(db_session, uuid4())
        assert found is None

    async def test_create(self, db_session: AsyncSession):
        """Create inserts a certificate and returns it with defaults."""
        uni = await _create_university(db_session)
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)
        h = uuid4().hex + uuid4().hex

        data = {
            "certificate_uid": f"{uni.short_code}-2025-00001",
            "university_id": uni.id,
            "student_id": student.id,
            "issued_by": admin.id,
            "recipient_name": "Test Student",
            "recipient_email_snapshot": student.email,
            "degree_title": "BSc Computer Science",
            "field_of_study": "Computer Science",
            "issue_date": date(2025, 6, 15),
            "sha256_hash": h,
            "file_path": "/uploads/test.pdf",
            "file_original_name": "test.pdf",
            "file_size_bytes": 10000,
            "file_mime_type": "application/pdf",
        }
        cert = await CertificateRepository.create(db_session, data)
        assert cert.id is not None
        assert cert.blockchain_status == BlockchainStatus.PENDING
        assert cert.is_active is True


# ═══════════════════════════════════════════════════════════════════════════════
#  Domain methods
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetByUid:
    """Tests for CertificateRepository.get_by_uid."""

    async def test_get_by_uid_found(self, db_session: AsyncSession):
        """Returns certificate when UID matches."""
        uni = await _create_university(db_session, short_code="UIDTST")
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)
        cert = await _create_certificate(
            db_session, uni, student, admin, uid="UIDTST-2025-00001"
        )
        found = await CertificateRepository.get_by_uid(
            db_session, "UIDTST-2025-00001"
        )
        assert found is not None
        assert found.id == cert.id

    async def test_get_by_uid_not_found(self, db_session: AsyncSession):
        """Returns None for non-existent UID."""
        found = await CertificateRepository.get_by_uid(
            db_session, "NONEXIST-9999-99999"
        )
        assert found is None


class TestGetByHash:
    """Tests for CertificateRepository.get_by_hash."""

    async def test_get_by_hash_found(self, db_session: AsyncSession):
        """Returns certificate when SHA-256 hash matches."""
        uni = await _create_university(db_session)
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)
        known_hash = "a" * 64
        cert = await _create_certificate(
            db_session, uni, student, admin, sha256_hash=known_hash
        )
        found = await CertificateRepository.get_by_hash(db_session, known_hash)
        assert found is not None
        assert found.id == cert.id

    async def test_get_by_hash_not_found(self, db_session: AsyncSession):
        """Returns None for non-existent hash."""
        found = await CertificateRepository.get_by_hash(db_session, "b" * 64)
        assert found is None


class TestUpdateBlockchainStatus:
    """Tests for CertificateRepository.update_blockchain_status."""

    async def test_update_status_to_confirmed(self, db_session: AsyncSession):
        """Updates from PENDING to CONFIRMED."""
        uni = await _create_university(db_session)
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)
        cert = await _create_certificate(db_session, uni, student, admin)
        assert cert.blockchain_status == BlockchainStatus.PENDING

        updated = await CertificateRepository.update_blockchain_status(
            db_session, cert.id, BlockchainStatus.CONFIRMED
        )
        assert updated is not None
        assert updated.blockchain_status == BlockchainStatus.CONFIRMED

    async def test_update_status_not_found(self, db_session: AsyncSession):
        """Returns None for non-existent certificate."""
        result = await CertificateRepository.update_blockchain_status(
            db_session, uuid4(), BlockchainStatus.CONFIRMED
        )
        assert result is None


class TestGetByStudent:
    """Tests for CertificateRepository.get_by_student."""

    async def test_get_by_student_active_only(self, db_session: AsyncSession):
        """Returns only active certs by default."""
        uni = await _create_university(db_session)
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)
        active = await _create_certificate(
            db_session, uni, student, admin, is_active=True
        )
        revoked = await _create_certificate(
            db_session, uni, student, admin,
            is_active=False, status=BlockchainStatus.REVOKED,
        )

        certs = await CertificateRepository.get_by_student(db_session, student.id)
        cert_ids = {c.id for c in certs}
        assert active.id in cert_ids
        assert revoked.id not in cert_ids

    async def test_get_by_student_all(self, db_session: AsyncSession):
        """With active_only=False, returns all certs."""
        uni = await _create_university(db_session)
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)
        await _create_certificate(db_session, uni, student, admin, is_active=True)
        await _create_certificate(
            db_session, uni, student, admin,
            is_active=False, status=BlockchainStatus.REVOKED,
        )

        certs = await CertificateRepository.get_by_student(
            db_session, student.id, active_only=False
        )
        assert len(certs) >= 2


class TestGetByUniversity:
    """Tests for CertificateRepository.get_by_university."""

    async def test_pagination(self, db_session: AsyncSession):
        """Returns paginated results with total count."""
        uni = await _create_university(db_session)
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)
        for _ in range(3):
            await _create_certificate(db_session, uni, student, admin)

        items, total = await CertificateRepository.get_by_university(
            db_session, uni.id, skip=0, limit=2
        )
        assert len(items) == 2
        assert total == 3


class TestRevoke:
    """Tests for CertificateRepository.revoke."""

    async def test_revoke_certificate(self, db_session: AsyncSession):
        """Revoke sets is_active=False and records metadata."""
        uni = await _create_university(db_session)
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)
        cert = await _create_certificate(
            db_session, uni, student, admin,
            status=BlockchainStatus.CONFIRMED, is_active=True,
        )

        revoked = await CertificateRepository.revoke(
            db_session, cert.id, reason="Fraudulent", revoked_by=admin.id
        )
        assert revoked is not None
        assert revoked.is_active is False
        assert revoked.revocation_reason == "Fraudulent"
        assert revoked.revoked_by == admin.id
        assert revoked.revoked_at is not None
        assert revoked.blockchain_status == BlockchainStatus.REVOKED

    async def test_revoke_not_found(self, db_session: AsyncSession):
        """Returns None for non-existent certificate."""
        result = await CertificateRepository.revoke(
            db_session, uuid4(), reason="Test", revoked_by=uuid4()
        )
        assert result is None


class TestUidSequence:
    """Tests for CertificateRepository.get_next_uid_sequence."""

    async def test_first_sequence(self, db_session: AsyncSession):
        """Returns 1 when no certificates exist for the prefix."""
        seq = await CertificateRepository.get_next_uid_sequence(
            db_session, "NEWUNI", 2025
        )
        assert seq == 1

    async def test_increments_after_existing(self, db_session: AsyncSession):
        """Returns max+1 when certificates exist."""
        uni = await _create_university(db_session, short_code="SEQTST")
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)

        await _create_certificate(
            db_session, uni, student, admin, uid="SEQTST-2025-00003"
        )
        seq = await CertificateRepository.get_next_uid_sequence(
            db_session, "SEQTST", 2025
        )
        assert seq == 4


class TestConfirmedCount:
    """Tests for CertificateRepository.get_confirmed_count_by_university."""

    async def test_count_confirmed_only(self, db_session: AsyncSession):
        """Only counts CONFIRMED certificates."""
        uni = await _create_university(db_session)
        student = await _create_user(db_session)
        admin = await _create_admin(db_session, uni.id)

        await _create_certificate(
            db_session, uni, student, admin, status=BlockchainStatus.CONFIRMED
        )
        await _create_certificate(
            db_session, uni, student, admin, status=BlockchainStatus.CONFIRMED
        )
        await _create_certificate(
            db_session, uni, student, admin, status=BlockchainStatus.PENDING
        )

        count = await CertificateRepository.get_confirmed_count_by_university(
            db_session, uni.id
        )
        assert count == 2
