"""make blockchain_transactions.tx_hash nullable

Revision ID: 014
Revises: 013
Create Date: 2026-09-25

Rationale:
    Phase 1 of both certificate issuance and revocation creates a
    BlockchainTransaction record with status=PENDING before the client
    submits the transaction to the blockchain.  The tx_hash is unknown
    at that point — it only becomes available after the MetaMask/wallet
    transaction is submitted and the client calls Phase 2 (confirm_*).

    The existing NOT NULL constraint therefore caused a DB error on every
    Phase 1 call.  Making tx_hash nullable restores the intended workflow:

        Phase 1 → INSERT with tx_hash=NULL, status=PENDING
        Phase 2 → UPDATE SET tx_hash=<real hash>, status=CONFIRMED/FAILED

    The format CHECK constraint (^0x[a-fA-F0-9]{64}$) is preserved and
    updated to be conditional: it only applies when tx_hash IS NOT NULL.
    This ensures that any non-null value is still a well-formed hash.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Drop the old NOT NULL + format CHECK on tx_hash
    op.drop_constraint('chk_blockchain_tx_hash_format', 'blockchain_transactions')

    # 2. Make tx_hash nullable
    op.alter_column(
        'blockchain_transactions',
        'tx_hash',
        nullable=True,
        existing_type=sa.String(length=66),
    )

    # 3. Re-add the format CHECK with IS NULL OR guard so it only fires
    #    when a non-null hash is present (preserves integrity for set values).
    op.create_check_constraint(
        'chk_blockchain_tx_hash_format',
        'blockchain_transactions',
        "tx_hash IS NULL OR tx_hash ~ '^0x[0-9a-fA-F]{64}$'",
    )


def downgrade():
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
