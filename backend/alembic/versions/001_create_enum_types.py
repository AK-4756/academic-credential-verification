"""create enum types

Revision ID: 001
Revises: None
Create Date: 2026-09-04 11:09:53.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    
    op.execute("CREATE TYPE user_role AS ENUM ('SUPER_ADMIN', 'UNIVERSITY_ADMIN', 'STUDENT', 'EMPLOYER');")
    op.execute("CREATE TYPE blockchain_status AS ENUM ('PENDING', 'SUBMITTED', 'CONFIRMED', 'FAILED', 'REVOKED');")
    op.execute("CREATE TYPE transaction_type AS ENUM ('STORE_HASH', 'REVOKE_HASH', 'AUTHORIZE_ISSUER');")
    op.execute("CREATE TYPE transaction_status AS ENUM ('PENDING', 'CONFIRMED', 'FAILED', 'REPLACED');")
    op.execute("CREATE TYPE verification_method AS ENUM ('FILE_UPLOAD', 'QR_SCAN', 'MANUAL_ID_LOOKUP');")
    op.execute("CREATE TYPE verification_result AS ENUM ('AUTHENTIC', 'TAMPERED', 'REVOKED', 'NOT_FOUND', 'PENDING_CHAIN', 'ERROR');")
    
    op.execute("""
    CREATE OR REPLACE FUNCTION trigger_set_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)


def downgrade():
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
