"""create universities

Revision ID: 002
Revises: 001
Create Date: 2026-09-04 11:09:53.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'universities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=300), nullable=False, unique=True),
        sa.Column('short_code', sa.String(length=20), nullable=False, unique=True),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('official_email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('registration_number', sa.String(length=100), nullable=True, unique=True),
        sa.Column('wallet_address', sa.String(length=42), nullable=True, unique=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('address_line', sa.Text(), nullable=True),
        sa.Column('phone_number', sa.String(length=30), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("wallet_address IS NULL OR wallet_address ~ '^0x[0-9a-fA-F]{40}$'", name='chk_universities_wallet_format'),
        sa.CheckConstraint("short_code = UPPER(short_code)", name='chk_universities_short_code_uppercase'),
        sa.CheckConstraint("LENGTH(short_code) BETWEEN 2 AND 20", name='chk_universities_short_code_length'),
        sa.CheckConstraint("(is_verified = FALSE AND verified_at IS NULL) OR (is_verified = TRUE AND verified_at IS NOT NULL)", name='chk_universities_verified_consistency'),
        sa.CheckConstraint("official_email ~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'", name='chk_universities_email_format'),
        sa.CheckConstraint("website_url IS NULL OR website_url ~ '^https?://'", name='chk_universities_website_format'),
        comment='Issuing institution entities'
    )
    
    op.execute("""
    CREATE TRIGGER trg_universities_updated_at 
    BEFORE UPDATE ON universities 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
    """)


def downgrade():
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
