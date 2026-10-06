"""create users

Revision ID: 003
Revises: 002
Create Date: 2026-09-04 11:09:53.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('SUPER_ADMIN', 'UNIVERSITY_ADMIN', 'STUDENT', 'EMPLOYER', name='user_role', create_type=False), nullable=False),
        sa.Column('university_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=30), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email_verify_token', sa.String(length=128), nullable=True),
        sa.Column('email_verify_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_ip', postgresql.INET(), nullable=True),
        sa.Column('failed_login_attempts', sa.SmallInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reset_token_hash', sa.String(length=64), nullable=True),
        sa.Column('reset_token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['university_id'], ['universities.id'], onupdate='CASCADE', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("email ~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'", name='chk_users_email_format'),
        sa.CheckConstraint("email = LOWER(email)", name='chk_users_email_lowercase'),
        sa.CheckConstraint("LENGTH(TRIM(first_name)) > 0 AND LENGTH(TRIM(last_name)) > 0", name='chk_users_names_not_empty'),
        sa.CheckConstraint("role != 'UNIVERSITY_ADMIN' OR university_id IS NOT NULL", name='chk_users_university_admin_requires_university'),
        sa.CheckConstraint("role != 'STUDENT' OR university_id IS NULL", name='chk_users_student_no_university'),
        sa.CheckConstraint("role != 'EMPLOYER' OR university_id IS NULL", name='chk_users_employer_no_university'),
        sa.CheckConstraint("failed_login_attempts >= 0", name='chk_users_failed_attempts_non_negative'),
        sa.CheckConstraint("(is_email_verified = FALSE AND email_verified_at IS NULL) OR (is_email_verified = TRUE AND email_verified_at IS NOT NULL)", name='chk_users_email_verified_consistency'),
        sa.CheckConstraint("locked_until IS NULL OR locked_until > created_at", name='chk_users_lock_consistency'),
        comment='Central authentication identity for all actors'
    )
    
    op.execute("""
    CREATE TRIGGER trg_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
    """)


def downgrade():
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
