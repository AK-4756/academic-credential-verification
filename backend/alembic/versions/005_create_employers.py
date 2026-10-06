"""create employers

Revision ID: 005
Revises: 004
Create Date: 2026-09-04 11:09:53.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'employers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('company_name', sa.String(length=300), nullable=False),
        sa.Column('company_website', sa.String(length=500), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('company_size', sa.String(length=50), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('job_title', sa.String(length=150), nullable=True),
        sa.Column('department', sa.String(length=150), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("LENGTH(TRIM(company_name)) > 0", name='chk_employers_company_name_not_empty'),
        sa.CheckConstraint("company_website IS NULL OR company_website ~ '^https?://'", name='chk_employers_website_format'),
        sa.CheckConstraint("(is_verified = FALSE AND verified_at IS NULL) OR (is_verified = TRUE AND verified_at IS NOT NULL)", name='chk_employers_verified_consistency'),
        sa.CheckConstraint("company_size IS NULL OR company_size IN ('1-10', '11-50', '51-200', '201-500', '501-1000', '1001-5000', '5000+')", name='chk_employers_company_size_values'),
        comment='Employer-specific profile data extending users'
    )
    
    op.execute("""
    CREATE TRIGGER trg_employers_updated_at 
    BEFORE UPDATE ON employers 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
    """)


def downgrade():
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
