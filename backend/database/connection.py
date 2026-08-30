# backend/database/connection.py
# Async SQLAlchemy engine, session factory, and session dependency.
#
# Architecture Reference: docs/backend.md Section 20 (Database Access Strategy)
# Pool Config: docs/backend.md Section 20.1
#
# Session lifecycle (from docs):
#   1. Request arrives → get_db() creates new AsyncSession
#   2. Session passed to router → service → repository
#   3. Service controls commit/rollback
#   4. After response: session.close() called by generator cleanup
#   5. Connection returned to pool

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings

# ─── Async Engine ─────────────────────────────────────────────────────────────
# Pool configuration values from docs/backend.md Section 20.1:
#   pool_size: 10, max_overflow: 20, pool_timeout: 30,
#   pool_recycle: 1800 (30 min), pool_pre_ping: True

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=settings.DEBUG,  # Log SQL in development only
)

# ─── Session Factory ──────────────────────────────────────────────────────────
# async_sessionmaker creates unbound sessions that are configured but not
# connected until first use. expire_on_commit=False prevents lazy-load
# exceptions after commit (common in async code).

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ─── Session Dependency ──────────────────────────────────────────────────────
# Used as a FastAPI dependency: Depends(get_db)
# The async generator pattern ensures the session is always closed,
# even if the request handler raises an exception.


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.

    Usage in routers:
        @router.post("/...")
        async def create_something(db: AsyncSession = Depends(get_db)):
            ...

    The session is closed automatically after the request completes.
    Commit and rollback are the responsibility of the service layer,
    NOT this dependency (per documented architecture).
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_engine() -> None:
    """
    Dispose of the engine and all pooled connections.

    Called during application shutdown to cleanly release resources.
    """
    await engine.dispose()
