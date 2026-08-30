# backend/routers/university_router.py
# University management endpoints — list, detail, wallet, dashboard.
#
# Architecture Reference: docs/backend.md Section 10.1 (University Service Design)
# Endpoint Catalog: docs/backend.md Section 27.1
#
# Endpoints:
#   GET  /api/v1/universities/                       — UNIVERSITY_ADMIN
#   GET  /api/v1/universities/{university_id}        — UNIVERSITY_ADMIN
#   PUT  /api/v1/universities/{university_id}/wallet  — UNIVERSITY_ADMIN (ownership)
#   GET  /api/v1/universities/{university_id}/dashboard — UNIVERSITY_ADMIN (ownership)

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from dependencies import get_db, require_university_admin
from models.user_model import User
from repositories import UniversityRepository
from schemas import (
    SuccessResponse,
    PaginatedResponse,
    PaginatedData,
    PaginationMeta,
    UniversityDetail,
    UniversityDashboard,
    UniversitySummary,
    WalletUpdateRequest,
)
from services import university_service

router = APIRouter(prefix="/api/v1/universities", tags=["University"])


# ─── GET / ────────────────────────────────────────────────────────────────────


@router.get("/")
async def list_universities(
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    is_verified: bool | None = Query(default=None),
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """List universities."""
    skip = (page - 1) * limit
    filters = {}
    if is_verified is not None:
        filters["is_verified"] = is_verified

    universities, total = await UniversityRepository.list(
        db, filters=filters, skip=skip, limit=limit
    )

    items = [UniversitySummary.model_validate(u) for u in universities]
    pagination = PaginationMeta.build(total=total, page=page, limit=limit)

    return PaginatedResponse(
        data=PaginatedData(items=items, pagination=pagination),
    )


# ─── GET /{university_id} ────────────────────────────────────────────────────


@router.get("/{university_id}")
async def get_university(
    university_id: UUID,
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get university detail."""
    from core.exceptions import UniversityNotFoundError

    university = await UniversityRepository.get_by_id(db, university_id)
    if university is None:
        raise UniversityNotFoundError()

    return SuccessResponse(
        data=UniversityDetail.model_validate(university),
    )


# ─── PUT /{university_id}/wallet ──────────────────────────────────────────────


@router.put("/{university_id}/wallet")
async def update_wallet(
    university_id: UUID,
    body: WalletUpdateRequest,
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update university wallet address (ownership check in service)."""
    university = await university_service.update_wallet_address(
        university_id=university_id,
        wallet_address=body.wallet_address,
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(
        data=UniversityDetail.model_validate(university),
        message="Wallet address updated successfully",
    )


# ─── GET /{university_id}/dashboard ──────────────────────────────────────────


@router.get("/{university_id}/dashboard")
async def get_dashboard(
    university_id: UUID,
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get university dashboard data (ownership check in service)."""
    dashboard = await university_service.get_university_dashboard_data(
        university_id=university_id,
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(data=dashboard)
