"""create indexes

Revision ID: 012
Revises: 011
Create Date: 2026-09-04 11:09:53.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # UNIVERSITIES indexes
    op.create_index('idx_universities_is_verified', 'universities', ['is_verified'], postgresql_where=sa.text("is_verified = FALSE"))
    op.create_index('idx_universities_country', 'universities', ['country'])
    op.create_index('idx_universities_is_active', 'universities', ['is_active'], postgresql_where=sa.text("is_active = FALSE"))

    # USERS indexes
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_users_university_id', 'users', ['university_id'], postgresql_where=sa.text('university_id IS NOT NULL'))
    op.create_index('idx_users_is_active', 'users', ['is_active'], postgresql_where=sa.text('is_active = FALSE'))
    op.create_index('idx_users_locked_until', 'users', ['locked_until'], postgresql_where=sa.text('locked_until IS NOT NULL'))
    op.create_index('idx_users_role_university', 'users', ['role', 'university_id'])
    op.create_index('idx_users_created_at', 'users', [sa.text('created_at DESC')])

    # STUDENTS indexes
    op.create_index('idx_students_current_university', 'students', ['current_university_id'], postgresql_where=sa.text('current_university_id IS NOT NULL'))
    op.create_index('idx_students_graduation_year', 'students', ['graduation_year'])
    op.create_index('idx_students_nationality', 'students', ['nationality'])

    # EMPLOYERS indexes
    op.create_index('idx_employers_company_name', 'employers', ['company_name'])
    op.create_index('idx_employers_country', 'employers', ['country'])
    op.create_index('idx_employers_is_verified', 'employers', ['is_verified'], postgresql_where=sa.text('is_verified = FALSE'))

    # CERTIFICATES indexes
    op.create_index('idx_certificates_university_id', 'certificates', ['university_id'])
    op.create_index('idx_certificates_student_id', 'certificates', ['student_id'])
    op.create_index('idx_certificates_issued_by', 'certificates', ['issued_by'])
    op.create_index('idx_certificates_blockchain_status', 'certificates', ['blockchain_status'])
    op.create_index('idx_certificates_issue_date', 'certificates', [sa.text('issue_date DESC')])
    op.create_index('idx_certificates_is_active', 'certificates', ['is_active'], postgresql_where=sa.text('is_active = FALSE'))
    op.create_index('idx_certificates_university_status', 'certificates', ['university_id', 'blockchain_status'])
    op.create_index('idx_certificates_student_active', 'certificates', ['student_id', 'is_active'])
    op.create_index('idx_certificates_university_issue_date', 'certificates', ['university_id', sa.text('issue_date DESC')])
    op.create_index('idx_certificates_created_at', 'certificates', [sa.text('created_at DESC')])
    op.create_index('idx_certificates_metadata_gin', 'certificates', ['extra_metadata'], postgresql_using='gin')

    # BLOCKCHAIN_TRANSACTIONS indexes
    op.create_index('idx_blockchain_tx_certificate_id', 'blockchain_transactions', ['certificate_id'], postgresql_where=sa.text('certificate_id IS NOT NULL'))
    op.create_index('idx_blockchain_tx_status', 'blockchain_transactions', ['status'])
    op.create_index('idx_blockchain_tx_from_address', 'blockchain_transactions', ['from_address'])
    op.create_index('idx_blockchain_tx_network', 'blockchain_transactions', ['network_chain_id', 'status'])
    op.create_index('idx_blockchain_tx_submitted_at', 'blockchain_transactions', [sa.text('submitted_at DESC')])
    op.create_index('idx_blockchain_tx_type_status', 'blockchain_transactions', ['tx_type', 'status'])

    # QR_VERIFICATIONS indexes
    op.create_index('idx_qr_certificate_id', 'qr_verifications', ['certificate_id'])
    op.create_index('idx_qr_is_active', 'qr_verifications', ['is_active'], postgresql_where=sa.text('is_active = TRUE'))
    op.create_index('idx_qr_expires_at', 'qr_verifications', ['expires_at'], postgresql_where=sa.text('expires_at IS NOT NULL'))
    op.create_index('idx_qr_generated_by', 'qr_verifications', ['generated_by'])

    # VERIFICATION_LOGS indexes
    op.create_index('idx_vlog_certificate_id', 'verification_logs', ['certificate_id'], postgresql_where=sa.text('certificate_id IS NOT NULL'))
    op.create_index('idx_vlog_verifier_user_id', 'verification_logs', ['verifier_user_id'], postgresql_where=sa.text('verifier_user_id IS NOT NULL'))
    op.create_index('idx_vlog_result', 'verification_logs', ['result'])
    op.create_index('idx_vlog_verified_at', 'verification_logs', [sa.text('verified_at DESC')])
    op.create_index('idx_vlog_method', 'verification_logs', ['verification_method'])
    op.create_index('idx_vlog_ip_address', 'verification_logs', ['ip_address'])
    op.create_index('idx_vlog_qr_verification_id', 'verification_logs', ['qr_verification_id'], postgresql_where=sa.text('qr_verification_id IS NOT NULL'))
    op.create_index('idx_vlog_certificate_verified_at', 'verification_logs', ['certificate_id', sa.text('verified_at DESC')], postgresql_where=sa.text('certificate_id IS NOT NULL'))
    op.create_index('idx_vlog_result_verified_at', 'verification_logs', ['result', sa.text('verified_at DESC')])
    op.create_index('idx_vlog_tampered_only', 'verification_logs', [sa.text('verified_at DESC')], postgresql_where=sa.text("result = 'TAMPERED'"))

    # REFRESH_TOKENS indexes
    op.create_index('idx_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('idx_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'], postgresql_where=sa.text('is_revoked = FALSE'))

    # AUDIT_LOG indexes
    op.create_index('idx_audit_log_table_record', 'audit_log', ['table_name', 'record_id'])
    op.create_index('idx_audit_log_changed_at', 'audit_log', [sa.text('changed_at DESC')])
    op.create_index('idx_audit_log_operation', 'audit_log', ['operation', 'table_name'])


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported -- migrations are forward-only.")
