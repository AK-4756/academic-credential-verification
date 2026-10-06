"""create certificates table

Revision ID: 006
Revises: 005
Create Date: 2026-09-04 11:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'certificates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('certificate_uid', sa.String(length=50), nullable=False, unique=True),
        sa.Column('university_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('issued_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recipient_name', sa.String(length=300), nullable=False),
        sa.Column('recipient_email_snapshot', sa.String(length=255), nullable=False),
        sa.Column('degree_title', sa.String(length=300), nullable=False),
        sa.Column('field_of_study', sa.String(length=300), nullable=False),
        sa.Column('grade_classification', sa.String(length=100), nullable=True),
        sa.Column('honors', sa.String(length=100), nullable=True),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('academic_year', sa.String(length=20), nullable=True),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False, unique=True),
        sa.Column('blockchain_status', postgresql.ENUM('PENDING', 'SUBMITTED', 'CONFIRMED', 'FAILED', 'REVOKED', name='blockchain_status', create_type=False), nullable=False, server_default='PENDING'),
        sa.Column('file_path', sa.String(length=1000), nullable=False),
        sa.Column('file_original_name', sa.String(length=500), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('file_mime_type', sa.String(length=100), nullable=False, server_default='application/pdf'),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('revocation_reason', sa.Text(), nullable=True),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['university_id'], ['universities.id'], onupdate='CASCADE', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], onupdate='CASCADE', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['issued_by'], ['users.id'], onupdate='CASCADE', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], onupdate='CASCADE', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("certificate_uid ~ '^[A-Z0-9]+-[0-9]{4}-[0-9]{5}$'", name='chk_certificates_uid_format'),
        sa.CheckConstraint("sha256_hash ~ '^[0-9a-f]{64}$'", name='chk_certificates_sha256_format'),
        sa.CheckConstraint("sha256_hash = LOWER(sha256_hash)", name='chk_certificates_sha256_lowercase'),
        sa.CheckConstraint("expiry_date IS NULL OR expiry_date > issue_date", name='chk_certificates_expiry_after_issue'),
        sa.CheckConstraint("issue_date >= '1900-01-01' AND issue_date <= CURRENT_DATE + INTERVAL '1 day'", name='chk_certificates_issue_date_reasonable'),
        sa.CheckConstraint("file_size_bytes > 0", name='chk_certificates_file_size_positive'),
        sa.CheckConstraint("file_size_bytes <= 52428800", name='chk_certificates_file_size_limit'),
        sa.CheckConstraint("file_mime_type IN ('application/pdf', 'application/x-pdf')", name='chk_certificates_mime_type'),
        sa.CheckConstraint("(is_active = TRUE AND revocation_reason IS NULL AND revoked_by IS NULL AND revoked_at IS NULL) OR (is_active = FALSE AND revocation_reason IS NOT NULL AND revoked_by IS NOT NULL AND revoked_at IS NOT NULL)", name='chk_certificates_revocation_consistency'),
        sa.CheckConstraint("NOT (is_active = FALSE AND blockchain_status != 'REVOKED')", name='chk_certificates_blockchain_status_revoked_sync'),
        sa.CheckConstraint("LENGTH(TRIM(recipient_name)) > 0", name='chk_certificates_recipient_name_not_empty'),
        sa.CheckConstraint("LENGTH(TRIM(degree_title)) > 0", name='chk_certificates_degree_not_empty'),
        comment='Core credential entity bridging off-chain to on-chain'
    )

    op.execute("""
    CREATE TRIGGER trg_certificates_updated_at
    BEFORE UPDATE ON certificates
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_confirmed_hash_change()
    RETURNS TRIGGER AS $$
    BEGIN
        IF OLD.blockchain_status = 'CONFIRMED'
           AND OLD.sha256_hash != NEW.sha256_hash THEN
            RAISE EXCEPTION
                'INTEGRITY VIOLATION: Cannot modify sha256_hash of a CONFIRMED certificate. Certificate ID: %. Current hash: %', OLD.id, OLD.sha256_hash;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_certificates_protect_confirmed_hash
    BEFORE UPDATE ON certificates
    FOR EACH ROW
    EXECUTE FUNCTION prevent_confirmed_hash_change();
    """)

    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_immutable_field_change()
    RETURNS TRIGGER AS $$
    BEGIN
        IF OLD.blockchain_status = 'CONFIRMED' THEN
            IF OLD.recipient_name   != NEW.recipient_name   OR
               OLD.degree_title     != NEW.degree_title     OR
               OLD.field_of_study   != NEW.field_of_study   OR
               OLD.issue_date       != NEW.issue_date        OR
               OLD.university_id    != NEW.university_id     OR
               OLD.student_id       != NEW.student_id        OR
               OLD.certificate_uid  != NEW.certificate_uid  THEN
                RAISE EXCEPTION
                    'INTEGRITY VIOLATION: Core certificate fields cannot be modified after blockchain confirmation. Certificate UID: %', OLD.certificate_uid;
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_certificates_immutable_fields
    BEFORE UPDATE ON certificates
    FOR EACH ROW
    EXECUTE FUNCTION prevent_immutable_field_change();
    """)

def downgrade():
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
