# backend/models/audit_log_model.py
# ORM model for the 'audit_log' table.
#
# Schema Reference: docs/database.md SUPPLEMENTARY (lines 1687–1704)
# Tracks ALL mutations to sensitive tables for forensic investigation.
# This table is never modified after INSERT — it is the forensic record.

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CHAR, CheckConstraint, Index, String, desc, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, UUIDMixin


class AuditLog(UUIDMixin, Base):
    """
    Universal audit trail for all INSERT/UPDATE/DELETE operations
    on sensitive tables.

    Captures old_values and new_values as JSONB for full change history.
    This table is never modified after INSERT — it is the forensic
    record of record.

    NOTE: Does NOT use TimestampMixin — this table has changed_at
    (not created_at/updated_at) and is append-only.

    Table: audit_log
    """

    __tablename__ = "audit_log"

    # ─── Audit Fields ─────────────────────────────────────────
    table_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Table that was modified"
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="PK of the modified record"
    )
    operation: Mapped[str] = mapped_column(
        CHAR(6), nullable=False, comment="INSERT | UPDATE | DELETE"
    )
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who made the change (app layer, not FK)",
    )
    changed_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        comment="Timestamp of the change",
    )
    old_values: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Row state before change"
    )
    new_values: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="Row state after change"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET, nullable=True, comment="Request IP"
    )
    application_user: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Database role or app-level user ID"
    )

    # ─── Table Args ───────────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "operation IN ('INSERT', 'UPDATE', 'DELETE')",
            name="chk_audit_operation",
        ),
        # Indexes
        Index("idx_audit_log_table_record", "table_name", "record_id"),
        Index("idx_audit_log_changed_at", desc("changed_at")),
        Index("idx_audit_log_operation", "operation", "table_name"),
        {
            "comment": "Universal audit trail for INSERT/UPDATE/DELETE on sensitive tables"
        },
    )
