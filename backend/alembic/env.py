"""Alembic async migration environment.

Configures the Alembic migration context to use the async SQLAlchemy
engine from core.config, and imports all ORM models so their metadata
is available for autogenerate.
"""
import asyncio
import sys
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# ---------------------------------------------------------------------------
# Ensure the backend package is importable when running from backend/ dir
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Alembic Config object (provides access to alembic.ini values)
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging from the config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import application metadata (target for autogenerate)
# ---------------------------------------------------------------------------
from database.base import Base  # noqa: E402

# Import ALL ORM models so they register with Base.metadata
from models.university_model import University  # noqa: E402, F401
from models.user_model import User  # noqa: E402, F401
from models.student_model import Student  # noqa: E402, F401
from models.employer_model import Employer  # noqa: E402, F401
from models.certificate_model import Certificate  # noqa: E402, F401
from models.blockchain_transaction_model import BlockchainTransaction  # noqa: E402, F401
from models.qr_verification_model import QRVerification  # noqa: E402, F401
from models.verification_log_model import VerificationLog  # noqa: E402, F401
from models.refresh_token_model import RefreshToken  # noqa: E402, F401
from models.audit_log_model import AuditLog  # noqa: E402, F401

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Import database URL from application config
# ---------------------------------------------------------------------------
from core.config import settings  # noqa: E402

DATABASE_URL = settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Run migrations using the provided connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        transaction_per_migration=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an async engine."""
    connectable = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
