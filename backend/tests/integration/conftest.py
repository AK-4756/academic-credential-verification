# backend/tests/integration/conftest.py
# Integration-test-specific fixtures.
#
# FIXTURES PROVIDED:
#
# 1. svc_db  (for P9+ service integration tests)
#    A fresh AsyncSession per test with autobegin=True (default).
#
#    BACKGROUND: WHY A SEPARATE FIXTURE AT ALL?
#    ──────────────────────────────────────────
#    Production services call `async with db.begin():` to begin and commit
#    their own transactions.  The root conftest `db_session` fixture creates a
#    session with the default autobegin=True but uses `session.rollback()` for
#    cleanup, relying on the fact that P8 repository tests only ever flush()
#    and never commit.
#
#    P9+ service tests call services that actually commit data to PostgreSQL.
#    A separate session (svc_db) is used so that:
#    - Its teardown runs table truncation instead of rollback, providing
#      reliable cleanup even after real commits.
#    - P8 tests using db_session are completely unaffected.
#
#    SESSION INTERACTION RULES FOR svc_db (autobegin=True):
#    ───────────────────────────────────────────────────────
#    With autobegin=True, SQLAlchemy silently starts a transaction on the
#    first DB operation (read or write).  Service calls use explicit
#    `async with db.begin():` to begin and commit their own transactions.
#
#    Rule: `async with session.begin()` raises "A transaction is already
#    begun on this Session" if autobegin has already fired.
#
#    Therefore:
#    a) Test setup data (e.g., university rows) must be inserted using
#       `async with svc_db.begin():` so they commit and leave the session
#       clean before the service call.
#    b) Test verification reads (after a service call) are fine because
#       the service committed/rolled back and left the session clean.
#    c) If a verification read is followed by ANOTHER service call, the
#       test must call `await svc_db.rollback()` after the read to close
#       the autobegun read-transaction before the next service call.
#
#    CLEANUP:
#    ────────
#    Table truncation is embedded in svc_db teardown and runs AFTER the
#    session is fully closed.  This prevents deadlocks with PostgreSQL row
#    locks from the test session.
#
#    P8 COMPATIBILITY:
#    ──────────────────
#    P8 repository tests use db_session (root conftest) and rollback-only
#    cleanup.  No autouse truncation is applied to them.  P8 tests are
#    unaffected by this file.
#
# TRUNCATION ORDER:
#    Leaf tables first (deepest FK dependants), root tables last.
#    Schema is preserved; no tables are dropped.
#    alembic_version is excluded so Alembic state is preserved.

from __future__ import annotations

import os
import sys
from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from core.config import settings  # noqa: E402


def _test_database_url() -> str:
    prod_url = settings.DATABASE_URL
    if "/credential_db" in prod_url:
        return prod_url.replace("/credential_db", "/credential_db_test")
    return prod_url.rstrip("/") + "_test"


# Truncation order: leaf-to-root (FK dependants first, referenced tables last).
_TRUNCATION_ORDER = [
    "audit_log",
    "verification_logs",
    "blockchain_transactions",
    "qr_verifications",
    "certificates",
    "refresh_tokens",
    "students",
    "employers",
    "users",
    "universities",
]


async def _truncate_all(db_url: str) -> None:
    """
    Truncate all application tables in FK-safe order.

    Uses a fresh engine so cleanup is independent of any test session.
    Called only after the test session has been fully closed.
    """
    engine = create_async_engine(db_url, pool_pre_ping=True, echo=False)
    try:
        async with engine.begin() as conn:
            for table in _TRUNCATION_ORDER:
                await conn.execute(
                    text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                )
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def svc_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Per-test database session for service integration tests (P9+).

    Uses autobegin=True (SQLAlchemy default) so that both service calls
    (which use `async with db.begin():`) and test-code repository reads
    (which rely on autobegin) work correctly.

    Session interaction pattern:
    - Pre-test DB setup must use `async with svc_db.begin():` to commit
      and leave the session clean before service calls.
    - Post-service verification reads work normally (session is clean
      after the service's own begin/commit cycle).
    - If a verification read is followed by another service call, call
      `await svc_db.rollback()` after the read to close the autobegun
      read-transaction.

    Teardown:
    1. Rollback any open transaction (no-op if session is already clean).
    2. Close the session and dispose the engine (releases all DB locks).
    3. Truncate all application tables (safe because session is closed).
    """
    db_url = _test_database_url()
    engine = create_async_engine(
        db_url,
        pool_size=2,
        max_overflow=0,
        echo=False,
    )
    session = AsyncSession(engine, expire_on_commit=False)

    try:
        yield session
    finally:
        # Rollback any open transaction, then close session and engine
        await session.rollback()
        await session.close()
        await engine.dispose()

        # Now safe to truncate: no competing locks from this session
        await _truncate_all(db_url)
