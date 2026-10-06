"""create qr_verifications table

Revision ID: 008
Revises: 007
Create Date: 2026-09-04 11:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'qr_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('certificate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(length=128), nullable=False, unique=True),
        sa.Column('verification_url', sa.String(length=1000), nullable=False),
        sa.Column('qr_image_path', sa.String(length=1000), nullable=True),
        sa.Column('qr_image_size_px', sa.SmallInteger(), nullable=True),
        sa.Column('total_scan_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_scanned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_scanned_ip', postgresql.INET(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deactivated_reason', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('generated_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['certificate_id'], ['certificates.id'], onupdate='CASCADE', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id'], onupdate='CASCADE', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("LENGTH(token) >= 32", name='chk_qr_token_length'),
        sa.CheckConstraint("verification_url ~ '^https?://'", name='chk_qr_url_format'),
        sa.CheckConstraint("total_scan_count >= 0", name='chk_qr_scan_count_non_negative'),
        sa.CheckConstraint("qr_image_size_px IS NULL OR qr_image_size_px > 0", name='chk_qr_image_size_positive'),
        sa.CheckConstraint("(is_active = TRUE AND deactivated_at IS NULL) OR (is_active = FALSE AND deactivated_at IS NOT NULL)", name='chk_qr_deactivation_consistency'),
        sa.CheckConstraint("expires_at IS NULL OR expires_at > created_at", name='chk_qr_expiry_future'),
        sa.CheckConstraint("(total_scan_count = 0 AND last_scanned_at IS NULL) OR (total_scan_count > 0 AND last_scanned_at IS NOT NULL)", name='chk_qr_scan_consistency'),
        comment='QR code artifacts for certificate verification'
    )

    op.create_index(
        'uq_qr_one_active_per_certificate',
        'qr_verifications',
        ['certificate_id'],
        unique=True,
        postgresql_where=sa.text('is_active = TRUE')
    )

    op.execute("""
    CREATE TRIGGER trg_qr_verifications_updated_at
    BEFORE UPDATE ON qr_verifications
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();
    """)

def downgrade():
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
