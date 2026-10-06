"""create_refresh_tokens

Revision ID: 010
Revises: 009
Create Date: 2026-09-04 11:09:53.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('FALSE')),
        sa.Column('replaced_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('refresh_tokens.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_ip', postgresql.INET(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_refresh_tokens_token_hash'),
        sa.CheckConstraint("LENGTH(token_hash) = 64", name='chk_refresh_token_hash_length'),
        sa.CheckConstraint("expires_at > created_at", name='chk_refresh_token_expiry_future'),
        sa.CheckConstraint("(is_revoked = FALSE AND revoked_at IS NULL) OR (is_revoked = TRUE AND revoked_at IS NOT NULL)", name='chk_refresh_token_revoked_consistency'),
        comment='JWT refresh token registry (SHA-256 hashed, rotation chain)'
    )

def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
