# backend/routers/certificate_router.py
# Certificate management endpoints — issuance, listing, detail, revocation.
#
# Architecture Reference: docs/backend.md Sections 14.1, 15.1
# Endpoint Catalog: docs/backend.md Section 27.1
#
# Endpoints:
#   POST /api/v1/certificates/upload                         — UNIVERSITY_ADMIN, RATE_LIMIT_CERTIFICATE_UPLOAD
#   POST /api/v1/certificates/confirm-hash                   — UNIVERSITY_ADMIN
#   GET  /api/v1/certificates/                               — UNIVERSITY_ADMIN
#   GET  /api/v1/certificates/{certificate_id}               — UNIVERSITY_ADMIN or STUDENT
#   POST /api/v1/certificates/{certificate_id}/revoke        — UNIVERSITY_ADMIN
#   POST /api/v1/certificates/{certificate_id}/confirm-revocation — UNIVERSITY_ADMIN

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import (
    ALLOWED_MIME_TYPES,
    DEFAULT_PAGE_SIZE,
    MAX_FILE_SIZE_BYTES,
    MAX_PAGE_SIZE,
    RATE_LIMIT_CERTIFICATE_UPLOAD,
    UserRole,
)
from core.exceptions import InvalidFileTypeError, FileTooLargeError, ServiceError
from dependencies import get_current_active_user, get_db, limiter, require_university_admin
from models.user_model import User
from repositories import CertificateRepository
from schemas import (
    CertificateDetail,
    CertificateDraftResponse,
    CertificateRevokedResponse,
    CertificateSummary,
    ConfirmHashRequest,
    ConfirmRevocationRequest,
    PaginatedData,
    PaginatedResponse,
    PaginationMeta,
    RevocationInitiatedResponse,
    RevokeRequest,
    SuccessResponse,
)
from services import certificate_issuance_service, certificate_revocation_service

router = APIRouter(prefix="/api/v1/certificates", tags=["Certificate"])


# ─── POST /upload ─────────────────────────────────────────────────────────────


@router.post("/upload", status_code=201)
@limiter.limit(RATE_LIMIT_CERTIFICATE_UPLOAD)
async def upload_certificate(
    request: Request,
    recipient_email: str = File(...),
    degree_title: str = File(...),
    field_of_study: str = File(...),
    issue_date: str = File(...),
    expiry_date: str | None = File(default=None),
    grade_classification: str | None = File(default=None),
    honors: str | None = File(default=None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Phase 1: Upload and hash a certificate PDF.

    multipart/form-data with PDF file + metadata fields.
    """
    # Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise InvalidFileTypeError()

    # Read file bytes
    file_bytes = await file.read()

    # Validate file size
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError()

    if len(file_bytes) == 0:
        raise ServiceError(message="File is empty")

    # Build metadata dict from form fields
    from datetime import date as date_type

    metadata = {
        "recipient_email": recipient_email,
        "degree_title": degree_title,
        "field_of_study": field_of_study,
        "issue_date": date_type.fromisoformat(issue_date),
    }
    if expiry_date:
        metadata["expiry_date"] = date_type.fromisoformat(expiry_date)
    if grade_classification:
        metadata["grade_classification"] = grade_classification
    if honors:
        metadata["honors"] = honors

    result = await certificate_issuance_service.upload_and_hash_certificate(
        file_bytes=file_bytes,
        file_original_name=file.filename or "certificate.pdf",
        metadata=metadata,
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(
        data=CertificateDraftResponse(**result),
        message="Certificate uploaded and hashed successfully",
    )


# ─── POST /confirm-hash ──────────────────────────────────────────────────────


@router.post("/confirm-hash")
async def confirm_hash(
    body: ConfirmHashRequest,
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Phase 2: Confirm blockchain storage after MetaMask TX.
    """
    result = await certificate_issuance_service.confirm_blockchain_storage(
        cert_id=body.certificate_id,
        blockchain_tx_hash=body.blockchain_tx_hash,
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(data=result, message="Certificate confirmed on blockchain")


# ─── GET / ────────────────────────────────────────────────────────────────────


@router.get("/")
async def list_certificates(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    status: str | None = Query(default=None),
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """List certificates issued by the admin's university."""
    skip = (page - 1) * limit
    filters = {}
    if status:
        filters["blockchain_status"] = status

    certs, total = await CertificateRepository.get_by_university(
        db, current_user.university_id, skip=skip, limit=limit, filters=filters
    )

    items = [CertificateSummary.model_validate(c) for c in certs]
    pagination = PaginationMeta.build(total=total, page=page, limit=limit)

    return PaginatedResponse(
        data=PaginatedData(items=items, pagination=pagination),
    )


# ─── GET /{certificate_id} ───────────────────────────────────────────────────


@router.get("/{certificate_id}")
async def get_certificate(
    certificate_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get certificate detail.

    Accessible by UNIVERSITY_ADMIN (ownership) or STUDENT (ownership).
    """
    from core.exceptions import CertificateNotFoundError, OwnershipViolationError
    from repositories import StudentRepository

    cert = await CertificateRepository.get_by_id(db, certificate_id)
    if cert is None:
        raise CertificateNotFoundError()

    # Ownership check: university admin or student
    if current_user.role == UserRole.UNIVERSITY_ADMIN:
        if cert.university_id != current_user.university_id:
            raise OwnershipViolationError()
    elif current_user.role == UserRole.STUDENT:
        student = await StudentRepository.get_by_user_id(db, current_user.id)
        if student is None or cert.student_id != student.id:
            raise OwnershipViolationError()
    else:
        raise OwnershipViolationError()

    return SuccessResponse(data=CertificateDetail.model_validate(cert))


# ─── POST /{certificate_id}/revoke ───────────────────────────────────────────


@router.post("/{certificate_id}/revoke")
async def revoke_certificate(
    certificate_id: UUID,
    body: RevokeRequest,
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """Phase 1: Initiate certificate revocation."""
    result = await certificate_revocation_service.initiate_revocation(
        cert_id=certificate_id,
        reason=body.reason,
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(
        data=RevocationInitiatedResponse(**result),
        message="Revocation initiated",
    )


# ─── POST /{certificate_id}/confirm-revocation ───────────────────────────────


@router.post("/{certificate_id}/confirm-revocation")
async def confirm_revocation(
    certificate_id: UUID,
    body: ConfirmRevocationRequest,
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """Phase 2: Confirm revocation after MetaMask TX."""
    result = await certificate_revocation_service.confirm_revocation(
        cert_id=certificate_id,
        blockchain_tx_hash=body.blockchain_tx_hash,
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(
        data=CertificateRevokedResponse(**result),
        message="Certificate revoked",
    )
