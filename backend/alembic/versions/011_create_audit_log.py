"""create_audit_log

Revision ID: 011
Revises: 010
Create Date: 2026-09-04 11:09:53.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('table_name', sa.String(length=100), nullable=False),
        sa.Column('record_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operation', sa.CHAR(length=6), nullable=False),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('old_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_values', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('application_user', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("operation IN ('INSERT', 'UPDATE', 'DELETE')", name='chk_audit_operation'),
        comment='Universal audit trail for INSERT/UPDATE/DELETE on sensitive tables'
    )

    op.execute("""
    CREATE OR REPLACE FUNCTION audit_trigger_function()
    RETURNS TRIGGER AS $$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            INSERT INTO audit_log (
                table_name, record_id, operation, new_values, application_user
            )
            VALUES (
                TG_TABLE_NAME,
                NEW.id,
                'INSERT',
                row_to_json(NEW)::JSONB,
                current_user
            );
            RETURN NEW;
        ELSIF TG_OP = 'UPDATE' THEN
            INSERT INTO audit_log (
                table_name, record_id, operation, old_values, new_values, application_user
            )
            VALUES (
                TG_TABLE_NAME,
                NEW.id,
                'UPDATE',
                row_to_json(OLD)::JSONB,
                row_to_json(NEW)::JSONB,
                current_user
            );
            RETURN NEW;
        ELSIF TG_OP = 'DELETE' THEN
            INSERT INTO audit_log (
                table_name, record_id, operation, old_values, application_user
            )
            VALUES (
                TG_TABLE_NAME,
                OLD.id,
                'DELETE',
                row_to_json(OLD)::JSONB,
                current_user
            );
            RETURN OLD;
        END IF;
        RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("CREATE TRIGGER trg_audit_universities AFTER INSERT OR UPDATE OR DELETE ON universities FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();")
    op.execute("CREATE TRIGGER trg_audit_users AFTER INSERT OR UPDATE OR DELETE ON users FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();")
    op.execute("CREATE TRIGGER trg_audit_certificates AFTER INSERT OR UPDATE OR DELETE ON certificates FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();")
    op.execute("CREATE TRIGGER trg_audit_qr_verifications AFTER INSERT OR UPDATE OR DELETE ON qr_verifications FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();")

def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
