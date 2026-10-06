"""create triggers

Revision ID: 013
Revises: 012
Create Date: 2026-09-04 11:09:53.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. prevent_verification_log_update function
    op.execute("""
CREATE OR REPLACE FUNCTION prevent_verification_log_update()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'INTEGRITY VIOLATION: verification_logs is append-only. '
        'Updates are not permitted. Log ID: %', OLD.id;
END;
$$ LANGUAGE plpgsql;
    """)

    # 2. trg_verification_logs_no_update trigger
    op.execute("""
CREATE TRIGGER trg_verification_logs_no_update
    BEFORE UPDATE ON verification_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_verification_log_update();
    """)

    # 3. prevent_verification_log_delete function
    op.execute("""
CREATE OR REPLACE FUNCTION prevent_verification_log_delete()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'INTEGRITY VIOLATION: verification_logs is append-only. '
        'Deletes are not permitted. Log ID: %', OLD.id;
END;
$$ LANGUAGE plpgsql;
    """)

    # 4. trg_verification_logs_no_delete trigger
    op.execute("""
CREATE TRIGGER trg_verification_logs_no_delete
    BEFORE DELETE ON verification_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_verification_log_delete();
    """)

    # 5. prevent_audit_log_update function
    op.execute("""
CREATE OR REPLACE FUNCTION prevent_audit_log_update()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'INTEGRITY VIOLATION: audit_log is immutable. '
        'Modifications are not permitted. Audit entry ID: %', OLD.id;
END;
$$ LANGUAGE plpgsql;
    """)

    # 6. trg_audit_log_immutable trigger
    op.execute("""
CREATE TRIGGER trg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_log_update();
    """)


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
