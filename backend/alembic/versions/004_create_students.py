"""create students

Revision ID: 004
Revises: 003
Create Date: 2026-09-04 11:09:53.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'students',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('student_id_number', sa.String(length=100), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('nationality', sa.String(length=100), nullable=True),
        sa.Column('gender', sa.String(length=30), nullable=True),
        sa.Column('enrollment_year', sa.SmallInteger(), nullable=True),
        sa.Column('graduation_year', sa.SmallInteger(), nullable=True),
        sa.Column('primary_major', sa.String(length=255), nullable=True),
        sa.Column('secondary_major', sa.String(length=255), nullable=True),
        sa.Column('current_university_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('profile_photo_url', sa.String(length=500), nullable=True),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['current_university_id'], ['universities.id'], onupdate='CASCADE', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("graduation_year IS NULL OR enrollment_year IS NULL OR graduation_year >= enrollment_year", name='chk_students_graduation_after_enrollment'),
        sa.CheckConstraint("enrollment_year IS NULL OR (enrollment_year BETWEEN 1900 AND EXTRACT(YEAR FROM NOW())::INT + 5)", name='chk_students_enrollment_year_range'),
        sa.CheckConstraint("graduation_year IS NULL OR (graduation_year BETWEEN 1900 AND EXTRACT(YEAR FROM NOW())::INT + 10)", name='chk_students_graduation_year_range'),
        sa.CheckConstraint("date_of_birth IS NULL OR (date_of_birth < CURRENT_DATE AND date_of_birth > '1900-01-01')", name='chk_students_dob_reasonable'),
        sa.CheckConstraint("linkedin_url IS NULL OR linkedin_url ~ '^https?://(www\\.)?linkedin\\.com/'", name='chk_students_linkedin_format'),
        comment='Student-specific profile data extending users'
    )
    
    op.execute("""
    CREATE TRIGGER trg_students_updated_at 
    BEFORE UPDATE ON students 
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
    """)


def downgrade():
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
