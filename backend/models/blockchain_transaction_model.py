# backend/models/blockchain_transaction_model.py
# ORM model for the 'blockchain_transactions' table.
#
# Schema Reference: docs/database.md TABLE 6 (lines 1216–1324)

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    desc,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import TransactionStatus, TransactionType
from database.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.certificate_model import Certificate


class BlockchainTransaction(UUIDMixin, TimestampMixin, Base):
    """
    Records every Ethereum transaction interacting with the CertificateRegistry.

    A certificate may have multiple TX records if initial attempts fail.
    The CONFIRMED TX with matching certificate_hash_stored is the authoritative record.

    Table: blockchain_transactions
    """

    __tablename__ = "blockchain_transactions"

    # ─── Link to Certificate ──────────────────────────────────
    certificate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("certificates.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        comment="NULL for AUTHORIZE_ISSUER TXs",
    )

    # ─── Transaction Identity ─────────────────────────────────
    tx_hash: Mapped[Optional[str]] = mapped_column(
        String(66),
        nullable=True,
        unique=True,
        comment="Ethereum TX hash (0x + 64 hex chars). NULL while status=PENDING.",
    )
    tx_type: Mapped[TransactionType] = mapped_column(
        ENUM(TransactionType, name="transaction_type", create_type=False),
        nullable=False,
        comment="STORE_HASH | REVOKE_HASH | AUTHORIZE_ISSUER",
    )

    # ─── Parties ──────────────────────────────────────────────
    from_address: Mapped[str] = mapped_column(
        String(42), nullable=False, comment="Sender wallet address"
    )
    to_address: Mapped[str] = mapped_column(
        String(42), nullable=False, comment="Recipient/contract address"
    )
    contract_address: Mapped[str] = mapped_column(
        String(42), nullable=False, comment="Smart contract address"
    )

    # ─── Block Data ───────────────────────────────────────────
    block_number: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="Block number (set after confirmation)"
    )
    block_hash: Mapped[Optional[str]] = mapped_column(
        String(66), nullable=True, comment="Block hash"
    )

    # ─── Gas Economics ────────────────────────────────────────
    gas_used: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="Gas consumed by TX"
    )
    gas_price_wei: Mapped[Optional[int]] = mapped_column(
        Numeric(30, 0), nullable=True, comment="Gas price in Wei (NUMERIC for precision)"
    )
    gas_limit: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="Gas limit set for TX"
    )
    transaction_fee_wei: Mapped[Optional[int]] = mapped_column(
        Numeric(30, 0), nullable=True, comment="Total fee in Wei"
    )

    # ─── Network Identity ─────────────────────────────────────
    network_name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Network name (e.g. hardhat, mainnet)"
    )
    network_chain_id: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="EVM chain ID"
    )

    # ─── Payload ──────────────────────────────────────────────
    certificate_hash_stored: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="sha256_hash passed to smart contract in this TX",
    )

    # ─── Transaction Status ───────────────────────────────────
    status: Mapped[TransactionStatus] = mapped_column(
        ENUM(TransactionStatus, name="transaction_status", create_type=False),
        nullable=False,
        default=TransactionStatus.PENDING,
        server_default="PENDING",
        comment="PENDING | CONFIRMED | FAILED | REPLACED",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Error message if failed"
    )
    revert_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Smart contract revert reason"
    )

    # ─── Confirmation Tracking ────────────────────────────────
    confirmations_required: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default="1",
        comment="Required block confirmations",
    )
    confirmations_received: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0",
        comment="Current confirmations count",
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        comment="TX submission timestamp",
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Confirmation timestamp"
    )
    failed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Failure timestamp"
    )

    # ─── Relationships ────────────────────────────────────────
    certificate: Mapped[Optional[Certificate]] = relationship(
        "Certificate", back_populates="blockchain_transactions", lazy="selectin"
    )

    # ─── Table Args ───────────────────────────────────────────
    __table_args__ = (
        CheckConstraint(
            "tx_hash ~ '^0x[0-9a-fA-F]{64}$'",
            name="chk_blockchain_tx_hash_format",
        ),
        CheckConstraint(
            "from_address ~ '^0x[0-9a-fA-F]{40}$'",
            name="chk_blockchain_from_address_format",
        ),
        CheckConstraint(
            "to_address ~ '^0x[0-9a-fA-F]{40}$'",
            name="chk_blockchain_to_address_format",
        ),
        CheckConstraint(
            "contract_address ~ '^0x[0-9a-fA-F]{40}$'",
            name="chk_blockchain_contract_address_format",
        ),
        CheckConstraint(
            "block_number IS NULL OR block_number > 0",
            name="chk_blockchain_block_number_positive",
        ),
        CheckConstraint(
            "gas_used IS NULL OR gas_used > 0",
            name="chk_blockchain_gas_used_positive",
        ),
        CheckConstraint(
            "confirmations_received >= 0 AND confirmations_required >= 1",
            name="chk_blockchain_confirmations_non_negative",
        ),
        CheckConstraint(
            "network_chain_id > 0",
            name="chk_blockchain_chain_id_positive",
        ),
        CheckConstraint(
            "status != 'CONFIRMED' "
            "OR (block_number IS NOT NULL AND confirmed_at IS NOT NULL)",
            name="chk_blockchain_confirmed_has_block",
        ),
        CheckConstraint(
            "certificate_hash_stored IS NULL "
            "OR certificate_hash_stored ~ '^[0-9a-f]{64}$'",
            name="chk_blockchain_hash_stored_format",
        ),
        CheckConstraint(
            "(gas_used IS NULL AND transaction_fee_wei IS NULL) "
            "OR (gas_used IS NOT NULL AND gas_price_wei IS NOT NULL "
            "AND transaction_fee_wei IS NOT NULL)",
            name="chk_blockchain_fee_consistency",
        ),
        # Indexes
        Index(
            "idx_blockchain_tx_certificate_id",
            "certificate_id",
            postgresql_where="certificate_id IS NOT NULL",
        ),
        Index("idx_blockchain_tx_status", "status"),
        Index("idx_blockchain_tx_from_address", "from_address"),
        Index("idx_blockchain_tx_network", "network_chain_id", "status"),
        Index("idx_blockchain_tx_submitted_at", desc("submitted_at")),
        Index("idx_blockchain_tx_type_status", "tx_type", "status"),
        {"comment": "Ethereum transaction records for CertificateRegistry"},
    )
