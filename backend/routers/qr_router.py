# backend/routers/qr_router.py
# QR code endpoints — generate QR for certificate, serve QR image.
#
# Architecture Reference: docs/backend.md Section 17.1 (QR Verification Service)
# Endpoint Catalog: docs/backend.md Section 27.1
#
# Endpoints:
#   POST /api/v1/qr/generate/{certificate_id}  — UNIVERSITY_ADMIN
#   GET  /api/v1/qr/{token}/image               — Public

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import QRTokenNotFoundError
from dependencies import get_db, require_university_admin
from models.user_model import User
from schemas import QRCodeResponse, SuccessResponse
from services import qr_verification_service
from utils.qr_image_generator import get_qr_image_path, save_qr_image_for_token

router = APIRouter(prefix="/api/v1/qr", tags=["QR Code"])


# ─── POST /generate/{certificate_id} ─────────────────────────────────────────


@router.post("/generate/{certificate_id}")
async def generate_qr(
    certificate_id: UUID,
    current_user: User = Depends(require_university_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a QR code for a CONFIRMED certificate.

    Deactivates any existing active QR for the certificate.
    Generates a new token and PNG image.
    """
    result = await qr_verification_service.generate_qr_for_certificate(
        cert_id=certificate_id,
        generated_by_user_id=current_user.id,
        db=db,
    )

    # Generate QR image file
    save_qr_image_for_token(
        token=result["token"],
        verification_url=result["verification_url"],
    )

    return SuccessResponse(
        data=QRCodeResponse(
            token=result["token"],
            verification_url=result["verification_url"],
            qr_image_url=f"/api/v1/qr/{result['token']}/image",
        ),
        message="QR code generated successfully",
    )


# ─── GET /{token}/image ──────────────────────────────────────────────────────


@router.get("/{token}/image")
async def get_qr_image(token: str):
    """
    Serve QR code PNG image (public, no auth required).

    The opaque token acts as access control.
    """
    image_path = get_qr_image_path(token)

    if not image_path.exists():
        raise QRTokenNotFoundError()

    return FileResponse(
        path=str(image_path),
        media_type="image/png",
    )
