"""add SUBMITTED value to transaction_status enum

Revision ID: 015
Revises: 014
Create Date: 2026-09-27

Rationale:
    The Python TransactionStatus domain model has always included SUBMITTED
    as a valid state representing a transaction that has been sent to the
    blockchain mempool but has not yet been included in a mined block.

    The PostgreSQL transaction_status enum was created in migration 001 with
    only ('PENDING', 'CONFIRMED', 'FAILED', 'REPLACED'), omitting 'SUBMITTED'.

    This caused a DB error whenever confirm_blockchain_storage() or
    confirm_revocation() called BlockchainTransactionRepository.update_status()
    with TransactionStatus.SUBMITTED (the "receipt not yet mined" code path).

    The fix adds SUBMITTED to the live enum using the PostgreSQL
    ALTER TYPE ... ADD VALUE statement, which is transactional-safe in
    PostgreSQL 12+ and does not require a table rewrite.

    Ordering: SUBMITTED is placed between PENDING and CONFIRMED to reflect
    the natural lifecycle: PENDING → SUBMITTED → CONFIRMED | FAILED.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # ADD VALUE is safe in PostgreSQL 12+ without a table rewrite.
    # IF NOT EXISTS prevents failure if the value was already added manually.
    op.execute(
        "ALTER TYPE transaction_status ADD VALUE IF NOT EXISTS 'SUBMITTED' "
        "BEFORE 'CONFIRMED'"
    )


def downgrade():
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
