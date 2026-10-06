"""create_verification_logs

Revision ID: 009
Revises: 008
Create Date: 2026-09-04 11:09:53.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'verification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('certificate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('certificates.id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=True),
        sa.Column('certificate_uid_queried', sa.String(length=50), nullable=True),
        sa.Column('verifier_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True),
        sa.Column('qr_verification_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('qr_verifications.id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True),
        sa.Column('verification_method', postgresql.ENUM('FILE_UPLOAD', 'QR_SCAN', 'MANUAL_ID_LOOKUP', name='verification_method', create_type=False), nullable=False),
        sa.Column('result', postgresql.ENUM('AUTHENTIC', 'TAMPERED', 'REVOKED', 'NOT_FOUND', 'PENDING_CHAIN', 'ERROR', name='verification_result', create_type=False), nullable=False),
        sa.Column('submitted_hash', sa.String(length=64), nullable=True),
        sa.Column('stored_hash', sa.String(length=64), nullable=True),
        sa.Column('hash_match', sa.Boolean(), nullable=True),
        sa.Column('blockchain_verified', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('blockchain_tx_hash', sa.String(length=66), nullable=True),
        sa.Column('blockchain_query_time_ms', sa.Integer(), nullable=True),
        sa.Column('university_name_snapshot', sa.String(length=300), nullable=True),
        sa.Column('degree_title_snapshot', sa.String(length=300), nullable=True),
        sa.Column('recipient_name_snapshot', sa.String(length=300), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('country_code', sa.CHAR(length=2), nullable=True),
        sa.Column('referrer_url', sa.String(length=1000), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("submitted_hash IS NULL OR submitted_hash ~ '^[0-9a-f]{64}$'", name='chk_vlog_submitted_hash_format'),
        sa.CheckConstraint("stored_hash IS NULL OR stored_hash ~ '^[0-9a-f]{64}$'", name='chk_vlog_stored_hash_format'),
        sa.CheckConstraint("blockchain_tx_hash IS NULL OR blockchain_tx_hash ~ '^0x[0-9a-fA-F]{64}$'", name='chk_vlog_blockchain_tx_format'),
        sa.CheckConstraint("hash_match IS NULL OR (submitted_hash IS NOT NULL AND stored_hash IS NOT NULL)", name='chk_vlog_hash_match_consistency'),
        sa.CheckConstraint("result != 'TAMPERED' OR (submitted_hash IS NOT NULL AND stored_hash IS NOT NULL)", name='chk_vlog_tampered_has_both_hashes'),
        sa.CheckConstraint("result != 'AUTHENTIC' OR hash_match = TRUE", name='chk_vlog_authentic_hash_match'),
        sa.CheckConstraint("verification_method != 'QR_SCAN' OR qr_verification_id IS NOT NULL", name='chk_vlog_qr_method_has_qr_id'),
        sa.CheckConstraint("processing_time_ms IS NULL OR processing_time_ms >= 0", name='chk_vlog_processing_time_positive'),
        sa.CheckConstraint("country_code IS NULL OR country_code ~ '^[A-Z]{2}$'", name='chk_vlog_country_code_format'),
        comment='Immutable audit log of every verification attempt (append-only)'
    )

def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
