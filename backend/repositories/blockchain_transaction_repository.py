# backend/repositories/blockchain_transaction_repository.py
# Data access for the 'blockchain_transactions' table.
#
# Architecture Reference: docs/backend.md Section 5.2 (Repository 06)
# Model Reference: models/blockchain_transaction_model.py
#
# Methods (5 total):
#   Inherited: create (via base), get_by_id, delete, list
#   Domain:    get_by_tx_hash, get_by_certificate_id,
#              update_status, get_pending_transactions

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import TransactionStatus
from models.blockchain_transaction_model import BlockchainTransaction
from repositories.base_repository import BaseRepository

_UTC = timezone.utc


class BlockchainTransactionRepository(BaseRepository[BlockchainTransaction]):
    """Repository for BlockchainTransaction entity tracking on-chain activity."""

    model = BlockchainTransaction

    @classmethod
    async def get_by_tx_hash(
        cls, db: AsyncSession, tx_hash: str
    ) -> BlockchainTransaction | None:
        """
        Fetch a transaction record by Ethereum TX hash (UNIQUE lookup).

        Args:
            db: Async database session.
            tx_hash: Ethereum transaction hash (0x + 64 hex chars).

        Returns:
            The BlockchainTransaction instance, or None if not found.
        """
        stmt = select(BlockchainTransaction).where(
            BlockchainTransaction.tx_hash == tx_hash
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_certificate_id(
        cls, db: AsyncSession, cert_id: uuid.UUID
    ) -> list[BlockchainTransaction]:
        """
        Fetch all blockchain transactions for a certificate.

        A certificate may have multiple transactions (store + revoke).

        Args:
            db: Async database session.
            cert_id: UUID of the certificate.

        Returns:
            List of BlockchainTransaction instances, ordered by submission time.
        """
        stmt = (
            select(BlockchainTransaction)
            .where(BlockchainTransaction.certificate_id == cert_id)
            .order_by(desc(BlockchainTransaction.submitted_at))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def update_status(
        cls,
        db: AsyncSession,
        tx_id: uuid.UUID,
        status: TransactionStatus,
        block_data: dict[str, Any] | None = None,
    ) -> BlockchainTransaction | None:
        """
        Update a blockchain transaction's status and block metadata.

        Called after transaction confirmation or failure.

        Args:
            db: Async database session.
            tx_id: UUID of the transaction record.
            status: New TransactionStatus enum value.
            block_data: Optional dict with block metadata:
                block_number, block_hash, gas_used, gas_price_wei,
                gas_limit, transaction_fee_wei, confirmations_received,
                confirmed_at, failed_at, error_message, revert_reason.

        Returns:
            The updated BlockchainTransaction, or None if not found.
        """
        stmt = select(BlockchainTransaction).where(
            BlockchainTransaction.id == tx_id
        )
        result = await db.execute(stmt)
        tx = result.scalar_one_or_none()
        if tx is None:
            return None
        tx.status = status
        if block_data:
            for key, value in block_data.items():
                if hasattr(tx, key):
                    setattr(tx, key, value)
        await db.flush()
        await db.refresh(tx)
        return tx

    @classmethod
    async def get_pending_transactions(
        cls, db: AsyncSession, older_than_minutes: int
    ) -> list[BlockchainTransaction]:
        """
        Fetch pending transactions older than a threshold.

        Used by the background polling task to detect stale transactions
        that may need retry or manual intervention.

        Args:
            db: Async database session.
            older_than_minutes: Age threshold in minutes.

        Returns:
            List of pending BlockchainTransaction instances older than cutoff.
        """
        cutoff = datetime.now(tz=_UTC) - timedelta(minutes=older_than_minutes)
        stmt = (
            select(BlockchainTransaction)
            .where(
                BlockchainTransaction.status == TransactionStatus.PENDING,
                BlockchainTransaction.submitted_at <= cutoff,
            )
            .order_by(BlockchainTransaction.submitted_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
