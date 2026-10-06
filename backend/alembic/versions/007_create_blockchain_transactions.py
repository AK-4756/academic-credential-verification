"""create blockchain_transactions table

Revision ID: 007
Revises: 006
Create Date: 2026-09-04 11:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'blockchain_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('certificate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tx_hash', sa.String(length=66), nullable=False, unique=True),
        sa.Column('tx_type', postgresql.ENUM('STORE_HASH', 'REVOKE_HASH', 'AUTHORIZE_ISSUER', name='transaction_type', create_type=False), nullable=False),
        sa.Column('from_address', sa.String(length=42), nullable=False),
        sa.Column('to_address', sa.String(length=42), nullable=False),
        sa.Column('contract_address', sa.String(length=42), nullable=False),
        sa.Column('block_number', sa.BigInteger(), nullable=True),
        sa.Column('block_hash', sa.String(length=66), nullable=True),
        sa.Column('gas_used', sa.BigInteger(), nullable=True),
        sa.Column('gas_price_wei', sa.Numeric(precision=30, scale=0), nullable=True),
        sa.Column('gas_limit', sa.BigInteger(), nullable=True),
        sa.Column('transaction_fee_wei', sa.Numeric(precision=30, scale=0), nullable=True),
        sa.Column('network_name', sa.String(length=50), nullable=False),
        sa.Column('network_chain_id', sa.Integer(), nullable=False),
        sa.Column('certificate_hash_stored', sa.String(length=64), nullable=True),
        sa.Column('status', postgresql.ENUM('PENDING', 'CONFIRMED', 'FAILED', 'REPLACED', name='transaction_status', create_type=False), nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('revert_reason', sa.Text(), nullable=True),
        sa.Column('confirmations_required', sa.SmallInteger(), nullable=False, server_default='1'),
        sa.Column('confirmations_received', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['certificate_id'], ['certificates.id'], onupdate='CASCADE', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("tx_hash ~ '^0x[0-9a-fA-F]{64}$'", name='chk_blockchain_tx_hash_format'),
        sa.CheckConstraint("from_address ~ '^0x[0-9a-fA-F]{40}$'", name='chk_blockchain_from_address_format'),
        sa.CheckConstraint("to_address ~ '^0x[0-9a-fA-F]{40}$'", name='chk_blockchain_to_address_format'),
        sa.CheckConstraint("contract_address ~ '^0x[0-9a-fA-F]{40}$'", name='chk_blockchain_contract_address_format'),
        sa.CheckConstraint("block_number IS NULL OR block_number > 0", name='chk_blockchain_block_number_positive'),
        sa.CheckConstraint("gas_used IS NULL OR gas_used > 0", name='chk_blockchain_gas_used_positive'),
        sa.CheckConstraint("confirmations_received >= 0 AND confirmations_required >= 1", name='chk_blockchain_confirmations_non_negative'),
        sa.CheckConstraint("network_chain_id > 0", name='chk_blockchain_chain_id_positive'),
        sa.CheckConstraint("status != 'CONFIRMED' OR (block_number IS NOT NULL AND confirmed_at IS NOT NULL)", name='chk_blockchain_confirmed_has_block'),
        sa.CheckConstraint("certificate_hash_stored IS NULL OR certificate_hash_stored ~ '^[0-9a-f]{64}$'", name='chk_blockchain_hash_stored_format'),
        sa.CheckConstraint("(gas_used IS NULL AND transaction_fee_wei IS NULL) OR (gas_used IS NOT NULL AND gas_price_wei IS NOT NULL AND transaction_fee_wei IS NOT NULL)", name='chk_blockchain_fee_consistency'),
        comment='Ethereum transaction records for CertificateRegistry'
    )

    op.execute("""
    CREATE TRIGGER trg_blockchain_transactions_updated_at
    BEFORE UPDATE ON blockchain_transactions
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();
    """)

def downgrade():
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
