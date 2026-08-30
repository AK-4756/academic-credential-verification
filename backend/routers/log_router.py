# backend/routers/log_router.py
# Verification log endpoints — query audit logs.
#
# Architecture Reference: docs/backend.md Section 16.1 (Verification logging)
# Endpoint Catalog: docs/backend.md Section 27.1
#
# Endpoints:
#   GET /api/v1/logs/                  — UNIVERSITY_ADMIN
#   GET /api/v1/logs/{certificate_id}  — UNIVERSITY_ADMIN or STUDENT

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, UserRole
from core.exceptions import (
    CertificateNotFoundError,
    OwnershipViolationError,
)
from dependencies import get_current_active_user, get_db, require_university_admin
from models.user_model import User
from repositories import CertificateRepository, StudentRepository
from schemas import (
    PaginatedData,
    PaginatedResponse,
    PaginationMeta,
    VerificationLogDetail,
    VerificationLogSummary,
)
from services import verification_log_service

router = APIRouter(prefix="/api/v1/logs", tags=["Verification Logs"])


# ─── GET / ────────────────────────────────────────────────────────────────────


@router.get("/")
async def list_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List verification logs for the admin's university certificates.

    Filters logs to only show verifications of certificates
    issued by the current user's university.
    """
    skip = (page - 1) * limit

    # Get all certificates for the admin's university to get their IDs
    certs, total_certs = await CertificateRepository.get_by_university(
        db, current_user.university_id, skip=0, limit=10000
    )
    cert_ids = [c.id for c in certs]

    # Aggregate logs for all university certificates
    all_logs = []
    total = 0
    for cert_id in cert_ids:
        logs, count = await verification_log_service.get_logs_for_certificate(
            certificate_id=cert_id,
            skip=0,
            limit=10000,
            db=db,
        )
        all_logs.extend(logs)
        total += count

    # Sort by verified_at descending, then paginate in-memory
    all_logs.sort(key=lambda x: x.verified_at, reverse=True)
    page_logs = all_logs[skip : skip + limit]

    items = [VerificationLogSummary.model_validate(log) for log in page_logs]
    pagination = PaginationMeta.build(total=total, page=page, limit=limit)

    return PaginatedResponse(
        data=PaginatedData(items=items, pagination=pagination),
    )


# ─── GET /{certificate_id} ───────────────────────────────────────────────────


@router.get("/{certificate_id}")
async def get_certificate_logs(
    certificate_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get verification logs for a specific certificate.

    Accessible by UNIVERSITY_ADMIN (certificate ownership)
    or STUDENT (certificate ownership).
    """
    # Load certificate and verify ownership
    cert = await CertificateRepository.get_by_id(db, certificate_id)
    if cert is None:
        raise CertificateNotFoundError()

    if current_user.role == UserRole.UNIVERSITY_ADMIN:
        if cert.university_id != current_user.university_id:
            raise OwnershipViolationError()
    elif current_user.role == UserRole.STUDENT:
        student = await StudentRepository.get_by_user_id(db, current_user.id)
        if student is None or cert.student_id != student.id:
            raise OwnershipViolationError()
    else:
        raise OwnershipViolationError()

    skip = (page - 1) * limit
    logs, total = await verification_log_service.get_logs_for_certificate(
        certificate_id=certificate_id,
        skip=skip,
        limit=limit,
        db=db,
    )

    items = [VerificationLogDetail.model_validate(log) for log in logs]
    pagination = PaginationMeta.build(total=total, page=page, limit=limit)

    return PaginatedResponse(
        data=PaginatedData(items=items, pagination=pagination),
    )
