# backend/schemas/qr_schemas.py
# QR code generation and access schemas.
#
# Architecture Reference: docs/backend.md Section 17 (QR Verification Service)
# Endpoint: docs/backend.md Section 28.1 lines 3488-3490
# Response: { token, verification_url, qr_image_url }
# Directory: docs/backend.md Section 27.1 (schemas/qr_schemas.py)

from __future__ import annotations

from pydantic import BaseModel


class QRCodeResponse(BaseModel):
    """
    QR code generation response.

    Docs Section 28.1 (POST /qr/generate/{certificate_id}):
    Returns: QRCodeResponse { token, verification_url, qr_image_url }
    """

    token: str
    verification_url: str
    qr_image_url: str
