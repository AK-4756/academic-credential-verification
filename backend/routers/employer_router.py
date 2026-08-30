# backend/routers/employer_router.py
# Employer management endpoints — profile, dashboard, verification history.
#
# Architecture Reference: docs/backend.md Section 12.1 (Employer Service Design)
# Endpoint Catalog: docs/backend.md Section 27.1
#
# Endpoints:
#   GET  /api/v1/employer/profile                           — EMPLOYER
#   PUT  /api/v1/employer/profile                           — EMPLOYER
#   GET  /api/v1/employer/dashboard                         — EMPLOYER
#   GET  /api/v1/employer/verifications                     — EMPLOYER
#   GET  /api/v1/employer/verifications/{verification_id}   — EMPLOYER

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, UserRole
from dependencies import get_db
from dependencies.rbac import require_role
from models.user_model import User
from schemas import (
    EmployerDashboard,
    EmployerProfile,
    EmployerProfileUpdate,
    PaginatedData,
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
    VerificationLogSummary,
)
from services import employer_service

router = APIRouter(prefix="/api/v1/employer", tags=["Employer"])

_require_employer = require_role(UserRole.EMPLOYER)


# ─── GET /profile ─────────────────────────────────────────────────────────────


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(_require_employer),
    db: AsyncSession = Depends(get_db),
):
    """Get employer profile."""
    profile = await employer_service.get_employer_profile(
        user_id=current_user.id,
        db=db,
    )

    return SuccessResponse(data=EmployerProfile.model_validate(profile))


# ─── PUT /profile ─────────────────────────────────────────────────────────────


@router.put("/profile")
async def update_profile(
    body: EmployerProfileUpdate,
    current_user: User = Depends(_require_employer),
    db: AsyncSession = Depends(get_db),
):
    """Update employer profile."""
    updated = await employer_service.update_employer_profile(
        user_id=current_user.id,
        update_data=body.model_dump(exclude_unset=True),
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(
        data=EmployerProfile.model_validate(updated),
        message="Profile updated successfully",
    )


# ─── GET /dashboard ──────────────────────────────────────────────────────────


@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(_require_employer),
    db: AsyncSession = Depends(get_db),
):
    """Get employer dashboard data."""
    result = await employer_service.get_employer_dashboard(
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(data=result)


# ─── GET /verifications ──────────────────────────────────────────────────────


@router.get("/verifications")
async def list_verifications(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: User = Depends(_require_employer),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated verification history."""
    skip = (page - 1) * limit

    logs, total = await employer_service.get_verification_history(
        current_user=current_user,
        skip=skip,
        limit=limit,
        db=db,
    )

    items = [VerificationLogSummary.model_validate(log) for log in logs]
    pagination = PaginationMeta.build(total=total, page=page, limit=limit)

    return PaginatedResponse(
        data=PaginatedData(items=items, pagination=pagination),
    )


# ─── GET /verifications/{verification_id} ────────────────────────────────────


@router.get("/verifications/{verification_id}")
async def get_verification(
    verification_id: UUID,
    current_user: User = Depends(_require_employer),
    db: AsyncSession = Depends(get_db),
):
    """Get verification detail (ownership check in service)."""
    log = await employer_service.get_verification_detail(
        verification_id=verification_id,
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(data=log)
