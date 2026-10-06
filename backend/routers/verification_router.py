# backend/routers/verification_router.py
# Verification endpoints — file upload, QR scan, result retrieval.
#
# Architecture Reference: docs/backend.md Section 16.1 (Verification Service)
# Endpoint Catalog: docs/backend.md Section 27.1
#
# Endpoints:
#   POST /api/v1/verify/upload               — EMPLOYER, RATE_LIMIT_VERIFY_UPLOAD
#   GET  /api/v1/verify/qr/{token}           — Public, RATE_LIMIT_QR_SCAN
#   GET  /api/v1/verify/result/{verification_id} — EMPLOYER

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import (
    MAX_VERIFICATION_FILE_SIZE_BYTES,
    RATE_LIMIT_QR_SCAN,
    RATE_LIMIT_VERIFY_UPLOAD,
    UserRole,
)
from core.exceptions import FileTooLargeError, InvalidFileTypeError, ServiceError
from dependencies import get_db, limiter
from dependencies.services import get_blockchain_service
from dependencies.rbac import require_role
from models.user_model import User
from schemas import (
    PublicVerificationResult,
    SuccessResponse,
    VerificationResponse,
)
from services import employer_service, verification_service

router = APIRouter(prefix="/api/v1/verify", tags=["Verification"])

_require_employer = require_role(UserRole.EMPLOYER)


# ─── POST /upload ─────────────────────────────────────────────────────────────


@router.post("/upload")
@limiter.limit(RATE_LIMIT_VERIFY_UPLOAD)
async def verify_by_upload(
    request: Request,
    file: UploadFile = File(...),
    certificate_uid: str | None = Query(default=None),
    current_user: User = Depends(_require_employer),
    db: AsyncSession = Depends(get_db),
    blockchain_service=Depends(get_blockchain_service),
):
    """
    Verify a certificate by uploading the PDF file.

    Computes SHA-256 hash and verifies against blockchain.
    """
    # Validate file type
    if file.content_type not in {"application/pdf"}:
        raise InvalidFileTypeError()

    # Read file bytes
    file_bytes = await file.read()

    # Validate size
    if len(file_bytes) > MAX_VERIFICATION_FILE_SIZE_BYTES:
        raise FileTooLargeError()

    if len(file_bytes) == 0:
        raise ServiceError(message="File is empty")

    result = await verification_service.verify_by_file_upload(
        file_bytes=file_bytes,
        cert_uid_hint=certificate_uid,
        current_user=current_user,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        db=db,
        blockchain_service=blockchain_service,
    )

    return SuccessResponse(data=result)


# ─── GET /qr/{token} ─────────────────────────────────────────────────────────


@router.get("/qr/{token}")
@limiter.limit(RATE_LIMIT_QR_SCAN)
async def verify_by_qr(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
    blockchain_service=Depends(get_blockchain_service),
):
    """
    Verify a certificate via QR token (public, no auth required).

    The opaque token acts as access control.
    """
    result = await verification_service.verify_by_qr_token(
        token=token,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        db=db,
        blockchain_service=blockchain_service,
    )

    return PublicVerificationResult(
        result=result["result"],
        certificate=result.get("certificate"),
        blockchain_proof=result.get("blockchain_proof"),
        verified_at=result["verified_at"],
        processing_time_ms=result["processing_time_ms"],
    )


# ─── GET /result/{verification_id} ───────────────────────────────────────────


@router.get("/result/{verification_id}")
async def get_verification_result(
    verification_id: UUID,
    current_user: User = Depends(_require_employer),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve past verification result (ownership check in service)."""
    log = await employer_service.get_verification_detail(
        verification_id=verification_id,
        current_user=current_user,
        db=db,
    )

    return SuccessResponse(data=log)
