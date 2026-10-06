"""
Development seed script -- NOT an Alembic migration.

Creates 3 development-only records:
  1. SUPER_ADMIN user (admin@platform.dev)
  2. Test University (TESTUNIV)
  3. University Admin (admin@testuniv.edu)

Run from project root:
  python scripts/seed_dev_data.py

Or from backend/ directory:
  python ../scripts/seed_dev_data.py

Idempotent: checks existence before inserting.
"""
import sys
import os
import asyncio
from datetime import datetime, timezone

# Add backend directory to sys.path and set CWD so .env.development is found
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
backend_dir = os.path.join(project_root, "backend")
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from core.config import settings
from models.user_model import User
from models.university_model import University
from core.constants import UserRole


def hash_password(plaintext: str) -> str:
    """Hash a password using bcrypt with cost factor 12."""
    return bcrypt.hashpw(
        plaintext.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


async def seed_data() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        async with session.begin():

            # --- 1. SUPER_ADMIN user ---
            result = await session.execute(
                select(User).where(User.email == "admin@platform.dev")
            )
            if result.scalars().first() is not None:
                print("SKIP: SUPER_ADMIN 'admin@platform.dev' already exists.")
            else:
                super_admin = User(
                    email="admin@platform.dev",
                    password_hash=hash_password("admin_dev_password_123"),
                    role=UserRole.SUPER_ADMIN,
                    first_name="Platform",
                    last_name="Admin",
                    is_active=True,
                    is_email_verified=True,
                    email_verified_at=datetime.now(timezone.utc),
                )
                session.add(super_admin)
                print("CREATED: SUPER_ADMIN 'admin@platform.dev'.")

            # --- 2. Test University ---
            result = await session.execute(
                select(University).where(University.short_code == "TESTUNIV")
            )
            test_univ = result.scalars().first()

            if test_univ is not None:
                print("SKIP: University 'TESTUNIV' already exists.")
            else:
                test_univ = University(
                    name="Test University",
                    short_code="TESTUNIV",
                    country="United States",
                    official_email="registrar@testuniv.edu",
                    is_verified=False,
                    is_active=True,
                )
                session.add(test_univ)
                await session.flush()  # get test_univ.id
                print("CREATED: University 'Test University' (TESTUNIV).")

            # --- 3. Test University Admin ---
            result = await session.execute(
                select(User).where(User.email == "admin@testuniv.edu")
            )
            if result.scalars().first() is not None:
                print("SKIP: UNIVERSITY_ADMIN 'admin@testuniv.edu' already exists.")
            else:
                univ_admin = User(
                    email="admin@testuniv.edu",
                    password_hash=hash_password("univ_admin_dev_123"),
                    role=UserRole.UNIVERSITY_ADMIN,
                    first_name="University",
                    last_name="Admin",
                    university_id=test_univ.id,
                    is_active=True,
                    is_email_verified=True,
                    email_verified_at=datetime.now(timezone.utc),
                )
                session.add(univ_admin)
                print("CREATED: UNIVERSITY_ADMIN 'admin@testuniv.edu'.")

    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed_data())
