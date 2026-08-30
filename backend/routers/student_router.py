# backend/routers/student_router.py
# Student credential endpoints — listing, detail, download, share, dashboard.
#
# Architecture Reference: docs/backend.md Section 11.1 (Student Service Design)
# Endpoint Catalog: docs/backend.md Section 27.1
#
# Endpoints:
#   GET  /api/v1/student/credentials                              — STUDENT
#   GET  /api/v1/student/credentials/{certificate_id}             — STUDENT
#   GET  /api/v1/student/credentials/{certificate_id}/download    — STUDENT
#   POST /api/v1/student/credentials/{certificate_id}/share       — STUDENT
#   GET  /api/v1/student/dashboard                                — STUDENT

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, UserRole
from core.exceptions import CertificateNotFoundError, FileNotFoundOnDiskError
from dependencies import get_db
from dependencies.rbac import require_role
from models.user_model import User
from repositories import CertificateRepository, StudentRepository
from schemas import (
    CredentialSummary,
    PaginatedData,
    PaginatedResponse,
    PaginationMeta,
    ShareLinkResponse,
    SuccessResponse,
)
from services import student_credential_service

router = APIRouter(prefix="/api/v1/student", tags=["Student"])

_require_student = require_role(UserRole.STUDENT)


# ─── GET /credentials ────────────────────────────────────────────────────────


@router.get("/credentials")
async def list_credentials(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    current_user: User = Depends(_require_student),
    db: AsyncSession = Depends(get_db),
):
    """List all credentials for the authenticated student."""
    all_certs = await student_credential_service.get_my_credentials(
        student_id=current_user.id,
        db=db,
    )

    # In-memory pagination (student cert counts are small)
    total = len(all_certs)
    skip = (page - 1) * limit
    page_certs = all_certs[skip : skip + limit]

    items = [CredentialSummary.model_validate(c) for c in page_certs]
    pagination = PaginationMeta.build(total=total, page=page, limit=limit)

    return PaginatedResponse(
        data=PaginatedData(items=items, pagination=pagination),
    )


# ─── GET /credentials/{certificate_id} ───────────────────────────────────────


@router.get("/credentials/{certificate_id}")
async def get_credential(
    certificate_id: UUID,
    current_user: User = Depends(_require_student),
    db: AsyncSession = Depends(get_db),
):
    """Get credential detail (ownership check in service)."""
    result = await student_credential_service.get_credential_detail(
        cert_id=certificate_id,
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(data=result)


# ─── GET /credentials/{certificate_id}/download ──────────────────────────────


@router.get("/credentials/{certificate_id}/download")
async def download_credential(
    certificate_id: UUID,
    current_user: User = Depends(_require_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Download certificate PDF (ownership check + CONFIRMED status).

    Returns FileResponse with Content-Disposition: attachment.
    """
    from core.constants import BlockchainStatus
    from core.exceptions import OwnershipViolationError, UnconfirmedCertificateError

    cert = await CertificateRepository.get_by_id(db, certificate_id)
    if cert is None:
        raise CertificateNotFoundError()

    # Ownership check
    student = await StudentRepository.get_by_user_id(db, current_user.id)
    if student is None or cert.student_id != student.id:
        raise OwnershipViolationError()

    # Must be CONFIRMED
    if cert.blockchain_status != BlockchainStatus.CONFIRMED:
        raise UnconfirmedCertificateError()

    # Build file path
    file_path = Path(settings.UPLOAD_ROOT) / cert.file_path
    if not file_path.exists():
        raise FileNotFoundOnDiskError()

    filename = f"{cert.certificate_uid}.pdf"
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── POST /credentials/{certificate_id}/share ────────────────────────────────


@router.post("/credentials/{certificate_id}/share")
async def share_credential(
    certificate_id: UUID,
    current_user: User = Depends(_require_student),
    db: AsyncSession = Depends(get_db),
):
    """Get or generate a share link for a credential (ownership in service)."""
    result = await student_credential_service.get_share_link(
        cert_id=certificate_id,
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(data=result)


# ─── GET /dashboard ──────────────────────────────────────────────────────────


@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(_require_student),
    db: AsyncSession = Depends(get_db),
):
    """Get student dashboard data."""
    result = await student_credential_service.get_student_dashboard(
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(data=result)
